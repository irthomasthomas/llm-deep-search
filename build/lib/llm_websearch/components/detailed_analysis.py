"""Detailed content analysis module for Tier 2 processing."""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from datetime import datetime
import time
import hashlib
import asyncio
import logging
import re

# Internal imports
from ..config import settings
from ..models import SearchResult, LLMError, ParsingError, LLMResponse # Import necessary types/exceptions
from ..utils import cache
from .llm_integration import LLMIntegration

logger = logging.getLogger(__name__)

@dataclass
class ContentMetadata:
    """Metadata about analyzed content"""
    word_count: int
    date_detected: Optional[datetime] = None
    language: str = "unknown"
    content_type: str = "unknown"
    quality_score: float = 0.0

@dataclass
class DetailedAnalysis:
    """Container for detailed content analysis results"""
    content: str
    metadata: ContentMetadata
    relevance_score: float = 0.0
    key_points: List[str] = field(default_factory=list)
    citations: List[Dict[str, str]] = field(default_factory=list)
    confidence: float = 0.0
    analysis_time: float = 0.0

class DetailedAnalyzer:
    """Advanced content analysis system (Async)"""

    def __init__(
        self,
        relevance_threshold: Optional[float] = None,
        max_workers: Optional[int] = None,
        llm_integration: Optional[LLMIntegration] = None,
        cache_instance: Optional[Any] = None,
    ):
        """Initialize the detailed analyzer."""
        self.relevance_threshold = relevance_threshold if relevance_threshold is not None else settings.detailed_analysis_relevance_threshold
        self.max_concurrent_tasks = max_workers if max_workers is not None else settings.max_concurrent_requests
        self.llm = llm_integration
        self.cache = cache_instance if cache_instance is not None else cache
        self.analysis_model = settings.detailed_analysis_model
        logger.debug(f"DetailedAnalyzer initialized. Relevance Threshold: {self.relevance_threshold}")

    def _create_cache_key(self, content: str, query: str) -> str:
        """Create a deterministic cache key for content analysis."""
        key_content = f"detailed_analysis:{query}:{content[:1000]}"
        return hashlib.md5(key_content.encode()).hexdigest()

    def extract_metadata(self, content: str) -> ContentMetadata:
        """Extract metadata from content (Synchronous helper method)"""
        word_count = len(content.split())
        language = "en"; content_type = "text/plain"
        quality_score = min(1.0, word_count / 500)
        return ContentMetadata(
            word_count=word_count, date_detected=datetime.now(), language=language,
            content_type=content_type, quality_score=quality_score
        )

    async def extract_key_points(self, content: str, query: str) -> List[str]:
        """(Async) Extract key points from content using LLM if available"""
        newline = chr(10)
        key_points = []

        if self.llm:
            try:
                max_chars = settings.detailed_analysis_max_chars_keypoints
                content_slice = content[:max_chars]
                prompt = f"""Extract key points from the content relevant to "{query}". 3-5 concise bullet points. Content:
{content_slice}"""
                system_prompt = "Extract key points."
                logger.debug(f"Requesting LLM key points (max_chars={max_chars}) for query: {query}")

                # --- Start Change: Removed 'if not response.error' ---
                response = await self.llm.generate_response(
                    prompt=prompt, system_prompt=system_prompt,
                    task_type="key_points_extraction", requested_model=self.analysis_model
                )
                logger.debug("LLM key points response received.")

                # Process response directly, assuming success if no exception raised
                key_points = [
                    point.strip().lstrip("-* ").strip()
                    for point in response.raw_text.split(newline) if point.strip()
                ]
                max_points = 5 # Consider making configurable
                key_points = key_points[:max_points]
                logger.info(f"Extracted {len(key_points)} key points via LLM.")
                # --- End Change ---

            except (LLMError, ParsingError) as e:
                 logger.error(f"LLM error during key points extraction: {e}")
                 # Fall through to fallback logic
            except Exception as e:
                logger.exception(f"Unexpected error extracting key points with LLM: {e}")
                 # Fall through to fallback logic

        # Fallback only if key_points is still empty
        if not key_points:
            logger.warning("Falling back to simple key points extraction.")
            try:
                points = [s.strip() for s in content.split(". ")[:3] if s and len(s.split()) > 5]
                logger.info(f"Extracted {len(points)} key points via fallback.")
                return points
            except Exception as fb_e:
                 logger.exception(f"Error during fallback key points extraction: {fb_e}")
                 return []
        else:
            return key_points

    def extract_citations(self, content: str) -> List[Dict[str, str]]:
        """Extract citations and references (Synchronous helper method)"""
        citations = []; citation_markers = ["cited in", "according to", "as mentioned in", "reference:"]
        newline_char = chr(10)
        for marker in citation_markers:
            try:
                idx = content.lower().find(marker)
                if idx != -1:
                    start = max(0, idx - 50); end = min(len(content), idx + len(marker) + 100)
                    citation_text = content[start:end].strip().replace(newline_char, ' ')
                    citations.append({"text": citation_text, "source": "document", "context": marker})
            except Exception as e: logger.exception(f"Error processing citation marker '{marker}': {e}")
        if not citations:
            default_text = content[:100].replace(newline_char, ' ') + ("..." if len(content) > 100 else "")
            citations.append({"text": default_text, "source": "document", "context": "general"})
        logger.debug(f"Extracted {len(citations)} citation entries.")
        return citations

    async def calculate_relevance(self, content: str, query: str) -> float:
        """(Async) Calculate detailed relevance score using LLM if available"""
        llm_score = None
        if self.llm:
            try:
                max_chars = settings.detailed_analysis_max_chars_relevance
                content_slice = content[:max_chars]
                prompt = f"""Rate relevance of content to query '{query}' from 0.0-1.0. Output ONLY score. Content:
{content_slice}"""
                system_prompt = "Evaluate relevance. Output ONLY numerical score 0.0-1.0."
                logger.debug(f"Requesting LLM relevance calc (max_chars={max_chars}) for query: {query}")

                # --- Start Change: Removed 'if not response.error' ---
                response = await self.llm.generate_response(
                    prompt=prompt, system_prompt=system_prompt,
                    task_type="relevance_analysis", requested_model=self.analysis_model
                )
                logger.debug("LLM relevance calculation response received.")

                # Process response directly, assuming success if no exception raised
                try:
                    score_text = re.sub(r"[^0-9.-]", "", response.raw_text.strip())
                    score = float(score_text)
                    llm_score = max(0.0, min(1.0, score))
                    logger.info(f"Calculated relevance via LLM: {llm_score:.2f}")
                except (ValueError, TypeError) as parse_err:
                     logger.warning(f"Could not parse relevance score '{response.raw_text}'. Error: {parse_err}. Falling back.")
                     # llm_score remains None
                # --- End Change ---

            except (LLMError, ParsingError) as e: logger.warning(f"LLM error during relevance calculation: {e}. Falling back.")
            except Exception as e: logger.exception(f"Unexpected error calculating relevance with LLM: {e}. Falling back.")

        if llm_score is None:
            logger.warning("Falling back to term-based relevance calculation.")
            try:
                query_terms = query.lower().split(); content_lower = content.lower()
                term_matches = sum(1 for term in query_terms if term in content_lower)
                base_score = term_matches / len(query_terms) if query_terms else 0.0
                proximity_bonus = 0.0; final_score = min(1.0, base_score + proximity_bonus)
                logger.info(f"Calculated relevance via fallback: {final_score:.2f}")
                return final_score
            except Exception as e: logger.exception(f"Error during fallback relevance calculation: {e}"); return 0.0
        else: return llm_score

    async def analyze_content(self, content: str, query: str) -> DetailedAnalysis:
        """Perform detailed content analysis (Async)"""
        logger.debug("Starting detailed analysis for content chunk.")
        cached_result = None; cache_key = None
        if self.cache and settings.cache_enabled:
            try:
                cache_key = self._create_cache_key(content, query)
                cached_result = await asyncio.to_thread(self.cache.get, cache_key, default=None)
                if cached_result and isinstance(cached_result, DetailedAnalysis):
                    logger.info(f"Cache hit for detailed analysis: {cache_key}"); return cached_result
                elif cached_result: logger.warning(f"Cache type mismatch for {cache_key}")
                else: logger.debug(f"Cache miss for detailed analysis: {cache_key}")
            except Exception as e: logger.exception(f"Cache check failed: {e}")

        start_time = time.time()
        metadata = self.extract_metadata(content)
        relevance = await self.calculate_relevance(content, query)
        logger.debug(f"Relevance calculated: {relevance:.2f}")

        key_points = []; citations = []
        if relevance >= self.relevance_threshold:
            logger.debug("Relevance threshold met, extracting points/citations.")
            kp_task = asyncio.create_task(self.extract_key_points(content, query))
            citations = self.extract_citations(content) # Keep sync for now
            key_points = await kp_task
        else: logger.debug(f"Relevance {relevance:.2f} below threshold.")

        result = DetailedAnalysis(
            content=content, metadata=metadata, relevance_score=relevance,
            key_points=key_points, citations=citations,
            confidence=0.8 * relevance, analysis_time=time.time() - start_time
        )
        logger.info(f"Detailed analysis completed in {result.analysis_time:.2f}s.")

        if self.cache and settings.cache_enabled and relevance >= self.relevance_threshold and cache_key:
             try:
                logger.debug(f"Setting cache for detailed analysis: {cache_key}")
                await asyncio.to_thread(self.cache.set, cache_key, result, expire=settings.cache_ttl_seconds)
             except Exception as e: logger.exception(f"Cache set failed: {e}")
        return result

    async def analyze_batch(
        self, contents: List[str], query: str, timeout: float = 30.0
    ) -> List[DetailedAnalysis]:
        """Analyze a batch of content in parallel using asyncio."""
        logger.info(f"Starting async batch analysis for {len(contents)} content chunks.")
        start_overall = time.time(); results = []; tasks = set()
        semaphore = asyncio.Semaphore(self.max_concurrent_tasks)

        async def analyze_with_semaphore(content):
             async with semaphore:
                 try:
                     task_timeout = timeout - (time.time() - start_overall)
                     if task_timeout <= 0: return None
                     logger.debug(f"Starting analysis task timeout {task_timeout:.2f}s")
                     return await asyncio.wait_for(self.analyze_content(content, query), timeout=task_timeout)
                 except asyncio.TimeoutError: logger.warning(f"Analysis task timed out: {content[:50]}..."); return None
                 except Exception as e: logger.exception(f"Analysis task failed: {content[:50]}... Error: {e}"); return None

        for content in contents: tasks.add(asyncio.create_task(analyze_with_semaphore(content)))

        processed_count = 0
        for future in asyncio.as_completed(tasks):
             if time.time() - start_overall > timeout:
                 logger.warning(f"Overall batch analysis timeout ({timeout}s) reached.");
                 for task in tasks:
                     if not task.done(): task.cancel()
                 break
             try:
                 result = await future; processed_count += 1
                 if result is not None and result.relevance_score >= self.relevance_threshold: results.append(result)
                 elif result is not None: logger.debug(f"Analysis result below threshold ({result.relevance_score:.2f})")
             except asyncio.CancelledError: logger.warning("Analysis task cancelled.")
             except Exception as e: logger.exception(f"Error retrieving analysis future result: {e}")

        logger.info(f"Async batch analysis finished in {time.time() - start_overall:.2f}s. Processed ~{processed_count}/{len(contents)}. Relevant: {len(results)}.")
        return results

    async def analyze_search_results(
        self, search_results: List[Any], query: str, timeout: float = 30.0
    ) -> List[DetailedAnalysis]:
        """Analyze a batch of search results using the async analyze_batch."""
        logger.info(f"Starting analysis of {len(search_results)} search results for query: '{query}'")
        contents = []; valid_results_count = 0
        for result in search_results:
            content_text = getattr(result, 'processed_content', None) or getattr(result, 'snippet', None)
            if content_text and isinstance(content_text, str):
                contents.append(content_text); valid_results_count += 1
            else: logger.warning(f"Result missing content: {getattr(result, 'url', 'N/A')}")

        if not contents: logger.warning("No content extracted for detailed analysis."); return []
        logger.debug(f"Extracted content from {valid_results_count} results for batch analysis.")
        analysis_results = await self.analyze_batch(contents, query, timeout)
        logger.info(f"Completed analysis, {len(analysis_results)} results met threshold.")
        return analysis_results