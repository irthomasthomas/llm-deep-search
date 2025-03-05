"""
Tests for the tiered result format system for DeepResearcher.
"""

import unittest
from datetime import datetime
from dataclasses import dataclass
from typing import Dict, List, Optional

# Import the classes we want to test
from result_formatter import (
    FormatType,
    FormatOptions,
    ResearchResultFormatter
)

# Mock classes to simulate the DeepResearcher output
@dataclass
class SearchPath:
    """Represents a search exploration path"""
    query: str
    parent_query: Optional[str]
    depth: int
    relevance_score: float
    timestamp: datetime

@dataclass
class ResearchResult:
    """Contains results from deep research"""
    query_tree: Dict[str, List[str]]
    key_findings: List[Dict]
    evidence: List[Dict]
    confidence_score: float
    research_time: float
    exploration_paths: List[SearchPath]


class TestResearchResultFormatter(unittest.TestCase):
    """Test cases for the research result formatter."""
    
    def setUp(self):
        """Set up a sample research result for testing."""
        # Create a sample research result
        self.sample_result = ResearchResult(
            query_tree={
                "root": ["python testing"],
                "python testing": [
                    "python testing detailed analysis",
                    "python testing advanced techniques"
                ],
                "python testing detailed analysis": [
                    "python testing frameworks"
                ]
            },
            key_findings=[
                {
                    "query": "python testing",
                    "depth": 0,
                    "confidence": 0.9,
                    "finding": "Python has several testing frameworks including pytest, unittest, and nose."
                },
                {
                    "query": "python testing detailed analysis",
                    "depth": 1,
                    "confidence": 0.85,
                    "finding": "Pytest is the most popular testing framework due to its simplicity and flexibility."
                },
                {
                    "query": "python testing advanced techniques",
                    "depth": 1,
                    "confidence": 0.8,
                    "finding": "Mocking and patching are advanced techniques for isolating components during testing."
                }
            ],
            evidence=[
                {
                    "query": "python testing",
                    "source": "Python Documentation",
                    "evidence": "The unittest module provides a rich set of tools for constructing and running tests.",
                    "confidence": 0.95
                },
                {
                    "query": "python testing",
                    "source": "Real Python Blog",
                    "evidence": "Pytest is a testing framework that makes it easy to write simple tests.",
                    "confidence": 0.9
                },
                {
                    "query": "python testing detailed analysis",
                    "source": "Stack Overflow",
                    "evidence": "According to 2021 survey, pytest is used by 87% of Python developers for testing.",
                    "confidence": 0.85
                },
                {
                    "query": "python testing advanced techniques",
                    "source": "Test Automation Blog",
                    "evidence": "Mocking allows you to replace parts of your system under test with mock objects.",
                    "confidence": 0.8
                }
            ],
            confidence_score=0.85,
            research_time=2.5,
            exploration_paths=[
                SearchPath(
                    query="python testing",
                    parent_query=None,
                    depth=0,
                    relevance_score=1.0,
                    timestamp=datetime.now()
                ),
                SearchPath(
                    query="python testing detailed analysis",
                    parent_query="python testing",
                    depth=1,
                    relevance_score=0.9,
                    timestamp=datetime.now()
                ),
                SearchPath(
                    query="python testing advanced techniques",
                    parent_query="python testing",
                    depth=1,
                    relevance_score=0.85,
                    timestamp=datetime.now()
                ),
                SearchPath(
                    query="python testing frameworks",
                    parent_query="python testing detailed analysis",
                    depth=2,
                    relevance_score=0.8,
                    timestamp=datetime.now()
                )
            ]
        )
    
    def test_compact_format(self):
        """Test the compact format output."""
        formatter = ResearchResultFormatter(FormatType.COMPACT)
        result = formatter.format_result(self.sample_result)
        
        # Verify the structure and content
        self.assertEqual(result["query"], "python testing")
        self.assertEqual(len(result["key_conclusions"]), 3)
        self.assertIn("Python has several testing frameworks", result["key_conclusions"][0])
        self.assertEqual(result["confidence"], 0.85)
        self.assertEqual(result["sources_count"], 4)
        
    def test_summary_format(self):
        """Test the summary format output."""
        formatter = ResearchResultFormatter(FormatType.SUMMARY)
        result = formatter.format_result(self.sample_result)
        
        # Verify the structure and content
        self.assertEqual(result["query"], "python testing")
        self.assertEqual(len(result["key_findings"]), 3)
        self.assertEqual(result["key_findings"][0]["confidence"], 0.9)
        self.assertIn("evidence_summary", result)
        self.assertIn("exploration_stats", result)
        self.assertEqual(result["exploration_stats"]["depth"], 2)
        self.assertEqual(result["exploration_stats"]["paths_explored"], 4)
        
    def test_full_format(self):
        """Test the full format output."""
        formatter = ResearchResultFormatter(FormatType.FULL, 
                                          FormatOptions(include_exploration_paths=True))
        result = formatter.format_result(self.sample_result)
        
        # Verify the structure and content
        self.assertIn("query_tree", result)
        self.assertIn("key_findings", result)
        self.assertIn("evidence", result)
        self.assertIn("exploration_paths", result)
        self.assertEqual(len(result["exploration_paths"]), 4)
        
    def test_format_with_options(self):
        """Test formatting with custom options."""
        # Create formatter with custom options
        options = FormatOptions(
            max_findings=2,
            confidence_threshold=0.85,
            include_metadata=True
        )
        formatter = ResearchResultFormatter(FormatType.COMPACT, options)
        result = formatter.format_result(self.sample_result)
        
        # Should only include findings with confidence >= 0.85
        self.assertEqual(len(result["key_conclusions"]), 2)
        
    def test_progressive_loading(self):
        """Test progressive loading of finding details."""
        formatter = ResearchResultFormatter(FormatType.SUMMARY)
        
        # First get the summary
        summary = formatter.format_result(self.sample_result)
        self.assertIn("key_findings", summary)
        
        # Then get details for a specific finding
        finding_details = formatter.get_finding_details(self.sample_result, 0)
        
        # Verify the detailed information
        self.assertIn("finding", finding_details)
        self.assertIn("evidence", finding_details)
        self.assertIn("related_queries", finding_details)
        self.assertEqual(finding_details["finding"]["query"], "python testing")
        
        # Verify evidence is related to the finding
        for evidence in finding_details["evidence"]:
            self.assertEqual(evidence["query"], "python testing")
            
        # Verify related queries
        self.assertIn("python testing detailed analysis", finding_details["related_queries"])


if __name__ == "__main__":
    unittest.main()
