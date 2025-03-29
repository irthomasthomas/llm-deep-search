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
    from .llm_integration import LLMIntegration
    from .query_expansion import QueryExpander
    from .fast_filter import FastFilter
    from .detailed_analysis import DetailedAnalyzer
    from .summarization import Summarizer
except ImportError:
    # Fallback for development/testing
    from deep_research import DeepResearcher, ResearchResult
    from result_formatter import ResearchResultFormatter, FormatType, FormatOptions
    from llm_integration import LLMIntegration
    from query_expansion import QueryExpander
    from fast_filter import FastFilter
    from detailed_analysis import DetailedAnalyzer
    from summarization import Summarizer

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

def fetch_and_summarize(url: str, query: str, timeout: float = 30.0, model_name: str = DEFAULT_LLM_MODEL, llm_integration: Optional[LLMIntegration] = None) -> str:
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
        
        # Use LLMIntegration if available, otherwise fallback to direct model usage
        if llm_integration:
            prompt_text = f"""Summarize the following text, focusing on information relevant to the query '{query}':

{text[:4000]}"""
            
            system_prompt = "You are a helpful assistant tasked with summarizing web content. Focus on extracting the most relevant information related to the user's query."
            
            response = llm_integration.generate_response(
                prompt=prompt_text,
                system_prompt=system_prompt,
                task_type="summarization"
            )
            
            summary = response.content
        else:
            # Use llm to summarize the content using the current API
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

def extract_themes(combined_summaries: str, query: str, model_name: str = DEFAULT_LLM_MODEL, llm_integration: Optional[LLMIntegration] = None) -> List[str]:
    """Extract key themes from the summaries."""
    prompt = f"""Based on the following search result summaries, identify the 5 most important themes that are relevant to the query '{query}'.
    
Search Result Summaries:
{combined_summaries}

Key Themes:"""
    
    if llm_integration:
        system_prompt = "You are a helpful assistant tasked with identifying key themes from search results. Extract the most important concepts related to the user's query."
        
        response = llm_integration.generate_response(
            prompt=prompt,
            system_prompt=system_prompt,
            task_type="theme_extraction"
        )
        
        themes_text = response.content
    else:
        # Get the model
        model = llm.get_model(model_name)
        
        # Create the prompt and get the response
        response = model.prompt(prompt)
        
        # Process the response
        themes_text = response.text()
    
    themes = [theme.strip() for theme in themes_text.split("
") if theme.strip()]
    return themes

def detect_contradictions(combined_summaries: str, model_name: str = DEFAULT_LLM_MODEL, llm_integration: Optional[LLMIntegration] = None) -> str:
    """Detect contradictions or conflicts in the search results."""
    prompt = f"""Analyze the following search result summaries and identify any contradictions or conflicting information:

Search Result Summaries:
{combined_summaries}

Contradictions/Conflicts:"""
    
    if llm_integration:
        system_prompt = "You are a helpful assistant tasked with identifying contradictions in search results. Look for statements that conflict with each other."
        
        response = llm_integration.generate_response(
            prompt=prompt,
            system_prompt=system_prompt,
            task_type="contradiction_detection"
        )
        
        return response.content
    else:
        # Get the model
        model = llm.get_model(model_name)
        
        # Create the prompt and get the response
        response = model.prompt(prompt)
        
        # Return the text of the response
        return response.text()

def generate_refined_queries(original_query: str, combined_summaries: str, themes: List[str], model_name: str = DEFAULT_LLM_MODEL, llm_integration: Optional[LLMIntegration] = None) -> List[str]:
    """Generate refined search queries based on the results."""
    themes_str = "
".join([f"- {theme}" for theme in themes])
    prompt = f"""Based on the original query '{original_query}', the following search result summaries, and the key themes identified, 
generate a list of refined search queries that would help to gather more specific and relevant information. Return ONLY a python list of strings:

Original Query: {original_query}

Search Result Summaries:
{combined_summaries}

Key Themes:
{themes_str}

Generate a list of refined search queries that would help to gather more specific and relevant information. Return ONLY a python list of strings:
"""
    
    if llm_integration:
        system_prompt = "You are a helpful assistant tasked with generating refined search queries. Create queries that will help gather more specific and relevant information."
        
        response = llm_integration.generate_response(
            prompt=prompt,
            system_prompt=system_prompt,
            task_type="query_refinement"
        )
        
        refined_queries_text = response.content
    else:
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
            refined_queries = [q.strip() for q in refined_queries_text.split("
") if q.strip()]
    except Exception:
        # If parsing fails, split by newlines and clean up
        refined_queries = [q.strip() for q in refined_queries_text.split("
") if q.strip()]
    
    return refined_queries[:5]  # Limit to top 5 refined queries

def _generate_llm_subqueries(original_query: str, combined_summaries: str, themes: List[str], llm_integration: LLMIntegration) -> List[str]:
    """
    Generate subqueries using LLM integration.
    
    Args:
        original_query: The original search query
        combined_summaries: Text summaries from search results
        themes: List of identified themes
        llm_integration: LLMIntegration instance for generating responses
        
    Returns:
        List of subqueries generated by the LLM
    """
    themes_str = "
".join([f"- {theme}" for theme in themes])
    
    prompt = f"""Based on the original query '{original_query}', the search result summaries, and the identified key themes, 
generate a list of 3-5 specific subqueries that would help explore this topic more deeply.

Original Query: {original_query}

Search Result Summaries:
{combined_summaries}

Key Themes:
{themes_str}

Consider:
1. What specific aspects need deeper exploration?
2. What related concepts should be investigated?
3. What follow-up questions would provide valuable additional context?

Return ONLY a python list of strings representing the subqueries:
"""
    
    system_prompt = """You are a research assistant helping to explore topics deeply. 
Generate specific, focused subqueries that help break down a complex topic into its important components.
Your subqueries should be diverse, covering different angles of the topic.
"""
    
    response = llm_integration.generate_response(
        prompt=prompt,
        system_prompt=system_prompt,
        task_type="subquery_generation",
        required_capabilities=["reasoning"]
    )
    
    # Parse the response into a list of subqueries
    subqueries_text = response.content
    
    # Attempt to parse the response as a Python list
    try:
        # Try to parse the result as a Python list using eval
        subqueries = eval(subqueries_text.strip())
        if not isinstance(subqueries, list) or not all(isinstance(q, str) for q in subqueries):
            # Fallback to simple string parsing if the eval didn't return the expected format
            subqueries = [q.strip() for q in subqueries_text.split("
") if q.strip()]
    except Exception:
        # If parsing fails, split by newlines and clean up
        subqueries = [q.strip() for q in subqueries_text.split("
") if q.strip()]
    
    # Filter out empty strings and limit to 5 subqueries
    subqueries = [q for q in subqueries if q.strip()]
    return subqueries[:5]

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

def search(query: str, num_results: int = 10, timeout: float = 10.0, fast_filter: Optional[FastFilter] = None) -> List[SearchResult]:
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
    
    # Apply fast filtering if available
    if fast_filter and all_results:
        try:
            # Extract snippets for filtering
            snippets = [result.snippet for result in all_results if hasattr(result, 'snippet')]
            filtered_results = fast_filter.filter_batch(snippets, query)
            
            # Match filtered snippets back to original results
            if filtered_results:
                filtered_indices = []
                for filter_result in filtered_results:
                    for i, result in enumerate(all_results):
                        if hasattr(result, 'snippet') and result.snippet == filter_result.content:
                            filtered_indices.append(i)
                            break
                
                # Keep only the filtered results
                all_results = [all_results[i] for i in filtered_indices]
            else:
                logger.warning(f"Fast filter removed all results, keeping original results")
        except Exception as e:
            logger.error(f"Error during fast filtering: {e}")
    
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

    # Initialize LLMIntegration for use across components
    llm_integration = LLMIntegration(cache_instance=cache)
    
    # Create FastFilter instance
    fast_filter = FastFilter(threshold=0.7, lightweight_model="gemini-2.0-flash", llm_integration=llm_integration)
    
    # Initialize QueryExpander
    query_expander = QueryExpander(llm_integration=llm_integration, cache_instance=cache)
    
    # Initialize DetailedAnalyzer
    detailed_analyzer = DetailedAnalyzer(
        relevance_threshold=0.6,
        max_workers=4,
        llm_integration=llm_integration,
        cache_instance=cache
    )
    
    # Try to expand the query
    try:
        expanded_result = query_expander.expand_query(query)
        if expanded_result and expanded_result.expanded_queries:
            # Use the highest confidence expanded query
            best_query = expanded_result.expanded_queries[0]
            logger.info(f"Expanded query '{query}' to '{best_query.query}' (confidence: {best_query.confidence:.2f})")
            expanded_query = best_query.query
        else:
            expanded_query = query
    except Exception as e:
        logger.error(f"Query expansion failed: {e}. Using original query.")
        expanded_query = query

    # Define a search function that will be used by DeepResearcher
    def search_function(search_query):
        results = search(search_query, num_results=num_results, timeout=timeout, fast_filter=fast_filter)
        
        # Use DetailedAnalyzer to enhance the search results
        try:
            # First perform detailed analysis
            analysis_results = detailed_analyzer.analyze_search_results(results, search_query, timeout=timeout/2)
            
            # Enhance search results with detailed analysis
            if analysis_results:
                # Match analysis results back to search results
                for i, result in enumerate(results):
                    if hasattr(result, 'snippet'):
                        for analysis in analysis_results:
                            if analysis.content == result.snippet:
                                # Add analysis metadata to the result
                                result.analysis = analysis
                                result.key_points = analysis.key_points
                                result.relevance_score = analysis.relevance_score
                                break
        except Exception as e:
            logger.error(f"Error during detailed analysis: {e}")
        
        return results

    # Fix the subquery generation function to match the expected interface
    def custom_subquery_generator(query, search_results_content, max_queries=3):
        """Wrapper for _generate_llm_subqueries that matches DeepResearcher's expected interface"""
        themes = extract_themes(search_results_content, query, llm_integration=llm_integration)
        return _generate_llm_subqueries(query, search_results_content, themes, llm_integration)

    # Initialize DeepResearcher with the actual search function and LLM integration
    researcher = DeepResearcher(
        search_function=search_function,
        max_iterations=max_iterations,
        relevance_threshold=0.7,
        generate_subqueries_function=custom_subquery_generator,
        llm_integration=llm_integration
    )
    
    # Monkey-patch the DeepResearcher instance to add the detailed_analyzer
    researcher.detailed_analyzer = detailed_analyzer
    
    # Run the deep research with actual search
    try:
        # Perform the actual research using the search function
        research_result = researcher.research(expanded_query)
        
        # Initialize Summarizer for formatting the final output
        summarizer = Summarizer(
            llm_integration=llm_integration,
            cache_instance=cache,
            short_summary_length=75,
            medium_summary_length=200,
            long_summary_length=500
        )
        
        # Use the enhanced summarize_research_result method
        summary_data = summarizer.summarize_research_result(research_result)
        
        # Add summary data to the research result
        research_result.tiered_summaries = summary_data["tiered_summaries"]
        research_result.key_insights = summary_data["key_insights"]
        
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
        
        # Add tiered summaries and key insights to the formatted result
        formatted_result["tiered_summaries"] = research_result.tiered_summaries
        formatted_result["key_insights"] = research_result.key_insights
        
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
        except Exception as e:
            click.echo(f"Error: {e}", err=True)
    
    @websearch.command(name="deep-search")
    @click.argument("query")
    @click.option("--num-results", "-n", default=DEFAULT_NUM_RESULTS, help="Number of search results to return")
    @click.option("--timeout", "-t", default=30.0, help="Timeout for search requests in seconds")
    @click.option("--iterations", "-i", default=MAX_ITERATIONS, help="Maximum number of iterative search rounds")
    @click.option("--format-type", "-f", type=click.Choice(['compact', 'summary', 'full'], case_sensitive=False), 
                  default='summary', help="Output format to optimize tokens")
    @click.option("--relevance-threshold", "-r", default=0.7, type=float, help="Minimum relevance score to continue exploration")
    @click.option("--diminishing-returns-threshold", "-d", default=0.1, type=float, help="Threshold for determining diminishing returns")
    @click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
    def deep_search_cmd(query, num_results, timeout, iterations, format_type, relevance_threshold, diminishing_returns_threshold, verbose):
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
