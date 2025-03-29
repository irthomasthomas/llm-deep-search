"""Core functionality for LLM-powered web search and deep research."""

import logging
import json
import os
from typing import List, Dict, Any, Optional, Union
from diskcache import Cache
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from .deep_research import DeepResearcher
from .result_formatter import ResearchResultFormatter, FormatType, FormatOptions
from .llm_integration import LLMIntegration
from .query_expansion import QueryExpander
from .fast_filter import FastFilter
from .detailed_analysis import DetailedAnalyzer
from .summarization import Summarizer, SummarizationResult

# Configuration
CACHE_DIR = os.getenv("CACHE_DIR", "/tmp/llm_websearch_cache")
DEFAULT_LLM_MODEL = "gemini-2"  # Default model
MAX_ITERATIONS = 3  # Maximum iterations for deep search

# Initialize cache
cache = Cache(CACHE_DIR)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SearchResult:
    """Class to represent a single search result."""
    def __init__(self, url: str, title: str, snippet: str, rank: int, source: str = "unknown"):
        self.url = url
        self.title = title
        self.snippet = snippet
        self.rank = rank
        self.source = source

class SearchError(Exception):
    """Custom exception for search failures."""
    pass

def search(query: str, num_results: int = 10, timeout: float = 10.0, fast_filter: Optional[FastFilter] = None) -> List[SearchResult]:
    """
    Perform a web search for the given query.
    
    Args:
        query: The search query string
        num_results: Number of results to fetch
        timeout: Timeout for search requests in seconds
        fast_filter: Optional FastFilter to filter results
        
    Returns:
        List of SearchResult objects
    """
    logger.info(f"Performing search for query: '{query}', num_results: {num_results}")
    
    # This would typically call Google and Bing search APIs
    # For now, we'll just return mock results
    mock_results = []
    for i in range(min(num_results, 20)):
        mock_results.append(SearchResult(
            url=f"https://example.com/result{i+1}",
            title=f"Mock Result {i+1} for '{query}'",
            snippet=f"This is a mock search result about {query}. It contains information that would be relevant to the query.",
            rank=i,
            source="mock"
        ))
    
    # Apply fast filtering if available
    if fast_filter and mock_results:
        try:
            # Extract snippets for filtering
            snippets = [result.snippet for result in mock_results if hasattr(result, 'snippet')]
            filtered_results = fast_filter.filter_batch(snippets, query)
            
            # Match filtered snippets back to original results
            if filtered_results:
                filtered_indices = []
                for filter_result in filtered_results:
                    for i, result in enumerate(mock_results):
                        if hasattr(result, 'snippet') and result.snippet == filter_result.content:
                            filtered_indices.append(i)
                            break
                
                # Keep only the filtered results
                mock_results = [mock_results[i] for i in filtered_indices]
            else:
                logger.warning(f"Fast filter removed all results, keeping original results")
        except Exception as e:
            logger.error(f"Error during fast filtering: {e}")
    
    return mock_results[:num_results]

def deep_search(query: str, num_results: int = 10, timeout: float = 30.0, max_iterations: int = MAX_ITERATIONS, 
                format_type: str = "summary", relevance_threshold: float = 0.7, 
                diminishing_returns_threshold: float = 0.2) -> Dict[str, Any]:
    """
    Performs a deep, iterative search that explores a topic in depth.
    
    Args:
        query: The search query
        num_results: Number of results to fetch per query
        timeout: Timeout for requests in seconds
        max_iterations: Maximum number of iterative search rounds
        format_type: Output format (compact, summary, full)
        relevance_threshold: Minimum relevance score to continue exploring a path
        diminishing_returns_threshold: Threshold for pruning paths with diminishing returns
        
    Returns:
        A dictionary with the formatted research results
    """
    logger.info(f"Performing deep search for query: '{query}', format: {format_type}")

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

    # Initialize DeepResearcher with custom functions and components
    researcher = DeepResearcher(
        search_function=search_function,
        max_iterations=max_iterations,
        max_branching=3,
        relevance_threshold=relevance_threshold,
        diminishing_returns_threshold=diminishing_returns_threshold,
        llm_integration=llm_integration,
        detailed_analyzer=detailed_analyzer
    )
    
    # Run the deep research
    try:
        # Perform the research
        research_result = researcher.research(expanded_query)
        
        # Initialize Summarizer
        summarizer = Summarizer(
            llm_integration=llm_integration,
            cache_instance=cache,
            short_summary_length=75,
            medium_summary_length=200,
            long_summary_length=500
        )
        
        # Generate summaries
        summary_data = summarizer.summarize_research_result(research_result)
        
        # Format the results
        format_type_enum = FormatType.SUMMARY  # Default
        if format_type.lower() == "compact":
            format_type_enum = FormatType.COMPACT
        elif format_type.lower() == "full":
            format_type_enum = FormatType.FULL
        
        options = FormatOptions(
            include_metadata=True,
            max_findings=None,
            confidence_threshold=0.6,
            include_exploration_paths=(format_type_enum == FormatType.FULL)
        )
        
        formatter = ResearchResultFormatter(format_type=format_type_enum, options=options)
        formatted_result = formatter.format_result(research_result)
        
        # Add summary data to formatted output
        formatted_result["tiered_summaries"] = summary_data.get("tiered_summaries", {})
        formatted_result["key_insights"] = summary_data.get("key_insights", [])
        formatted_result["exploration_parameters"] = {
            "relevance_threshold": relevance_threshold,
            "diminishing_returns_threshold": diminishing_returns_threshold,
            "max_iterations": max_iterations
        }
        
        return formatted_result
        
    except Exception as e:
        logger.error(f"Error during deep research: {e}")
        return {
            "error": str(e),
            "query": query
        }
