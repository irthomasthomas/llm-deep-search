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

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration
GOOGLE_SEARCH_KEY = os.getenv("GOOGLE_SEARCH_KEY")
GOOGLE_SEARCH_ID = os.getenv("GOOGLE_SEARCH_ID")
BING_CUSTOM_SEARCH_KEY = os.getenv("BING_CUSTOM_SEARCH_KEY")
BING_CUSTOM_CONFIG_ID = os.getenv("BING_CUSTOM_CONFIG_ID")
AZURE_REGION = os.getenv("AZURE_REGION")
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

class SearchError(Exception):
    """Custom exception for search failures."""
    pass

class SearchResult:
    """Class to represent a single search result."""
    def __init__(self, url: str, title: str, snippet: str, rank: int, source: str = "unknown"):
        self.url = url
        self.title = title
        self.snippet = snippet
        self.rank = rank
        self.source = source

class ProcessedResult:
    """Class to represent a search result that has been processed (e.g., summarized)."""
    def __init__(self, url: str, title: str, summary: str, source: str = "unknown"):
        self.url = url
        self.title = title
        self.summary = summary
        self.source = source

def _cache_key(prefix: str, *args) -> str:
    """Create a cache key from a prefix and args."""
    key = prefix + ":" + ":".join(str(arg) for arg in args)
    return hashlib.md5(key.encode()).hexdigest()

# Fixed functions with proper llm API usage

def fetch_and_summarize(url: str, query: str, timeout: float = 30.0, model_name: str = DEFAULT_LLM_MODEL) -> str:
    """Fetches content from a URL, extracts text, and summarizes it using an LLM."""
    cache_key = _cache_key("fetch_and_summarize", url, query)
    cached_result = cache.get(cache_key)
    if cached_result:
        logger.info(f"Using cached summary for URL: {url}")
        return cached_result
    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.get(url)
            response.raise_for_status()

            # Extract text content using BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            for script in soup(["script", "style"]):  # Remove script and style elements
                script.extract()
            text = soup.get_text()

            # Clean up whitespace
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ''.join(chunk for chunk in chunks if chunk)

        if not text:
            logger.warning(f"No text content found at URL: {url}")
            return "Error: No text content found."
        
        # Use llm to summarize the content properly using the current API
        prompt_text = f"""Summarize the following text, focusing on information relevant to the query '{query}':

{text[:4000]}"""
        
        # Get the model
        model = llm.get_model(model_name)
        
        # Create the prompt and get the response
        response = model.prompt(prompt_text)
        
        # Get the text of the response
        summary = response.text()
        
        cache.set(cache_key, summary, expire=CACHE_EXPIRATION.total_seconds())
        return summary
        
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error fetching {url}: {e.response.status_code}")
        return f"Error: HTTP {e.response.status_code} when fetching content."
    except httpx.RequestError as e:
        logger.error(f"Error fetching {url}: {e}")
        return f"Error: Failed to fetch content - {str(e)}"
    except Exception as e:
        logger.error(f"An unexpected error occurred while fetching and summarizing {url}: {e}")
        return f"Error: {str(e)}"

def extract_themes(combined_summaries: str, query: str, model_name: str = DEFAULT_LLM_MODEL) -> List[str]:
    """Extract key themes from the summaries."""
    prompt = f"""Based on the following search result summaries, identify the 5 most important themes that are relevant to the query '{query}'.
    
Search Result Summaries:
{combined_summaries}

Key Themes:"""
    
    # Get the model
    model = llm.get_model(model_name)
    
    # Create the prompt and get the response
    response = model.prompt(prompt)
    
    # Process the response
    themes_text = response.text()
    themes = [theme.strip() for theme in themes_text.split("\n") if theme.strip()]
    return themes

def detect_contradictions(combined_summaries: str, model_name: str = DEFAULT_LLM_MODEL) -> str:
    """Detect contradictions or conflicts in the search results."""
    prompt = f"""Analyze the following search result summaries and identify any contradictions or conflicting information:

Search Result Summaries:
{combined_summaries}

Contradictions/Conflicts:"""
    
    # Get the model
    model = llm.get_model(model_name)
    
    # Create the prompt and get the response
    response = model.prompt(prompt)
    
    # Return the text of the response
    return response.text()

def generate_refined_queries(original_query: str, combined_summaries: str, themes: List[str], model_name: str = DEFAULT_LLM_MODEL) -> List[str]:
    """Generate refined search queries based on the results."""
    themes_str = "\n".join([f"- {theme}" for theme in themes])
    prompt = f"""Based on the original query '{original_query}', the following search result summaries, and the key themes identified, 
generate a list of refined search queries that would help to gather more specific and relevant information. Return ONLY a python list of strings:

Original Query: {original_query}

Search Result Summaries:
{combined_summaries}

Key Themes:
{themes_str}

Generate a list of refined search queries that would help to gather more specific and relevant information. Return ONLY a python list of strings:
"""
    
    # Get the model
    model = llm.get_model(model_name)
    
    # Create the prompt and get the response
    response = model.prompt(prompt)
    
    # Get the response text
    refined_queries_text = response.text()
    
    # Attempt to parse the response as a Python list
    try:
        # Try to parse the result as a Python list using eval
        refined_queries = eval(refined_queries_text.strip())
        if not isinstance(refined_queries, list) or not all(isinstance(q, str) for q in refined_queries):
            # Fallback to simple string parsing if the eval didn't return the expected format
            refined_queries = [q.strip() for q in refined_queries_text.split("\n") if q.strip()]
    except Exception:
        # If parsing fails, split by newlines and clean up
        refined_queries = [q.strip() for q in refined_queries_text.split("\n") if q.strip()]
    
    return refined_queries[:5]  # Limit to top 5 refined queries

def rate_limit(limit_per_second: float):
    """Rate limiting decorator."""
    min_interval = 1.0 / limit_per_second
    last_called = [0.0]
    lock = threading.Lock()
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            with lock:
                elapsed = time.time() - last_called[0]
                if elapsed < min_interval:
                    time.sleep(min_interval - elapsed)
                result = func(*args, **kwargs)
                last_called[0] = time.time()
            return result
        return wrapper
    return decorator

@rate_limit(GOOGLE_RATE_LIMIT)
def google_search(query: str, num_results: int = 10, timeout: float = 10.0) -> List[SearchResult]:
    """Perform a Google Custom Search."""
    if not GOOGLE_SEARCH_KEY or not GOOGLE_SEARCH_ID:
        raise SearchError("Google Search API key or Search Engine ID not provided.")
    
    cache_key = _cache_key("google_search", query, num_results)
    cached_result = cache.get(cache_key)
    if cached_result:
        logger.info(f"Using cached Google search results for query: '{query}'")
        return cached_result
    
    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "key": GOOGLE_SEARCH_KEY,
        "cx": GOOGLE_SEARCH_ID,
        "q": query,
        "num": min(num_results, 10),  # Google API limit is 10 per request
    }
    
    results = []
    try:
        with httpx.Client(timeout=timeout) as client:
            for start_index in range(1, min(num_results, MAX_RESULTS) + 1, 10):
                params["start"] = start_index
                response = client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                
                if "items" not in data:
                    break
                
                for i, item in enumerate(data["items"]):
                    results.append(SearchResult(
                        url=item.get("link", ""),
                        title=item.get("title", ""),
                        snippet=item.get("snippet", ""),
                        rank=start_index + i,
                        source="google"
                    ))
                
                if len(results) >= num_results:
                    break
    except httpx.HTTPStatusError as e:
        logger.error(f"Google Search API error: {e.response.status_code}")
        raise SearchError(f"Google Search API error: {e.response.status_code}")
    except httpx.RequestError as e:
        logger.error(f"Google Search request error: {e}")
        raise SearchError(f"Google Search request error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error in Google Search: {e}")
        raise SearchError(f"Unexpected error in Google Search: {e}")
    
    cache.set(cache_key, results, expire=CACHE_EXPIRATION.total_seconds())
    return results[:num_results]

@rate_limit(BING_RATE_LIMIT)
def bing_search(query: str, num_results: int = 10, timeout: float = 10.0) -> List[SearchResult]:
    """Perform a Bing Custom Search."""
    if not BING_CUSTOM_SEARCH_KEY:
        raise SearchError("Bing Custom Search API key not provided.")
    
    cache_key = _cache_key("bing_search", query, num_results)
    cached_result = cache.get(cache_key)
    if cached_result:
        logger.info(f"Using cached Bing search results for query: '{query}'")
        return cached_result
    
    url = f"https://{AZURE_REGION or 'api'}.cognitive.microsoft.com/bing/v7.0/search"
    headers = {"Ocp-Apim-Subscription-Key": BING_CUSTOM_SEARCH_KEY}
    params = {
        "q": query,
        "count": min(num_results, 50),  # Bing API limit
        "responseFilter": "Webpages",
    }
    
    if BING_CUSTOM_CONFIG_ID:
        params["customConfig"] = BING_CUSTOM_CONFIG_ID
    
    results = []
    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            
            if "webPages" in data and "value" in data["webPages"]:
                for i, item in enumerate(data["webPages"]["value"]):
                    results.append(SearchResult(
                        url=item.get("url", ""),
                        title=item.get("name", ""),
                        snippet=item.get("snippet", ""),
                        rank=i,
                        source="bing"
                    ))
    except httpx.HTTPStatusError as e:
        logger.error(f"Bing Search API error: {e.response.status_code}")
        raise SearchError(f"Bing Search API error: {e.response.status_code}")
    except httpx.RequestError as e:
        logger.error(f"Bing Search request error: {e}")
        raise SearchError(f"Bing Search request error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error in Bing Search: {e}")
        raise SearchError(f"Unexpected error in Bing Search: {e}")
    
    cache.set(cache_key, results, expire=CACHE_EXPIRATION.total_seconds())
    return results[:num_results]

def search(query: str, num_results: int = 10, timeout: float = 10.0) -> List[SearchResult]:
    """Perform a combined search using multiple search engines."""
    logger.info(f"Performing search for query: '{query}', num_results: {num_results}")
    
    all_results = []
    errors = []
    
    # Try Google search
    try:
        google_results = google_search(query, num_results // 2 + num_results % 2, timeout)
        all_results.extend(google_results)
    except SearchError as e:
        errors.append(f"Google search error: {str(e)}")
        logger.warning(f"Google search failed: {e}. Continuing with other sources.")
    
    # Try Bing search
    try:
        bing_results = bing_search(query, num_results // 2, timeout)
        all_results.extend(bing_results)
    except SearchError as e:
        errors.append(f"Bing search error: {str(e)}")
        logger.warning(f"Bing search failed: {e}. Continuing with other sources.")
    
    # If all searches failed, provide mock results
    if not all_results:
        if errors:
            logger.error(f"All search engines failed: {'; '.join(errors)}")
        
        logger.warning("Falling back to mock results")
        for i in range(num_results):
            all_results.append({
                "url": f"https://example.com/result{i+1}",
                "title": f"Mock Result {i+1} for '{query}'",
                "snippet": f"This is a mock result because all search engines failed. Pretending to have information about {query}.",
                "rank": i,
                "source": "mock"
            })
    
    # Sort by rank and limit to requested number
    all_results.sort(key=lambda x: x.rank if hasattr(x, 'rank') else x["rank"])
    return all_results[:num_results]

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
            future_to_url = {executor.submit(fetch_and_summarize, result.url, current_query, timeout): result for result in search_results}
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
            
            # Create an overall summary using the fixed API approach
            model = llm.get_model(DEFAULT_LLM_MODEL)
            future_overall_summary = executor.submit(
                lambda: model.prompt(f"""Create a comprehensive summary based on the following individual summaries,
                                    addressing the query: '{current_query}'.
                                    Individual Summaries:
{combined_summaries}""").text()
            )

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
                for theme in all_themes[:3]  # Limit to top 3 themes
            }
            for future in as_completed(future_to_theme):
                theme = future_to_theme[future]
                try:
                    theme_results = future.result()
                    all_iterative_results.extend([
                        {"theme": theme, "url": result.url, "title": result.title, "snippet": result.snippet}
                        for result in theme_results[:3]  # Limit to top 3 results per theme
                    ])
                except Exception as e:
                    logger.error(f"Error running search for theme '{theme}': {e}")

    # Perform final analysis - process overall findings
    model = llm.get_model(DEFAULT_LLM_MODEL)
    overall_analysis = model.prompt(f"""
Given the search query: '{query}'
And based on all the analyzed search results, provide a comprehensive analysis focusing on:
1. Main findings
2. Different perspectives identified
3. Key areas for further exploration
4. Most reliable sources and why
5. Possible limitations in the search results

Please synthesize the information thoughtfully to help the user understand the subject in depth.
""").text()

    # Prepare the final result object
    final_result = {
        "query": query,
        "results": [{"url": r.url, "title": r.title, "summary": r.summary, "source": r.source} for r in all_results],
        "summary": overall_summary,
        "themes": all_themes,
        "contradictions": all_contradictions,
        "iterative_results": all_iterative_results,
        "analysis": overall_analysis
    }

    return final_result

# Plugin hook implementation using the correct decorator
@llm.hookimpl
def register_commands(cli):
    """Add websearch commands to the llm CLI."""
    
    @cli.group(name="websearch")
    def websearch():
        """Web search commands for llm."""
        pass

    @websearch.command(name="search")
    @click.argument("query")
    @click.option("--num-results", "-n", default=DEFAULT_NUM_RESULTS, help="Number of search results to return")
    @click.option("--timeout", "-t", default=30.0, help="Timeout for search requests in seconds")
    @click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
    def search_cmd(query, num_results, timeout, verbose):
        """Performs a web search using both Google and Bing."""
        if verbose:
            logging.getLogger().setLevel(logging.DEBUG) 
        try:
            results = search(query, num_results, timeout)
            for i, result in enumerate(results, 1):
                click.echo(f"{i}. {result.title}")
                click.echo(f"   URL: {result.url}")
                click.echo(f"   Snippet: {result.snippet}")
                click.echo(f"   Source: {result.source}")
                click.echo()
        except SearchError as e:
            click.echo(f"Error: {e}", err=True)
    
    @websearch.command(name="deep-search")
    @click.argument("query")
    @click.option("--num-results", "-n", default=DEFAULT_NUM_RESULTS, help="Number of search results to return")
    @click.option("--timeout", "-t", default=30.0, help="Timeout for search requests in seconds")
    @click.option("--iterations", "-i", default=MAX_ITERATIONS, help="Maximum number of iterative search rounds")
    @click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
    def deep_search_cmd(query, num_results, timeout, iterations, verbose):
        """Performs a deep search using both Google and Bing, and analyzes the results."""
        if verbose:
            logging.getLogger().setLevel(logging.DEBUG)
        try:
            result = deep_search(query, num_results, timeout, iterations)
            click.echo(json.dumps(result, indent=2))
        except SearchError as e:
            click.echo(f"Error: {e}", err=True)

    return websearch
