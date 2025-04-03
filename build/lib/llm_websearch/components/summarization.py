"""(Async) Summarization module for generating multi-level summaries and key insights."""

import asyncio
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field # Import field
import time
from datetime import datetime
import hashlib
import logging

# Internal imports
from ..config import settings
from ..utils import cache
from ..models import LLMResponse, LLMError, ParsingError # Import relevant exceptions
from .llm_integration import LLMIntegration # Import for type hint

logger = logging.getLogger(__name__)

@dataclass
class Summary:
    """Represents a summary with metadata."""
    content: str
    level: int  # 1: Short, 2: Medium, 3: Detailed
    source_indices: List[int] = field(default_factory=list) # Add default factory
    confidence: float = 0.0 # Add default
    generation_time: float = 0.0 # Add default

@dataclass
class SummarizationResult:
    """Contains results of summarization."""
    original_content: List[str]
    summaries: List[Summary]
    total_time: float
    key_insights: List[str]

class Summarizer:
    """(Async) Advanced summarization system using settings for defaults."""

    def __init__(
        self,
        llm_integration: Optional[LLMIntegration] = None, # Use correct type hint
        short_summary_length: Optional[int] = None,
        medium_summary_length: Optional[int] = None,
        long_summary_length: Optional[int] = None,
        min_confidence: Optional[float] = None,
        cache_instance: Optional[Any] = None,
    ):
        """Initialize the summarizer, using settings as defaults."""
        self.llm = llm_integration
        self.cache = cache_instance if cache_instance is not None else cache

        self.short_length = short_summary_length if short_summary_length is not None else settings.summarizer_short_length
        self.medium_length = medium_summary_length if medium_summary_length is not None else settings.summarizer_medium_length
        self.long_length = long_summary_length if long_summary_length is not None else settings.summarizer_long_length
        self.min_confidence = min_confidence if min_confidence is not None else settings.summarizer_min_confidence

        logger.debug(f"Summarizer initialized. Lengths: S={self.short_length}, M={self.medium_length}, L={self.long_length}. Min Confidence: {self.min_confidence}")

    def _create_cache_key(self, content: List[str], level: int) -> str:
        """Create a deterministic cache key for summarization."""
        newline = chr(10)
        content_str = newline.join([c[:500] for c in content])
        key_content = f"summarization:{level}:{hashlib.md5(content_str.encode()).hexdigest()}"
        return hashlib.md5(key_content.encode()).hexdigest()

    async def _generate_summary(
        self, content: str, level: int, context: Optional[Dict[str, Any]] = None
    ) -> Summary:
        """(Async) Generate a summary of specified level using LLM."""
        start_time = time.time()

        if not content.strip():
            return Summary(content="", level=level, source_indices=[], confidence=0.0, generation_time=0.0)

        cached_result = None; cache_key = None
        if self.cache and settings.cache_enabled:
            try:
                cache_key = self._create_cache_key([content], level)
                cached_result = await asyncio.to_thread(self.cache.get, cache_key, default=None)
                if cached_result and isinstance(cached_result, Summary): # Check type
                    logger.debug(f"Cache hit for summary level {level}"); return cached_result
                logger.debug(f"Cache miss for summary level {level}")
            except Exception as e: logger.warning(f"Cache get failed for summary level {level}: {e}")

        if level == 1: target_length = self.short_length
        elif level == 2: target_length = self.medium_length
        elif level == 3: target_length = self.long_length
        else: raise ValueError("Invalid summary level.")

        model_override = settings.summarizer_model

        if self.llm:
            try:
                if level == 1:
                    prompt = f"""Generate a concise summary (~{target_length} words) of the following text:

{content}"""
                    system_prompt = "You are a concise summarizer."
                elif level == 2:
                    prompt = f"""Generate a medium-length summary (~{target_length} words) of the following text:

{content}"""
                    system_prompt = "You are a balanced summarizer."
                else: # level == 3
                    prompt = f"""Generate a detailed summary (~{target_length} words) of the following text:

{content}"""
                    system_prompt = "You are a detailed summarizer."

                response = await self.llm.generate_response(
                    prompt, system_prompt=system_prompt, task_type=f"summarization_L{level}",
                    requested_model=model_override, required_capabilities=["summarization"],
                )

                # --- Start Change: Removed 'if not response.error' ---
                # Process response directly assuming success if no exception raised
                result = Summary(
                    content=response.raw_text.strip(), level=level, source_indices=[0],
                    confidence=getattr(response, 'confidence_score', 0.8), # Use getattr for safety
                    generation_time=time.time() - start_time,
                )
                # --- End Change ---

                if self.cache and settings.cache_enabled and result.confidence >= self.min_confidence and cache_key:
                    try:
                         logger.debug(f"Setting cache for summary level {level}")
                         await asyncio.to_thread(self.cache.set, cache_key, result, expire=settings.cache_ttl_seconds)
                    except Exception as e: logger.warning(f"Cache set failed for summary level {level}: {e}")
                return result

            except (LLMError, ParsingError) as e: # Catch specific errors
                logger.error(f"LLM error generating summary level {level}: {e}")
            except Exception as e: # Catch unexpected errors
                logger.exception(f"Unexpected error during LLM summary generation level {level}: {e}")

        logger.warning(f"LLM unavailable/failed for summary level {level}, using mock.")
        mock_summary = f"Mock {['short', 'medium', 'detailed'][level - 1]} summary."
        return Summary(
            content=mock_summary, level=level, source_indices=[0], confidence=0.5, generation_time=time.time() - start_time
        )

    async def _extract_key_insights(self, content: List[str]) -> List[str]:
        """(Async) Extract key insights from content using LLM."""
        newline = chr(10); cache_key = None; cached_result = None
        final_insights = [] # Initialize

        if self.cache and settings.cache_enabled:
            try:
                content_str = newline.join([c[:300] for c in content])
                cache_key = f"key_insights:{hashlib.md5(content_str.encode()).hexdigest()}"
                cached_result = await asyncio.to_thread(self.cache.get, cache_key, default=None)
                if cached_result and isinstance(cached_result, list): # Check type
                    logger.debug("Cache hit for key insights"); return cached_result
                logger.debug("Cache miss for key insights")
            except Exception as e: logger.warning(f"Cache get failed for key insights: {e}")

        if self.llm:
            double_newline = chr(10) * 2
            combined_content = double_newline.join(content)
            max_len = settings.summarizer_insight_max_chars
            if len(combined_content) > max_len:
                logger.warning(f"Key insights content truncated to {max_len} characters.")
                combined_content = combined_content[:max_len] + "... [truncated]"

            prompt = f"""Analyze the following content and identify the {settings.summarizer_max_insights} most important insights. Present each insight clearly.

Content:
{combined_content}

Key Insights:"""
            system_prompt = "Extract key insights."; model_override = settings.summarizer_insight_model

            try:
                response = await self.llm.generate_response( # Await
                    prompt, system_prompt=system_prompt, task_type="key_insights",
                    requested_model=model_override, required_capabilities=["reasoning", "summarization"],
                )

                # --- Start Change: Removed 'if not response.error' ---
                insights_text = response.raw_text
                insights = []
                lines = insights_text.split(newline)
                for line in lines:
                    line = line.strip().lstrip("-* ").lstrip("0123456789.").strip()
                    if line: insights.append(line)
                final_insights = insights[:settings.summarizer_max_insights] # Use setting
                # --- End Change ---

                if self.cache and settings.cache_enabled and final_insights and cache_key:
                    try:
                         logger.debug("Setting cache for key insights")
                         await asyncio.to_thread(self.cache.set, cache_key, final_insights, expire=settings.cache_ttl_seconds)
                    except Exception as e: logger.warning(f"Cache set failed for key insights: {e}")
                return final_insights

            except (LLMError, ParsingError) as e: logger.error(f"LLM error extracting key insights: {e}")
            except Exception as e: logger.exception(f"Unexpected error during LLM key insight extraction: {e}")

        # Fallback only if final_insights is still empty
        if not final_insights:
            logger.warning("LLM integration not available or failed, using mock key insights.")
            return ["Mock Key Insight 1", "Mock Key Insight 2", "Mock Key Insight 3"]
        else:
            # This path should technically not be reached if LLM succeeded, but included for safety
            return final_insights


    async def _generate_combined_summary(
        self, summaries: List[Summary], level: int
    ) -> Summary:
        """(Async) Generate a combined summary from multiple source summaries."""
        start_time = time.time()

        if not summaries: return Summary(content="", level=level, source_indices=[], confidence=0.0, generation_time=0.0)
        level_summaries = [s for s in summaries if s.level == level]
        if not level_summaries: return Summary(content="", level=level, source_indices=[], confidence=0.0, generation_time=0.0)
        if len(level_summaries) == 1: return level_summaries[0]

        source_indices = list(set(idx for s in level_summaries for idx in s.source_indices))
        combined_content = (chr(10)*2).join([s.content for s in level_summaries])

        cached_result = None; cache_key = None
        if self.cache and settings.cache_enabled:
             try:
                cache_key = self._create_cache_key([s.content for s in level_summaries], level)
                cached_result = await asyncio.to_thread(self.cache.get, cache_key, default=None)
                if cached_result and isinstance(cached_result, Summary): # Check type
                    logger.debug(f"Cache hit for combined summary level {level}"); return cached_result
                logger.debug(f"Cache miss for combined summary level {level}")
             except Exception as e: logger.warning(f"Cache get failed for combined summary level {level}: {e}")

        if level == 1: target_length = self.short_length
        elif level == 2: target_length = self.medium_length
        elif level == 3: target_length = self.long_length
        else: raise ValueError("Invalid summary level.")

        model_override = settings.summarizer_model

        if self.llm:
            try:
                if level == 1:
                    prompt = f"""Synthesize a concise summary (~{target_length} words) from these summaries:

{combined_content}"""; system_prompt = "Synthesize concise summary."
                elif level == 2:
                     prompt = f"""Synthesize a medium summary (~{target_length} words) from these summaries:

{combined_content}"""; system_prompt = "Synthesize balanced summary."
                else: # level == 3
                    prompt = f"""Synthesize a detailed summary (~{target_length} words) from these summaries:

{combined_content}"""; system_prompt = "Synthesize detailed summary."

                # --- Start Change: Remove 'if not response.error' ---
                response = await self.llm.generate_response( # Await
                    prompt, system_prompt=system_prompt, task_type=f"summary_synthesis_L{level}",
                    requested_model=model_override, required_capabilities=["summarization"],
                )
                # Process directly assuming success
                result = Summary(
                    content=response.raw_text.strip(), level=level, source_indices=source_indices,
                    confidence=getattr(response, 'confidence_score', 0.8),
                    generation_time=time.time() - start_time,
                )
                # --- End Change ---

                if self.cache and settings.cache_enabled and result.confidence >= self.min_confidence and cache_key:
                    try:
                        logger.debug(f"Setting cache for combined summary level {level}")
                        await asyncio.to_thread(self.cache.set, cache_key, result, expire=settings.cache_ttl_seconds)
                    except Exception as e: logger.warning(f"Cache set failed for combined summary level {level}: {e}")
                return result

            except (LLMError, ParsingError) as e: logger.error(f"LLM error generating combined summary level {level}: {e}")
            except Exception as e: logger.exception(f"Unexpected error during LLM combined summary generation level {level}: {e}")

        logger.warning(f"LLM failed/unavailable for combined summary level {level}, using fallback.")
        fallback_content = " ".join([s.content for s in level_summaries])
        fallback_multiplier = getattr(settings, 'summarizer_fallback_max_len_multiplier', 4.0)
        max_fallback_len = int(target_length * fallback_multiplier)
        if len(fallback_content) > max_fallback_len:
             logger.warning(f"Fallback combined summary truncated to {max_fallback_len} characters.")
             fallback_content = fallback_content[:max_fallback_len] + "..."

        return Summary(
            content=fallback_content, level=level, source_indices=source_indices,
            confidence=0.5, generation_time=time.time() - start_time,
        )


    async def summarize(
        self, content: List[str], context: Optional[Dict[str, Any]] = None
    ) -> SummarizationResult:
        """(Async) Generate multi-level summaries and extract key insights."""
        start_time_dt = datetime.now(); all_summaries = []
        logger.info(f"Starting async summarization for {len(content)} content items.")
        if not content: return SummarizationResult(original_content=[], summaries=[], total_time=0.0, key_insights=[])

        individual_summary_tasks = []; content_indices_map = {}; task_counter = 0
        for i, text in enumerate(content):
            if text and text.strip():
                for level in [1, 2, 3]:
                    task = asyncio.create_task(self._generate_summary(text, level, context), name=f"IndivSumm_L{level}_Idx{i}")
                    individual_summary_tasks.append(task); content_indices_map[task_counter] = i; task_counter += 1
            else: logger.warning(f"Skipping empty content item at index {i}")

        logger.debug(f"Created {len(individual_summary_tasks)} individual summary tasks.")
        individual_results = await asyncio.gather(*individual_summary_tasks, return_exceptions=True)

        item_summaries = {1: [], 2: [], 3: []}
        for i, result_or_exc in enumerate(individual_results):
             original_content_index = content_indices_map.get(i, -1)
             if isinstance(result_or_exc, Summary):
                  result_or_exc.source_indices = [original_content_index]; all_summaries.append(result_or_exc)
                  if original_content_index != -1: item_summaries[result_or_exc.level].append(result_or_exc)
             elif isinstance(result_or_exc, Exception): logger.error(f"Individual summary task {i} failed: {result_or_exc}")
             else: logger.error(f"Unexpected result type from task {i}: {type(result_or_exc)}")

        combined_summary_tasks = []
        if len(content) > 1:
            logger.info("Generating combined summaries.")
            for level in [1, 2, 3]:
                if item_summaries[level]:
                     combined_summary_tasks.append(
                          asyncio.create_task(self._generate_combined_summary(item_summaries[level], level), name=f"CombSumm_L{level}")
                     )
            if combined_summary_tasks:
                logger.debug(f"Created {len(combined_summary_tasks)} combined summary tasks.")
                combined_results = await asyncio.gather(*combined_summary_tasks, return_exceptions=True)
                for i, result_or_exc in enumerate(combined_results):
                    if isinstance(result_or_exc, Summary) and result_or_exc.content: all_summaries.append(result_or_exc)
                    elif isinstance(result_or_exc, Exception): logger.error(f"Combined summary task {i} failed: {result_or_exc}")
                    elif isinstance(result_or_exc, Summary): logger.warning(f"Combined summary task {i} produced empty content.")
            else: logger.info("No summaries to combine.")
        else: logger.info("Skipping combined summaries (single item).")

        logger.info("Extracting key insights.")
        key_insights = await self._extract_key_insights(content)
        logger.info(f"Extracted {len(key_insights)} key insights.")

        total_time = (datetime.now() - start_time_dt).total_seconds()
        logger.info(f"Async summarization completed in {total_time:.2f} seconds.")

        return SummarizationResult(
            original_content=content, summaries=all_summaries,
            total_time=total_time, key_insights=key_insights
        )

    async def summarize_research_result(self, research_result) -> Dict[str, Any]:
        """(Async) Summarize a ResearchResult object."""
        logger.info("Starting async summarization of ResearchResult.")
        findings_text = []; evidence_text = []

        if research_result.key_findings:
            logger.debug(f"Extracting text from {len(research_result.key_findings)} findings.")
            for finding in research_result.key_findings:
                if isinstance(finding, dict): findings_text.append(finding.get("finding", ""))
                elif isinstance(finding, str): findings_text.append(finding)
        findings_text = [t for t in findings_text if t]

        evidence_sources_count = 0
        if research_result.paths:
            logger.debug(f"Extracting evidence text from {len(research_result.paths)} paths.")
            for path in research_result.paths.values():
                if path.search_results:
                    for result in path.search_results:
                        if result.processed_content and result.processed_content.strip():
                            evidence_text.append(result.processed_content); evidence_sources_count += 1
            logger.debug(f"Extracted evidence from {evidence_sources_count} sources.")
        else: logger.debug("No paths found.")

        all_text = findings_text + evidence_text
        logger.info(f"Total text items for summarization: {len(all_text)}")

        if all_text:
            try:
                logger.info("Calling async internal summarize method.")
                summary_result = await self.summarize(all_text)
                logger.info("Internal summarize method completed.")

                num_sources = len(all_text)
                def find_summary_by_level(level):
                    target_indices_count = 1 if num_sources <= 1 else 2
                    combined = next((s for s in summary_result.summaries if s.level == level and len(s.source_indices) >= target_indices_count), None)
                    if combined: return combined.content
                    first = next((s for s in summary_result.summaries if s.level == level), None)
                    return first.content if first else ""

                summary_data = {
                    "tiered_summaries": { "short": find_summary_by_level(1), "medium": find_summary_by_level(2), "detailed": find_summary_by_level(3) },
                    "key_insights": summary_result.key_insights,
                    "generation_time": summary_result.total_time,
                }
                logger.info("Successfully generated summary data for ResearchResult.")
                return summary_data
            except Exception as e:
                logger.exception(f"Error during summarization of combined text: {e}")
                return { "tiered_summaries": {"short": "Summarization failed.", "medium": "", "detailed": ""}, "key_insights": [], "generation_time": 0.0, "error": f"Summarization failed: {e}"}
        else:
            logger.warning("No text available to summarize for ResearchResult.")
            return { "tiered_summaries": {"short": "", "medium": "", "detailed": ""}, "key_insights": [], "generation_time": 0.0, "status": "No content to summarize" }
