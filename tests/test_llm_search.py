import pytest
from llm_search.llm_search import call_llm

def test_call_llm_success():
    """Test that call_llm returns a string when a valid model is used."""
    result = call_llm("Say hello", "You are a helpful assistant.", models=["cerebras-llama3.3-70b"])
    assert isinstance(result, str)
    assert len(result) > 0

def test_call_llm_failure():
    """Test that call_llm returns an error message when all models fail."""
    result = call_llm("Say hello", "You are a helpful assistant.", models=["invalid-model"])
    assert "Error: All LLM models failed" in result

