"""Bing Custom Search Engine interaction using async httpx."""

import httpx
import logging
import asyncio
from typing import List, Optional

# Internal imports
from ..models import SearchResult, SearchEngineError
from ..config import settings
from ..utils import cache, _cache_key, get_limiter  # Import async limiter

logger = logging.getLogger(__name__)


async def bing_search(
    query: str, num_results: Optional[int] = None, timeout: Optional[float] = None
) -> List[SearchResult]:
    """(Async) Perform a Bing Custom Search.

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
    api_key = settings.bing_api_key
    custom_config_id = settings.bing_custom_config_id

    if not api_key or not custom_config_id:
        raise SearchEngineError(
            engine="bing",
            query=query,
            message="Bing API key (BING_API_KEY) or Custom Config ID (BING_CUSTOM_CONFIG_ID) is missing.",
        )

    max_results = (
        num_results if num_results is not None else settings.max_results_per_engine
    )
    request_timeout = (
        timeout if timeout is not None else settings.search_request_timeout
    )
    logger.debug(
        f"Executing Bing Search for '{query}', num_results={max_results}, timeout={request_timeout}"
    )

    # --- Cache Check ---
    cache_key = None
    if cache and settings.cache_enabled:
        cache_key = _cache_key("bing_search", query, max_results)
        try:
            cached_result = await asyncio.to_thread(cache.get, cache_key)
            if cached_result and isinstance(cached_result, list):  # Basic type check
                logger.info(
                    f"Cache hit for Bing Search: '{query}' (max_results={max_results})"
                )
                return cached_result
        except Exception as e:
            logger.warning(f"Cache get failed for Bing search: {e}")

    # --- API Call ---
    # Bing API allows max 50 results per request, uses 'count' and 'offset'
    url = "https://api.bing.microsoft.com/v7.0/custom/search"
    headers = {"Ocp-Apim-Subscription-Key": api_key}
    azure_region = getattr(settings, "azure_region", None)  # Optional Azure region
    if azure_region:
        headers["Ocp-Apim-Subscription-Region"] = azure_region

    results: List[SearchResult] = []
    results_per_page = 50  # Max count for Bing
    offset = 0
    limiter = await get_limiter("bing_search", rate=settings.bing_search_rate)

    try:
        async with httpx.AsyncClient(timeout=request_timeout) as client:
            while len(results) < max_results:
                num_to_fetch = min(results_per_page, max_results - len(results))
                if num_to_fetch <= 0:
                    break

                params = {
                    "q": query,
                    "customConfig": custom_config_id,
                    "count": num_to_fetch,
                    "offset": offset,
                    "responseFilter": "Webpages",  # Ensure we only get web results
                    "safeSearch": "Strict",  # Consider making this configurable
                }
                logger.debug(f"Bing API request: offset={offset}, count={num_to_fetch}")

                async with limiter:
                    response = await client.get(url, headers=headers, params=params)

                response.raise_for_status()  # Raise HTTPStatusError for bad responses (4xx or 5xx)
                data = response.json()

                if (
                    "webPages" not in data
                    or "value" not in data["webPages"]
                    or not data["webPages"]["value"]
                ):
                    logger.debug(
                        f"No more Bing results found for '{query}' at offset {offset}."
                    )
                    break  # No more results

                current_rank_base = offset  # Start ranking from the current offset
                items = data["webPages"]["value"]
                for i, item in enumerate(items):
                    current_rank = (
                        current_rank_base + i + 1
                    )  # Bing rank is usually 1-based
                    result = SearchResult(
                        url=item.get("url", ""),
                        title=item.get("name", ""),
                        snippet=item.get("snippet", ""),
                        query=query,
                        engine="bing",
                        metadata={"rank": current_rank},  # Store rank in metadata
                    )
                    # Basic validation
                    if result.url and result.title:
                        results.append(result)
                        if len(results) >= max_results:
                            break  # Stop if we hit the limit within this page
                    else:
                        logger.warning(f"Skipping incomplete Bing result: {item}")

                if len(results) >= max_results:
                    break  # Stop fetching if we reached the desired number

                # Prepare for next page (if needed)
                offset += len(items)
                estimated_total = data.get("webPages", {}).get(
                    "totalEstimatedMatches", 0
                )
                if offset >= estimated_total and estimated_total > 0:
                    logger.debug(
                        f"Reached estimated total Bing matches ({estimated_total})."
                    )
                    break  # Stop if offset indicates we've seen all estimated matches
                if not items:  # Safety break if value is empty list
                    break

    except httpx.HTTPStatusError as e:
        message = f"Bing API error: {e.response.status_code}"
        try:  # Try to get more specific error message from response
            error_details = e.response.json()
            message += f" - {error_details}"
        except Exception:
            pass  # Ignore if response isn't JSON or parsing fails
        logger.error(
            f"Bing API HTTP error {e.response.status_code} for query '{query}': {message}"
        )
        raise SearchEngineError(
            engine="bing",
            query=query,
            status_code=e.response.status_code,
            message=message,
            original_exception=e,
        ) from e
    except httpx.RequestError as e:
        logger.error(f"Bing API request error for query '{query}': {e}")
        raise SearchEngineError(
            engine="bing",
            query=query,
            message=f"Bing request error: {e}",
            original_exception=e,
        ) from e
    except Exception as e:
        logger.exception(
            f"An unexpected error occurred during Bing search for query '{query}': {e}"
        )
        raise SearchEngineError(
            engine="bing",
            query=query,
            message=f"Unexpected Bing search error: {e}",
            original_exception=e,
        ) from e

    logger.info(f"Bing Search returned {len(results)} results for '{query}'")

    # --- Cache Result ---
    if cache and settings.cache_enabled and cache_key and results:
        try:
            await asyncio.to_thread(
                cache.set, cache_key, results, expire=settings.cache_ttl_seconds
            )
            logger.debug(f"Cached Bing results for key: {cache_key}")
        except Exception as cache_err:
            logger.error(f"Failed to cache Bing results for '{query}': {cache_err}")

    return results[:max_results]  # Return up to the number requested
