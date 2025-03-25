#!/usr/bin/env python3
import json
import logging
from llm_websearch import search, deep_search
from llm_websearch.deep_research import DeepResearcher

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Test query
test_query = "list of models and their apis which support logprobs"

# Function to print formatted JSON
def print_json(data):
    print(json.dumps(data, indent=2))

# Test direct search
print("\n=== Testing direct search ===")
search_results = search(test_query, num_results=5, timeout=30.0)
print(f"Search found {len(search_results)} results")
for i, result in enumerate(search_results, 1):
    print(f"{i}. {result.title}")
    print(f"   URL: {result.url}")
    print(f"   Snippet: {result.snippet}")
    print()

# Test the deep search function with real search integration
print("\n=== Testing deep search ===")
deep_search_results = deep_search(test_query, num_results=5, timeout=30.0, format_type="summary")
print_json(deep_search_results)

# Examine DeepResearcher mechanics
print("\n=== Testing DeepResearcher directly ===")

# Define a wrapped search function for debugging
def debug_search_function(query):
    print(f"Debug: Searching for query: {query}")
    results = search(query, num_results=5, timeout=30.0)
    print(f"Debug: Found {len(results)} results")
    return results

# Create a researcher with our debug function
researcher = DeepResearcher(
    search_function=debug_search_function,
    max_depth=2,
    relevance_threshold=0.6,
    max_workers=2,
    timeout=30.0
)

# Run research directly
research_result = researcher.research(test_query)
print(f"Research exploration paths: {len(research_result.exploration_paths)}")
print(f"Research key findings: {len(research_result.key_findings)}")
print(f"First finding: {research_result.key_findings[0] if research_result.key_findings else 'None'}")
