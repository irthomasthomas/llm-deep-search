"""Tests for the enhanced LLM integration."""

import pytest
from datetime import datetime
from llm_search.llm_integration import (
    LLMIntegration,
    LLMResponse,
    ModelConfig,
    ModelTier
)

def test_error_handling():
    """Test error handling with all invalid models"""
    llm = LLMIntegration(
        primary_models=["invalid-model-1"],
        fallback_models=["invalid-model-2"]
    )
    
    # Both primary and fallback models should fail
    response = llm.generate_response("Test prompt")
    
    assert isinstance(response, LLMResponse)
    assert response.error is not None
    assert "All models failed" in response.error
    assert "invalid-model-1" in response.error
    assert "invalid-model-2" in response.error
    assert response.model_used == "none"
    assert not response.content
    assert response.confidence_score == 0.0

def test_model_fallback_chain():
    """Test the complete fallback chain"""
    llm = LLMIntegration(
        primary_models=["invalid-model-1", "anthropic/claude-3-opus-20240229"],
        fallback_models=["invalid-model-2", "openai/gpt-4-0125-preview"]
    )
    
    # First invalid model should fail, then use valid model
    response = llm.generate_response("Test prompt")
    
    assert isinstance(response, LLMResponse)
    assert response.error is None
    assert response.model_used == "anthropic/claude-3-opus-20240229"
    assert response.content.startswith("Response from")
    assert response.confidence_score > 0.7

# [Rest of the test file remains the same...]
