#!/usr/bin/env python
"""
Demonstrates the token optimization features of the llm-websearch plugin.
This script compares different output formats and their token usage.
"""

import sys
import json
from llm_websearch import deep_search

def format_size(size):
    return f"{size:,} tokens"

def main():
    if len(sys.argv) < 2:
        print("Usage: python demo_token_optimization.py \"your search query\"")
        sys.exit(1)
    
    query = sys.argv[1]
    print(f"\n==== Token Optimization Demo for Query: '{query}' ====\n")
    
    # Run deep search with each format
    formats = ["compact", "summary", "full"]
    results = {}
    
    for fmt in formats:
        print(f"Running deep search with {fmt.upper()} format...")
        results[fmt] = deep_search(query, format_type=fmt)
    
    # Display token usage comparison
    print("\n==== Token Usage Comparison ====\n")
    print(f"{'Format':<10} {'Token Usage':<15} {'Savings vs FULL':<20}")
    print("-" * 45)
    
    full_tokens = results["full"]["token_usage"]
    for fmt in formats:
        tokens = results[fmt]["token_usage"]
        savings = "-"
        if fmt != "full":
            savings_pct = (full_tokens - tokens) / full_tokens * 100
            savings = f"{savings_pct:.1f}% ({full_tokens - tokens} tokens)"
        print(f"{fmt.upper():<10} {format_size(tokens):<15} {savings:<20}")
    
    # Show examples of each format
    print("\n==== Format Examples ====\n")
    
    print("== COMPACT FORMAT ==")
    print(json.dumps(results["compact"], indent=2))
    
    print("\n== SUMMARY FORMAT (Preview) ==")
    summary = results["summary"]
    # Only show part of the summary to save space
    if "key_findings" in summary:
        summary["key_findings"] = summary["key_findings"][:2]
        summary["key_findings"].append({"note": "... more findings truncated for demo"})
    print(json.dumps(summary, indent=2))
    
    print("\n== FULL FORMAT (Structure Only) ==")
    # Just show the keys, not the full content
    full_structure = {k: type(v).__name__ for k, v in results["full"].items()}
    print(json.dumps(full_structure, indent=2))
    
    print("\n==== Demo Complete ====")
    print("For actual use, run: llm websearch deep-search \"your query\" --format compact|summary|full")

if __name__ == "__main__":
    main()
