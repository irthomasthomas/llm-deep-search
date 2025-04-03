"""Core orchestrator for llm-websearch plugin, handling search and deep research flows."""

import asyncio
import json
import logging
import dataclasses
from pathlib import Path
from typing import List, Dict, Optional, Any, Coroutine, Tuple, Union

# Internal imports
from .models import SearchResult, LLMResponse, SearchEngineError, WebSearchError, ResearchResult, ConfigError # Added ConfigError
from .components.detailed_analysis import DetailedAnalysis, DetailedAnalyzer
from .config import settings
from .utils import cache, get_limiter
from .search_engines import google_search, bing_search
from .components.llm_integration import LLMIntegration
from .components.fast_filter import FastFilter
from .components.query_expansion import QueryExpander
from .components.summarization import Summarizer
from .components.deep_research import DeepResearcher
from .content_processing import (
    fetch_and_summarize,
    extract_themes,
    _generate_llm_subqueries,
    ResearchResultFormatter, FormatType, FormatOptions
)

logger = logging.getLogger(__name__)

# --- Refactored Deep Search Helper Functions ---

# --- Start Change: Removed try...except, let errors propagate ---
def _initialize_deep_search_components(cache_instance: Optional[Any]) -> Tuple[LLMIntegration, QueryExpander, DetailedAnalyzer, Summarizer]:
    """Initializes components required for deep search."""
    logger.debug("Initializing deep search components...")
    llm_integration = LLMIntegration(cache_instance=cache_instance)
    query_expander = QueryExpander(llm_integration=llm_integration, cache_instance=cache_instance)
    detailed_analyzer = DetailedAnalyzer(llm_integration=llm_integration, cache_instance=cache_instance)
    summarizer = Summarizer(llm_integration=llm_integration, cache_instance=cache_instance)
    logger.debug("Deep search components initialized.")
    return llm_integration, query_expander, detailed_analyzer, summarizer
# --- End Change ---

async def _expand_query(original_query: str, query_expander: QueryExpander) -> str:
    """Expands the query using the QueryExpander component."""
    effective_query = original_query
    try:
        logger.debug(f"Attempting query expansion for: '{original_query}'")
        exp_res = await query_expander.expand_query(original_query)
        if exp_res and exp_res.expanded_queries:
            best_q = exp_res.expanded_queries[0]
            logger.info(f"Expanded '{original_query}' to '{best_q.query}' (confidence: {best_q.confidence:.2f})")
            effective_query = best_q.query
        else:
            logger.info(f"Query expansion did not return results for '{original_query}'. Using original.")
    except Exception as e: # Keep generic catch here as fallback is acceptable
        logger.error(f"Query expansion failed for '{original_query}': {e}. Using original query.", exc_info=True)
    return effective_query

def _define_search_closure(
    num_results: int,
    effective_timeout: float,
    detailed_analyzer: DetailedAnalyzer
) -> callable:
    """Defines the closure function used by DeepResearcher to fetch and analyze results."""
    async def search_fn_closure(current_query: str) -> List[SearchResult]:
        logger.info(f"search_fn_closure called for query: '{current_query}'")
        # Let errors from search() propagate up
        results = await search(current_query, num_results=num_results, timeout=effective_timeout, use_fast_filter=settings.fast_filter_enabled)
        if not results:
            logger.warning(f"search_fn_closure: No results from search for '{current_query}'")
            return []
        try:
            logger.debug(f"search_fn_closure: Starting detailed analysis for {len(results)} results.")
            analysis_results: List[DetailedAnalysis] = await detailed_analyzer.analyze_search_results(results, current_query, timeout=effective_timeout / 2)
            logger.debug(f"search_fn_closure: Detailed analysis returned {len(analysis_results)} results.")

            analysis_map = {}
            for analysis in analysis_results:
                 if hasattr(analysis, 'content') and analysis.content:
                     analysis_map[analysis.content] = analysis

            matched_count = 0
            for res in results:
                snippet = getattr(res, 'snippet', None)
                if snippet and snippet in analysis_map:
                    analysis = analysis_map[snippet]
                    res.metadata = res.metadata or {}
                    res.metadata['analysis'] = dataclasses.asdict(analysis)
                    res.relevance_score = analysis.relevance_score
                    res.key_points = analysis.key_points
                    matched_count += 1
                elif snippet:
                    logger.warning(f"search_fn_closure: No analysis found for snippet: {snippet[:50]}...")
            logger.debug(f"search_fn_closure: Applied analysis metadata to {matched_count} results.")

        except Exception as e: # Catch errors during analysis application phase
            logger.error(f"Detailed analysis apply error in search_fn_closure: {e}", exc_info=True)
            # Return results without analysis in case of error applying it
        return results
    return search_fn_closure

async def _run_research_and_summarize(
    query_to_research: str,
    search_closure: callable,
    llm_integration: LLMIntegration,
    detailed_analyzer: DetailedAnalyzer,
    summarizer: Summarizer,
    max_iterations: int
) -> Optional[ResearchResult]:
    """Initializes and runs the DeepResearcher, then summarizes the result."""
    research_result = None
    # Let exceptions from DeepResearcher/Summarizer propagate
    logger.info("Initializing DeepResearcher...")
    researcher = DeepResearcher(
        search_function=search_closure, llm_integration=llm_integration,
        detailed_analyzer=detailed_analyzer, max_iterations=max_iterations
    )
    logger.info(f"Starting DeepResearcher for query: '{query_to_research}'...")
    research_result = await researcher.research(query_to_research)

    if not research_result:
        raise WebSearchError("DeepResearcher returned no result.") # Raise specific error

    logger.info(f"DeepResearcher completed with status: {research_result.status}")

    if research_result.status != "Failed":
        logger.info("Starting summarization of research result...")
        try:
            summary_data = await summarizer.summarize_research_result(research_result)
            research_result.tiered_summaries = summary_data.get("tiered_summaries", {})
            research_result.key_insights_summary = summary_data.get("key_insights", [])
            logger.info("Summarization complete.")
        except Exception as sum_e:
             # Log and potentially mark result as failed/partial here, but let caller handle reporting
             logger.error(f"Summarization phase failed: {sum_e}", exc_info=True)
             research_result.error_message = (research_result.error_message or "") + f"; Summarization error: {sum_e}"
             research_result.status = "Failed_Summarization"
             # Re-raise or let propagate? Letting it propagate might be better for CLI handling.
             # raise WebSearchError(f"Summarization failed: {sum_e}") from sum_e
    else:
        logger.warning("Skipping summarization because research process failed.")

    return research_result


def _format_output(research_result: ResearchResult, format_type_str: str) -> str:
    """Formats the ResearchResult object into a Markdown string."""
    logger.info(f"Formatting research result (Status: {research_result.status}, Format: {format_type_str}).")
    format_map = {"compact": FormatType.COMPACT, "full": FormatType.FULL}
    fmt_type = format_map.get(format_type_str.lower(), FormatType.SUMMARY)
    opts = FormatOptions(
        include_metadata=True, confidence_threshold=settings.deep_search_relevance_threshold,
        max_findings=7, include_exploration_paths=(fmt_type == FormatType.FULL)
    )
    formatter = ResearchResultFormatter(format_type=fmt_type, options=opts)
    formatted_string = formatter.format_result(research_result)
    logger.debug("Formatting complete.")
    return formatted_string


# --- Refactored Search Helper Functions ---

def _create_search_tasks(query: str, num_google: int, num_bing: int, timeout: float) -> List[Coroutine]:
    """Creates asyncio tasks for configured search engines."""
    tasks: List[Coroutine] = []
    if settings.google_api_key and settings.google_cse_id:
        logger.debug(f"Creating Google search task (n={num_google}, t={timeout})")
        tasks.append(google_search(query, num_google, timeout))
    # else: logger.warning("Google search skipped: API Key/CSE ID missing.") # Already logged in config load

    if settings.bing_api_key and settings.bing_custom_config_id:
        logger.debug(f"Creating Bing search task (n={num_bing}, t={timeout})")
        tasks.append(bing_search(query, num_bing, timeout))
    # else: logger.warning("Bing search skipped: API Key/Custom Config ID missing.") # Already logged

    if not tasks:
        # Raise config error if no engines are usable
        raise ConfigError("No search engines are configured or enabled. Please set API keys/IDs in config or environment.")
    return tasks

async def _process_gathered_results(results_or_errors: List[Any], query: str) -> List[SearchResult]:
    """Processes results from asyncio.gather, separating SearchResults and logging errors."""
    all_results: List[SearchResult] = []
    engine_errors: List[SearchEngineError] = []
    other_errors: List[BaseException] = []

    for res_or_err in results_or_errors:
        if isinstance(res_or_err, SearchEngineError):
            engine_errors.append(res_or_err)
            logger.warning(f"Engine '{res_or_err.engine}' failed query '{res_or_err.query}': {res_or_err.message}")
        elif isinstance(res_or_err, BaseException):
            other_errors.append(res_or_err)
            logger.warning(f"Unexpected search gather error: {res_or_err}", exc_info=res_or_err)
        elif isinstance(res_or_err, list):
            valid_results = [item for item in res_or_err if isinstance(item, SearchResult)]
            if len(valid_results) != len(res_or_err):
                 logger.warning(f"Gather returned list contained non-SearchResult items: {res_or_err}")
            all_results.extend(valid_results)
        else:
            logger.warning(f"Unexpected item type from gather: {type(res_or_err)}")

    if not all_results and (engine_errors or other_errors):
        error_summary = "; ".join([f"{type(e).__name__}: {str(e)[:100]}..." for e in engine_errors + other_errors])
        logger.error(f"All search engines failed for query '{query}'. Errors: {error_summary}")
        # Raise a general error if all engines fail
        raise WebSearchError(f"All search engines failed for query '{query}'. See logs for details.")

    return all_results

def _deduplicate_results(results: List[SearchResult]) -> List[SearchResult]:
    """Deduplicates search results based on normalized URL."""
    seen_urls = set(); unique_results: List[SearchResult] = []
    for res in results:
        url_key = None; raw_url = getattr(res, 'url', None)
        if isinstance(raw_url, str): url_key = raw_url
        elif hasattr(raw_url, 'unicode_string'): url_key = raw_url.unicode_string()
        elif hasattr(raw_url, 'host') and hasattr(raw_url, 'path'): url_key = str(raw_url)
        if url_key:
            url_norm = url_key.strip().rstrip('/'); url_norm_http = url_norm.replace("https://","http://") # Check http/https variations
            if url_norm not in seen_urls and url_norm_http not in seen_urls:
                unique_results.append(res); seen_urls.add(url_norm); seen_urls.add(url_norm_http)
        else: logger.warning(f"Could not extract valid URL for deduplication: {res}")
    logger.info(f"Deduplicated {len(results)} results to {len(unique_results)}.")
    return unique_results

async def _apply_fast_filter(results: List[SearchResult], query: str, cache_instance: Optional[Any]) -> List[SearchResult]:
    """Applies fast filtering to search results if enabled and necessary."""
    if not results or not settings.fast_filter_enabled:
        logger.debug("Skipping fast filter (no results or disabled).")
        return results
    logger.info("Applying fast filter...")
    try:
        # Avoid re-initializing LLMIntegration if possible, pass from caller? For now, new instance.
        llm_integ = LLMIntegration(cache_instance=cache_instance)
        fast_filter = FastFilter(llm_integration=llm_integ)
        filtered_results = await fast_filter.filter_batch(results, query)
        logger.info(f"Fast filter kept {len(filtered_results)}/{len(results)} items.")
        return filtered_results
    except Exception as e: # Catch potential errors during filtering itself
        logger.error(f"Error during fast filtering process: {e}", exc_info=True)
        logger.warning("Returning original results due to fast filter error.")
        return results # Return original results on filter error

def _sort_and_slice_results(results: List[SearchResult], num_results: int) -> List[SearchResult]:
    """Sorts results by rank and returns the specified number."""
    def get_rank(r):
        return r.metadata.get('rank', float('inf')) if hasattr(r, 'metadata') and isinstance(r.metadata, dict) else float('inf')
    results.sort(key=get_rank)
    final_results = results[:num_results]
    logger.info(f"Sorted and sliced results, returning {len(final_results)}.")
    return final_results


# --- Main Search Function (Refactored) ---

async def search(query: str, num_results: Optional[int] = None, timeout: Optional[float] = None, use_fast_filter: bool = False) -> List[SearchResult]:
    """Performs a standard web search using configured engines (Refactored)."""
    if num_results is None: num_results = settings.max_results_per_engine * 2
    num_google = num_results // 2 + num_results % 2; num_bing = num_results // 2
    effective_timeout = timeout if timeout is not None else settings.search_request_timeout
    logger.info(f"Core Search (Refactored): '{query}', num={num_results}, timeout={effective_timeout}, filter={use_fast_filter}")

    # Let exceptions from helpers propagate to the CLI wrapper
    tasks = _create_search_tasks(query, num_google, num_bing, effective_timeout)
    if not tasks: return [] # No engines configured
    results_or_errors = await asyncio.gather(*tasks, return_exceptions=True)
    all_results = await _process_gathered_results(results_or_errors, query)
    if not all_results: return [] # No results from any engine
    unique_results = _deduplicate_results(all_results)
    filtered_results = await _apply_fast_filter(unique_results, query, cache) if use_fast_filter else unique_results
    final_results = _sort_and_slice_results(filtered_results, num_results)
    return final_results


# --- Main Deep Search Function (Refactored) ---
async def deep_search(
    query: str, num_results: int = 10, timeout: Optional[float] = None,
    max_iterations: Optional[int] = None, format_type: str = "summary"
) -> Union[str, Dict[str, Any]]:
    """Performs deep search, returning formatted string or error dict."""
    effective_timeout = timeout if timeout is not None else settings.request_timeout_general
    effective_max_iter = max_iterations if max_iterations is not None else settings.deep_search_max_iterations
    logger.info(f"Core Deep Search (Refactored): '{query}', num={num_results}, iter={effective_max_iter}, fmt={format_type}")

    error_output: Dict[str, Any] = {"query": query, "status": "Failed"}
    research_result: Optional[ResearchResult] = None

    try:
        # 1. Initialize Components (Errors propagate)
        llm_integration, query_expander, detailed_analyzer, summarizer = _initialize_deep_search_components(cache)

        # 2. Expand Query (Errors logged, uses original query on failure)
        expanded_query = await _expand_query(query, query_expander)

        # 3. Define Search Closure (Handles internal analysis errors)
        search_closure = _define_search_closure(num_results, effective_timeout, detailed_analyzer)

        # 4. Run Research and Summarization (Errors logged, may return partial result)
        research_result = await _run_research_and_summarize(
            expanded_query, search_closure, llm_integration, detailed_analyzer, summarizer, effective_max_iter
        )

        # 5. Format Output
        if research_result and "Failed" not in research_result.status: # Check for explicit failure status
            formatted_string = _format_output(research_result, format_type)
            logger.info(f"Deep search for '{query}' finished successfully.")
            return formatted_string
        else:
            # Handle failure states or None result
            error_message = "Research process did not complete successfully."
            partial_status = "Unknown"
            if research_result: # If we got a partial/failed result object
                error_message = research_result.error_message or error_message
                partial_status = research_result.status
            else: # If _run_research_and_summarize returned None
                 error_message = "Research process failed to produce any result object."

            logger.error(f"Deep search failed: {error_message}")
            error_output["error_message"] = error_message
            error_output["partial_result_status"] = partial_status
            return error_output

    # Catch specific errors from core operations (like component init)
    except (ConfigError, WebSearchError, LLMError, SearchEngineError) as e:
        logger.error(f"Deep search failed due to {type(e).__name__}: {e}", exc_info=False)
        error_output["error_message"] = f"{type(e).__name__}: {e}"
        if research_result: error_output["partial_result_status"] = research_result.status
        return error_output
    except Exception as e: # Catch truly unexpected errors
        logger.exception(f"Critical unexpected error during deep search for '{query}': {e}")
        error_output["error_message"] = f"Critical unexpected error: {e}"
        if research_result: error_output["partial_result_status"] = research_result.status
        return error_output
