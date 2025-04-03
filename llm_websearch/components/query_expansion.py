"""Query Expansion component for enhancing search queries using async operations."""

import logging
import time
import json
import asyncio
from typing import List, Dict, Optional, Any, Union # Added Union
from enum import Enum
from pydantic import BaseModel, Field, confloat

# Internal imports
from .llm_integration import LLMIntegration, LLMError, ModelCapability
from ..models import ParsingError, validate_llm_json
from ..utils import cache, _cache_key
from ..config import settings

logger = logging.getLogger(__name__)

class ExpansionType(Enum):
    SEMANTIC = "semantic"; SYNTACTIC = "syntactic"; CONTEXTUAL = "contextual"
    DOMAIN = "domain"; LLM_GENERATED = "llm_generated"; ORIGINAL = "original"

class QueryVariant(BaseModel):
    query: str; expansion_type: ExpansionType; confidence: confloat(ge=0.0, le=1.0)
    source: str; parent_query: Optional[str] = None; context: Optional[Dict[str, Any]] = None

class ExpansionResult(BaseModel):
    original_query: str; expanded_queries: List[QueryVariant] = Field(default_factory=list)
    expansion_time: float; total_variants_generated: int = 0
    quality_score: Optional[float] = None; context_used: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None

class LLMExpansionOutput(BaseModel):
     variations: List[Dict[str, Union[str, float]]] = Field(..., description="List of query variations, each with 'query' and 'confidence'.")

class QueryExpander:
    """Expands search queries using LLM and rule-based strategies (async)."""
    def __init__(self, llm_integration: LLMIntegration, cache_instance=None):
        self.llm = llm_integration; self.cache = cache_instance if cache_instance is not None else cache
        self.max_variants = getattr(settings, 'query_expander_max_variants', 5)
        self.min_confidence = getattr(settings, 'query_expander_min_confidence', 0.7)
        self.expansion_model = getattr(settings, 'query_expander_model', None)
        self.domain_templates = {
            "programming": ["{q} tut", "{q} eg code", "{q} doc", "how to {q}", "{q} best practice"],
            "research": ["latest on {q}", "{q} methodology", "{q} analysis", "{q} review"],
        }
        logger.info(f"QueryExpander init: max_v={self.max_variants}, min_conf={self.min_confidence}")

    async def _generate_semantic_variants_llm(self, query: str, context: Dict[str, Any]) -> List[QueryVariant]:
        if not self.llm: logger.warning("LLM not avail for semantic expansion."); return []
        variants = [] 
        try:
            ctx_str = json.dumps(context) if context else "None"
            prompt = f"""Gen diverse semantic variations for query: "{query}". Use context if provided. Output ONLY JSON {{ "variations": [{{ "query": "...", "confidence": 0.0-1.0 }}] }}. Context: {ctx_str[:500]}"""
            sys_prompt = "Generate semantic variations as JSON list of query/confidence objects."
            response = await self.llm.generate_response(prompt, system_prompt=sys_prompt, task_type="sem_q_exp", requested_model=self.expansion_model, required_capabilities=[ModelCapability.JSON_OUTPUT, ModelCapability.REASONING], response_format="json")
            data = validate_llm_json(response.raw_text, LLMExpansionOutput)
            for item in data.variations:
                 q = item.get('query'); conf = item.get('confidence')
                 if isinstance(q, str) and isinstance(conf, (float, int)):
                     if conf >= self.min_confidence: variants.append(QueryVariant(query=q.strip(), expansion_type=ExpansionType.LLM_GENERATED, confidence=float(conf), source="llm", parent_query=query, context=context))
                 else: logger.warning(f"Skipping invalid LLM variation: {item}")
            logger.debug(f"LLM gen {len(variants)} semantic variants for '{query}'.")
        except (LLMError, ParsingError) as e: logger.warning(f"LLM semantic expansion fail '{query}': {e}")
        except Exception as e: logger.exception(f"Unexpected semantic expansion err '{query}': {e}")
        return variants

    def _generate_syntactic_variants(self, query: str, context: Dict[str, Any]) -> List[QueryVariant]:
        variants = []
        variants.append(QueryVariant(query=f'\"{query}\"', expansion_type=ExpansionType.SYNTACTIC, confidence=0.95, source="syntax_exact", parent_query=query, context=context))
        return variants

    def _generate_contextual_variants(self, query: str, context: Dict[str, Any]) -> List[QueryVariant]:
        variants = []; domain = context.get("domain")
        # Remove unused variable user_preferences
        # user_preferences = context.get("preferences", {})
        if domain and isinstance(domain, str) and domain in self.domain_templates:
            logger.debug(f"Applying domain templates '{domain}' to '{query}'")
            templates = self.domain_templates[domain]
            for t in templates: 
                try: variants.append(QueryVariant(query=t.format(q=query), expansion_type=ExpansionType.DOMAIN, confidence=0.85, source=f"dom_{domain}", parent_query=query, context=context))
                except KeyError: logger.warning(f"Template '{t}' failed for '{query}'.")
        return variants

    def _filter_and_rank_variants(self, variants: List[QueryVariant], original_query: str) -> List[QueryVariant]:
        all_inc_orig = [QueryVariant(query=original_query, expansion_type=ExpansionType.ORIGINAL, confidence=1.0, source='original')] + variants
        seen: Dict[str, QueryVariant] = {}
        for v in all_inc_orig:
            q_low = v.query.strip().lower()
            if not q_low: continue
            if q_low not in seen or v.confidence > seen[q_low].confidence: seen[q_low] = v
        unique = list(seen.values()); unique.sort(key=lambda x: x.confidence, reverse=True)
        final = unique[:self.max_variants]; logger.debug(f"Filtered {len(variants)} vars to {len(final)}."); return final

    async def expand_query(self, query: str, context: Optional[Dict[str, Any]] = None) -> ExpansionResult:
        start = time.monotonic(); context = context or {}; orig_q = query.strip()
        res = ExpansionResult(original_query=orig_q, expansion_time=0.0, context_used=context)
        if not orig_q: res.expansion_time = time.monotonic() - start; res.error_message = "Query empty."; return res
        cache_key = None
        if self.cache and settings.cache_enabled: cache_key = _cache_key("q_exp", orig_q, context)
        if cache_key:
            try: cached = await asyncio.to_thread(self.cache.get, cache_key) 
            except Exception as e: logger.warning(f"Cache get fail q_exp: {e}"); cached=None
            if cached and isinstance(cached, ExpansionResult): logger.info(f"Cache hit q_exp: '{orig_q}'"); return cached
        llm_task = self._generate_semantic_variants_llm(orig_q, context)
        sync_vars = self._generate_syntactic_variants(orig_q, context) + self._generate_contextual_variants(orig_q, context)
        llm_vars = [] 
        try: llm_results = await asyncio.gather(llm_task); llm_vars = llm_results[0] if llm_results else []
        except Exception as e: logger.error(f"Err gathering LLM expansion: {e}"); res.error_message = f"LLM expansion fail: {e}"
        all_vars = llm_vars + sync_vars; res.total_variants_generated = len(all_vars)
        final_vars = self._filter_and_rank_variants(all_vars, orig_q); res.expanded_queries = final_vars
        if final_vars: res.quality_score = sum(v.confidence for v in final_vars) / len(final_vars)
        res.expansion_time = time.monotonic() - start
        logger.info(f"Q_exp for '{orig_q}' done in {res.expansion_time:.2f}s. Gen {len(final_vars)} variants.")
        if cache_key and not res.error_message:
            try: await asyncio.to_thread(self.cache.set, cache_key, res, expire=settings.cache_ttl_seconds); logger.info(f"Cached q_exp result key: {cache_key}")
            except Exception as e: logger.warning(f"Cache set fail q_exp: {e}")
        return res
