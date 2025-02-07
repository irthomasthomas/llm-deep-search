import pytest
from llm_search import llm_search


def test_imports():
    assert hasattr(llm_search, "search")
    assert hasattr(llm_search, "google_search")
    assert hasattr(llm_search, "bing_search")
    assert hasattr(llm_search, "generate_summary")
    assert hasattr(llm_search, "process_single_url")

