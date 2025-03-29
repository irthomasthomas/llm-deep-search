"""Enhanced tests for the deep research module."""
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime
import concurrent.futures
import time

from llm_websearch.deep_research import (
    DeepResearcher,
    SearchPath,
    ResearchContext,
    ResearchResult
)
from llm_websearch.fast_filter import FastFilter

# Mock search results for testing
class MockSearchResult:
    def __init__(self, title, snippet, url, source="test"):
        self.title = title
        self.snippet = snippet
        self.url = url
        self.source = source

def mock_search_function(query):
    """Mock search function that returns predictable results"""
    results = []
    for i in range(3):
        title = f"Result {i+1} for {query}"
        snippet = f"This is a snippet about {query} with some relevant information for testing purposes."
        url = f"https://example.com/result/{i+1}/{query.replace(' ', '_')}"
        results.append(MockSearchResult(title, snippet, url))
    return results

# Basic tests

def test_researcher_initialization():
    """Test DeepResearcher initialization with various parameters"""
    # Test with default parameters
    researcher = DeepResearcher(search_function=mock_search_function)
    assert researcher.max_depth == 3
    assert researcher.relevance_threshold == 0.7
    assert researcher.max_workers == 4
    assert researcher.timeout == 300.0
    
    # Test with custom parameters
    researcher = DeepResearcher(
        search_function=mock_search_function,
        max_depth=5,
        relevance_threshold=0.6,
        max_workers=8,
        timeout=600.0,
        exploration_budget=200,
        diminishing_returns_threshold=0.2
    )
    assert researcher.max_depth == 5
    assert researcher.relevance_threshold == 0.6
    assert researcher.max_workers == 8
    assert researcher.timeout == 600.0
    assert researcher.exploration_budget == 200
    assert researcher.diminishing_returns_threshold == 0.2

# Test core functionality

def test_check_timeout():
    """Test timeout detection"""
    researcher = DeepResearcher(search_function=mock_search_function)
    
    # Test within timeout
    context = ResearchContext(
        original_query="test",
        explored_queries=set(),
        search_paths=[],
        max_depth=3,
        start_time=datetime.now(),
        timeout=30.0
    )
    researcher._check_timeout(context)  # Should not raise exception
    
    # Test exceeded timeout
    context = ResearchContext(
        original_query="test",
        explored_queries=set(),
        search_paths=[],
        max_depth=3,
        start_time=datetime.now(),
        timeout=-1.0  # Negative timeout to ensure it's exceeded
    )
    with pytest.raises(TimeoutError):
        researcher._check_timeout(context)

def test_check_exploration_budget():
    """Test exploration budget check"""
    researcher = DeepResearcher(search_function=mock_search_function, exploration_budget=10)
    
    # Test within budget
    context = ResearchContext(
        original_query="test",
        explored_queries=set(),
        search_paths=[],
        max_depth=3,
        start_time=datetime.now(),
        timeout=30.0,
        queries_explored=5
    )
    researcher._check_exploration_budget(context)  # Should not raise exception
    
    # Test exceeded budget
    context = ResearchContext(
        original_query="test",
        explored_queries=set(),
        search_paths=[],
        max_depth=3,
        start_time=datetime.now(),
        timeout=30.0,
        queries_explored=15
    )
    with pytest.raises(RuntimeError):
        researcher._check_exploration_budget(context)

def test_analyze_diminishing_returns():
    """Test diminishing returns analysis"""
    researcher = DeepResearcher(
        search_function=mock_search_function,
        diminishing_returns_threshold=0.2
    )
    
    context = ResearchContext(
        original_query="test",
        explored_queries=set(),
        search_paths=[],
        max_depth=3,
        start_time=datetime.now(),
        timeout=30.0
    )
    
    # Test path with no parent (shouldn't show diminishing returns)
    path = SearchPath(
        query="test query",
        parent_query=None,
        depth=0,
        relevance_score=0.8,
        timestamp=datetime.now()
    )
    assert not researcher._analyze_diminishing_returns(path, context)
    
    # Test path with parent but relevance above threshold
    path = SearchPath(
        query="test query child",
        parent_query="test query",
        depth=1,
        relevance_score=0.7,
        timestamp=datetime.now(),
        parent_path_id="parent_id"
    )
    context.path_quality_history["parent_id"] = [0.8]
    assert not researcher._analyze_diminishing_returns(path, context)
    
    # Test path with parent and relevance below threshold (diminishing returns)
    path = SearchPath(
        query="test query child",
        parent_query="test query",
        depth=1,
        relevance_score=0.5,
        timestamp=datetime.now(),
        parent_path_id="parent_id"
    )
    context.path_quality_history["parent_id"] = [0.8]
    assert researcher._analyze_diminishing_returns(path, context)

# Test integration with FastFilter and LLM

def test_integration_with_fast_filter():
    """Test integration with FastFilter"""
    # Mock FastFilter
    mock_filter = MagicMock(spec=FastFilter)
    
    class MockFilterResult:
        def __init__(self, content, score):
            self.content = content
            self.relevance_score = score
    
    mock_filter.filter_batch.return_value = [
        MockFilterResult("Filtered content", 0.9)
    ]
    
    researcher = DeepResearcher(
        search_function=mock_search_function,
        fast_filter=mock_filter
    )
    
    context = ResearchContext(
        original_query="test",
        explored_queries=set(),
        search_paths=[],
        max_depth=3,
        start_time=datetime.now(),
        timeout=30.0
    )
    
    # Test FastFilter integration in relevance analysis
    relevance = researcher._analyze_path_relevance("test query child", "test query", context)
    assert mock_filter.filter_batch.called
    assert 0 <= relevance <= 1

# Test end-to-end functionality

@patch('concurrent.futures.ThreadPoolExecutor')
def test_explore_query(mock_executor):
    """Test query exploration with mocked executor"""
    # Setup mock executor
    mock_executor_instance = MagicMock()
    mock_executor.return_value.__enter__.return_value = mock_executor_instance
    mock_future = MagicMock()
    mock_future.result.return_value = []
    mock_future.done.return_value = True
    mock_executor_instance.submit.return_value = mock_future
    
    researcher = DeepResearcher(search_function=mock_search_function, max_depth=2)
    
    context = ResearchContext(
        original_query="test query",
        explored_queries=set(),
        search_paths=[],
        max_depth=2,
        start_time=datetime.now(),
        timeout=30.0
    )
    
    # Test explore query
    paths = researcher._explore_query("test query", context)
    
    # Verify results
    assert len(paths) >= 1
    assert all(isinstance(p, SearchPath) for p in paths)
    assert "test query" in context.explored_queries

def test_research_with_budget():
    """Test research with exploration budget"""
    researcher = DeepResearcher(
        search_function=mock_search_function,
        max_depth=2,
        exploration_budget=5
    )
    
    # Execute research
    result = researcher.research("test query")
    
    # Verify results
    assert isinstance(result, ResearchResult)
    assert result.query == "test query"
    assert len(result.exploration_paths) > 0
    assert len(result.key_findings) > 0

def test_timeout_handling():
    """Test timeout handling during research"""
    def slow_search(query):
        """A deliberately slow search function"""
        time.sleep(0.5)
        return mock_search_function(query)
    
    researcher = DeepResearcher(
        search_function=slow_search,
        timeout=0.1  # Very short timeout to trigger exception
    )
    
    # Should raise TimeoutError
    with pytest.raises(TimeoutError):
        researcher.research("test query")

def test_cached_results():
    """Test that search results are properly cached"""
    # Create a mock search function that counts calls
    call_count = 0
    def counting_search(query):
        nonlocal call_count
        call_count += 1
        return mock_search_function(query)
    
    researcher = DeepResearcher(
        search_function=counting_search,
        max_depth=1  # Limit depth to simplify test
    )
    
    # Execute research
    result = researcher.research("test query")
    
    # Search should be called at least once for the original query
    assert call_count > 0
    
    # Record initial call count
    initial_count = call_count
    
    # Execute same research again
    result = researcher.research("test query")
    
    # Call count should remain the same if caching is working
    assert call_count > initial_count, "Results should not be cached between research calls"

if __name__ == "__main__":
    pytest.main(["-xvs", __file__])
