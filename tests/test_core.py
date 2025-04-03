"""Tests for core functionality and search engine integration (Phase 3 focus)."""

import pytest
import httpx # Import httpx to check for its exceptions
from unittest.mock import patch # Added for patching internal functions

# Import components and models to test/use
from llm_websearch.search_engines import google_search, bing_search
from llm_websearch.core import search
from llm_websearch.models import SearchResult, SearchEngineError
from llm_websearch.config import settings # Import settings for API keys

# Set mock API keys for tests directly or via fixture
@pytest.fixture(autouse=True)
def setup_settings(monkeypatch):
    # Ensure API keys are set for tests, otherwise search functions will raise errors early
    monkeypatch.setattr(settings, 'google_api_key', 'mock_google_key', raising=False)
    monkeypatch.setattr(settings, 'google_cse_id', 'mock_google_cse_id', raising=False)
    monkeypatch.setattr(settings, 'bing_api_key', 'mock_bing_key', raising=False)
    monkeypatch.setattr(settings, 'bing_custom_config_id', 'mock_bing_config_id', raising=False)
    # Disable cache for most tests unless specifically testing caching
    monkeypatch.setattr(settings, 'cache_enabled', False, raising=False)

# --- Tests for Search Engines (using respx) --- 

@pytest.mark.asyncio
async def test_google_search_success(respx_mock):
    """Test successful google_search call."""
    query = "test query"
    num_results = 1
    google_url = "https://www.googleapis.com/customsearch/v1"
    
    mock_response_data = {
        "items": [
            {"link": "https://example.com/g1", "title": "Google Result 1", "snippet": "Snippet G1"}
        ]
    }
    respx_mock.get(google_url).mock(return_value=httpx.Response(200, json=mock_response_data))

    results = await google_search(query, num_results=num_results)

    assert len(results) == num_results
    assert isinstance(results[0], SearchResult)
    assert results[0].url == "https://example.com/g1"
    assert results[0].title == "Google Result 1"
    assert results[0].snippet == "Snippet G1"
    assert results[0].engine == "google"
    assert results[0].query == query
    assert results[0].metadata.get('rank') == 1 

@pytest.mark.asyncio
async def test_google_search_api_error(respx_mock):
    """Test google_search handling API error status."""
    query = "test query"
    google_url = "https://www.googleapis.com/customsearch/v1"
    respx_mock.get(google_url).mock(return_value=httpx.Response(403, json={"error": "forbidden"}))

    with pytest.raises(SearchEngineError) as excinfo:
        await google_search(query)
    assert excinfo.value.engine == "google"
    assert excinfo.value.status_code == 403
    assert "403" in str(excinfo.value)

@pytest.mark.asyncio
async def test_google_search_request_error(respx_mock):
    """Test google_search handling network/request error."""
    query = "test query"
    google_url = "https://www.googleapis.com/customsearch/v1"
    respx_mock.get(google_url).mock(side_effect=httpx.RequestError("Network error"))

    with pytest.raises(SearchEngineError) as excinfo:
        await google_search(query)
    assert excinfo.value.engine == "google"
    assert isinstance(excinfo.value.original_exception, httpx.RequestError)

@pytest.mark.asyncio
async def test_bing_search_success(respx_mock):
    """Test successful bing_search call."""
    query = "test query"
    num_results = 1
    bing_url = "https://api.bing.microsoft.com/v7.0/custom/search"
    
    mock_response_data = {
        "webPages": {
            "value": [
                {"url": "https://example.com/b1", "name": "Bing Result 1", "snippet": "Snippet B1"}
            ],
            "totalEstimatedMatches": 10
        }
    }
    respx_mock.get(bing_url).mock(return_value=httpx.Response(200, json=mock_response_data))

    results = await bing_search(query, num_results=num_results)

    assert len(results) == num_results
    assert isinstance(results[0], SearchResult)
    assert results[0].url == "https://example.com/b1"
    assert results[0].title == "Bing Result 1"
    assert results[0].snippet == "Snippet B1"
    assert results[0].engine == "bing"
    assert results[0].query == query
    assert results[0].metadata.get('rank') == 1 

@pytest.mark.asyncio
async def test_bing_search_api_error(respx_mock):
    """Test bing_search handling API error status."""
    query = "test query"
    bing_url = "https://api.bing.microsoft.com/v7.0/custom/search"
    respx_mock.get(bing_url).mock(return_value=httpx.Response(401, json={"error": "unauthorized"}))

    with pytest.raises(SearchEngineError) as excinfo:
        await bing_search(query)
    assert excinfo.value.engine == "bing"
    assert excinfo.value.status_code == 401
    assert "401" in str(excinfo.value)

@pytest.mark.asyncio
async def test_bing_search_request_error(respx_mock):
    """Test bing_search handling network/request error."""
    query = "test query"
    bing_url = "https://api.bing.microsoft.com/v7.0/custom/search"
    respx_mock.get(bing_url).mock(side_effect=httpx.ConnectError("Connection failed"))

    with pytest.raises(SearchEngineError) as excinfo:
        await bing_search(query)
    assert excinfo.value.engine == "bing"
    assert isinstance(excinfo.value.original_exception, httpx.ConnectError)

# --- Tests for Core Search Orchestration --- 

@pytest.mark.asyncio
@patch("llm_websearch.search_engines.google.google_search") 
@patch("llm_websearch.search_engines.bing.bing_search")
async def test_core_search_success(mock_bing_search, mock_google_search):
    """Test core.search combines results from mocked engines."""
    query = "combined query"
    mock_google_results = [
        SearchResult(url="https://g.com/1", title="G1", snippet="GS1", query=query, engine="google", metadata={'rank': 1})
    ]
    mock_bing_results = [
        SearchResult(url="https://b.com/1", title="B1", snippet="BS1", query=query, engine="bing", metadata={'rank': 1})
    ]
    mock_google_search.return_value = mock_google_results
    mock_bing_search.return_value = mock_bing_results

    results = await search(query, num_results=2)

    assert len(results) == 2
    engines = {r.engine for r in results}
    assert "google" in engines
    assert "bing" in engines
    mock_google_search.assert_awaited_once()
    mock_bing_search.assert_awaited_once()

@pytest.mark.asyncio
@patch("llm_websearch.search_engines.google.google_search")
@patch("llm_websearch.search_engines.bing.bing_search")
async def test_core_search_one_engine_fails(mock_bing_search, mock_google_search):
    """Test core.search handles failure of one engine gracefully."""
    query = "one fails query"
    mock_google_results = [
        SearchResult(url="https://g.com/1", title="G1", snippet="GS1", query=query, engine="google", metadata={'rank': 1})
    ]
    mock_google_search.return_value = mock_google_results
    mock_bing_search.side_effect = SearchEngineError(engine="bing", query=query, message="Bing failed")

    results = await search(query, num_results=2)

    assert len(results) == 1
    assert results[0].engine == "google"
    mock_google_search.assert_awaited_once()
    mock_bing_search.assert_awaited_once()

@pytest.mark.asyncio
@patch("llm_websearch.search_engines.google.google_search")
@patch("llm_websearch.search_engines.bing.bing_search")
async def test_core_search_all_engines_fail(mock_bing_search, mock_google_search):
    """Test core.search returns empty list if all engines fail."""
    query = "all fail query"
    mock_google_search.side_effect = SearchEngineError(engine="google", query=query, message="Google failed")
    mock_bing_search.side_effect = SearchEngineError(engine="bing", query=query, message="Bing failed")

    results = await search(query, num_results=2)

    assert len(results) == 0
    mock_google_search.assert_awaited_once()
    mock_bing_search.assert_awaited_once()

# --- Placeholder/Skipped Tests for other functions/components --- 

@pytest.mark.skip(reason="Test needs rewrite for async, mocking, new structure")
@pytest.mark.asyncio
async def test_fetch_and_summarize():
    pass

@pytest.mark.skip(reason="Test needs rewrite for async, mocking, new structure")
@pytest.mark.asyncio
async def test_deep_search_basic():
    pass

@pytest.mark.skip(reason="CLI tests need review after async changes")
def test_search_command():
    pass

@pytest.mark.skip(reason="CLI tests need review after async changes")
def test_deep_search_command():
    pass

