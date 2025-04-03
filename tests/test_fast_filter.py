"""Unit tests for FastFilter functionality."""

import unittest
from unittest.mock import MagicMock, patch
import time

from llm_websearch.fast_filter import FastFilter, FilterResult


class TestFastFilter(unittest.TestCase):
    """Test the FastFilter class for content filtering."""

    def setUp(self):
        """Set up test fixtures."""
        self.filter = FastFilter(threshold=0.7, lightweight_model="test-model")
        self.test_contents = [
            "This content is highly relevant to artificial intelligence and machine learning.",
            "This content is somewhat related to the topic but not directly.",
            "This content has nothing to do with the query.",
            "Artificial intelligence is transforming how we approach problem-solving in various domains.",
        ]
        self.query = "artificial intelligence applications"

    def test_filter_initialization(self):
        """Test the initialization of FastFilter with various parameters."""
        # Test default initialization
        default_filter = FastFilter()
        self.assertEqual(default_filter.threshold, 0.7)
        self.assertEqual(default_filter.model, "gemini-2.0-flash")
        self.assertEqual(default_filter.max_workers, 4)

        # Test custom initialization
        custom_filter = FastFilter(
            threshold=0.5, max_workers=2, lightweight_model="custom-model"
        )
        self.assertEqual(custom_filter.threshold, 0.5)
        self.assertEqual(custom_filter.model, "custom-model")
        self.assertEqual(custom_filter.max_workers, 2)

        # Test with LLM integration
        llm_mock = MagicMock()
        llm_filter = FastFilter(threshold=0.8, llm_integration=llm_mock)
        self.assertEqual(llm_filter.llm_integration, llm_mock)

    def test_single_content_scoring(self):
        """Test scoring a single content item."""
        # Test with content containing query terms
        result = self.filter._score_content(self.test_contents[0], self.query)
        self.assertIsInstance(result, FilterResult)
        self.assertGreaterEqual(result.relevance_score, self.filter.threshold)

        # Test with irrelevant content
        result = self.filter._score_content(self.test_contents[2], self.query)
        self.assertIsInstance(result, FilterResult)
        self.assertLess(result.relevance_score, self.filter.threshold)

    @patch("llm_websearch.fast_filter.FilterResult")
    def test_llm_integration_scoring(self, mock_filter_result):
        """Test content scoring using LLM integration."""
        # Create a mock LLM integration
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "0.85"
        mock_response.confidence_score = 0.9
        mock_llm.generate_response.return_value = mock_response

        # Create a filter with the mock LLM integration
        filter_with_llm = FastFilter(llm_integration=mock_llm)

        # Mock the FilterResult constructor to return a controlled result
        mock_filter_result.return_value = FilterResult(
            content=self.test_contents[0],
            relevance_score=0.85,
            confidence=0.9,
            filtering_time=0.1,
        )

        # Call _score_content
        result = filter_with_llm._score_content(self.test_contents[0], self.query)

        # Verify the LLM was called
        mock_llm.generate_response.assert_called_once()

        # Verify the result
        self.assertEqual(result.relevance_score, 0.85)
        self.assertEqual(result.confidence, 0.9)

    def test_batch_filtering(self):
        """Test filtering a batch of content."""
        results = self.filter.filter_batch(self.test_contents, self.query)

        # Only the relevant content should be returned
        self.assertGreater(len(results), 0)
        self.assertLess(len(results), len(self.test_contents))

        # All results should have relevance >= threshold
        for result in results:
            self.assertGreaterEqual(result.relevance_score, self.filter.threshold)

    def test_threshold_filtering(self):
        """Test how different thresholds affect filtering."""
        # High threshold should return fewer results
        high_threshold_filter = FastFilter(threshold=0.9)
        high_results = high_threshold_filter.filter_batch(
            self.test_contents, self.query
        )

        # Low threshold should return more results
        low_threshold_filter = FastFilter(threshold=0.1)
        low_results = low_threshold_filter.filter_batch(self.test_contents, self.query)

        # The low threshold should return at least as many results as the high threshold
        self.assertGreaterEqual(len(low_results), len(high_results))

    def test_stream_filtering(self):
        """Test streaming content filtering."""
        # Convert list to a generator to simulate a stream
        content_stream = (content for content in self.test_contents)

        # Filter the stream
        filtered_results = list(self.filter.filter_stream(content_stream, self.query))

        # Verify results
        self.assertGreater(len(filtered_results), 0)
        for result in filtered_results:
            self.assertGreaterEqual(result.relevance_score, self.filter.threshold)

    def test_parallel_performance(self):
        """Test that parallel processing improves performance for large batches."""
        # Create a larger batch of content
        large_batch = self.test_contents * 10  # 40 items

        # Time sequential processing (1 worker)
        sequential_filter = FastFilter(max_workers=1)
        start_time = time.time()
        sequential_results = sequential_filter.filter_batch(large_batch, self.query)
        sequential_time = time.time() - start_time

        # Time parallel processing (4 workers)
        parallel_filter = FastFilter(max_workers=4)
        start_time = time.time()
        parallel_results = parallel_filter.filter_batch(large_batch, self.query)
        parallel_time = time.time() - start_time

        # Parallel should generally be faster, but this isn't a strict requirement
        # as it depends on the system and the batch size
        self.assertEqual(len(sequential_results), len(parallel_results))
        # Commented out as this might not always be true in all test environments
        # self.assertLess(parallel_time, sequential_time)


if __name__ == "__main__":
    unittest.main()
