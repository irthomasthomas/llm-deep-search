import click
import llm
import httpx
import os
import json
import logging
from typing import List, Dict, Optional, Callable
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed
from diskcache import Cache
import hashlib
from datetime import timedelta
from bs4 import BeautifulSoup
import time
import threading
from functools import wraps, lru_cache
import subprocess
import asyncio

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration
GOOGLE_SEARCH_KEY = os.getenv("GOOGLE_SEARCH_KEY")
GOOGLE_SEARCH_ID = os.getenv("GOOGLE_SEARCH_ID")
BING_SEARCH_API_KEY = os.getenv("BING_SEARCH_API_KEY") or os.getenv("BING_SUBSCRIPTION_KEY")
MAX_RESULTS = 100
DEFAULT_NUM_RESULTS = 10
CACHE_DIR = os.getenv("CACHE_DIR", "/tmp/llm_websearch_cache")
CACHE_EXPIRATION = timedelta(hours=24)
DEFAULT_LLM_MODEL = "gemini-2"  # You can change this to your preferred model
MAX_RETRIES = 3
RETRY_DELAY = 1  # Initial delay in seconds
MAX_ITERATIONS = 3  # Maximum number of iterative search rounds

# Rate limiting configuration
GOOGLE_RATE_LIMIT = 10  # requests per second
BING_RATE_LIMIT = 3  # requests per second

# Initialize cache
cache = Cache(CACHE_DIR)

# Global headers
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3",
    "Accept-Language": "en-US,en;q=0.9",
}

class SearchError(Exception):
    """Custom exception for search failures."""
    pass

class SearchResult:
    def __init__(self, url: str, title: str, snippet: str, rank: int, source: str):
        self.url = url
        self.title = title
        self.snippet = snippet
        self.rank = rank
        self.source = source

class ProcessedResult:
    def __init__(self, url: str, title: str, summary: str, source: str):
        self.url = url
        self.title = title
        self.summary = summary
        self.source = source

class RateLimiter:
    def __init__(self, rate: int):
        self.rate = rate
        self.tokens = rate
        self.last_refill = time.time()
        self.lock = threading.Lock()

    def acquire(self):
        with self.lock:
            now = time.time()
            time_passed = now - self.last_refill
            self.tokens = min(self.rate, self.tokens + time_passed * self.rate)
            self.last_refill = now

            if self.tokens < 1:
                return False
            self.tokens -= 1
            return True

def rate_limited(rate_limiter: RateLimiter):
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            while not rate_limiter.acquire():
                time.sleep(0.1)
            return func(*args, **kwargs)
        return wrapper
    return decorator

google_rate_limiter = RateLimiter(GOOGLE_RATE_LIMIT)
bing_rate_limiter = RateLimiter(BING_RATE_LIMIT)

def _mock_search_results(query: str, num_results: int = 10) -> List[Dict]:
    """Provides mock search results for fallback."""
    logger.debug(f"Generating mock results for query: {query}")
    results = []
    for i in range(num_results):
        results.append({
            "title": f"Mock Result {i} for '{query}'",
            "url": f"https://mock.example.com/{i}",
            "snippet": f"This is a mock result {i} for the query '{query}'.",
            "source": "mock"
        })
    return results

def _cache_key(func_name: str, *args, **kwargs) -> str:
    """Generate a cache key based on function name and arguments."""
    key = f"{func_name}:{args}:{kwargs}"
    return hashlib.md5(key.encode()).hexdigest()

@rate_limited(google_rate_limiter)
def google_search(query: str, num_results: int = 10, timeout: float = 10.0) -> List[SearchResult]:
    """Performs a Google search using the Custom Search JSON API with retries."""
    cache_key = _cache_key("google_search", query, num_results, timeout)
    cached_result = cache.get(cache_key)
    if cached_result:
        logger.info(f"Using cached results for Google search: {query}")
        return cached_result

    if not GOOGLE_SEARCH_KEY or not GOOGLE_SEARCH_ID:
        raise SearchError("GOOGLE_SEARCH_KEY and GOOGLE_SEARCH_ID must be set.")

    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "key": GOOGLE_SEARCH_KEY,
        "cx": GOOGLE_SEARCH_ID,
        "q": query,
        "num": min(num_results, 10),  # API allows max 10 results per request
    }

    results = []
    for attempt in range(MAX_RETRIES):
        try:
            with httpx.Client(timeout=timeout, follow_redirects=True, headers=HEADERS) as client:
                while len(results) < num_results:
                    response = client.get(url, params=params)
                    response.raise_for_status()
                    data = response.json()

                    if "items" in data:
                        for rank, item in enumerate(data["items"], start=len(results)):
                            results.append(SearchResult(
                                url=item["link"],
                                title=item["title"],
                                snippet=item.get("snippet", ""),
                                rank=rank,
                                source="google"
                            ))

                        if "nextPage" not in data["queries"]:
                            break
                        params["start"] = data["queries"]["nextPage"][0]["startIndex"]
                    else:
                        break

            results = results[:num_results]
            cache.set(cache_key, results, expire=CACHE_EXPIRATION.total_seconds())
            return results
        except (httpx.RequestError, httpx.HTTPStatusError) as e:
            logger.warning(f"Attempt {attempt + 1} failed for Google search: {e}")
            if attempt == MAX_RETRIES - 1:
                raise SearchError(f"Google Search API failed after multiple retries: {e}")
            time.sleep(RETRY_DELAY * (2 ** attempt))  # Exponential backoff
        except Exception as e:
            logger.exception(f"An unexpected error occurred during Google search: {e}")
            raise

@rate_limited(bing_rate_limiter)
def bing_search(query: str, num_results: int = 10, timeout: float = 10.0) -> List[SearchResult]:
    """Performs a Bing search using the Bing Web Search API with retries."""
    cache_key = _cache_key("bing_search", query, num_results, timeout)
    cached_result = cache.get(cache_key)
    if cached_result:
        logger.info(f"Using cached results for Bing search: {query}")
        return cached_result

    if not BING_SEARCH_API_KEY:
        raise SearchError("BING_SEARCH_API_KEY must be set.")

    url = "https://api.bing.microsoft.com/v7.0/search"
    headers = {"Ocp-Apim-Subscription-Key": BING_SEARCH_API_KEY}
    params = {
        "q": query,
        "count": min(num_results, 50),  # API allows max 50 results per request
        "offset": 0,
    }

    results = []
    for attempt in range(MAX_RETRIES):
        try:
            with httpx.Client(timeout=timeout, follow_redirects=True, headers=HEADERS) as client:
                while len(results) < num_results:
                    response = client.get(url, headers=headers, params=params)
                    response.raise_for_status()
                    data = response.json()

                    if "webPages" in data and "value" in data["webPages"]:
                        for rank, item in enumerate(data["webPages"]["value"], start=len(results)):
                            results.append(SearchResult(
                                url=item["url"],
                                title=item["name"],
                                snippet=item.get("snippet", ""),
                                rank=rank,
                                source="bing"
                            ))

                        if len(results) >= num_results or len(data["webPages"]["value"]) < params["count"]:
                            break
                        params["offset"] += params["count"]
                    else:
                        break

            results = results[:num_results]
            cache.set(cache_key, results, expire=CACHE_EXPIRATION.total_seconds())
            return results
        except (httpx.RequestError, httpx.HTTPStatusError) as e:
            logger.warning(f"Attempt {attempt + 1} failed for Bing search: {e}")
            if attempt == MAX_RETRIES - 1:
                raise SearchError(f"Bing Search API failed after multiple retries: {e}")
            time.sleep(RETRY_DELAY * (2 ** attempt))  # Exponential backoff
        except Exception as e:
             logger.exception(f"An unexpected error occurred during Bing search: {e}")
             raise

def search(query: str, num_results: int = 10, timeout: float = 30.0) -> List[SearchResult]:
    """Performs a web search using Bing and Google, falling back to mock results."""
    logger.info(f"Performing web search for query: {query}, num_results: {num_results}, timeout: {timeout}")
    
    results = []
    errors = []

    with ThreadPoolExecutor(max_workers=2) as executor:
        future_to_engine = {
            executor.submit(google_search, query, num_results, timeout): "Google",
            executor.submit(bing_search, query, num_results, timeout): "Bing"
        }

        for future in as_completed(future_to_engine):
            engine = future_to_engine[future]
            try:
                engine_results = future.result()
                results.extend(engine_results)
                logger.info(f"{engine} search successful for query: {query}")
            except SearchError as e:
                logger.warning(f"{engine} search failed: {e}")
                errors.append(str(e))

    if not results:
        if errors:
            logger.error(f"All searches failed. Errors: {', '.join(errors)}")
        logger.warning("Falling back to mock search results.")
        return _mock_search_results(query, num_results)

    # Deduplicate results based on URL and sort by rank
    unique_results = list({r.url: r for r in results}.values())
    unique_results.sort(key=lambda x: x.rank)

    return unique_results[:num_results]

@lru_cache(maxsize=100)
def fetch_and_summarize(url: str, timeout: float, max_content_length: int = 10000) -> str:
    """Fetches content from a URL, extracts text, and summarizes it using an LLM."""
    cache_key = _cache_key("fetch_and_summarize", url)
    cached_result = cache.get(cache_key)
    if cached_result:
        logger.info(f"Using cached summary for URL: {url}")
        return cached_result
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True, headers=HEADERS) as client:
            response = client.get(url)
            if response.status_code == 403:
                logger.warning(f"Request to {url} returned 403 Forbidden.")
                return f"Error: Access to {url} is forbidden (403 error). Try a different search, or use a different tool to access the content."
            response.raise_for_status()
            content_type = response.headers.get("Content-Type", "")
            if "application/pdf" in content_type.lower():
                return f"Error: URL {url} points to a PDF document. This plugin cannot process PDF content directly. Try searching for an HTML version of this content."
            content = response.content.replace(b'\x00', b'')
            try:
                decoded_content = content.decode('utf-8', errors='replace')
            except UnicodeDecodeError:
                decoded_content = content.decode('latin-1', errors='replace')
            truncated_content = decoded_content[:max_content_length]
            soup = BeautifulSoup(truncated_content, "html.parser")
            text_content = soup.get_text()
            result = subprocess.run(
                [
                    "llm",
                    "prompt",
                    "Summarize the following web page content:\n\n" + text_content,
                    "-m",
                    "gemini-2.0-pro-exp-02-05"
                ],
                capture_output=True,
                text=True,
                check=True
            )
            summary = result.stdout.strip()
            logger.info(f"Summarized {url}: {summary}")
            return summary

    except httpx.RequestError as e:
        logger.error(f"Request error for {url}: {e}")
        return f"Error: Could not fetch content from {url} ({type(e).__name__})."
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error for {url}: {e}")
        return f"Error: HTTP error while fetching {url} ({e.response.status_code})."
    except subprocess.CalledProcessError as e:
        logger.error(f"LLM summarization error for {url}: {e.stderr}")
        return f"Error: Could not summarize content from {url} (LLM error)."
    except Exception as e:
        logger.error(f"General error for {url}: {e}")
        return f"Error: An unexpected error occurred while fetching or summarizing {url} ({type(e).__name__})."

@lru_cache(maxsize=100)
def extract_themes(summaries: str, query: str) -> List[str]:
    """Extracts key themes from a list of summaries using an LLM."""
    if not summaries:
        return []

    prompt = f"""Identify the key themes or topics discussed in the following summaries,
                related to the query: '{query}'.
                Summaries:
{summaries}

Key Themes:"""
    # Use subprocess to call the llm CLI
    try:
        result = subprocess.run(
            ["llm", "-m", DEFAULT_LLM_MODEL, prompt],
            capture_output=True,
            text=True,
            check=True
        )
        themes_text = result.stdout.strip()
        themes = [theme.strip() for theme in themes_text.split("\n") if theme.strip()]
        return themes
    except subprocess.CalledProcessError as e:
        logger.error(f"LLM command failed: {e}")
        return [f"Error: LLM command failed: {e.stderr}"]
    except Exception as e:
        logger.exception(f"An unexpected error occurred while extracting themes: {e}")
        return [f"Error: An unexpected error occurred: {str(e)}"]

@lru_cache(maxsize=100)
def detect_contradictions(summaries: str) -> str:
    """Detects potential contradictions or conflicting viewpoints in summaries."""
    if not summaries:
        return "No contradictions detected (not enough information)."

    prompt = f"""Analyze the following summaries for any conflicting information,
                contradictory statements, or differing viewpoints:
                Summaries:
{summaries}

Contradictions/Conflicts:"""
    # Use subprocess to call the llm CLI
    try:
        result = subprocess.run(
            ["llm", "-m", DEFAULT_LLM_MODEL, prompt],
            capture_output=True,
            text=True,
            check=True
        )
        contradictions = result.stdout.strip()
        return contradictions
    except subprocess.CalledProcessError as e:
        logger.error(f"LLM command failed: {e}")
        return f"Error: LLM command failed: {e.stderr}"
    except Exception as e:
        logger.exception(f"An unexpected error occurred while detecting contradictions: {e}")
        return f"Error: An unexpected error occurred: {str(e)}"

def generate_refined_queries(query: str, summaries: str, themes: List[str]) -> List[str]:
    """Generates refined search queries based on the original query, summaries, and themes."""
    if not summaries:
        return [query]

    prompt = f"""Based on the original query '{query}', the following summaries:
{summaries}
and the identified themes: {', '.join(themes)}.
Generate a list of refined search queries that would help to gather more specific and relevant information. Return ONLY a python list of strings:
"""
     # Use subprocess to call the llm CLI
    try:
        result = subprocess.run(
            ["llm", "-m", DEFAULT_LLM_MODEL, prompt],
            capture_output=True,
            text=True,
            check=True
        )
        refined_queries_text = result.stdout.strip()
        # Attempt to parse the response as a Python list
        try:
            refined_queries = eval(refined_queries_text)
            if not isinstance(refined_queries, list):
                raise ValueError("LLM did not return a list of strings.")
            return refined_queries
        except (SyntaxError, ValueError) as e:
            logger.warning(f"Failed to parse refined queries. LLM response: {refined_queries_text}. Error: {e}")
            return [query]
    except subprocess.CalledProcessError as e:
        logger.error(f"LLM command failed: {e}")
        return [f"Error: LLM command failed: {e.stderr}"]
    except Exception as e:
        logger.exception(f"An unexpected error occurred while generating refined queries: {e}")
        return [f"Error: An unexpected error occurred: {str(e)}"]

def create_overall_summary(summaries: str, query: str) -> str:
    """Creates a comprehensive summary from individual summaries using an LLM."""
    prompt = f"""Create a comprehensive summary based on the following individual summaries,
                        addressing the query: '{query}'.
                        Individual Summaries:
{summaries}"""
    try:
        result = subprocess.run(
            ["llm", "-m", DEFAULT_LLM_MODEL, prompt],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        logger.error(f"LLM command failed: {e}")
        return f"Error: LLM command failed: {e.stderr}"
    except Exception as e:
        logger.exception(f"An unexpected error occurred while creating the overall summary: {e}")
        return f"Error: An unexpected error occurred: {str(e)}"


def deep_search(query: str, num_results: int = 10, timeout: float = 30.0, max_iterations: int = MAX_ITERATIONS) -> Dict:
    """Performs a deep, iterative search using both Google and Bing, and analyzes the results."""
    logger.info(f"Performing deep search for query: '{query}', num_results: {num_results}, timeout: {timeout}, max_iterations: {max_iterations}")

    all_results = []
    all_summaries = []
    all_themes = []
    all_contradictions = []
    all_iterative_results = []

    current_query = query

    for iteration in range(max_iterations):
        logger.info(f"Starting iteration {iteration + 1} for query: '{current_query}'")
        search_results = search(current_query, num_results, timeout)

        with ThreadPoolExecutor(max_workers=min(10, num_results)) as executor:
            future_to_url = {executor.submit(fetch_and_summarize, result.url, timeout): result for result in search_results}
            processed_results = []
            for future in as_completed(future_to_url):
                result = future_to_url[future]
                try:
                    summary = future.result()
                    processed_results.append(ProcessedResult(url=result.url, title=result.title, summary=summary, source=result.source))
                    all_summaries.append(summary)
                except Exception as e:
                    logger.error(f"Error processing {result.url}: {e}")

        all_results.extend(processed_results)

        # Extract summaries and perform analysis
        combined_summaries = " ".join(f"{res.title} ({res.url}):{res.summary}" for res in processed_results)
        with ThreadPoolExecutor(max_workers=3) as executor:
            future_themes = executor.submit(extract_themes, combined_summaries, current_query)
            future_contradictions = executor.submit(detect_contradictions, combined_summaries)
            future_overall_summary = executor.submit(create_overall_summary, combined_summaries, current_query)  # Use the new function

            themes = future_themes.result()
            contradictions = future_contradictions.result()
            overall_summary = future_overall_summary.result()

        all_themes.extend(themes)
        all_contradictions.append(contradictions)


        if iteration < max_iterations - 1:  # Generate refined queries for next iteration, except the last one
            refined_queries = generate_refined_queries(current_query, combined_summaries, themes)

            if refined_queries:  # Select a query to use in the next iteration
                next_query = refined_queries[0]

            # Check if the new query is substantially different from the previous one
            if next_query.lower() == current_query.lower():
                logger.info("Refined query is the same as the previous one. Stopping iterations.")
                break  # Stop if the query is not changing

            logger.info(f"Refined query for next iteration: {next_query}")
            current_query = next_query
        else:  # Last iteration
            logger.info(f"Reached max_iterations ({max_iterations}). Finishing deep search.")


    # Basic iterative search: Use themes as new search queries
    if all_themes:
        logger.info(f"Performing final iterative search based on themes: {all_themes}")
        with ThreadPoolExecutor(max_workers=3) as executor:
            future_to_theme = {
                executor.submit(search, theme, num_results=3, timeout=timeout): theme
                for theme in all_themes[:3]  # Limit the number of theme searches
            }
            for future in as_completed(future_to_theme):
                theme = future_to_theme[future]
                try:
                    theme_results = future.result()
                    all_iterative_results.extend([vars(r) for r in theme_results])
                except Exception as e:
                    logger.error(f"Error during iterative search for theme '{theme}': {e}")

    return {
        "query": query,
        "results": [vars(r) for r in all_results],
        "summary": overall_summary,
        "themes": all_themes,
        "contradictions": all_contradictions,
        "iterative_results": all_iterative_results,
        "analysis": "Further analysis and refinement steps can be added here."
    }

@llm.hookimpl
def register_commands(cli):
    @cli.group()
    def websearch():
        """Web search commands using LLM"""
        pass

    @websearch.command(name="search")
    @click.argument("query", type=str)
    @click.option("-n", "--num-results", type=int, default=DEFAULT_NUM_RESULTS, help="Number of results")
    @click.option("-t", "--timeout", type=float, default=30.0, help="Timeout in seconds")
    @click.option("-v", "--verbose", is_flag=True, help="Enable verbose logging")
    def search_cmd(query, num_results, timeout, verbose):
        """Performs a web search using Bing and Google, falling back to mock results."""
        if verbose:
            logging.getLogger().setLevel(logging.DEBUG)

        try:
            results = search(query, num_results, timeout)
            click.echo(json.dumps([vars(r) for r in results], indent=2))
        except SearchError as e:
            click.echo(f"Error: {e}", err=True)

    @websearch.command(name="deep-search")
    @click.argument("query", type=str)
    @click.option("-n", "--num-results", type=int, default=DEFAULT_NUM_RESULTS, help="Number of results")
    @click.option("-t", "--timeout", type=float, default=30.0, help="Timeout in seconds")
    @click.option("-i", "--iterations", type=int, default=MAX_ITERATIONS, help="Maximum number of search iterations")
    @click.option("-v", "--verbose", is_flag=True, help="Enable verbose logging")
    def deep_search_cmd(query, num_results, timeout, iterations, verbose):
        """Performs a deep search using both Google and Bing, and analyzes the results."""
        if verbose:
            logging.getLogger().setLevel(logging.DEBUG)
        try:
            result = deep_search(query, num_results, timeout, iterations)
            click.echo(json.dumps(result, indent=2))
        except SearchError as e:
            click.echo(f"Error: {e}", err=True)
