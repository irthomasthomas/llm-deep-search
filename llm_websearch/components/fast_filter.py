"""Fast filtering module for initial content relevance assessment."""

from typing import List, TYPE_CHECKING, Optional
import asyncio
from dataclasses import dataclass
import time
import logging
import re

# Internal imports
from ..models import SearchResult, LLMResponse, LLMError, ParsingError # Import necessary exceptions
from ..config import settings
from ..utils import cache, _cache_key, get_limiter

if TYPE_CHECKING:
    from .llm_integration import LLMIntegration

logger = logging.getLogger(__name__)

@dataclass
class FilterScore:
    """Container for relevance score and metadata."""
    search_result: 'SearchResult'
    relevance_score: float
    confidence: float
    filtering_time: float


class FastFilter:
    """Fast filtering system using lightweight LLMs (Now Async)"""

    def __init__(
        self,
        threshold: Optional[float] = None, # Allow override via init
        max_workers: Optional[int] = None,
        lightweight_model: Optional[str] = None,
        llm_integration: Optional['LLMIntegration'] = None,
    ):
        self.threshold = threshold if threshold is not None else settings.fast_filter_threshold
        self.max_concurrent_tasks = max_workers if max_workers is not None else settings.max_concurrent_requests
        self.model = lightweight_model if lightweight_model is not None else settings.fast_filter_model
        self.llm_integration = llm_integration
        logger.debug(f"FastFilter (Async) initialized. Threshold: {self.threshold}, LLM integration: {'Yes' if llm_integration else 'No'}")

    async def _score_content(self, content_obj: 'SearchResult', query: str) -> FilterScore:
        """Score individual SearchResult object for relevance (Async)"""
        start_time = time.time()
        score = 0.0
        confidence = 0.0
        newline = chr(10)

        title = content_obj.title or ""
        snippet = content_obj.snippet or ""
        text_to_score = f"{title}{newline}{snippet}".strip()[:settings.fast_filter_max_chars]

        if not text_to_score:
             logger.warning(f"Skipping scoring for SearchResult with no title/snippet: {content_obj.url}")
             return FilterScore(search_result=content_obj, relevance_score=0.0, confidence=0.0, filtering_time=time.time() - start_time)

        llm_used = False
        if self.llm_integration:
            logger.debug(f"Attempting LLM scoring for: {content_obj.url}")
            try:
                prompt = f"""Evaluate the relevance of the following content summary to the search query.

Search Query: "{query}"

Content Summary (Title and Snippet):
{text_to_score}

Return only a single floating-point number between 0.0 and 1.0, where 0.0 means completely irrelevant and 1.0 means highly relevant."""
                system_prompt = "You are a relevance scoring system. Respond with only a single numerical value between 0.0 and 1.0."

                response = await self.llm_integration.generate_response(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    task_type="relevance_scoring",
                    requested_model=self.model,
                    required_capabilities=[],
                )
                # If generate_response succeeded (no exception), attempt to parse
                llm_used = True
                # --- Start Change: Removed 'if not response.error:' ---
                try:
                    score_text = re.sub(r"[^0-9.-]", "", response.raw_text)
                    score = float(score_text)
                    score = max(0.0, min(1.0, score))
                    confidence = getattr(response, 'confidence_score', 0.8)
                    logger.debug(f"LLM scored {content_obj.url}: {score:.2f} (Confidence: {confidence:.2f})")
                    return FilterScore(
                        search_result=content_obj, relevance_score=score, confidence=confidence, filtering_time=time.time() - start_time
                    )
                except (ValueError, TypeError) as parse_err:
                    logger.warning(f"Could not parse LLM relevance score '{response.raw_text}'. Error: {parse_err}. Falling back.")
                    llm_used = False # Trigger fallback
                # --- End Change ---

            except (LLMError, ParsingError) as llm_e:
                logger.warning(f"LLM relevance scoring failed for {content_obj.url}. Falling back. Error: {llm_e}")
                llm_used = False
            except Exception as e:
                logger.exception(f"Unexpected error during LLM relevance scoring for {content_obj.url}. Falling back. Error: {e}")
                llm_used = False

        # Fallback: simple keyword matching approach
        if not llm_used:
            logger.debug(f"Using fallback keyword scoring for: {content_obj.url}")
            try:
                 query_terms = query.lower().split()
                 content_lower = text_to_score.lower()
                 if any(term in content_lower for term in query_terms):
                     score = 0.6
                     confidence = 0.7
                 else:
                     score = 0.1
                     confidence = 0.5
            except Exception as e:
                 logger.exception(f"Error during keyword matching fallback for {content_obj.url}. Error: {e}")
                 score = 0.0
                 confidence = 0.0
            logger.debug(f"Keyword scored {content_obj.url}: {score:.2f}")

        return FilterScore(
            search_result=content_obj, relevance_score=score, confidence=confidence, filtering_time=time.time() - start_time
        )

    async def filter_batch(self, contents: List['SearchResult'], query: str) -> List['SearchResult']:
        """Filter a batch of SearchResult objects in parallel using asyncio."""
        logger.info(f"Starting async fast filter batch for {len(contents)} items.")
        filtered_results = []
        tasks = []

        semaphore = asyncio.Semaphore(self.max_concurrent_tasks)
        async def score_with_semaphore(content_obj):
             async with semaphore:
                 return await self._score_content(content_obj, query)

        for content_obj in contents:
            tasks.append(asyncio.create_task(score_with_semaphore(content_obj)))

        processed_count = 0
        for future in asyncio.as_completed(tasks):
            try:
                score_result = await future
                processed_count += 1
                if score_result:
                    logger.debug(f"Filter score for {score_result.search_result.url}: {score_result.relevance_score:.2f} (Threshold: {self.threshold})")
                    if score_result.relevance_score >= self.threshold:
                        score_result.search_result.relevance_score = score_result.relevance_score
                        filtered_results.append(score_result.search_result)
            except Exception as exc:
                logger.exception(f"Error processing filter future: {exc}")

        logger.info(f"Async fast filter batch completed. Processed {processed_count}/{len(contents)}. {len(filtered_results)} items passed threshold.")
        return filtered_results

    async def filter_stream(self, content_stream, query: str):
        """Filter content as it streams in (ASSUMES stream yields SearchResult objects)"""
        logger.warning("filter_stream assumes input is SearchResult objects, adjust if necessary.")
        async for content_obj in content_stream:
            if not isinstance(content_obj, SearchResult):
                 logger.error(f"filter_stream received non-SearchResult object: {type(content_obj)}")
                 continue
            result = await self._score_content(content_obj, query)
            if result.relevance_score >= self.threshold:
                yield result.search_result
