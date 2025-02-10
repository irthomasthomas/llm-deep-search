"""Tests for the llm_search module."""

import pytest
from llm_search.llm_search import (
    call_llm,
    google_search,
    bing_search,
    generate_summary,
    process_single_url,
    search,
    filter_search_results
)

def test_call_llm_success():
    """Test that call_llm returns a string when a valid model is used."""
    result = call_llm("Say hello", "You are a helpful assistant.", ["cerebras-llama3.3-70b"])
    assert isinstance(result, str)
    assert len(result) > 0

def test_call_llm_failure():
    """Test that call_llm returns an error message when all models fail."""
    result = call_llm("Say hello", "You are a helpful assistant.", ["invalid-model"])
    assert "Error: All LLM models failed" in result

def test_google_search():
    """Test Google search functionality"""
    query = "python testing"
    results = google_search(query)
    assert isinstance(results, list)
    assert len(results) > 0
    assert all(isinstance(result, dict) for result in results)

def test_bing_search():
    """Test Bing search functionality"""
    query = "python testing"
    results = bing_search(query)
    assert isinstance(results, list)
    assert len(results) > 0
    assert all(isinstance(result, dict) for result in results)

def test_generate_summary():
    """Test summary generation"""
    text = "This is a test text that needs to be summarized."
    summary = generate_summary(text)
    assert isinstance(summary, str)
    assert len(summary) > 0

def test_process_single_url():
    """Test URL processing"""
    url = "https://www.python.org"
    result = process_single_url(url)
    assert isinstance(result, dict)
    assert "title" in result
    assert "content" in result
    assert "url" in result

def test_search_integration():
    """Test the main search function"""
    query = "python unit testing best practices"
    results = search(query)
    assert isinstance(results, dict)
    assert "search_results" in results
    assert "summary" in results

def test_filter_search_results():
    """Test the search results filtering"""
    results = [
        {"snippet": "Python testing is important", "title": "Test 1"},
        {"snippet": "Unrelated content", "title": "Test 2"},
        {"snippet": "More Python testing info", "title": "Test 3"},
    ]
    filtered = filter_search_results(results, "python", threshold=0.7)
    assert len(filtered) >= 2  # Should find at least 2 Python-related results
    assert len(filtered) < len(results)  # Should filter out some results
    assert all("python" in result["snippet"].lower() for result in filtered)

@pytest.mark.parametrize("query", [
    "",
    "   ",
    None,
    123,
    ["invalid"],
])
def test_search_invalid_input(query):
    """Test search function with invalid inputs"""
    with pytest.raises(ValueError):
        search(query)

def test_search_timeout():
    """Test search function timeout handling"""
    with pytest.raises(TimeoutError):
        search("python testing", timeout=0.001)

def test_rate_limit_handling():
    """Test rate limit handling"""
    queries = ["test1", "test2", "test3"]
    for query in queries:
        result = search(query)
        assert isinstance(result, dict)
        assert "error" not in result

def test_parallel_search():
    """Test that parallel search processes results correctly"""
    result = search("test")
    assert isinstance(result, dict)
    assert "search_results" in result
    assert "summary" in result
    assert len(result["search_results"]) > 0
