"""Tests for the token optimization functionality."""

import sys
import os
import pytest
from datetime import datetime

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from llm_websearch.deep_research import ResearchResult, SearchPath
from llm_websearch.result_formatter import ResearchResultFormatter, FormatType, FormatOptions

@pytest.fixture
def sample_research_result():
    """Create a sample research result for testing."""
    return ResearchResult(
        query_tree={
            "root": ["neural networks"],
            "neural networks": ["neural networks architecture", "neural networks applications"]
        },
        key_findings=[
            {
                "query": "neural networks",
                "depth": 0,
                "confidence": 0.9,
                "finding": "Neural networks are computational models inspired by the human brain."
            },
            {
                "query": "neural networks architecture",
                "depth": 1,
                "confidence": 0.85,
                "finding": "Most neural networks include input, hidden, and output layers."
            },
            {
                "query": "neural networks applications",
                "depth": 1,
                "confidence": 0.8,
                "finding": "Neural networks are widely used in image recognition and NLP."
            }
        ],
        evidence=[
            {
                "query": "neural networks",
                "source": "AI Textbook",
                "evidence": "Neural networks consist of interconnected nodes that process information.",
                "confidence": 0.9
            },
            {
                "query": "neural networks architecture",
                "source": "IEEE Paper",
                "evidence": "The hidden layers extract hierarchical features from the input data.",
                "confidence": 0.85
            },
            {
                "query": "neural networks applications",
                "source": "Research Journal",
                "evidence": "CNNs are particularly effective for image recognition tasks.",
                "confidence": 0.8
            }
        ],
        confidence_score=0.85,
        research_time=2.5,
        exploration_paths=[
            SearchPath(
                query="neural networks",
                parent_query=None,
                depth=0,
                relevance_score=1.0,
                timestamp=datetime.now()
            ),
            SearchPath(
                query="neural networks architecture",
                parent_query="neural networks",
                depth=1,
                relevance_score=0.85,
                timestamp=datetime.now()
            ),
            SearchPath(
                query="neural networks applications",
                parent_query="neural networks",
                depth=1,
                relevance_score=0.8,
                timestamp=datetime.now()
            )
        ]
    )

def test_compact_format(sample_research_result):
    """Test the compact format produces minimal output."""
    formatter = ResearchResultFormatter(format_type=FormatType.COMPACT)
    result = formatter.format_result(sample_research_result)
    
    # Check that compact format has only essential fields
    assert "key_conclusions" in result
    assert "query" in result
    
    # Check that verbose fields are excluded
    assert "evidence" not in result
    assert "exploration_paths" not in result
    assert "query_tree" not in result
    
    # Check that findings are simplified to just text
    assert isinstance(result["key_conclusions"], list)
    assert isinstance(result["key_conclusions"][0], str)
    
    # Compact should have all findings but in simplified form
    assert len(result["key_conclusions"]) == len(sample_research_result.key_findings)

def test_summary_format(sample_research_result):
    """Test the summary format has moderate detail."""
    formatter = ResearchResultFormatter(format_type=FormatType.SUMMARY)
    result = formatter.format_result(sample_research_result)
    
    # Check that summary format has key summary fields
    assert "key_findings" in result
    assert "evidence_summary" in result
    assert isinstance(result["evidence_summary"], str)
    
    # Check that we have metadata but not full paths
    assert "exploration_stats" in result
    assert "paths_explored" in result["exploration_stats"]
    
    # Check that findings have confidence but not full details
    assert isinstance(result["key_findings"], list)
    assert "confidence" in result["key_findings"][0]
    assert "finding" in result["key_findings"][0]

def test_full_format(sample_research_result):
    """Test the full format includes complete details."""
    formatter = ResearchResultFormatter(format_type=FormatType.FULL, 
                                      options=FormatOptions(include_exploration_paths=True))
    result = formatter.format_result(sample_research_result)
    
    # Check that full format has all major sections
    assert "query_tree" in result
    assert "key_findings" in result
    assert "evidence" in result
    assert "confidence_score" in result
    assert "research_time" in result
    
    # Check that exploration paths are included when requested
    assert "exploration_paths" in result
    assert len(result["exploration_paths"]) == len(sample_research_result.exploration_paths)
    
    # Check that we have complete findings
    assert len(result["key_findings"]) == len(sample_research_result.key_findings)
    assert len(result["evidence"]) == len(sample_research_result.evidence)

def test_confidence_filtering(sample_research_result):
    """Test filtering results by confidence threshold."""
    formatter = ResearchResultFormatter(
        format_type=FormatType.SUMMARY,
        options=FormatOptions(confidence_threshold=0.85)
    )
    result = formatter.format_result(sample_research_result)
    
    # Should only include findings with confidence >= 0.85
    assert len(result["key_findings"]) == 2
    for finding in result["key_findings"]:
        assert finding["confidence"] >= 0.85

def test_progressive_loading(sample_research_result):
    """Test progressive loading of findings."""
    formatter = ResearchResultFormatter(format_type=FormatType.COMPACT)
    
    # First get compact format
    compact_result = formatter.format_result(sample_research_result)
    
    # Then load details for a specific finding
    finding_details = formatter.get_finding_details(sample_research_result, 0)
    
    # Check that finding details include evidence and related queries
    assert "finding" in finding_details
    assert "evidence" in finding_details
    assert "related_queries" in finding_details
