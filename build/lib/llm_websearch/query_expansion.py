"""Query Expansion module for enhancing search queries with semantic understanding."""

from typing import List, Dict, Optional, Set, Tuple, Any
from dataclasses import dataclass
from datetime import datetime
import threading
from enum import Enum
import json

class ExpansionType(Enum):
    """Types of query expansion"""
    SEMANTIC = "semantic"      # Meaning-based expansion
    SYNTACTIC = "syntactic"    # Structure-based expansion
    CONTEXTUAL = "contextual"  # Context-aware expansion
    DOMAIN = "domain"         # Domain-specific expansion

@dataclass
class QueryVariant:
    """Represents a query variation with metadata"""
    query: str
    expansion_type: ExpansionType
    confidence: float
    source: str
    parent_query: Optional[str] = None
    context: Dict[str, Any] = None

@dataclass
class ExpansionResult:
    """Contains results of query expansion"""
    original_query: str
    expanded_queries: List[QueryVariant]
    expansion_time: float
    total_variants: int
    quality_score: float
    context_used: Dict[str, Any]

class QueryExpander:
    """Advanced query expansion system"""
    
    def __init__(self,
                 llm_integration = None,
                 max_variants: int = 5,
                 min_confidence: float = 0.7,
                 cache_instance = None):
        """Initialize query expander"""
        self.llm = llm_integration
        self.max_variants = max_variants
        self.min_confidence = min_confidence
        self.cache = cache_instance
        self._lock = threading.RLock()
        
        self.domain_templates = {
            "programming": [
                "{query} tutorial",
                "{query} example code",
                "{query} documentation",
                "how to {query}",
                "{query} best practices"
            ],
            "research": [
                "latest research on {query}",
                "{query} methodology",
                "{query} analysis",
                "{query} review",
                "{query} findings"
            ],
            "technical": [
                "{query} architecture",
                "{query} design patterns",
                "{query} implementation",
                "{query} comparison",
                "{query} performance"
            ]
        }
    
    def _generate_semantic_variants(self,
                                  query: str,
                                  context: Dict[str, Any]) -> List[QueryVariant]:
        """Generate semantically related query variants"""
        if not query.strip():
            return []
            
        if self.llm is None:
            return [QueryVariant(
                query=query,
                expansion_type=ExpansionType.SEMANTIC,
                confidence=1.0,
                source="original",
                context=context
            )]
        
        # Use LLM to generate semantic variations
        prompt = f"""Generate semantic variations of the query: "{query}"
Consider synonyms, related concepts, and alternative phrasings.
Context: {json.dumps(context)}
Response format: List of variations with confidence scores."""
        
        response = self.llm.generate_response(
            prompt=prompt,
            task_type="query_expansion",
            required_capabilities=["reasoning"]
        )
        
        variants = []
        if not response.error:
            # Mock processing of LLM response
            variations = [
                (f"{query} alternative approach", 0.9),
                (f"similar to {query}", 0.8),
                (f"{query} equivalent", 0.85)
            ]
            
            for var_query, confidence in variations:
                if confidence >= self.min_confidence:
                    variants.append(QueryVariant(
                        query=var_query,
                        expansion_type=ExpansionType.SEMANTIC,
                        confidence=confidence,
                        source="llm",
                        parent_query=query,
                        context=context
                    ))
        
        return variants[:self.max_variants]
    
    def _generate_syntactic_variants(self,
                                   query: str,
                                   context: Dict[str, Any]) -> List[QueryVariant]:
        """Generate syntactically modified query variants"""
        if not query.strip():
            return []
            
        variants = []
        
        # Basic syntactic transformations
        transformations = [
            (f'"{query}"', 0.95),  # Exact match
            (f"({query})", 0.9),   # Grouped
            (f"{query}*", 0.85),   # Wildcard
        ]
        
        for var_query, confidence in transformations:
            variants.append(QueryVariant(
                query=var_query,
                expansion_type=ExpansionType.SYNTACTIC,
                confidence=confidence,
                source="syntactic",
                parent_query=query,
                context=context
            ))
        
        return variants
    
    def _generate_contextual_variants(self,
                                    query: str,
                                    context: Dict[str, Any]) -> List[QueryVariant]:
        """Generate context-aware query variants"""
        if not query.strip():
            return []
            
        variants = []
        
        # Extract relevant context elements
        domain = context.get("domain", "")
        recent_queries = context.get("recent_queries", [])
        user_preferences = context.get("preferences", {})
        
        # Apply domain-specific templates
        if domain in self.domain_templates:
            templates = self.domain_templates[domain]
            for template in templates:
                expanded_query = template.format(query=query)
                variants.append(QueryVariant(
                    query=expanded_query,
                    expansion_type=ExpansionType.CONTEXTUAL,
                    confidence=0.85,
                    source="domain_template",
                    parent_query=query,
                    context=context
                ))
        
        # Consider recent queries for context
        if recent_queries:
            relevant_query = recent_queries[-1]
            variants.append(QueryVariant(
                query=f"{query} related to {relevant_query}",
                expansion_type=ExpansionType.CONTEXTUAL,
                confidence=0.8,
                source="query_history",
                parent_query=query,
                context=context
            ))
        
        return variants[:self.max_variants]
    
    def _filter_variants(self,
                        variants: List[QueryVariant],
                        context: Dict[str, Any]) -> List[QueryVariant]:
        """Filter and rank query variants"""
        # Remove duplicates while preserving order
        seen = set()
        unique_variants = []
        for variant in variants:
            if variant.query not in seen and variant.query.strip():
                seen.add(variant.query)
                unique_variants.append(variant)
        
        # Sort by confidence
        unique_variants.sort(key=lambda x: x.confidence, reverse=True)
        
        # Apply context-based filtering
        filtered_variants = []
        excluded_terms = context.get("excluded_terms", set())
        required_terms = context.get("required_terms", set())
        
        for variant in unique_variants:
            # Skip variants with excluded terms
            if any(term in variant.query.lower() for term in excluded_terms):
                continue
            
            # Ensure required terms are present
            if not required_terms or all(term in variant.query.lower() for term in required_terms):
                filtered_variants.append(variant)
        
        return filtered_variants[:self.max_variants]
    
    def expand_query(self,
                    query: str,
                    context: Optional[Dict[str, Any]] = None) -> ExpansionResult:
        """Expand query using multiple strategies"""
        start_time = datetime.now()
        context = context or {}
        
        # Handle empty query
        if not query.strip():
            return ExpansionResult(
                original_query=query,
                expanded_queries=[],
                expansion_time=0.0,
                total_variants=0,
                quality_score=0.0,
                context_used=context
            )
        
        # Try cache first
        if self.cache:
            cache_key = f"query_expansion_{hash(query)}_{hash(str(sorted(context.items())))}"
            cached_result = self.cache.get(cache_key, None)
            if cached_result:
                return cached_result
        
        # Generate variants using different strategies
        semantic_variants = self._generate_semantic_variants(query, context)
        syntactic_variants = self._generate_syntactic_variants(query, context)
        contextual_variants = self._generate_contextual_variants(query, context)
        
        # Combine all variants with domain-specific ones first
        all_variants = contextual_variants + semantic_variants + syntactic_variants
        
        # Filter and rank variants
        filtered_variants = self._filter_variants(all_variants, context)
        
        # Calculate quality score
        quality_score = sum(v.confidence for v in filtered_variants) / len(filtered_variants) if filtered_variants else 0
        
        result = ExpansionResult(
            original_query=query,
            expanded_queries=filtered_variants,
            expansion_time=(datetime.now() - start_time).total_seconds(),
            total_variants=len(filtered_variants),
            quality_score=quality_score,
            context_used=context
        )
        
        # Cache result
        if self.cache and filtered_variants:
            self.cache.set(cache_key, result)
        
        return result