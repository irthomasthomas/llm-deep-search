"""Tests for the summarization system."""

import pytest
from llm_search.summarization import (
    Summarizer,
    Summary,
    SummarizationResult
)

class MockLLMIntegration:
    def generate_response(self, prompt, task_type=None, required_capabilities=None):
        class MockResponse:
            error = None
            content = f"Mock LLM response to: {prompt[:20]}..."
            confidence_score = 0.9
        return MockResponse()

@pytest.fixture
def summarizer():
    """Create a Summarizer instance for testing."""
    return Summarizer()

@pytest.fixture
def llm_integration():
    """Create a mock LLM integration for testing."""
    return MockLLMIntegration()

def test_summarizer_initialization(summarizer):
    """Test summarizer initialization."""
    assert summarizer.short_length == 50
    assert summarizer.medium_length == 150
    assert summarizer.long_length == 500
    assert summarizer.min_confidence == 0.7

def test_generate_summary(summarizer):
    """Test summary generation at different levels."""
    content = "This is a test content for summarization. It should generate summaries of different lengths."

    summary_short = summarizer._generate_summary(content, 1)
    assert isinstance(summary_short, Summary)
    assert summary_short.level == 1
    assert len(summary_short.content) > 0

    summary_medium = summarizer._generate_summary(content, 2)
    assert isinstance(summary_medium, Summary)
    assert summary_medium.level == 2
    assert len(summary_medium.content) > 0

    summary_long = summarizer._generate_summary(content, 3)
    assert isinstance(summary_long, Summary)
    assert summary_long.level == 3
    assert len(summary_long.content) > 0

def test_extract_key_insights(summarizer):
    """Test key insights extraction."""
    content = [
        "This is the first content.",
        "This is the second content with more details.",
        "Finally, the third content provides a conclusion."
    ]
    insights = summarizer._extract_key_insights(content)
    assert isinstance(insights, list)
    assert len(insights) > 0

def test_summarize(summarizer):
    """Test the main summarize method."""
    content = [
        "This is a short content.",
        "This is a longer content with more details and information.",
        "This is a third piece of content."
    ]

    result = summarizer.summarize(content)
    assert isinstance(result, SummarizationResult)
    assert result.original_content == content
    assert len(result.summaries) > 0 # Should generate multiple summaries
    assert all(isinstance(s, Summary) for s in result.summaries)
    assert len(result.key_insights) > 0

def test_empty_content(summarizer):
    """Test summarizing empty content."""
    result = summarizer.summarize([])
    assert len(result.summaries) == 0
    assert len(result.key_insights) > 0 # Still tries to generate them.

def test_llm_integration(summarizer, llm_integration):
    """Test LLM integration for summarization."""
    summarizer.llm = llm_integration
    content = "This is a test content."
    summary = summarizer._generate_summary(content, 1)

    assert isinstance(summary, Summary)
    assert summary.confidence > 0

def test_invalid_summary_level(summarizer):
   """Test handling of invalid summary level."""
   content = "Test content."
   with pytest.raises(ValueError):
       summarizer._generate_summary(content, 4)
