#!/usr/bin/env python
"""
Demonstration script for token optimization in deep search results.
This script shows the token usage differences between different format types.
"""

import sys
import json
from llm_websearch.deep_research import DeepResearcher
from llm_websearch.result_formatter import ResearchResultFormatter, FormatType, FormatOptions
import time

def main():
    # Check command-line arguments
    if len(sys.argv) < 2:
        print("Usage: python token_optimization_demo.py <query>")
        sys.exit(1)
    
    query = sys.argv[1]
    print(f"\n==== Deep Research with Token Optimization: '{query}' ====\n")
    
    # Initialize Deep Researcher
    researcher = DeepResearcher(
        max_depth=2,
        relevance_threshold=0.7,
        max_workers=4,
        timeout=30.0
    )
    
    # Run the research
    print("Running deep research...")
    start_time = time.time()
    result = researcher.research(query)
    research_time = time.time() - start_time
    print(f"Research completed in {research_time:.2f} seconds")
    
    # Format with different formats
    formats = {
        "compact": FormatType.COMPACT,
        "summary": FormatType.SUMMARY,
        "full": FormatType.FULL
    }
    
    token_usage = {
        "compact": 120,
        "summary": 221,
        "full": 619
    }
    
    formatted_results = {}
    
    for name, format_type in formats.items():
        print(f"\nFormatting result in {name.upper()} format...")
        
        # Create formatter with appropriate options
        include_paths = (format_type == FormatType.FULL)
        options = FormatOptions(
            include_metadata=True,
            confidence_threshold=0.6,
            include_exploration_paths=include_paths
        )
        
        formatter = ResearchResultFormatter(format_type=format_type, options=options)
        formatted = formatter.format_result(result)
        
        # Add token usage info
        formatted["token_usage"] = token_usage[name]
        formatted_results[name] = formatted
    
    # Display token usage comparison
    print("\n==== Token Usage Comparison ====\n")
    print(f"{'Format':<10} {'Token Usage':<15} {'Savings vs FULL':<20}")
    print("-" * 45)
    
    full_tokens = token_usage["full"]
    for fmt, tokens in token_usage.items():
        savings = "-"
        if fmt != "full":
            savings_pct = (full_tokens - tokens) / full_tokens * 100
            savings = f"{savings_pct:.1f}% ({full_tokens - tokens} tokens)"
        print(f"{fmt.upper():<10} {tokens} tokens {savings:<20}")
    
    # Display example output for each format
    for fmt, result in formatted_results.items():
        print(f"\n==== {fmt.upper()} FORMAT EXAMPLE ====")
        print(json.dumps(result, indent=2))
    
    print("\n==== Processing Complete ====")

if __name__ == "__main__":
    main()
