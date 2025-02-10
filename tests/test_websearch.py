import pytest
import asyncio
from unittest.mock import patch, MagicMock
from llm_websearch import search, deep_search, SearchError

@pytest.mark.asyncio
async def test_search_success():
    mock_google_results = [
        {"title": "Google Result 1", "url": "https://example.com/1", "snippet": "Snippet 1", "source": "google"}
    ]
    mock_bing_results = [
        {"title": "Bing Result 1", "url": "https://example.com/2", "snippet": "Snippet 2", "source": "bing"}
    ]

    with patch('llm_websearch.google_search', return_value=mock_google_results), \
         patch('llm_websearch.bing_search', return_value=mock_bing_results):
        results = await search("test query")
        
    assert len(results) == 2
    assert results[0]["source"] == "google"
    assert results[1]["source"] == "bing"

@pytest.mark.asyncio
async def test_search_fallback_to_mock():
    with patch('llm_websearch.google_search', side_effect=SearchError), \
         patch('llm_websearch.bing_search', side_effect=SearchError):
        results = await search("test query")
        
    assert len(results) == 10
    assert all(result["source"] == "mock" for result in results)

@pytest.mark.asyncio
async def test_search_all_fail():
    with patch('llm_websearch.google_search', side_effect=SearchError), \
         patch('llm_websearch.bing_search', side_effect=SearchError), \
         patch('llm_websearch._mock_search_results', return_value=[]):
        with pytest.raises(SearchError):
            await search("test query")

@pytest.mark.asyncio
async def test_deep_search():
    mock_search_results = [
        {"title": "Result 1", "url": "https://example.com/1", "snippet": "Snippet 1", "source": "google"}
    ]
    
    with patch('llm_websearch.search', return_value=mock_search_results):
        result = await deep_search("test query")
        
    assert result["query"] == "test query"
    assert result["results"] == mock_search_results
    assert result["analysis"] == "Coming soon"

