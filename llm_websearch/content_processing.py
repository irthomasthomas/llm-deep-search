"""
Content processing functions including fetching, parsing, summarization helpers,
and result formatting (now produces Markdown).
"""

from enum import Enum
from typing import Dict, List, Any, Optional, Tuple
import json
import asyncio
import logging
import httpx
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field, confloat

from .models import (
    LLMResponse, LLMError, ContentProcessingError, SearchResult, ResearchResult,
    ParsingError, validate_llm_json,
    SubqueryList, ThemeList
)
from .config import settings, ConfigError
from .utils import cache, _cache_key
from .components.llm_integration import LLMIntegration, ModelCapability

logger = logging.getLogger(__name__)

# --- Result Formatting (Markdown Output) ---
class FormatType(Enum): COMPACT = "compact"; SUMMARY = "summary"; FULL = "full"

class FormatOptions(BaseModel):
    include_metadata: bool = True
    max_findings: Optional[int] = 7 # Default max findings to show
    max_evidence_per_finding: Optional[int] = None # Not currently used in formatter
    confidence_threshold: float = 0.5 # Default confidence threshold for findings
    include_exploration_paths: bool = False

class ResearchResultFormatter:
    """Formats ResearchResult into a Markdown string."""

    def __init__(self, format_type: FormatType = FormatType.SUMMARY, options: Optional[FormatOptions] = None):
        self.format_type = format_type
        self.options = options or FormatOptions()
        self.newline = chr(10) # Use chr(10) for consistency

    def format_result(self, result: ResearchResult) -> str:
        """Formats the ResearchResult object into a Markdown string."""
        if not isinstance(result, ResearchResult):
            logger.error(f"Formatter received invalid type: {type(result)}")
            return f"## Error: Invalid result object received by formatter. ##"

        base_md = f"# Deep Search Results for: \"{result.original_query}\"{self.newline}"
        base_md += f"**Status:** {result.status}{self.newline}{self.newline}"

        if result.error_message:
            base_md += f"**Error:** {result.error_message}{self.newline}{self.newline}"

        if self.format_type == FormatType.COMPACT:
            return self._format_compact(result, base_md)
        elif self.format_type == FormatType.SUMMARY:
            return self._format_summary(result, base_md)
        else: # FormatType.FULL
            return self._format_full(result, base_md)

    def _filter_findings(self, findings: List[Dict]) -> List[Dict]:
        """Filters and sorts findings based on options."""
        if not isinstance(findings, list): return []
        valid_findings = [f for f in findings if isinstance(f, dict) and f.get("confidence", 0.0) >= self.options.confidence_threshold]
        sorted_findings = sorted(valid_findings, key=lambda f: f.get("confidence", 0.0), reverse=True)
        if self.options.max_findings is not None:
            return sorted_findings[:self.options.max_findings]
        return sorted_findings

    def _format_compact(self, result: ResearchResult, md: str) -> str:
        """Formats result into a compact Markdown string."""
        md += f"## Summary{self.newline}"
        summary = result.tiered_summaries.get("short") or result.tiered_summaries.get("medium")
        if summary:
            md += f"{summary}{self.newline}{self.newline}"
        else:
            md += f"*No summary available.*{self.newline}{self.newline}"

        if self.options.include_metadata and result.exploration_metrics:
            metrics = result.exploration_metrics
            md += f"**Stats:** Explored {metrics.total_paths_explored} paths to depth {metrics.max_depth_reached}."
            if metrics.start_time and metrics.end_time:
                 duration = (metrics.end_time - metrics.start_time).total_seconds()
                 md += f" Took {duration:.2f}s."
            md += self.newline

        return md.strip()

    def _format_summary(self, result: ResearchResult, md: str) -> str:
        """Formats result into a standard summary Markdown string."""
        md += f"## Key Findings{self.newline}"
        filtered_findings = self._filter_findings(result.key_findings)
        if filtered_findings:
            for i, finding_data in enumerate(filtered_findings):
                conf = finding_data.get("confidence", 0.0)
                md += f"{i+1}. {finding_data.get('finding', 'N/A')} (Confidence: {conf:.2f}){self.newline}"
        else:
            md += f"*No key findings met the criteria (Threshold: {self.options.confidence_threshold}).*{self.newline}"
        md += self.newline

        md += f"## Summary{self.newline}"
        summary = result.tiered_summaries.get("medium") or result.tiered_summaries.get("short")
        if summary:
             md += f"{summary}{self.newline}{self.newline}"
        else:
             md += f"*No summary available.*{self.newline}{self.newline}"

        if self.options.include_metadata and result.exploration_metrics:
            metrics = result.exploration_metrics
            md += f"**Stats:** Explored {metrics.total_paths_explored} paths to depth {metrics.max_depth_reached}. Found {metrics.total_search_results_collected} results."
            if metrics.start_time and metrics.end_time:
                 duration = (metrics.end_time - metrics.start_time).total_seconds()
                 md += f" Took {duration:.2f}s."
            md += self.newline

        return md.strip()

    def _format_full(self, result: ResearchResult, md: str) -> str:
        """Formats result into a detailed Markdown string."""
        # Key Findings
        md += f"## Key Findings{self.newline}"
        filtered_findings = self._filter_findings(result.key_findings)
        if filtered_findings:
            for i, finding_data in enumerate(filtered_findings):
                conf = finding_data.get("confidence", 0.0)
                source = finding_data.get("source", "N/A")
                pids = finding_data.get("source_path_ids", [])
                md += f"{i+1}. **Finding:** {finding_data.get('finding', 'N/A')} {self.newline}"
                md += f"   - **Confidence:** {conf:.2f}{self.newline}"
                md += f"   - **Source:** {source}{self.newline}"
                md += f"   - **Relevant Path IDs:** {', '.join(pids) if pids else 'N/A'}{self.newline}"
        else:
            md += f"*No key findings met the criteria (Threshold: {self.options.confidence_threshold}).*{self.newline}"
        md += self.newline

        # Contradictions
        if result.contradictions:
            md += f"## Potential Contradictions{self.newline}"
            for i, con_data in enumerate(result.contradictions):
                claims = con_data.get('conflicting_claims', [])
                pids = con_data.get('source_path_ids', [])
                md += f"{i+1}. **Description:** {con_data.get('description', 'N/A')}{self.newline}"
                md += f"   - **Claims:**{self.newline}"
                for claim in claims: md += f"     - {claim}{self.newline}"
                md += f"   - **Source Path IDs:** {', '.join(pids)}{self.newline}"
            md += self.newline

        # Tiered Summaries
        if result.tiered_summaries:
             md += f"## Summaries{self.newline}"
             for level, summary_text in result.tiered_summaries.items():
                  if summary_text:
                       md += f"### {level.capitalize()} Summary{self.newline}{summary_text}{self.newline}{self.newline}"
             md += self.newline

        # Key Insights Summary (if different from findings)
        if result.key_insights_summary:
             md += f"## Overall Key Insights{self.newline}"
             for i, insight in enumerate(result.key_insights_summary):
                 md += f"- {insight}{self.newline}"
             md += self.newline

        # Exploration Paths (Optional)
        if self.options.include_exploration_paths and result.paths:
            md += f"## Exploration Paths{self.newline}"
            for path_id, path_obj in result.paths.items():
                md += f"### Path: {path_id} (Depth: {path_obj.depth}){self.newline}"
                md += f"- **Query:** \"{path_obj.query}\"{self.newline}"
                md += f"- **Parent:** {path_obj.parent_path_id or 'Root'}{self.newline}"
                md += f"- **Explored:** {path_obj.has_been_explored}{self.newline}"
                md += f"- **Relevance:** {path_obj.relevance_score:.2f}{self.newline}"
                if path_obj.key_insights:
                     md += f"- **Insights:**{self.newline}"
                     for insight_data in path_obj.key_insights:
                          conf = insight_data.get("confidence", 0.0)
                          src = insight_data.get("source", "N/A")
                          md += f"  - {insight_data.get('insight','N/A')} (Conf: {conf:.2f}, Src: {src}){self.newline}"
                if path_obj.search_results:
                    md += f"- **Search Results ({len(path_obj.search_results)}):**{self.newline}"
                    for sr in path_obj.search_results[:3]:
                         rank = sr.metadata.get('rank', '?')
                         md += f"  - [{sr.title}]({sr.url}) (Rank: {rank}){self.newline}"
                         if sr.snippet: md += f"    > {sr.snippet[:150]}...{self.newline}"
                md += self.newline

        # Exploration Metrics (Optional)
        if self.options.include_metadata and result.exploration_metrics:
            metrics = result.exploration_metrics
            md += f"## Exploration Metrics{self.newline}"
            md += f"- Paths Explored: {metrics.total_paths_explored}{self.newline}"
            md += f"- Max Depth Reached: {metrics.max_depth_reached}{self.newline}"
            md += f"- Total Results Collected: {metrics.total_search_results_collected}{self.newline}"
            if metrics.start_time and metrics.end_time:
                 duration = (metrics.end_time - metrics.start_time).total_seconds()
                 md += f"- Total Duration: {duration:.2f} seconds{self.newline}"
            md += self.newline

        return md.strip()


# --- Content Fetching & Processing (Async) ---
async def fetch_and_summarize(url: str, query: str, timeout: Optional[float] = None, llm_integration: Optional[LLMIntegration] = None) -> str:
    cache_key = None; effective_timeout = timeout if timeout is not None else settings.request_timeout_general
    if cache and settings.cache_enabled: cache_key = _cache_key("f&s_async", url, query);
    if cache_key:
        try: cached = await asyncio.to_thread(cache.get, cache_key);
        except Exception as e: logger.warning(f"Cache get fail sum: {e}"); cached = None
        if cached and isinstance(cached, str): logger.info(f"Cache hit sum: {url}"); return cached
    try:
        async with httpx.AsyncClient(timeout=effective_timeout, follow_redirects=True, verify=False) as client:
            logger.debug(f"Fetching: {url}"); resp = await client.get(url); resp.raise_for_status()
            ctype = resp.headers.get('content-type','').lower()
            if 'html' not in ctype: raise ContentProcessingError(f"Not HTML {ctype}: {url}")
            def parse(html): # Local sync helper
                try:
                    soup = BeautifulSoup(html, 'html.parser')
                    for el in soup(["script", "style", "nav", "footer", "aside", "header", "form"]): el.extract()
                    mc = soup.find('main') or soup.find('article') or soup.find('div',role='main')
                    txt = (mc or soup.body).get_text(separator=' ',strip=True) if (mc or soup.body) else ""
                    return ' '.join(txt.split())
                except Exception as e: logger.error(f"Parse fail {url}: {e}"); return ""
            text = await asyncio.to_thread(parse, resp.text); logger.debug(f"Extracted ~{len(text)} chars: {url}")
        if not text: raise ContentProcessingError(f"No text found: {url}.")
        prompt_base = f"""Based *only* on the following text, provide a concise summary relevant to the query '{query}'. Focus on key info, ignore irrelevant details. Text:

"""
        max_c = getattr(settings,'summarizer_long_length', 8000); prompt = prompt_base + text[:max_c]
        if not llm_integration: llm_integration = LLMIntegration()
        if not llm_integration.api_key_configured: raise ConfigError("LLM not config for sum.")
        sys_prompt = "Expert summarizer. Brief, factual, query-relevant summary."
        logger.debug(f"LLM summary req: {url}"); llm_resp = await llm_integration.generate_response(prompt, system_prompt=sys_prompt, task_type="url_sum")
        summary = llm_resp.raw_text.strip()
        if not summary: raise LLMError(model=llm_resp.model_name, message="Summary empty.")
        if cache_key and summary:
            try: await asyncio.to_thread(cache.set, cache_key, summary, expire=settings.cache_ttl_seconds); logger.info(f"Cached sum: {url}")
            except Exception as e: logger.warning(f"Cache set fail sum: {e}")
        return summary
    except httpx.HTTPStatusError as e: logger.warning(f"HTTP {e.response.status_code}: {url}"); raise ContentProcessingError(f"HTTP err {e.response.status_code}: {url}") from e
    except httpx.RequestError as e: logger.warning(f"Req err {url}: {e}"); raise ContentProcessingError(f"Fetch fail: {url}") from e
    except (ContentProcessingError, LLMError, ConfigError) as e: raise e
    except Exception as e: logger.exception(f"Unexpected err processing {url}: {e}"); raise ContentProcessingError(f"Unexpected err sum: {url}") from e

async def extract_themes(content: str, query: str, llm: LLMIntegration) -> List[str]:
    logger.info(f"Extracting themes q='{query}'"); max_c = getattr(settings,'summarizer_insight_max_chars',4000)
    prompt = f"""Identify main themes (max 5) in text below re query '{query}'. Output ONLY JSON {{ "themes": ["theme1", ...] }}. Text:

{content[:max_c]}"""
    sys_prompt = "Extract themes as JSON list. Example: {{ \"themes\": [\"t1\", \"t2\"] }}"
    try:
        if not llm.api_key_configured: raise ConfigError("LLM not config for themes.")
        resp = await llm.generate_response(prompt, system_prompt=sys_prompt, task_type="themes", required_capabilities=[ModelCapability.JSON_OUTPUT, ModelCapability.REASONING], response_format="json")
        data = validate_llm_json(resp.raw_text, ThemeList); return [t.strip() for t in data.themes if t.strip()]
    except (LLMError, ParsingError, ConfigError) as e: logger.warning(f"Theme extract fail: {e}"); return []
    except Exception as e: logger.exception(f"Unexpected theme err: {e}"); return []

async def _generate_llm_subqueries(orig_q: str, context: str, themes: Optional[List[str]], llm: LLMIntegration, max_q: int = 5) -> List[str]:
    logger.info(f"Generating subqueries for: '{orig_q}'")
    # --- Start Change: Use chr(10) for join ---
    newline = chr(10)
    themes_str = newline.join([f"- {t}" for t in themes]) if themes else "None"
    # --- End Change ---
    max_c = getattr(settings, 'summarizer_combine_max_chars_l2', 2000) # Revisit this limit setting name
    prompt = f"""Query: '{orig_q}'. Context/Themes below. Generate {max_q} sub-queries to deepen research based *only* on context. Output ONLY JSON {{ "subqueries": ["q1?", ...] }}.

Context:
{context[:max_c]}

Themes:
{themes_str}

Sub-queries (JSON Object):"""
    sys_prompt = "Generate sub-queries based *only* on context. Output ONLY JSON: {{ \"subqueries\": [\"q1?\"] }}"
    try:
        if not llm.api_key_configured: raise ConfigError("LLM not config for subq.")
        resp = await llm.generate_response(prompt, system_prompt=sys_prompt, task_type="subq", required_capabilities=[ModelCapability.JSON_OUTPUT, ModelCapability.REASONING], response_format="json")
        data = validate_llm_json(resp.raw_text, SubqueryList); return [q.strip() for q in data.subqueries if q.strip() and len(q.strip()) > 5][:max_q]
    except (LLMError, ParsingError, ConfigError) as e: logger.warning(f"Subquery gen fail: {e}"); return []
    except Exception as e: logger.exception(f"Unexpected subq err: {e}"); return []
