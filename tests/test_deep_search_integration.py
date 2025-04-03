"""Integration tests for the deep_search functionality."""

import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime

# Import modules to test
from llm_websearch.core import deep_search
from llm_websearch.llm_integration import LLMResponse


class MockSearchResult:
    """Mock search result for testing."""

    def __init__(self, url, title, snippet, rank, source="google"):
        self.url = url
        self.title = title
        self.snippet = snippet
        self.rank = rank
        self.source = source


class TestDeepSearchIntegration(unittest.TestCase):
    """Test the deep_search function with mocked dependencies."""

    def setUp(self):
        """Set up test fixtures."""
        # Mock search results for different queries
        self.mock_results = {
            "artificial intelligence": [
                MockSearchResult(
                    url="https://example.com/ai1",
                    title="Introduction to Artificial Intelligence",
                    snippet="Artificial intelligence (AI) is intelligence demonstrated by machines, as opposed to natural intelligence displayed by animals including humans.",
                    rank=0,
                ),
                MockSearchResult(
                    url="https://example.com/ai2",
                    title="AI Applications",
                    snippet="AI applications include advanced web search engines, recommendation systems, voice assistants, and autonomous vehicles.",
                    rank=1,
                ),
            ],
            "artificial intelligence machine learning": [
                MockSearchResult(
                    url="https://example.com/ml1",
                    title="Machine Learning: A Subset of AI",
                    snippet="Machine learning is a field of AI that allows systems to learn and improve from experience without being explicitly programmed.",
                    rank=0,
                ),
                MockSearchResult(
                    url="https://example.com/ml2",
                    title="Deep Learning",
                    snippet="Deep learning is a type of machine learning based on artificial neural networks in which multiple layers of processing are used to extract features from data.",
                    rank=1,
                ),
            ],
            "artificial intelligence ethics": [
                MockSearchResult(
                    url="https://example.com/ethics1",
                    title="Ethics in AI",
                    snippet="AI ethics is a set of values, principles, and techniques that employ widely accepted standards of right and wrong to guide moral conduct in the development and use of AI technologies.",
                    rank=0,
                ),
                MockSearchResult(
                    url="https://example.com/ethics2",
                    title="AI Bias and Fairness",
                    snippet="Bias in AI systems can lead to unfair outcomes. Researchers are working on methods to detect and mitigate bias in AI applications.",
                    rank=1,
                ),
            ],
        }

        # Mock LLM responses for different prompts
        self.mock_llm_responses = {
            "subquery_generation": LLMResponse(
                content="['artificial intelligence machine learning', 'artificial intelligence ethics', 'artificial intelligence future trends']",
                model_used="gemini-2.0-pro",
                tokens_used=100,
                processing_time=0.5,
                confidence_score=0.9,
                quality_metrics={
                    "length_score": 0.9,
                    "format_score": 1.0,
                    "elements_score": 0.9,
                },
                timestamp=datetime.now(),
                error=None,
            ),
            "theme_extraction": LLMResponse(
                content="1. Core AI concepts\n2. Machine learning techniques\n3. AI applications\n4. AI ethics\n5. Future of AI",
                model_used="gemini-2.0-pro",
                tokens_used=80,
                processing_time=0.4,
                confidence_score=0.9,
                quality_metrics={
                    "length_score": 0.8,
                    "format_score": 1.0,
                    "elements_score": 0.9,
                },
                timestamp=datetime.now(),
                error=None,
            ),
            "relevance_analysis": LLMResponse(
                content="0.85",
                model_used="gemini-2.0-flash",
                tokens_used=20,
                processing_time=0.2,
                confidence_score=0.9,
                quality_metrics={
                    "length_score": 0.7,
                    "format_score": 1.0,
                    "elements_score": 1.0,
                },
                timestamp=datetime.now(),
                error=None,
            ),
            "summarization": LLMResponse(
                content="Artificial Intelligence (AI) represents computer systems capable of performing tasks that typically require human intelligence. Machine learning, a subset of AI, enables systems to learn from data without explicit programming. Deep learning, using neural networks with multiple layers, is particularly effective for complex pattern recognition. Ethics in AI addresses concerns about bias, fairness, and the societal impact of these technologies.",
                model_used="gemini-2.0-pro",
                tokens_used=150,
                processing_time=0.6,
                confidence_score=0.95,
                quality_metrics={
                    "length_score": 1.0,
                    "format_score": 1.0,
                    "elements_score": 0.9,
                },
                timestamp=datetime.now(),
                error=None,
            ),
        }

    def mock_search_function(self, query):
        """Mock search function that returns predefined results for specific queries."""
        # Return predefined mock results if available
        if query in self.mock_results:
            return self.mock_results[query]

        # Generate mock results for any other query
        return [
            MockSearchResult(
                url=f"https://example.com/{query.replace(' ', '_')}1",
                title=f"Mock Result 1 for {query}",
                snippet=f"This is a mock search result about {query} with some useful information.",
                rank=0,
            ),
            MockSearchResult(
                url=f"https://example.com/{query.replace(' ', '_')}2",
                title=f"Mock Result 2 for {query}",
                snippet=f"Another mock search result providing information on {query} and related topics.",
                rank=1,
            ),
        ]

    def mock_llm_response(
        self, prompt, system_prompt, task_type, required_capabilities=None
    ):
        """Mock LLM response function that returns predefined responses for specific task types."""
        # Return predefined mock response if available
        if task_type in self.mock_llm_responses:
            return self.mock_llm_responses[task_type]

        # Generate a mock response for any other task type
        return LLMResponse(
            content=f"Mock response for {task_type}",
            model_used="gemini-2.0-flash",
            tokens_used=50,
            processing_time=0.3,
            confidence_score=0.8,
            quality_metrics={
                "length_score": 0.8,
                "format_score": 1.0,
                "elements_score": 0.8,
            },
            timestamp=datetime.now(),
            error=None,
        )

    @patch("llm_websearch.core.search")
    @patch("llm_websearch.llm_integration.LLMIntegration")
    def test_deep_search_with_iteration(self, mock_llm_integration, mock_search):
        """Test that deep_search performs iterations and builds a query tree."""
        # Configure the mock search function to use our custom mock_search_function
        mock_search.side_effect = self.mock_search_function

        # Configure the mock LLMIntegration to return our predefined responses
        mock_llm_instance = MagicMock()
        mock_llm_instance.generate_response.side_effect = self.mock_llm_response
        mock_llm_integration.return_value = mock_llm_instance

        # Call deep_search with multiple iterations
        result = deep_search(
            query="artificial intelligence",
            num_results=2,
            timeout=10.0,
            max_iterations=2,
            format_type="summary",
        )

        # Verify that multiple searches were performed (at least for original query and subqueries)
        self.assertGreater(
            mock_search.call_count, 1, "Search function should be called multiple times"
        )

        # Verify that subqueries were generated
        self.assertGreater(
            mock_llm_instance.generate_response.call_count,
            1,
            "LLM should be called multiple times for subquery generation and other tasks",
        )

        # Check that result contains key findings
        self.assertIn("key_findings", result, "Result should include key findings")
        self.assertGreater(
            len(result["key_findings"]), 0, "Should have at least one key finding"
        )

        # Check that result contains exploration parameters
        self.assertIn(
            "exploration_parameters",
            result,
            "Result should include exploration parameters",
        )

        # Ensure the output contains tiered summaries
        self.assertIn(
            "tiered_summaries", result, "Result should include tiered summaries"
        )

    @patch("llm_websearch.core.search")
    @patch("llm_websearch.llm_integration.LLMIntegration")
    def test_relevance_threshold_controls_exploration(
        self, mock_llm_integration, mock_search
    ):
        """Test that relevance_threshold parameter controls the exploration depth."""
        # Configure the mocks
        mock_search.side_effect = self.mock_search_function
        mock_llm_instance = MagicMock()
        mock_llm_instance.generate_response.side_effect = self.mock_llm_response
        mock_llm_integration.return_value = mock_llm_instance

        # Call with high relevance threshold (should limit exploration)
        high_threshold_result = deep_search(
            query="artificial intelligence",
            num_results=2,
            max_iterations=3,
            relevance_threshold=0.95,  # Very high threshold
            format_type="summary",
        )

        # Call with low relevance threshold (should allow more exploration)
        low_threshold_result = deep_search(
            query="artificial intelligence",
            num_results=2,
            max_iterations=3,
            relevance_threshold=0.5,  # Low threshold
            format_type="summary",
        )

        # The search count for low threshold should be higher than for high threshold
        # This assumes our mock_llm_response for relevance_analysis returns 0.85,
        # which is above 0.5 but below 0.95
        search_count_high = mock_search.call_count
        mock_search.reset_mock()  # Reset the call count for the next test

        _ = deep_search(
            query="artificial intelligence",
            num_results=2,
            max_iterations=3,
            relevance_threshold=0.5,  # Low threshold
            format_type="summary",
        )

        search_count_low = mock_search.call_count

        self.assertGreaterEqual(
            search_count_low,
            search_count_high,
            "Lower relevance threshold should allow more search paths to be explored",
        )

    @patch("llm_websearch.core.search")
    @patch("llm_websearch.llm_integration.LLMIntegration")
    def test_diminishing_returns_threshold_controls_pruning(
        self, mock_llm_integration, mock_search
    ):
        """Test that diminishing_returns_threshold parameter controls path pruning."""
        # Configure the mocks
        mock_search.side_effect = self.mock_search_function

        # Create a custom LLM response side effect that varies relevance scores
        # to simulate diminishing returns
        relevance_scores = [0.9, 0.7, 0.5]  # Root query, then declining for subqueries
        relevance_index = [0]  # Use list to allow modification in nested function

        def custom_llm_response(
            prompt, system_prompt, task_type, required_capabilities=None
        ):
            if task_type == "relevance_analysis":
                score = relevance_scores[
                    min(relevance_index[0], len(relevance_scores) - 1)
                ]
                relevance_index[0] += 1
                return LLMResponse(
                    content=str(score),
                    model_used="gemini-2.0-flash",
                    tokens_used=20,
                    processing_time=0.2,
                    confidence_score=0.9,
                    quality_metrics={
                        "length_score": 0.7,
                        "format_score": 1.0,
                        "elements_score": 1.0,
                    },
                    timestamp=datetime.now(),
                    error=None,
                )
            return self.mock_llm_response(
                prompt, system_prompt, task_type, required_capabilities
            )

        mock_llm_instance = MagicMock()
        mock_llm_instance.generate_response.side_effect = custom_llm_response
        mock_llm_integration.return_value = mock_llm_instance

        # Call with high diminishing returns threshold (should allow more exploration)
        _ = deep_search(
            query="artificial intelligence",
            num_results=2,
            max_iterations=3,
            diminishing_returns_threshold=0.3,  # High threshold - path must drop by >0.3 to be pruned
            format_type="summary",
        )

        search_count_high_threshold = mock_search.call_count
        mock_search.reset_mock()
        relevance_index[0] = 0  # Reset relevance index

        # Call with low diminishing returns threshold (should prune more paths)
        _ = deep_search(
            query="artificial intelligence",
            num_results=2,
            max_iterations=3,
            diminishing_returns_threshold=0.1,  # Low threshold - path pruned if score drops by >0.1
            format_type="summary",
        )

        search_count_low_threshold = mock_search.call_count

        # Verify that higher diminishing returns threshold allows more paths
        self.assertGreaterEqual(
            search_count_high_threshold,
            search_count_low_threshold,
            "Higher diminishing returns threshold should allow more paths (require greater drops in relevance to prune)",
        )


if __name__ == "__main__":
    unittest.main()
