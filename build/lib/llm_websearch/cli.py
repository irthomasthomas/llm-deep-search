"""Command Line Interface definitions for llm_websearch."""

import click
import json
import logging
import asyncio
import httpx # Import httpx
from functools import wraps
from typing import Optional, List

# Import core functions and settings.
from .core import search, deep_search
from .config import settings, ConfigError # Import ConfigError
from .models import SearchResult, WebSearchError, LLMError, SearchEngineError # Import custom exceptions

logger = logging.getLogger(__name__)

# Helper to run async functions from Click commands
def run_async(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Ensure the logger is configured before running anything if not done globally
        if not logging.getLogger('llm_websearch').hasHandlers():
             log_level_name = settings.log_level.upper()
             # Use force=True to reconfigure if necessary, useful in plugin contexts
             logging.basicConfig(level=getattr(logging, log_level_name, logging.INFO), force=True)
             logger.info(f"Configured basic logging for llm_websearch (Level: {log_level_name})")

        try:
            # Use asyncio.run() which handles loop creation/closing
            return asyncio.run(func(*args, **kwargs))
        except RuntimeError as e:
            if "cannot run loop while another loop is running" in str(e):
                logger.error("Asyncio loop already running. Cannot execute command asynchronously.")
                click.echo("Error: Cannot run async command (event loop already running).", err=True)
            else:
                 logger.exception(f"Unhandled Runtime Error in async wrapper: {e}")
                 click.echo(f"Error: An unexpected runtime error occurred: {e}", err=True)
        # --- Start Change: More Specific Exception Handling in Wrapper ---
        except ConfigError as cfg_err:
             logger.error(f"Configuration error: {cfg_err}", exc_info=settings.log_level.upper()=="DEBUG")
             click.echo(f"Configuration Error: {cfg_err}", err=True)
             click.echo("Please check your environment variables or llm_websearch_config.yaml.", err=True)
        except SearchEngineError as se_err:
             logger.error(f"Search engine error ({se_err.engine}): {se_err.message}", exc_info=settings.log_level.upper()=="DEBUG")
             click.echo(f"Search Engine Error ({se_err.engine}): {se_err.message}", err=True)
        except LLMError as llm_err:
             logger.error(f"LLM interaction error: {llm_err.message}", exc_info=settings.log_level.upper()=="DEBUG")
             click.echo(f"LLM Error: {llm_err.message}", err=True)
        except WebSearchError as ws_err: # Catch other general plugin errors
             logger.error(f"Plugin execution error: {ws_err}", exc_info=settings.log_level.upper()=="DEBUG")
             click.echo(f"Error: {ws_err}", err=True)
        except httpx.TimeoutException as timeout_err:
             logger.error(f"Network request timed out: {timeout_err}")
             click.echo(f"Error: Network request timed out - {timeout_err}", err=True)
        except httpx.RequestError as http_err:
             logger.error(f"Network request failed: {http_err}")
             click.echo(f"Error: Network request failed - {http_err}", err=True)
        except Exception as e: # Catch-all for truly unexpected errors
            logger.exception(f"An unexpected error occurred during command execution: {e}")
            click.echo(f"An unexpected error occurred: {type(e).__name__}: {e}", err=True)
        # --- End Change ---
    return wrapper

def get_websearch_commands():
    @click.group()
    def websearch():
        """Web search and deep research commands for LLM."""
        pass

    @websearch.command(name="search")
    @click.argument("query")
    @click.option("-n", "num_results", type=int, default=None, help=f"Approx total results (default: {settings.max_results_per_engine * 2}).")
    @click.option("-t", "timeout", type=float, default=None, help=f"Timeout per engine (default: {settings.search_request_timeout})." )
    @click.option("--filter", "use_fast_filter", is_flag=True, default=False, help="Apply fast relevance filtering.")
    @click.option("--verbose", "verbose", is_flag=True, default=False, help="Enable verbose logging.")
    @run_async
    async def search_cmd(query: str, num_results: Optional[int], timeout: Optional[float], use_fast_filter: bool, verbose: bool):
        """Performs a standard web search and prints formatted results."""
        num_results = num_results if num_results is not None else settings.max_results_per_engine * 2
        timeout = timeout if timeout is not None else settings.search_request_timeout
        log_level = logging.DEBUG if verbose else settings.log_level.upper()
        # Configure logging properly via basicConfig or logger setup
        logging.basicConfig(level=log_level if verbose else logging.INFO, force=True)
        logging.getLogger('llm_websearch').setLevel(log_level)
        logger.debug("Verbose search logging enabled.")
        logger.info(f"Executing search: '{query}' (Num Results={num_results}, Timeout={timeout}, Fast Filter={use_fast_filter})")

        # Errors caught by run_async wrapper
        results: List[SearchResult] = await search(
            query, num_results=num_results, timeout=timeout, use_fast_filter=use_fast_filter
        )

        if not results:
            click.echo(f"No results found for: '{query}'")
            return

        click.echo(f"Found {len(results)} results:{chr(10)}")
        for i, r in enumerate(results, 1):
            title = getattr(r, 'title', 'N/A'); url_obj = getattr(r, 'url', 'N/A')
            url_str = str(url_obj) if url_obj else 'N/A'; snippet = getattr(r, 'snippet', 'N/A')
            engine = getattr(r, 'engine', 'N/A')
            rank = r.metadata.get('rank', 'N/A') if hasattr(r, 'metadata') and isinstance(r.metadata, dict) else 'N/A'
            relevance = r.relevance_score if hasattr(r, 'relevance_score') and r.relevance_score is not None else None

            click.echo(f"{i}. **{title}**")
            click.echo(f"   URL: {url_str}")
            click.echo(f"   Source: {engine.capitalize()} (Rank: {rank})")
            if relevance is not None: click.echo(f"   Relevance Score: {relevance:.2f}")
            if snippet:
                snippet_lines = snippet.splitlines()
                indented_snippet = chr(10).join([f"   > {line}" for line in snippet_lines])
                click.echo(indented_snippet)
            click.echo("---")


    @websearch.command(name="deep-search")
    @click.argument("query")
    @click.option("-n", "num_results", type=int, default=None, help=f"Results per iteration (default: {settings.max_results_per_engine}).")
    @click.option("-t", "timeout", type=float, default=None, help=f"General timeout (default: {settings.request_timeout_general}).")
    @click.option("-i", "max_iterations", type=int, default=None, help=f"Max iterations (default: {settings.deep_search_max_iterations}).")
    @click.option("-f", "format_type", type=click.Choice(['compact', 'summary', 'full'], case_sensitive=False), default='summary', help="Output format (compact, summary, full).")
    @click.option("--verbose", "verbose", is_flag=True, default=False, help="Enable verbose logging.")
    @run_async
    async def deep_search_cmd(query: str, num_results: Optional[int], timeout: Optional[float], max_iterations: Optional[int], format_type: str, verbose: bool):
        """Performs a deep iterative web search and prints formatted results."""
        num_results = num_results if num_results is not None else settings.max_results_per_engine
        timeout = timeout if timeout is not None else settings.request_timeout_general
        max_iterations = max_iterations if max_iterations is not None else settings.deep_search_max_iterations
        log_level = logging.DEBUG if verbose else settings.log_level.upper()
        logging.basicConfig(level=log_level if verbose else logging.INFO, force=True) # Ensure logging level is set
        logging.getLogger('llm_websearch').setLevel(log_level)
        logger.debug("Verbose deep-search logging enabled.")
        logger.info(f"Executing deep-search: '{query}' (Num Results/Iter={num_results}, Timeout={timeout}, Max Iter={max_iterations}, Format={format_type})")

        # Errors caught by run_async wrapper
        result_output = await deep_search(
            query, num_results=num_results, timeout=timeout, max_iterations=max_iterations, format_type=format_type
        )

        # Print output or handle error dict returned by deep_search
        if isinstance(result_output, str):
            click.echo(result_output)
        elif isinstance(result_output, dict) and result_output.get("status") == "Failed":
            logger.warning(f"Deep search process reported failure: {result_output.get('error_message')}")
            # Wrapper likely printed the error already. Optionally add context:
            # click.echo("Deep search failed.", err=True)
            if "partial_result_status" in result_output:
                 click.echo(f"(Partial Status: {result_output['partial_result_status']})", err=True)
        else:
            # Fallback for unexpected return types
            logger.error(f"Deep search returned unexpected type: {type(result_output)}. Attempting JSON dump.")
            try:
                 click.echo(json.dumps(result_output, indent=2, default=str))
            except Exception as json_err:
                 logger.error(f"Fallback JSON serialization failed: {json_err}")
                 # --- Start Change: Use chr(10) in f-string ---
                 nl = chr(10)
                 click.echo(f"Warning: Could not serialize result. Type: {type(result_output)}{nl}Raw Result:{nl}{result_output}", err=True)
                 # --- End Change ---

    return websearch