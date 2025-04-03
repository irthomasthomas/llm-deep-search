"""Tests for the Summarizer component."""

import unittest
from unittest.mock import MagicMock, patch

# Need to adjust import path based on new structure
from llm_websearch.components.summarization import Summarizer, SummarizationResult, Summary
from llm_websearch.models import LLMResponse, ResearchResult # Assuming ResearchResult needed

# Assume a mock LLMIntegration instance is passed or mocked
# Define a mock cache if needed
mock_cache = MagicMock()

class TestSummarizer(unittest.TestCase):

    def setUp(self):
        """Set up test fixtures."""
        self.mock_llm = MagicMock()
        # Configure default mock response for generate_response
        self.mock_llm.generate_response.return_value = MagicMock(
            spec=LLMResponse, # Use the Pydantic model spec
            raw_text="Default mock summary",
            model_name="mock-model",
            tokens_used=10,
            finish_reason="STOP",
            error=None # Simulate success by default
        )
        self.summarizer = Summarizer(llm_integration=self.mock_llm, cache_instance=mock_cache)

    @patch('time.time', return_value=1234567890.0) # Mock time for consistent generation_time
    def test_generate_summary_level1(self, mock_time):
        """Test generating a short summary (level 1)."""
        content = "This is a long piece of text that needs to be summarized concisely."
        expected_length = self.summarizer.short_length
        self.mock_llm.generate_response.return_value = MagicMock(spec=LLMResponse, raw_text="Short summary.", model_name='mock', error=None)

        # Make generate_summary async if needed by running in event loop
        # summary = asyncio.run(self.summarizer._generate_summary(content, 1, 0))
        # For unittest, let's assume for now _generate_summary might be sync or we mock the async part
        # If generate_summary IS async, these tests need pytest-asyncio
        summary = self.summarizer._generate_summary(content, 1, 0)

        self.assertEqual(summary.level, 1)
        self.assertEqual(summary.content, "Short summary.")
        self.assertEqual(summary.source_indices, [0])
        self.mock_llm.generate_response.assert_called_once()
        # Check if prompt contained target length
        call_args, call_kwargs = self.mock_llm.generate_response.call_args
        self.assertIn(f"around {expected_length} words", call_args[0]) # Check prompt arg

    # Add similar tests for level 2 and level 3

    def test_generate_summary_empty_content(self):
        """Test generating summary with empty content."""
        summary = self.summarizer._generate_summary("", 1, 0)
        self.assertEqual(summary.content, "")
        self.assertEqual(summary.confidence, 0.0)
        self.mock_llm.generate_response.assert_not_called()

    def test_generate_summary_llm_error(self):
        """Test handling of LLM error during summary generation."""
        content = "Some content"
        self.mock_llm.generate_response.return_value = MagicMock(spec=LLMResponse, raw_text="", model_name='mock', error="LLM failed")
        
        summary = self.summarizer._generate_summary(content, 1, 0)

        self.assertEqual(summary.level, 1)
        self.assertTrue(summary.content.startswith("Error:"))
        self.assertEqual(summary.confidence, 0.0)

    # Test key insights extraction
    def test_extract_key_insights(self):
        """Test extracting key insights."""
        content_list = [
            "AI is transforming healthcare.", 
            "Machine learning models predict patient outcomes.",
            "Ethical considerations are important in AI healthcare applications."
        ]
        # Mock the LLM response for key insights
        # Corrected multi-line string:
        insights_content = """1. First insight: AI transformation in healthcare.
2. Second insight: ML for prediction.
3. Third insight: Ethics matter."""
        self.mock_llm.generate_response.return_value = MagicMock(
            spec=LLMResponse,
            raw_text=insights_content,
            model_name='mock-insight',
            error=None
        )

        # If _extract_key_insights is async:
        # insights = asyncio.run(self.summarizer._extract_key_insights(content_list))
        insights = self.summarizer._extract_key_insights(content_list)

        self.assertIsInstance(insights, list)
        self.assertGreater(len(insights), 0)
        self.assertIn("First insight: AI transformation in healthcare.", insights)
        self.assertIn("ML for prediction.", insights)
        self.assertIn("Ethics matter.", insights)
        self.mock_llm.generate_response.assert_called_once()
        call_args, call_kwargs = self.mock_llm.generate_response.call_args
        self.assertIn("healthcare", call_args[0]) # Check if prompt contains content
        self.assertIn("Key Insights", call_args[0])
        
    @patch.object(Summarizer, '_generate_summary', return_value=Summary(content="Mock Sum", level=1, source_indices=[0], confidence=0.9, generation_time=0.1))
    @patch.object(Summarizer, '_generate_combined_summary', return_value=Summary(content="Mock Combined Sum", level=1, source_indices=[0,1], confidence=0.8, generation_time=0.2))
    @patch.object(Summarizer, '_extract_key_insights', return_value=["Insight A", "Insight B"])
    def test_summarize(self, mock_insights, mock_combined, mock_single):
        """Test the full summarization process."""
        content = ["Content 1", "Content 2"]
        result = self.summarizer.summarize(content)

        self.assertIsInstance(result, SummarizationResult)
        self.assertIn(1, result.combined_summaries) # Check if combined summaries were generated
        # self.assertGreater(len(result.summaries), 0)
        self.assertEqual(result.key_insights, ["Insight A", "Insight B"])
        # Check if mocks were called (may need adjustment based on logic flow)
        # mock_single.assert_called()
        mock_combined.assert_called() # Should be called if len(content)>1
        mock_insights.assert_called_once()
            
    # Test summarizing a ResearchResult object
    # This requires a mock ResearchResult conforming to the Pydantic model
    def test_summarize_research_result(self):
        """Test summarizing a ResearchResult object."""
        # Create a mock ResearchResult (use dict to simulate Pydantic for now)
        mock_research = MagicMock(spec=ResearchResult)
        mock_research.original_query = "Test Query"
        mock_research.key_findings = [
            {'finding': 'Finding one is important.', 'confidence': 0.9, 'source_path_ids': ['p1']},
            {'finding': 'Finding two provides context.', 'confidence': 0.8, 'source_path_ids': ['p2']}
        ]
        mock_research.evidence = [] # Assume no separate evidence text for now
        
        # Mock the main summarize method which is called internally
        mock_summarization_result = SummarizationResult(
            combined_summaries={
                1: Summary(content="Short combined summary.", level=1, source_indices=[0,1], confidence=0.8, generation_time=0.1),
                2: Summary(content="Medium combined summary.", level=2, source_indices=[0,1], confidence=0.8, generation_time=0.1),
                3: Summary(content="Detailed combined summary.", level=3, source_indices=[0,1], confidence=0.8, generation_time=0.1)
            },
            key_insights=["Insight from findings"],
            total_time=0.5
        )
        with patch.object(self.summarizer, 'summarize', return_value=mock_summarization_result) as mock_summarize_call:
            summary_data = self.summarizer.summarize_research_result(mock_research)

            self.assertIsInstance(summary_data, dict)
            self.assertIn('tiered_summaries', summary_data)
            self.assertIn('key_insights', summary_data)
            self.assertEqual(summary_data['tiered_summaries']['short'], "Short combined summary.")
            self.assertEqual(summary_data['key_insights'], ["Insight from findings"])
            # Check that the internal summarize method was called with the findings text
            mock_summarize_call.assert_called_once()
            call_args, _ = mock_summarize_call.call_args
            self.assertIsInstance(call_args[0], list)
            self.assertIn('Finding one is important.', call_args[0])
            self.assertIn('Finding two provides context.', call_args[0])

# Note: If the methods become async, these tests need conversion to use pytest-asyncio
# and asyncio.run or equivalent.
# if __name__ == "__main__":
#     unittest.main()
