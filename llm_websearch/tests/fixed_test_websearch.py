import pytest
from unittest.mock import patch, MagicMock
import httpx
import json
from llm_websearch import (
    search, deep_search, google_search, bing_search,
    SearchResult, ProcessedResult, SearchError, fetch_and_summarize
)
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
@patch("llm_websearch.httpx.Client")
@patch("llm_websearch.BeautifulSoup")
@patch("llm_websearch.llm.get_model")
def test_fetch_and_summarize(mock_get_model, mock_bs, mock_client):
    mock_response = MagicMock()
    mock_response.text = "<html><body>Test content</body></html>"
    mock_client.return_value.__enter__.return_value.get.return_value = mock_response

    mock_bs.return_value.get_text.return_value = "Test content"

    # Create mock model and response
    mock_model = MagicMock()
    mock_response = MagicMock()
    mock_response.text.return_value = "Summarized content"
    mock_model.prompt.return_value = mock_response
    mock_get_model.return_value = mock_model

    result = fetch_and_summarize("https://example.com", "test query")

    assert result == "Summarized content"

# Test deep_search function
@patch("llm_websearch.search")
@patch("llm_websearch.fetch_and_summarize")
@patch("llm_websearch.llm.get_model")
def test_deep_search(mock_get_model, mock_fetch_and_summarize, mock_search):
    mock_search_results = [
        SearchResult("https://example1.com", "Example 1", "Snippet 1", 0, "google"),
        SearchResult("https://example2.com", "Example 2", "Snippet 2", 1, "bing")
    ]
    mock_search.return_value = mock_search_results

    mock_fetch_and_summarize.side_effect = ["Summary 1", "Summary 2"]

    # Create mock model and response
    mock_model = MagicMock()
    mock_response = MagicMock()
    mock_response.text.return_value = "Overall summary"
    mock_model.prompt.return_value = mock_response
    mock_get_model.return_value = mock_model

    result = deep_search("test query", num_results=2)

    assert result["query"] == "test query"
    assert len(result["results"]) == 2
    assert result["results"][0]["url"] == "https://example1.com"
    assert result["results"][1]["url"] == "https://example2.com"
    assert result["summary"] == "Overall summary"

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
    assert all(isinstance(r, dict) for r in results)
    assert all(r["source"] == "mock" for r in results)

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
      "query": "test",
      "results": "results",
      "summary": "summary",
      "themes": "themes",
      "contradictions": "contradictions",
      "iterative_results": "iterative results",
      "analysis": "analysis"
    }
    mock_deep_search.return_value = mock_result
    result = cli_runner.invoke(llm.cli, ["websearch", "deep-search", "test query"])

    assert result.exit_code == 0
    assert "test" in result.output
    assert "summary" in result.output
