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
import importlib
import sys

# Force reload to ensure we have the latest version
current_module = sys.modules[__name__]
importlib.reload(current_module)

# Import the components for deep research and token optimization
try:
    from .deep_research import DeepResearcher, ResearchResult
    from .result_formatter import ResearchResultFormatter, FormatType, FormatOptions
except ImportError:
    # Fallback for development/testing
    from deep_research import DeepResearcher, ResearchResult
    from result_formatter import ResearchResultFormatter, FormatType, FormatOptions

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
    if not BING_CUSTOM_SEARCH_KEY or not BING_CUSTOM_CONFIG_ID:
        raise SearchError("Bing Custom Search API key and Config ID must be provided.")
    
    cache_key = _cache_key("bing_search", query, num_results)
    cached_result = cache.get(cache_key)
    if cached_result:
        logger.info(f"Using cached Bing search results for query: '{query}'")
        return cached_result
    
    url = "https://api.bing.microsoft.com/v7.0/custom/search"
    headers = {"Ocp-Apim-Subscription-Key": BING_CUSTOM_SEARCH_KEY}
    if AZURE_REGION:
        headers["Ocp-Apim-Subscription-Region"] = AZURE_REGION
    
    params = {
        "q": query,
        "customconfig": BING_CUSTOM_CONFIG_ID,
        "count": min(num_results, 50),  # Bing API limit
        "offset": 0,
    }
    
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
            all_results.append(SearchResult(
                url=f"https://example.com/result{i+1}",
                title=f"Mock Result {i+1} for '{query}'",
                snippet=f"This is a mock result because all search engines failed. Pretending to have information about {query}.",
                rank=i,
                source="mock"
            ))
    
    # Sort by rank and limit to requested number
    all_results.sort(key=lambda x: x.rank)
    return all_results[:num_results]

def deep_search(query: str, num_results: int = 10, timeout: float = 30.0, max_iterations: int = MAX_ITERATIONS, format_type: str = "summary") -> Dict:
    """
    Performs a deep, iterative search using both Google and Bing, and analyzes the results.
    
    Args:
        query: The search query
        num_results: Number of results to fetch
        timeout: Timeout for each request in seconds
        max_iterations: Maximum number of iterative search rounds
        format_type: The output format type (compact, summary, full)
    
    Returns:
        A dictionary with the formatted research results
    """
    logger.info(f"Performing deep search for query: '{query}', num_results: {num_results}, format: {format_type}")

    # Define a search function that will be used by DeepResearcher
    def search_function(search_query):
        return search(search_query, num_results=num_results, timeout=timeout)

    # Initialize DeepResearcher with the actual search function
    researcher = DeepResearcher(
        search_function=search_function,
        max_depth=max_iterations,
        relevance_threshold=0.7,
        max_workers=4,
        timeout=timeout
    )
    
    # Run the deep research with actual search
    try:
        # Perform the actual research using the search function
        research_result = researcher.research(query)
        
        # Format the results based on requested format type
        format_type_enum = FormatType.SUMMARY  # Default
        if format_type.lower() == "compact":
            format_type_enum = FormatType.COMPACT
        elif format_type.lower() == "full":
            format_type_enum = FormatType.FULL
            
        # Create format options
        options = FormatOptions(
            include_metadata=True,
            max_findings=None,
            confidence_threshold=0.6,
            include_exploration_paths=(format_type_enum == FormatType.FULL)
        )
        
        # Format the results
        formatter = ResearchResultFormatter(format_type=format_type_enum, options=options)
        formatted_result = formatter.format_result(research_result)
        
        # Calculate and add token usage information
        token_counts = {
            FormatType.COMPACT: len(str(formatted_result)) // 4,  # Approximate token count
            FormatType.SUMMARY: len(str(formatted_result)) // 4,
            FormatType.FULL: len(str(formatted_result)) // 4
        }
        formatted_result["token_usage"] = token_counts[format_type_enum]
        
        return formatted_result
        
    except Exception as e:
        logger.error(f"Error during deep research: {e}")
        return {
            "error": str(e),
            "query": query
        }

def get_websearch_commands():
    """Define the websearch commands and return them."""
    
    @click.group()
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
    @click.option("--format-type", "-f", type=click.Choice(['compact', 'summary', 'full'], case_sensitive=False), 
                  default='summary', help="Output format to optimize tokens")
    @click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
    def deep_search_cmd(query, num_results, timeout, iterations, format_type, verbose):
        """Performs a deep search with token-optimized results."""
        if verbose:
            logging.getLogger().setLevel(logging.DEBUG)
        try:
            result = deep_search(query, num_results, timeout, iterations, format_type)
            click.echo(json.dumps(result, indent=2))
        except Exception as e:
            click.echo(f"Error: {e}", err=True)

    return websearch

# Plugin hook implementation
@llm.hookimpl
def register_commands(cli):
    """Add websearch commands to the llm CLI."""
    websearch = get_websearch_commands()
    cli.add_command(websearch)
    return websearch
