"""Tests for the fast filtering system."""

import pytest
from llm_search.fast_filter import FastFilter, FilterResult

def test_filter_initialization():
    """Test FastFilter initialization"""
    filter = FastFilter(threshold=0.8)
    assert filter.threshold == 0.8
    assert filter.max_workers == 4

def test_single_content_scoring():
    """Test scoring of single content piece"""
    filter = FastFilter()
    result = filter._score_content("This is a test about Python", "python")
    assert isinstance(result, FilterResult)
    assert result.relevance_score >= 0
    assert result.relevance_score <= 1
    assert result.confidence > 0
    assert result.filtering_time > 0

def test_batch_filtering():
    """Test parallel batch filtering"""
    filter = FastFilter()
    contents = [
        "Python is a programming language",
        "Cats are cute animals",
        "Python scripts can be fast",
        "Weather is nice today"
    ]
    results = filter.filter_batch(contents, "python")
    assert len(results) > 0
    assert all(isinstance(r, FilterResult) for r in results)
    assert all(r.relevance_score >= filter.threshold for r in results)

def test_stream_filtering():
    """Test content stream filtering"""
    filter = FastFilter()
    stream = iter([
        "Python code example",
        "Random text",
        "More Python content",
    ])
    results = list(filter.filter_stream(stream, "python"))
    assert len(results) > 0
    assert all(isinstance(r, FilterResult) for r in results)
    assert all(r.relevance_score >= filter.threshold for r in results)

def test_threshold_filtering():
    """Test threshold-based filtering"""
    filter = FastFilter(threshold=0.9)  # High threshold
    content = "This is unrelated content"
    result = filter._score_content(content, "python")
    assert result.relevance_score < filter.threshold

def test_parallel_performance():
    """Test performance of parallel filtering"""
    import time
    filter = FastFilter(max_workers=4)
    large_content_list = ["Test content"] * 100
    
    start_time = time.time()
    results = filter.filter_batch(large_content_list, "test")
    execution_time = time.time() - start_time
    
    assert execution_time < 2.0  # Should complete quickly
    assert len(results) > 0
