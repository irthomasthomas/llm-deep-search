#!/usr/bin/env python3
"""
Demo script showing how to use the ResearchResultFormatter in a real application.
"""

from datetime import datetime
from result_formatter import FormatType, FormatOptions, ResearchResultFormatter

# Import these just for the demo
# In a real application, you would import from your actual implementation
from test_result_formatter import SearchPath, ResearchResult


def create_sample_research_result():
    """Create a sample research result for demonstration."""
    return ResearchResult(
        query_tree={
            "root": ["neural networks"],
            "neural networks": [
                "neural networks architecture",
                "neural networks applications"
            ],
            "neural networks architecture": [
                "deep neural networks",
                "convolutional neural networks"
            ],
            "neural networks applications": [
                "neural networks in healthcare",
                "neural networks in finance"
            ]
        },
        key_findings=[
            {
                "query": "neural networks",
                "depth": 0,
                "confidence": 0.92,
                "finding": "Neural networks are computational models inspired by the human brain."
            },
            {
                "query": "neural networks architecture",
                "depth": 1,
                "confidence": 0.88,
                "finding": "Most neural networks include input, hidden, and output layers."
            },
            {
                "query": "neural networks applications",
                "depth": 1,
                "confidence": 0.85,
                "finding": "Neural networks are widely used in image recognition, NLP, and recommendation systems."
            },
            {
                "query": "deep neural networks",
                "depth": 2,
                "confidence": 0.80,
                "finding": "Deep neural networks contain multiple hidden layers that extract hierarchical features."
            },
            {
                "query": "neural networks in healthcare",
                "depth": 2,
                "confidence": 0.78,
                "finding": "Neural networks help in medical image analysis and disease prediction."
            }
        ],
        evidence=[
            {
                "query": "neural networks",
                "source": "Machine Learning Textbook",
                "evidence": "Neural networks simulate the behavior of the human brain to recognize patterns.",
                "confidence": 0.95
            },
            {
                "query": "neural networks architecture",
                "source": "Deep Learning Journal",
                "evidence": "The depth of hidden layers determines the complexity of features that can be learned.",
                "confidence": 0.9
            },
            {
                "query": "neural networks applications",
                "source": "IEEE Conference Paper",
                "evidence": "Convolutional neural networks have revolutionized computer vision applications.",
                "confidence": 0.87
            },
            {
                "query": "deep neural networks",
                "source": "ArXiv Paper",
                "evidence": "Each layer in a deep network transforms the representation at one level to a higher level.",
                "confidence": 0.83
            },
            {
                "query": "neural networks in healthcare",
                "source": "Medical AI Journal",
                "evidence": "Neural networks achieve 95% accuracy in identifying diabetic retinopathy from retinal scans.",
                "confidence": 0.79
            }
        ],
        confidence_score=0.87,
        research_time=3.2,
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
                relevance_score=0.9,
                timestamp=datetime.now()
            ),
            # ... other paths would be included here
        ]
    )


def print_section(title):
    """Print a section title with decorative formatting."""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def main():
    """Demonstrate the usage of different formatter options."""
    # Create a sample research result
    research_result = create_sample_research_result()
    
    print_section("TOKEN OPTIMIZATION DEMONSTRATION")
    print("This demo shows how the same research result can be formatted")
    print("at different detail levels to optimize token usage.")
    
    # Format in COMPACT mode
    print_section("COMPACT FORMAT (Minimal Tokens)")
    compact_formatter = ResearchResultFormatter(FormatType.COMPACT)
    compact_result = compact_formatter.format_result(research_result)
    print(f"Token usage: Approximately {len(str(compact_result)) // 4} tokens")
    print("Content:")
    for key, value in compact_result.items():
        print(f"  {key}: {value}")
    
    # Format in SUMMARY mode
    print_section("SUMMARY FORMAT (Moderate Tokens)")
    summary_formatter = ResearchResultFormatter(FormatType.SUMMARY)
    summary_result = summary_formatter.format_result(research_result)
    print(f"Token usage: Approximately {len(str(summary_result)) // 4} tokens")
    print("Content preview:")
    print(f"  Query: {summary_result['query']}")
    print(f"  Findings count: {len(summary_result['key_findings'])}")
    print(f"  Evidence summary: {summary_result['evidence_summary']}")
    if 'exploration_stats' in summary_result:
        print(f"  Exploration stats: {summary_result['exploration_stats']}")
    
    # Format in FULL mode
    print_section("FULL FORMAT (Maximum Detail)")
    full_formatter = ResearchResultFormatter(FormatType.FULL, 
                                           FormatOptions(include_exploration_paths=True))
    full_result = full_formatter.format_result(research_result)
    print(f"Token usage: Approximately {len(str(full_result)) // 4} tokens")
    print("Content structure:")
    for key in full_result.keys():
        if isinstance(full_result[key], list):
            print(f"  {key}: {len(full_result[key])} items")
        else:
            print(f"  {key}: {type(full_result[key])}")
    
    # Demonstrate progressive loading
    print_section("PROGRESSIVE LOADING DEMONSTRATION")
    print("Starting with compact format, then loading details for one finding:")
    
    # First get compact format
    compact_result = compact_formatter.format_result(research_result)
    print(f"1. Compact result: {len(compact_result['key_conclusions'])} key conclusions")
    
    # Then get details for the first finding
    finding_details = compact_formatter.get_finding_details(research_result, 0)
    print(f"2. Loaded details for finding: '{finding_details['finding']['finding']}'")
    print(f"   Evidence items: {len(finding_details['evidence'])}")
    print(f"   Related queries: {finding_details['related_queries']}")
    
    # Show token comparison
    print_section("TOKEN USAGE COMPARISON")
    compact_tokens = len(str(compact_result)) // 4
    summary_tokens = len(str(summary_result)) // 4
    full_tokens = len(str(full_result)) // 4
    progressive_tokens = compact_tokens + (len(str(finding_details)) // 4)
    
    print(f"COMPACT format:     {compact_tokens} tokens")
    print(f"SUMMARY format:     {summary_tokens} tokens")
    print(f"FULL format:        {full_tokens} tokens")
    print(f"PROGRESSIVE loading: {progressive_tokens} tokens (compact + one finding details)")
    print(f"\nToken savings vs FULL format:")
    print(f"  COMPACT:           {full_tokens - compact_tokens} tokens ({(full_tokens - compact_tokens) / full_tokens * 100:.1f}%)")
    print(f"  SUMMARY:           {full_tokens - summary_tokens} tokens ({(full_tokens - summary_tokens) / full_tokens * 100:.1f}%)")
    print(f"  PROGRESSIVE:       {full_tokens - progressive_tokens} tokens ({(full_tokens - progressive_tokens) / full_tokens * 100:.1f}%)")


if __name__ == "__main__":
    main()
