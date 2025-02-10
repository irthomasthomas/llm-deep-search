"""Tests for the deep research module."""

import pytest
from datetime import datetime
from llm_search.deep_research import (
    DeepResearcher,
    SearchPath,
    ResearchContext,
    ResearchResult
)

def test_researcher_initialization():
    """Test DeepResearcher initialization"""
    researcher = DeepResearcher(max_depth=4)
    assert researcher.max_depth == 4
    assert researcher.max_workers == 4
    assert researcher.timeout == 300.0

def test_subquery_generation():
    """Test subquery generation"""
    researcher = DeepResearcher()
    context = ResearchContext(
        original_query="test query",
        explored_queries=set(),
        search_paths=[],
        max_depth=3,
        start_time=datetime.now(),
        timeout=30.0
    )
    
    subqueries = researcher._generate_subqueries("python testing", context)
    assert len(subqueries) > 0
    assert all(isinstance(q, str) for q in subqueries)
    assert "python testing" not in subqueries  # Should not include original query

def test_path_relevance():
    """Test path relevance analysis"""
    researcher = DeepResearcher()
    context = ResearchContext(
        original_query="python testing",
        explored_queries=set(),
        search_paths=[],
        max_depth=3,
        start_time=datetime.now(),
        timeout=30.0
    )
    
    relevance = researcher._analyze_path_relevance(
        "python testing methods",
        "python testing",
        context
    )
    assert 0 <= relevance <= 1
    assert relevance > 0.5  # Should be relevant

def test_query_exploration():
    """Test query exploration"""
    researcher = DeepResearcher(max_depth=2)
    context = ResearchContext(
        original_query="python testing",
        explored_queries=set(),
        search_paths=[],
        max_depth=2,
        start_time=datetime.now(),
        timeout=30.0
    )
    
    paths = researcher._explore_query("python testing", context)
    assert len(paths) > 0
    assert all(isinstance(p, SearchPath) for p in paths)
    assert all(p.depth <= 2 for p in paths)

def test_deep_research():
    """Test complete research process"""
    researcher = DeepResearcher(max_depth=2, timeout=30.0)
    result = researcher.research("python testing")
    
    assert isinstance(result, ResearchResult)
    assert "root" in result.query_tree
    assert len(result.key_findings) > 0
    assert len(result.evidence) > 0
    assert 0 <= result.confidence_score <= 1
    assert result.research_time > 0

def test_research_timeout():
    """Test research timeout handling"""
    researcher = DeepResearcher(timeout=0.001)
    with pytest.raises(TimeoutError):
        researcher.research("python testing")

def test_duplicate_query_prevention():
    """Test prevention of duplicate query exploration"""
    researcher = DeepResearcher()
    context = ResearchContext(
        original_query="test",
        explored_queries={"test query"},
        search_paths=[],
        max_depth=3,
        start_time=datetime.now(),
        timeout=30.0
    )
    
    subqueries = researcher._generate_subqueries("test query", context)
    assert len(subqueries) == 0

def test_concurrent_exploration():
    """Test concurrent query exploration"""
    researcher = DeepResearcher(max_workers=4)
    start_time = datetime.now()
    result = researcher.research("python testing")
    execution_time = (datetime.now() - start_time).total_seconds()
    
    assert execution_time < 5.0  # Should complete quickly with parallel execution
    assert len(result.exploration_paths) > 0

def test_evidence_gathering():
    """Test evidence gathering"""
    researcher = DeepResearcher()
    context = ResearchContext(
        original_query="test query",
        explored_queries=set(),
        search_paths=[],
        max_depth=3,
        start_time=datetime.now(),
        timeout=30.0
    )
    paths = [
        SearchPath(
            query="test query",
            parent_query=None,
            depth=0,
            relevance_score=0.8,
            timestamp=datetime.now()
        )
    ]
    
    evidence = researcher._gather_evidence(paths, context)
    assert len(evidence) > 0
    assert all(isinstance(e, dict) for e in evidence)
    assert all("evidence" in e for e in evidence)
    assert all("confidence" in e for e in evidence)
