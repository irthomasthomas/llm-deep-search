"""Unit tests for Summarizer functionality."""
import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime

from llm_websearch.summarization import (
    Summarizer, Summary, SummarizationResult
)
from llm_websearch.deep_research import ResearchResult, SearchPath

class TestSummarizer(unittest.TestCase):
    """Test the Summarizer class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_llm = MagicMock()
        self.mock_llm.generate_response.return_value = MagicMock(
            content="Mock summary content",
            error=None
        )
        self.summarizer = Summarizer(
            llm_integration=self.mock_llm,
            short_summary_length=50,
            medium_summary_length=150,
            long_summary_length=300
        )
        self.test_content = [
            "Artificial intelligence (AI) is intelligence demonstrated by machines, as opposed to natural intelligence displayed by animals including humans.",
            "Machine learning is a field of AI that allows systems to learn and improve from experience without being explicitly programmed.",
            "Neural networks are computing systems inspired by the biological neural networks that constitute animal brains.",
            "Deep learning is a subset of machine learning that uses multiple layers to progressively extract higher-level features from raw input."
        ]
        
    def test_summarizer_initialization(self):
        """Test the initialization of Summarizer with various parameters."""
        # Test default initialization
        default_summarizer = Summarizer()
        self.assertEqual(default_summarizer.short_length, 50)
        self.assertEqual(default_summarizer.medium_length, 150)
        self.assertEqual(default_summarizer.long_length, 500)
        self.assertEqual(default_summarizer.min_confidence, 0.7)
        self.assertIsNone(default_summarizer.llm)
        self.assertIsNone(default_summarizer.cache)
        
        # Test custom initialization
        custom_summarizer = Summarizer(
            short_summary_length=30,
            medium_summary_length=100,
            long_summary_length=200,
            min_confidence=0.5,
            llm_integration=self.mock_llm,
            cache_instance=MagicMock()
        )
        self.assertEqual(custom_summarizer.short_length, 30)
        self.assertEqual(custom_summarizer.medium_length, 100)
        self.assertEqual(custom_summarizer.long_length, 200)
        self.assertEqual(custom_summarizer.min_confidence, 0.5)
        self.assertEqual(custom_summarizer.llm, self.mock_llm)
        self.assertIsNotNone(custom_summarizer.cache)
        
    def test_generate_summary(self):
        """Test generating a summary for a single content piece."""
        # Test short summary (level 1)
        short_summary = self.summarizer._generate_summary(self.test_content[0], 1)
        self.assertIsInstance(short_summary, Summary)
        self.assertEqual(short_summary.level, 1)
        self.assertEqual(short_summary.content, "Mock summary content")
        
        # Test medium summary (level 2)
        medium_summary = self.summarizer._generate_summary(self.test_content[0], 2)
        self.assertEqual(medium_summary.level, 2)
        
        # Test long summary (level 3)
        long_summary = self.summarizer._generate_summary(self.test_content[0], 3)
        self.assertEqual(long_summary.level, 3)
        
        # Verify the LLM was called with different prompts for each level
        self.assertEqual(self.mock_llm.generate_response.call_count, 3)
        
    def test_combined_summary(self):
        """Test generating a combined summary from multiple sources."""
        # Create some test summaries
        summaries = [
            Summary(
                content=f"Summary for content {i}",
                level=1,
                source_indices=[i],
                confidence=0.8,
                generation_time=0.1
            )
            for i in range(3)
        ]
        
        # Test combined summary generation
        combined_summary = self.summarizer._generate_combined_summary(summaries, 1)
        self.assertIsInstance(combined_summary, Summary)
        self.assertEqual(combined_summary.level, 1)
        self.assertEqual(combined_summary.content, "Mock summary content")
        self.assertEqual(len(combined_summary.source_indices), 3)
        
        # Verify LLM was called
        self.mock_llm.generate_response.assert_called()
        
    def test_extract_key_insights(self):
        """Test extracting key insights from content."""
        # Mock the LLM response for key insights
        insights_content = "1. First insight
2. Second insight
3. Third insight"
        self.mock_llm.generate_response.return_value = MagicMock(
            content=insights_content,
            error=None
        )
        
        # Test key insights extraction
        insights = self.summarizer._extract_key_insights(self.test_content)
        self.assertIsInstance(insights, list)
        self.assertEqual(len(insights), 3)
        self.assertIn("First insight", insights[0])
        
        # Verify LLM was called
        self.mock_llm.generate_response.assert_called()
        
    def test_summarize(self):
        """Test the full summarization process."""
        # Mock the individual summary methods
        with patch.object(self.summarizer, '_generate_summary') as mock_gen_summary, \
             patch.object(self.summarizer, '_generate_combined_summary') as mock_combined, \
             patch.object(self.summarizer, '_extract_key_insights') as mock_insights:
            
            # Configure mocks
            mock_gen_summary.return_value = Summary(
                content="Individual summary",
                level=1,
                source_indices=[0],
                confidence=0.8,
                generation_time=0.1
            )
            mock_combined.return_value = Summary(
                content="Combined summary",
                level=1,
                source_indices=[0, 1, 2, 3],
                confidence=0.9,
                generation_time=0.2
            )
            mock_insights.return_value = ["Insight 1", "Insight 2"]
            
            # Test summarization
            result = self.summarizer.summarize(self.test_content)
            self.assertIsInstance(result, SummarizationResult)
            self.assertEqual(result.original_content, self.test_content)
            self.assertGreater(len(result.summaries), 0)
            self.assertEqual(len(result.key_insights), 2)
            
            # Verify all methods were called
            self.assertEqual(mock_gen_summary.call_count, 12)  # 4 contents * 3 levels
            self.assertEqual(mock_combined.call_count, 3)  # One for each level
            mock_insights.assert_called_once()
            
    def test_summarize_research_result(self):
        """Test summarizing a ResearchResult object."""
        # Create a mock ResearchResult
        mock_research_result = MagicMock(spec=ResearchResult)
        mock_research_result.key_findings = [
            {"finding": "AI is a broad field of computer science."},
            {"finding": "Machine learning is a subset of AI."}
        ]
        mock_research_result.evidence = [
            {"evidence": "Studies show rapid advancements in AI technology."},
            {"evidence": "Machine learning algorithms can improve over time."}
        ]
        
        # Mock the summarize method
        with patch.object(self.summarizer, 'summarize') as mock_summarize:
            mock_summarize.return_value = SummarizationResult(
                original_content=["content1", "content2"],
                summaries=[
                    Summary(content="Short summary", level=1, source_indices=[0, 1, 2, 3], confidence=0.9, generation_time=0.1),
                    Summary(content="Medium summary", level=2, source_indices=[0, 1, 2, 3], confidence=0.9, generation_time=0.1),
                    Summary(content="Long summary", level=3, source_indices=[0, 1, 2, 3], confidence=0.9, generation_time=0.1)
                ],
                total_time=0.5,
                key_insights=["Insight 1", "Insight 2"]
            )
            
            # Test the summarization
            result = self.summarizer.summarize_research_result(mock_research_result)
            self.assertIsInstance(result, dict)
            self.assertIn("tiered_summaries", result)
            self.assertIn("short", result["tiered_summaries"])
            self.assertIn("medium", result["tiered_summaries"])
            self.assertIn("detailed", result["tiered_summaries"])
            self.assertIn("key_insights", result)
            
            # Verify summarize was called with the combined findings and evidence
            mock_summarize.assert_called_once()
            call_args = mock_summarize.call_args[0][0]
            self.assertEqual(len(call_args), 4)  # 2 findings + 2 evidence

if __name__ == "__main__":
    unittest.main()
