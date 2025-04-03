"""Deep Research component for detailed recursive exploration of topics using async operations."""

import logging
import time
import json
import uuid
import re
import asyncio
from typing import List, Dict, Any, Callable, Optional, Tuple, Set, Coroutine
from datetime import datetime

# Internal imports
from ..models import (
    SearchResult, SearchPath, ResearchResult, LLMResponse, LLMError, WebSearchError,
    ExplorationMetrics, ParsingError, validate_llm_json, # Ensure these are imported
    SubqueryList, RelevanceScore, InsightList, FindingList, ContradictionList # Ensure these are imported
)
from .llm_integration import LLMIntegration, ModelCapability
from .detailed_analysis import DetailedAnalyzer
from ..config import settings

logger = logging.getLogger(__name__)

SearchFunctionType = Callable[[str], Coroutine[Any, Any, List[SearchResult]]]

class DeepResearcher:
    """Manages the recursive exploration of a research topic using async operations."""

    def __init__(
        self,
        search_function: SearchFunctionType,
        llm_integration: LLMIntegration,
        detailed_analyzer: Optional[DetailedAnalyzer] = None,
        max_iterations: Optional[int] = None,
        max_branching: Optional[int] = None,
        relevance_threshold: Optional[float] = None,
        diminishing_returns_threshold: Optional[float] = None
    ):
        """Initialize the DeepResearcher."""
        self.search_function = search_function
        self.llm = llm_integration
        self.detailed_analyzer = detailed_analyzer
        self.max_iterations = max(1, max_iterations if max_iterations is not None else settings.deep_search_max_iterations)
        self.max_branching = max(1, max_branching if max_branching is not None else settings.deep_search_max_branching)
        self.relevance_threshold = relevance_threshold if relevance_threshold is not None else settings.deep_search_relevance_threshold
        self.diminishing_returns_threshold = diminishing_returns_threshold if diminishing_returns_threshold is not None else settings.deep_search_diminishing_returns
        logger.info(f"DeepResearcher initialized: max_iter={self.max_iterations}, max_branch={self.max_branching}, rel_thresh={self.relevance_threshold}, dim_ret={self.diminishing_returns_threshold}")

    async def research(self, query: str) -> ResearchResult:
        """(Async) Perform deep research starting from the initial query."""
        start_time = time.monotonic()
        logger.info(f"Starting async deep research for: '{query}'")
        metrics = ExplorationMetrics(
             start_time=datetime.now(),
             exploration_parameters={
                 "max_iterations": self.max_iterations, "max_branching": self.max_branching,
                 "relevance_threshold": self.relevance_threshold, "diminishing_returns_threshold": self.diminishing_returns_threshold
             }
        )
        result = ResearchResult(original_query=query, exploration_metrics=metrics, status="Running")
        root = SearchPath(query=query, depth=0)
        self.add_path(result, root)
        result.root_path_id = root.path_id
        try:
            await self._explore_path(root, result, 0)
            logger.info("Exploration complete. Synthesizing findings and contradictions...")
            await self._extract_key_findings(result)
            await self._detect_contradictions(result)
            result.status = "Completed"
        except Exception as e:
             logger.exception(f"Deep research failed for '{query}': {e}")
             result.status = "Failed"; result.error_message = f"Exploration error: {e}"
        finally:
             if metrics:
                 metrics.end_time = datetime.now()
                 metrics.total_paths_explored = sum(1 for p in result.paths.values() if p.has_been_explored)
                 metrics.total_search_results_collected = sum(len(p.search_results) for p in result.paths.values() if p.search_results)
                 metrics.max_depth_reached = self._calculate_max_depth(result)
             duration = time.monotonic() - start_time
             logger.info(f"Deep research '{query}' status '{result.status}' in {duration:.2f}s. Paths: {metrics.total_paths_explored if metrics else 'N/A'}. Depth: {metrics.max_depth_reached if metrics else 'N/A'}")
        return result

    def _calculate_max_depth(self, result: ResearchResult) -> int:
        if not result.paths: return 0
        return max((p.depth for p in result.paths.values()), default=0)

    def add_path(self, result: ResearchResult, path: SearchPath):
        if path and path.path_id not in result.paths: result.paths[path.path_id] = path

    async def _explore_path(self, path: SearchPath, result: ResearchResult, depth: int):
        if depth >= self.max_iterations: return logger.debug(f"Max depth {self.max_iterations} reached path {path.path_id}")
        if path.has_been_explored: return logger.debug(f"Path {path.path_id} already explored.")

        logger.info(f"Exploring Path {path.path_id} (Depth {depth+1}/{self.max_iterations}): {path.query}")
        path.has_been_explored = True
        try:
            search_res = await self.search_function(path.query)
            path.search_results = search_res
            logger.debug(f"Path {path.path_id} got {len(search_res)} results.")
            insight_task = asyncio.create_task(self._extract_insights_from_search_results(path, search_res))

            if depth >= self.max_iterations - 1:
                logger.debug(f"Max iter reached for path {path.path_id}"); await insight_task; return
            if not search_res:
                logger.warning(f"No results for '{path.query}' (Path {path.path_id})"); await insight_task; return

            snippets = [r.snippet for r in search_res if r.snippet]; content = (chr(10)*2).join(snippets) if snippets else ""
            if not content:
                logger.warning(f"No snippets for subquery gen from '{path.query}'"); await insight_task; return

            subqueries = await self._generate_subqueries(path.query, content, self.max_branching)
            logger.debug(f"Path {path.path_id} generated {len(subqueries)} subqueries.")

            child_tasks = []
            if subqueries:
                parent_rel_score = path.relevance_score if path.relevance_score is not None else (1.0 if depth == 0 else 0.0)
                logger.debug(f"Analyzing relevance for {len(subqueries)} subqueries (parent rel: {parent_rel_score:.2f}).")
                rel_tasks = [self._analyze_path_relevance(result.original_query, sq, parent_rel_score) for sq in subqueries]
                rel_scores = await asyncio.gather(*rel_tasks, return_exceptions=True)

                for i, sq in enumerate(subqueries):
                    clean_sq = sq.strip()
                    if not clean_sq or len(clean_sq) < 3: logger.warning(f"Skipping invalid subquery: '{sq}'"); continue

                    rel_score_or_exc = rel_scores[i]; child_rel_score = 0.5
                    if isinstance(rel_score_or_exc, Exception): logger.warning(f"Relevance analysis failed for '{clean_sq}': {rel_score_or_exc}")
                    elif isinstance(rel_score_or_exc, (float, int)): child_rel_score = float(rel_score_or_exc)

                    child = SearchPath(query=clean_sq, parent_path_id=path.path_id, depth=depth + 1, relevance_score=child_rel_score)
                    self.add_path(result, child); path.child_path_ids.append(child.path_id)

                    explore_child = False
                    if child_rel_score >= self.relevance_threshold:
                         diminishing_returns_ok = (child_rel_score - parent_rel_score) >= -abs(self.diminishing_returns_threshold)
                         if parent_rel_score == 0 or diminishing_returns_ok: explore_child = True
                         else: logger.info(f"Pruning child path {child.path_id} ('{clean_sq}') - diminishing returns.")
                    else: logger.info(f"Pruning child path {child.path_id} ('{clean_sq}') - low relevance.")
                    if explore_child: child_tasks.append(asyncio.create_task(self._explore_path(child, result, depth + 1)))

            await insight_task
            if child_tasks: logger.debug(f"Waiting for {len(child_tasks)} child explorations..."); await asyncio.gather(*child_tasks)
            else: logger.debug(f"No child paths to explore from path {path.path_id}.")
        except Exception as e:
            logger.exception(f"Error exploring path {path.path_id} ('{path.query}'): {e}")
            path.has_been_explored = True

    async def _generate_subqueries(self, query: str, content: str, max_q: int) -> List[str]:
        if not content or not self.llm: return self._fallback_subqueries(query, max_q)
        try:
            ctx_limit = settings.llm_prompt_content_limit
            content_slice = content[:ctx_limit]
            prompt = f"""Given query '{query}' and text snippets, generate {max_q} specific sub-queries. Output ONLY JSON {{ "subqueries": ["q1?", ...] }}. Snippets:
{content_slice}"""
            sys_prompt = f"Gen specific sub-queries based *only* on context snippets for '{query}'. Output ONLY JSON."
            response = await self.llm.generate_response(
                prompt, system_prompt=sys_prompt, task_type="subq_gen",
                required_capabilities=[ModelCapability.JSON_OUTPUT, ModelCapability.REASONING], response_format="json"
            )
            # --- Start Change: Add validation ---
            data: SubqueryList = validate_llm_json(response.raw_text, SubqueryList)
            # --- End Change ---
            sq = [q.strip() for q in data.subqueries if q.strip()]
            logger.debug(f"LLM generated {len(sq)} subqueries for '{query}'.")
            return sq[:max_q]
        except (LLMError, ParsingError) as e:
            logger.warning(f"LLM subquery generation/parsing failed: {e}. Falling back.")
            return self._fallback_subqueries(query, max_q)
        except Exception as e:
            logger.exception(f"Unexpected subquery generation error: {e}")
            return self._fallback_subqueries(query, max_q)

    def _fallback_subqueries(self, query: str, max_q: int) -> List[str]:
        logger.debug(f"Using fallback subquery generation for '{query}'")
        potential = [f"What are aspects of {query}?", f"Examples of {query}?", f"{query}: pros/cons?", f"Applications of {query}?", f"Future of {query}?"]
        used = {query.lower()}; result = []
        for sq in potential:
            clean = sq.strip();
            if len(result) < max_q and clean.lower() not in used: used.add(clean.lower()); result.append(clean)
        return result

    async def _analyze_path_relevance(self, orig_q: str, curr_q: str, parent_rel: float) -> float:
        if self._is_similar(orig_q, curr_q): return 0.1
        if not self.llm: return self._analyze_keyword_relevance(orig_q, curr_q)
        try:
            prompt = f"""Original: '{orig_q}'. Sub-query: '{curr_q}'. How relevant? Output ONLY JSON {{ "score": 0.0-1.0, "reasoning": "..." }}."""
            sys_prompt = "Analyze sub-query relevance. Output ONLY JSON score/reasoning."
            response = await self.llm.generate_response(
                prompt, system_prompt=sys_prompt, task_type="relevance",
                required_capabilities=[ModelCapability.JSON_OUTPUT, ModelCapability.REASONING], response_format="json"
            )
            # --- Start Change: Add validation ---
            data: RelevanceScore = validate_llm_json(response.raw_text, RelevanceScore)
            # --- End Change ---
            score = data.score
            logger.debug(f"LLM relevance '{curr_q}'->'{orig_q}': {score:.2f}. R: {data.reasoning}")
            return score
        except (LLMError, ParsingError) as e:
            logger.warning(f"LLM relevance analysis failed: {e}. Falling back.")
            return self._analyze_keyword_relevance(orig_q, curr_q)
        except Exception as e:
            logger.exception(f"Unexpected relevance analysis error: {e}")
            return self._analyze_keyword_relevance(orig_q, curr_q)

    def _analyze_keyword_relevance(self, orig_q: str, curr_q: str) -> float:
        logger.debug(f"Using keyword relevance for '{curr_q}' vs '{orig_q}'")
        try:
            q1w=set(re.findall(r'\w+', orig_q.lower())); q2w=set(re.findall(r'\w+', curr_q.lower()))
            stop={'a','an','the','is','are','was','of','in','on','at','to','for','with','what','how','why'}
            q1w -= stop; q2w -= stop;
            if not q1w or not q2w: return 0.3
            inter = len(q1w.intersection(q2w)); union = len(q1w.union(q2w))
            jaccard = inter / union if union > 0 else 0.0
            return max(0.0, min(1.0, jaccard * 0.8 + 0.2))
        except Exception as e: logger.error(f"Keyword relevance fail: {e}"); return 0.5

    async def _extract_insights_from_search_results(self, path: SearchPath, results: List[SearchResult]):
        if not results: return
        snippets = [r.snippet for r in results if r.snippet]; content_for_llm = (chr(10)*2).join(snippets)
        if not snippets: return

        analyzer_succeeded = False
        # ... (Analyzer logic - keep as is for now) ...
        if self.detailed_analyzer:
            logger.debug(f"Attempting insight extraction via DetailedAnalyzer for path {path.path_id}.")
            try:
                analysis_result = await self.detailed_analyzer.analyze_content(content_for_llm, path.query)
                if analysis_result and analysis_result.key_points:
                    insights = [{"insight": kp, "source": "analyzer", "confidence": analysis_result.confidence} for kp in analysis_result.key_points if kp]
                    if insights: path.key_insights.extend(insights); logger.info(f"Added {len(insights)} insights via Analyzer."); analyzer_succeeded = True
                    else: logger.debug(f"Analyzer returned no key points.")
                else: logger.debug(f"Analyzer did not return valid analysis/key points.")
            except Exception as da_e: logger.error(f"DetailedAnalyzer insight extraction failed: {da_e}", exc_info=True)


        if not analyzer_succeeded:
            if not self.llm: return logger.warning("LLM not avail for insight fallback.")
            logger.debug(f"Using LLM fallback for insight extraction for path {path.path_id}.")
            try:
                max_chars = settings.llm_prompt_content_limit
                content_slice = content_for_llm[:max_chars]
                prompt = f"""Extract 3-5 key insights re query '{path.query}' from snippets:
{content_slice}
Output ONLY JSON {{ "insights": [{{ "insight": "...", "confidence": 0.0-1.0 }}] }}"""
                sys_prompt = "Extract insights as JSON list of insight/confidence objects."
                response = await self.llm.generate_response(
                    prompt, system_prompt=sys_prompt, task_type="insight",
                    required_capabilities=[ModelCapability.JSON_OUTPUT, ModelCapability.REASONING], response_format="json"
                )
                # --- Start Change: Add validation ---
                data: InsightList = validate_llm_json(response.raw_text, InsightList)
                # --- End Change ---
                llm_ins = [{"insight": i.insight, "source": "llm_fallback", "confidence": i.confidence} for i in data.insights if i.insight]
                if llm_ins: path.key_insights.extend(llm_ins); logger.info(f"Added {len(llm_ins)} insights via LLM fallback.")
                else: logger.warning(f"LLM fallback generated no valid insights.")
            except (LLMError, ParsingError) as e: logger.warning(f"LLM insight extraction fallback failed: {e}")
            except Exception as e: logger.exception(f"Unexpected error during LLM insight fallback: {e}")

    async def _extract_key_findings(self, result: ResearchResult):
        all_insights = [{'text': i.get('insight',''), 'conf': i.get('confidence',0.5), 'pid': pid}
                        for pid, p in result.paths.items() for i in p.key_insights if isinstance(i,dict) and i.get('insight')]
        if not all_insights: return logger.warning(f"No insights to synth findings for query '{result.original_query}'.")
        logger.info(f"Synthesizing key findings from {len(all_insights)} collected insights...")

        analyzer_synth_succeeded = False
        # ... (Analyzer synth logic - placeholder) ...
        if self.detailed_analyzer: pass

        if not analyzer_synth_succeeded:
            if not self.llm: return self._fallback_key_findings(result, all_insights)
            logger.debug("Using LLM fallback for key findings synthesis.")
            try:
                newline = chr(10)
                fmt_insights = newline.join([f"- {i['text']} (Conf: {i['conf']:.1f}, Path: {i['pid']})" for i in all_insights])
                max_chars = settings.llm_prompt_content_limit
                insights_slice = fmt_insights[:max_chars]
                prompt = f"""Synth top 5-7 findings from insights re query '{result.original_query}'. Combine related. Avoid redundancy. Insights:
{insights_slice}
Output ONLY JSON {{ "findings": [{{ "finding": "...", "confidence": 0.0-1.0 }}] }}"""
                sys_prompt = "Synthesize distinct findings. Output ONLY JSON list."
                response = await self.llm.generate_response(
                    prompt, system_prompt=sys_prompt, task_type="finding_synth",
                    required_capabilities=[ModelCapability.JSON_OUTPUT, ModelCapability.REASONING], response_format="json"
                )
                # --- Start Change: Add validation ---
                data: FindingList = validate_llm_json(response.raw_text, FindingList)
                # --- End Change ---
                count = 0
                for item in data.findings:
                    if item.finding:
                        source_pids = list(set(i['pid'] for i in all_insights if self._is_related(item.finding, i['text'])))
                        result.key_findings.append({ "finding": item.finding, "confidence": item.confidence, "source": "llm_synth", "source_path_ids": source_pids or list(result.paths.keys()) })
                        count += 1
                if count > 0: logger.info(f"Extracted {count} findings via LLM synthesis.")
                else: logger.warning("LLM synth no valid findings. Fallback."); self._fallback_key_findings(result, all_insights)
            except (LLMError, ParsingError) as e: logger.warning(f"LLM finding synthesis failed: {e}. Fallback."); self._fallback_key_findings(result, all_insights)
            except Exception as e: logger.exception(f"Unexpected finding synthesis error: {e}"); self._fallback_key_findings(result, all_insights)

    def _is_related(self, text1: str, text2: str) -> bool:
        if not text1 or not text2: return False
        try:
            w1=set(re.findall(r'\w+', text1.lower())); w2=set(re.findall(r'\w+', text2.lower()))
            stop={'a','an','the','is','are','was','of','in','on','at','to','for','with','it','about','as','and','or','but','not','be'}
            w1 -= stop; w2 -= stop;
            if not w1 or not w2: return False
            inter=len(w1.intersection(w2)); min_len=min(len(w1), len(w2))
            return (inter / min_len) >= 0.3 if min_len > 0 else False
        except Exception: return False

    def _fallback_key_findings(self, result: ResearchResult, insights: List[Dict]):
        logger.debug("Executing fallback finding extraction from insights.")
        if not insights: return
        sorted_insights = sorted(insights, key=lambda x: (x.get('conf', 0.0), len(x.get('text', ''))), reverse=True)
        count = 0; added_texts_lower = set(); max_findings = 7
        for data in sorted_insights:
            txt = data.get('text','').strip();
            if not txt: continue
            txt_lower = txt.lower();
            if txt_lower in added_texts_lower: continue
            is_highly_similar = any(self._is_similar(txt, f.get('finding','')) for f in result.key_findings)
            if not is_highly_similar:
                result.key_findings.append({ "finding": txt, "confidence": data.get('conf', 0.5) * 0.9, "source": "fallback_insight_selection", "source_path_ids": [data['pid']] })
                added_texts_lower.add(txt_lower); count += 1
            if count >= max_findings: break
        logger.info(f"Added {count} findings via fallback insight selection.");
        if count == 0: logger.warning("Fallback failed to extract any findings.")

    def _is_similar(self, text1: str, text2: str) -> bool:
        if not text1 or not text2: return False
        try:
            w1=set(re.findall(r'\w+', text1.lower())); w2=set(re.findall(r'\w+', text2.lower()))
            stop={'a','an','the','is','are','was','of','in','on','at','to','for','with','it','about','as','and','or','but','not','be'}
            w1 -= stop; w2 -= stop;
            if not w1 or not w2: return False
            inter=len(w1.intersection(w2)); union=len(w1.union(w2))
            return (inter / union) > 0.7 if union > 0 else (text1.lower() == text2.lower())
        except Exception: return False

    async def _detect_contradictions(self, result: ResearchResult):
        if len(result.paths) < 2: return logger.info("Need >= 2 paths for contradictions.")
        path_insights: Dict[str, List[str]] = {}
        for pid, p in result.paths.items():
            insights = [i.get('insight', '') for i in p.key_insights if isinstance(i, dict) and i.get('insight')]
            if insights: path_insights[pid] = list(set(insights))
        if len(path_insights) < 2: return logger.info("Not enough paths with distinct insights for contradictions.")
        if not self.llm: return logger.warning("LLM N/A for contradictions.")

        logger.info(f"Checking for contradictions across {len(path_insights)} paths...")
        try:
            newline = chr(10); fmt_content = ""
            path_query_map = {pid: p.query for pid, p in result.paths.items()}
            for pid, insights in path_insights.items():
                query_info = path_query_map.get(pid, "Unknown")
                fmt_content += f"--- Path {pid} (Query: {query_info}) ---{newline}"
                fmt_content += newline.join([f"- {insight}" for insight in insights])
                fmt_content += newline * 2

            max_chars = settings.llm_prompt_content_limit
            content_slice = fmt_content[:max_chars]
            prompt = f"""Analyze info below re query '{result.original_query}'. Find contradictions/conflicts between paths. Info:
{content_slice}
Output ONLY JSON {{ "contradictions": [{{ "description": "...", "conflicting_claims": [...], "source_path_ids": [...] }}] }}. If none, output empty list."""
            sys_prompt = "Identify contradictions between paths. Output ONLY JSON structure."
            response = await self.llm.generate_response(
                prompt, system_prompt=sys_prompt, task_type="contradiction",
                required_capabilities=[ModelCapability.JSON_OUTPUT, ModelCapability.REASONING, ModelCapability.CRITICAL_THINKING],
                response_format="json"
            )
            # --- Start Change: Add validation ---
            data: ContradictionList = validate_llm_json(response.raw_text, ContradictionList)
            # --- End Change ---
            count = 0
            for item in data.contradictions:
                 if item.description and item.conflicting_claims and item.source_path_ids:
                     valid_pids = [pid for pid in item.source_path_ids if pid in result.paths]
                     if len(valid_pids) >= 2:
                         result.contradictions.append({ "description": item.description, "conflicting_claims": item.conflicting_claims, "source_path_ids": valid_pids })
                         count += 1
                     else: logger.warning(f"Contradiction invalid path IDs: {item.source_path_ids}")
            if count > 0: logger.info(f"Detected {count} potential contradictions.")
            else: logger.info("No significant contradictions detected by LLM.")
        except (LLMError, ParsingError) as e: logger.warning(f"LLM contradiction detection/parsing failed: {e}")
        except Exception as e: logger.exception(f"Unexpected error during contradiction detection: {e}")
