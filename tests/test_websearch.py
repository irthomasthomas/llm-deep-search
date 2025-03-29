"""Unit tests for LLM-WebSearch module."""

import pytest
from unittest.mock import patch, MagicMock
import httpx
import json
from datetime import datetime

# Import directly from __init__ module since the functions aren't in core.py
from llm_websearch import (
    search, deep_search, google_search, bing_search,
    fetch_and_summarize, SearchResult, ProcessedResult, SearchError
)

# Import core components
from llm_websearch.core import cache
from llm_websearch.llm_integration import LLMResponse

# Import for CLI testing
from click.testing import CliRunner
import llm

# Mock environment variables
@pytest.fixture(autouse=True)
def mock_env_vars(monkeypatch):
    monkeypatch.setenv("GOOGLE_SEARCH_KEY", "mock_google_key")
    monkeypatch.setenv("GOOGLE_SEARCH_ID", "mock_google_id")
    monkeypatch.setenv("BING_CUSTOM_SEARCH_KEY", "mock_bing_key")

# Mock httpx.Client for API calls
@pytest.fixture
def mock_httpx_client():
    with patch("httpx.Client") as mock_client:
        yield mock_client

# Mock LLMIntegration for testing
@pytest.fixture
def mock_llm_integration():
    mock_llm = MagicMock()
    mock_llm.generate_response.return_value = LLMResponse(
        content="Mock LLM response",
        model_used="mock-model",
        tokens_used=10,
        processing_time=0.1,
        confidence_score=0.9,
        quality_metrics={"length_score": 0.9, "format_score": 1.0, "elements_score": 0.9},
        timestamp=datetime.now(),
        error=None
    )
    return mock_llm

# Test google_search function
def test_google_search(mock_httpx_client):
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "items": [
            {
                "link": "https://example.com",
                "title": "Example",
                "snippet": "This is an example"
            }
        ]
    }
    mock_response.raise_for_status.return_value = None
    mock_httpx_client.return_value.__enter__.return_value.get.return_value = mock_response

    results = google_search("test query", num_results=1)
    
    assert len(results) == 1
    assert isinstance(results[0], SearchResult)
    assert results[0].url == "https://example.com"
    assert results[0].title == "Example"
    assert results[0].snippet == "This is an example"
    assert results[0].source == "google"

# Test bing_search function
def test_bing_search(mock_httpx_client):
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "webPages": {
            "value": [
                {
                    "url": "https://example.com",
                    "name": "Example",
                    "snippet": "This is an example"
                }
            ]
        }
    }
    mock_response.raise_for_status.return_value = None
    mock_httpx_client.return_value.__enter__.return_value.get.return_value = mock_response

    results = bing_search("test query", num_results=1)
    
    assert len(results) == 1
    assert isinstance(results[0], SearchResult)
    assert results[0].url == "https://example.com"
    assert results[0].title == "Example"
    assert results[0].snippet == "This is an example"
    assert results[0].source == "bing"

# Test search function
@patch("llm_websearch.google_search")
@patch("llm_websearch.bing_search")
def test_search(mock_bing_search, mock_google_search):
    mock_google_result = SearchResult("https://google.com", "Google Result", "Google snippet", 0, "google")
    mock_bing_result = SearchResult("https://bing.com", "Bing Result", "Bing snippet", 1, "bing")
    
    mock_google_search.return_value = [mock_google_result]
    mock_bing_search.return_value = [mock_bing_result]

    results = search("test query", num_results=2)

    assert len(results) == 2
    assert results[0].source == "google"
    assert results[1].source == "bing"

# Test fetch_and_summarize function
@patch("httpx.Client")
@patch("llm_websearch.BeautifulSoup")
def test_fetch_and_summarize(mock_bs, mock_client, mock_llm_integration):
    mock_response = MagicMock()
    mock_response.text = "<html><body>Test content</body></html>"
    mock_response.raise_for_status.return_value = None
    mock_client.return_value.__enter__.return_value.get.return_value = mock_response

    mock_soup = MagicMock()
    mock_soup.get_text.return_value = "Test content"
    mock_bs.return_value = mock_soup

    # Configure LLM response for summarization
    mock_llm_integration.generate_response.return_value = LLMResponse(
        content="Summarized content",
        model_used="mock-model",
        tokens_used=10,
        processing_time=0.1,
        confidence_score=0.9,
        quality_metrics={"length_score": 0.9},
        timestamp=datetime.now()
    )

    result = fetch_and_summarize("https://example.com", "test query", llm_integration=mock_llm_integration)

    assert result == "Summarized content"
    assert mock_llm_integration.generate_response.called

# Test error handling
def test_google_search_error(mock_httpx_client):
    mock_httpx_client.return_value.__enter__.return_value.get.side_effect = httpx.RequestError("Network error")

    with pytest.raises(SearchError):
        google_search("test query")

def test_bing_search_error(mock_httpx_client):
    mock_httpx_client.return_value.__enter__.return_value.get.side_effect = httpx.RequestError("Network error")

    with pytest.raises(SearchError):
        bing_search("test query")

# Test fallback to mock results
@patch("llm_websearch.google_search", side_effect=SearchError("Google error"))
@patch("llm_websearch.bing_search", side_effect=SearchError("Bing error"))
def test_search_fallback_to_mock(mock_bing_search, mock_google_search):
    results = search("test query", num_results=2)

    assert len(results) == 2
    assert all(isinstance(r, SearchResult) for r in results)
    assert all(r.source == "mock" for r in results)

# Test deep_search basic functionality
@patch("llm_websearch.search")
@patch("llm_websearch.LLMIntegration")
def test_deep_search_basic(mock_llm_integration_class, mock_search):
    # Setup search results
    mock_search_results = [
        SearchResult("https://example1.com", "Example 1", "Snippet 1", 0, "google"),
        SearchResult("https://example2.com", "Example 2", "Snippet 2", 1, "bing")
    ]
    mock_search.return_value = mock_search_results
    
    # Mock LLMIntegration for different request types
    def mock_generate_response(prompt, system_prompt, task_type, required_capabilities=None):
        responses = {
            "subquery_generation": LLMResponse(
                content="['subquery1', 'subquery2']",
                model_used="mock-model",
                tokens_used=10,
                processing_time=0.1,
                confidence_score=0.9,
                quality_metrics={},
                timestamp=datetime.now()
            ),
            "theme_extraction": LLMResponse(
                content="Theme 1
Theme 2",
                model_used="mock-model",
                tokens_used=10,
                processing_time=0.1,
                confidence_score=0.9,
                quality_metrics={},
                timestamp=datetime.now()
            ),
            "summarization": LLMResponse(
                content="Summarized content",
                model_used="mock-model",
                tokens_used=10,
                processing_time=0.1,
                confidence_score=0.9,
                quality_metrics={},
                timestamp=datetime.now()
            ),
            "relevance_analysis": LLMResponse(
                content="0.85",
                model_used="mock-model",
                tokens_used=10,
                processing_time=0.1,
                confidence_score=0.9,
                quality_metrics={},
                timestamp=datetime.now()
            )
        }
        return responses.get(task_type, responses["summarization"])
    
    mock_llm_instance = MagicMock()
    mock_llm_instance.generate_response.side_effect = mock_generate_response
    mock_llm_integration_class.return_value = mock_llm_instance
    
    # Test deep_search function
    result = deep_search("test query", num_results=2, max_iterations=1)
    
    # Basic validation
    assert isinstance(result, dict)
    assert "query" in result
    assert "key_findings" in result
    
    # Verify LLM was called multiple times for various tasks
    assert mock_llm_instance.generate_response.call_count > 1

# Integration Tests
@pytest.fixture
def cli_runner():
    return CliRunner()

@patch("llm_websearch.search")
def test_search_command(mock_search, cli_runner):
    mock_results = [
        SearchResult("https://example.com/1", "Example 1", "Snippet 1", 0, "google"),
        SearchResult("https://example.com/2", "Example 2", "Snippet 2", 1, "bing"),
    ]
    mock_search.return_value = mock_results

    result = cli_runner.invoke(llm.cli, ["websearch", "search", "test query"])

    assert result.exit_code == 0
    assert "Example 1" in result.output
    assert "https://example.com/1" in result.output
    assert "Example 2" in result.output
    assert "https://example.com/2" in result.output

@patch("llm_websearch.deep_search")
def test_deep_search_command(mock_deep_search, cli_runner):
    mock_result = {
        "query": "test query",
        "key_findings": [
            {"finding": "Finding 1", "confidence": 0.9},
            {"finding": "Finding 2", "confidence": 0.8}
        ],
        "tiered_summaries": {
            "short": "Short summary",
            "medium": "Medium summary",
            "detailed": "Detailed summary"
        },
        "key_insights": ["Insight 1", "Insight 2"],
        "exploration_parameters": {
            "relevance_threshold": 0.7,
            "diminishing_returns_threshold": 0.1
        }
    }
    mock_deep_search.return_value = mock_result
    
    result = cli_runner.invoke(llm.cli, ["websearch", "deep-search", "test query"])

    assert result.exit_code == 0
    assert "test query" in result.output
    assert "Finding 1" in result.output
    assert "Short summary" in result.output
    assert "Insight 1" in result.output

# Test FastFilter
@pytest.mark.skip(reason="Requires full implementation")
def test_fast_filter():
    from llm_websearch.fast_filter import FastFilter
    
    # Initialize with low threshold to ensure results pass filtering
    fast_filter = FastFilter(threshold=0.1)
    
    contents = [
        "This is about artificial intelligence and its impacts.",
        "This is about something completely different."
    ]
    
    query = "artificial intelligence"
    
    results = fast_filter.filter_batch(contents, query)
    
    assert len(results) >= 1
    assert results[0].content == contents[0]
    assert results[0].relevance_score > 0.1

# Test QueryExpander
@pytest.mark.skip(reason="Requires full implementation")
def test_query_expander(mock_llm_integration):
    from llm_websearch.query_expansion import QueryExpander
    
    query_expander = QueryExpander(llm_integration=mock_llm_integration)
    
    # Configure LLM response for query expansion
    mock_llm_integration.generate_response.return_value = LLMResponse(
        content="Expanded query content",
        model_used="mock-model",
        tokens_used=10,
        processing_time=0.1,
        confidence_score=0.9,
        quality_metrics={},
        timestamp=datetime.now()
    )
    
    expanded_result = query_expander.expand_query("artificial intelligence")
    
    assert expanded_result.original_query == "artificial intelligence"
    assert len(expanded_result.expanded_queries) > 0

if __name__ == "__main__":
    pytest.main()
