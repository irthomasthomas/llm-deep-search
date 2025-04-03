"""Google Custom Search Engine interaction using async httpx."""

import httpx
import logging
import asyncio
from typing import List, Optional

# Internal imports
from ..models import SearchResult, SearchEngineError
from ..config import settings
from ..utils import cache, _cache_key, get_limiter  # Import async limiter

logger = logging.getLogger(__name__)


async def google_search(
    query: str, num_results: Optional[int] = None, timeout: Optional[float] = None
) -> List[SearchResult]:
    """(Async) Perform a Google Custom Search.

    Args:
        query: The search query string.
        num_results: The desired number of results.
        timeout: Request timeout in seconds.

    Returns:
        A list of SearchResult objects.

    Raises:
        SearchEngineError: If the API key/ID is missing or the request fails.
        ConfigError: If required settings are missing.
    """
    api_key = settings.google_api_key
    cse_id = settings.google_cse_id
    if not api_key or not cse_id:
        raise SearchEngineError(
            engine="google",
            query=query,
            message="Google API key (GOOGLE_API_KEY) or CSE ID (GOOGLE_CSE_ID) is missing.",
        )

    max_results = (
        num_results if num_results is not None else settings.max_results_per_engine
    )
    request_timeout = (
        timeout if timeout is not None else settings.search_request_timeout
    )
    logger.debug(
        f"Executing Google Search for '{query}', num_results={max_results}, timeout={request_timeout}"
    )

    # --- Cache Check ---
    cache_key = None
    if cache and settings.cache_enabled:
        cache_key = _cache_key("google_search", query, max_results)
        try:
            cached_result = await asyncio.to_thread(cache.get, cache_key)
            if cached_result and isinstance(cached_result, list):
                logger.info(
                    f"Cache hit for Google Search: '{query}' (max_results={max_results})"
                )
                return cached_result
        except Exception as e:
            logger.warning(f"Cache get failed for Google search: {e}")

    # --- API Call ---
    url = "https://www.googleapis.com/customsearch/v1"
    results: List[SearchResult] = []
    results_per_page = 10  # Google API allows max 10 results per request
    limiter = await get_limiter("google_search", rate=settings.google_search_rate)

    try:
        async with httpx.AsyncClient(timeout=request_timeout) as client:
            for start_index in range(1, max_results + 1, results_per_page):
                num_to_fetch = min(results_per_page, max_results - len(results))
                if num_to_fetch <= 0:
                    break

                params = {
                    "key": api_key,
                    "cx": cse_id,
                    "q": query,
                    "num": num_to_fetch,
                    "start": start_index,
                    "safe": "active",  # Consider making safe search configurable
                }
                logger.debug(
                    f"Google API request: start={start_index}, num={num_to_fetch}"
                )

                async with limiter:
                    response = await client.get(url, params=params)

                response.raise_for_status()  # Raise HTTPStatusError for bad responses (4xx or 5xx)
                data = response.json()

                if "items" not in data:
                    logger.debug(
                        f"No more Google results found for '{query}' starting at index {start_index}."
                    )
                    break  # No more results

                for i, item in enumerate(data["items"]):
                    result = SearchResult(
                        url=item.get("link", ""),
                        title=item.get("title", ""),
                        snippet=item.get("snippet", ""),
                        query=query,
                        engine="google",
                        metadata={
                            "rank": start_index + i
                        },  # Store rank (0-based index within page)
                    )
                    # Basic validation
                    if result.url and result.title:
                        results.append(result)
                    else:
                        logger.warning(f"Skipping incomplete Google result: {item}")

                if len(results) >= max_results:
                    break  # Stop fetching if we reached the desired number

    except httpx.HTTPStatusError as e:
        message = f"Google API error: {e.response.status_code}"
        try:
            message += f" - {e.response.json()}"  # Try to get JSON error body
        except Exception:
            pass
        logger.error(
            f"Google API HTTP error {e.response.status_code} for query '{query}': {message}"
        )
        raise SearchEngineError(
            engine="google",
            query=query,
            status_code=e.response.status_code,
            message=message,
            original_exception=e,
        ) from e
    except httpx.RequestError as e:
        logger.error(f"Google API request error for query '{query}': {e}")
        raise SearchEngineError(
            engine="google",
            query=query,
            message=f"Google request error: {e}",
            original_exception=e,
        ) from e
    except Exception as e:
        logger.exception(
            f"An unexpected error occurred during Google search for query '{query}': {e}"
        )
        raise SearchEngineError(
            engine="google",
            query=query,
            message=f"Unexpected Google search error: {e}",
            original_exception=e,
        ) from e

    logger.info(f"Google Search returned {len(results)} results for '{query}'")

    # --- Cache Result ---
    if cache and settings.cache_enabled and cache_key and results:
        try:
            await asyncio.to_thread(
                cache.set, cache_key, results, expire=settings.cache_ttl_seconds
            )
            logger.debug(f"Cached Google results for key: {cache_key}")
        except Exception as cache_err:
            logger.error(f"Failed to cache Google results for '{query}': {cache_err}")

    return results[:max_results]  # Return up to the number requested
