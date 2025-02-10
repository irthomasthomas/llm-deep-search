"""Tests for the query expansion system."""

import pytest
from datetime import datetime
from llm_search.query_expansion import (
    QueryExpander,
    QueryVariant,
    ExpansionResult,
    ExpansionType
)

class MockCache:
    def __init__(self):
        self.store = {}
    
    def get(self, key, default=None):
        return self.store.get(key, default)
    
    def set(self, key, value):
        self.store[key] = value

class MockLLMIntegration:
    def generate_response(self, prompt, task_type=None, required_capabilities=None):
        class MockResponse:
            error = None
            content = "Mock LLM response"
        return MockResponse()

@pytest.fixture
def expander():
    """Create QueryExpander instance for testing"""
    return QueryExpander()

@pytest.fixture
def llm_integration():
    """Create mock LLM integration"""
    return MockLLMIntegration()

@pytest.fixture
def cache():
    """Create mock cache"""
    return MockCache()

def test_basic_expansion(expander):
    """Test basic query expansion"""
    result = expander.expand_query("python testing")
    
    assert isinstance(result, ExpansionResult)
    assert result.original_query == "python testing"
    assert len(result.expanded_queries) > 0
    assert all(isinstance(q, QueryVariant) for q in result.expanded_queries)
    assert result.expansion_time > 0
    assert 0 <= result.quality_score <= 1

def test_semantic_variants(expander):
    """Test semantic query variation generation"""
    variants = expander._generate_semantic_variants(
        "python testing",
        {"domain": "programming"}
    )
    
    assert len(variants) > 0
    assert all(v.expansion_type == ExpansionType.SEMANTIC for v in variants)
    assert all(v.confidence >= expander.min_confidence for v in variants)

def test_syntactic_variants(expander):
    """Test syntactic query variation generation"""
    variants = expander._generate_syntactic_variants(
        "python testing",
        {"domain": "programming"}
    )
    
    assert len(variants) > 0
    assert all(v.expansion_type == ExpansionType.SYNTACTIC for v in variants)
    assert any('"python testing"' in v.query for v in variants)  # Exact match variant

def test_contextual_variants(expander):
    """Test context-aware query variation generation"""
    context = {
        "domain": "programming",
        "recent_queries": ["unit testing"],
        "preferences": {"language": "python"}
    }
    
    variants = expander._generate_contextual_variants(
        "python testing",
        context
    )
    
    assert len(variants) > 0
    assert all(v.expansion_type == ExpansionType.CONTEXTUAL for v in variants)
    assert any("tutorial" in v.query.lower() for v in variants)

def test_variant_filtering(expander):
    """Test query variant filtering"""
    variants = [
        QueryVariant("test query 1", ExpansionType.SEMANTIC, 0.9, "test", None, {}),
        QueryVariant("test query 2", ExpansionType.SEMANTIC, 0.8, "test", None, {}),
        QueryVariant("test query 1", ExpansionType.SYNTACTIC, 0.7, "test", None, {}),  # Duplicate
        QueryVariant("bad query", ExpansionType.SEMANTIC, 0.6, "test", None, {}),  # Low confidence
    ]
    
    context = {
        "excluded_terms": {"bad"},
        "required_terms": {"test"}
    }
    
    filtered = expander._filter_variants(variants, context)
    
    assert len(filtered) < len(variants)  # Should remove duplicates and low confidence
    assert all(v.confidence >= expander.min_confidence for v in filtered)
    assert not any("bad" in v.query.lower() for v in filtered)

def test_domain_specific_expansion(expander):
    """Test domain-specific query expansion"""
    context = {"domain": "programming"}
    result = expander.expand_query("python testing", context=context)
    
    programming_terms = ["tutorial", "example", "documentation"]
    
    # Verify we have domain-specific expansions
    contextual_variants = [v for v in result.expanded_queries 
                         if v.expansion_type == ExpansionType.CONTEXTUAL]
    assert len(contextual_variants) > 0
    
    # Check for programming-specific terms
    has_domain_terms = False
    for variant in result.expanded_queries:
        for term in programming_terms:
            if term in variant.query.lower():
                has_domain_terms = True
                break
        if has_domain_terms:
            break
    
    assert has_domain_terms, f"No programming terms found in variants: {[v.query for v in result.expanded_queries]}"

def test_empty_query_handling(expander):
    """Test empty query handling"""
    result = expander.expand_query("")
    
    assert len(result.expanded_queries) == 0
    assert result.quality_score == 0

def test_max_variants_limit(expander):
    """Test maximum variants limit"""
    expander.max_variants = 3
    result = expander.expand_query("python testing")
    
    assert len(result.expanded_queries) <= expander.max_variants

def test_confidence_threshold(expander):
    """Test confidence threshold filtering"""
    expander.min_confidence = 0.8
    result = expander.expand_query("python testing")
    
    assert all(v.confidence >= expander.min_confidence 
              for v in result.expanded_queries)

def test_context_preservation(expander):
    """Test context information preservation"""
    context = {
        "domain": "programming",
        "recent_queries": ["unit testing"],
        "preferences": {"language": "python"}
    }
    
    result = expander.expand_query("python testing", context)
    
    assert result.context_used == context
    assert all(v.context == context for v in result.expanded_queries)

def test_llm_integration(expander, llm_integration):
    """Test LLM integration for semantic expansion"""
    expander.llm = llm_integration
    result = expander.expand_query("python testing")
    
    semantic_variants = [v for v in result.expanded_queries 
                        if v.expansion_type == ExpansionType.SEMANTIC]
    
    assert len(semantic_variants) > 0
    assert all(v.source == "llm" for v in semantic_variants)

def test_cache_integration(expander, cache):
    """Test cache integration"""
    expander.cache = cache
    query = "test query"
    context = {"test": "context"}
    
    # First request
    result1 = expander.expand_query(query, context)
    expansion_time1 = result1.expansion_time
    
    # Second request (should hit cache)
    result2 = expander.expand_query(query, context)
    expansion_time2 = result2.expansion_time
    
    assert result1.expanded_queries == result2.expanded_queries
    assert len(cache.store) > 0  # Cache should be used
