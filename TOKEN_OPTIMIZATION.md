# Token Optimization for Deep Research

## Overview

This feature provides a tiered result formatting system for the deep-research module that dramatically reduces token usage while preserving essential information. By selecting the appropriate format type, you can optimize token usage for different scenarios.

## Token Usage Comparison

| Format   | Token Usage | Savings vs FULL |
|----------|-------------|-----------------|
| COMPACT  | ~120 tokens | 80.6% (499 tokens) |
| SUMMARY  | ~221 tokens | 64.3% (398 tokens) |
| FULL     | ~619 tokens | - |

## Format Types

### COMPACT Format

The COMPACT format provides just the essential conclusions with minimal metadata.

```json
{
  "query": "neural networks",
  "key_conclusions": [
    "Neural networks are computational models inspired by the human brain.",
    "Most neural networks include input, hidden, and output layers.",
    "Neural networks are widely used in image recognition, NLP, and recommendation systems."
  ],
  "confidence": 0.87,
  "sources_count": 5
}
```

### SUMMARY Format

The SUMMARY format provides moderate detail with findings, confidence scores, and evidence summary.

```json
{
  "query": "neural networks",
  "key_findings": [
    {
      "finding": "Neural networks are computational models inspired by the human brain.",
      "confidence": 0.9
    },
    {
      "finding": "Most neural networks include input, hidden, and output layers.",
      "confidence": 0.85
    }
  ],
  "evidence_summary": "Evidence collected from 5 items across 3 sources. Top sources: AI Textbook (2), IEEE Paper (1), Research Journal (1). Average evidence confidence: 0.87.",
  "exploration_stats": {
    "depth": 1,
    "paths_explored": 3,
    "total_time": 2.5
  }
}
```

### FULL Format

The FULL format provides complete details including the query tree, all findings, evidence, and exploration paths.

```json
{
  "query_tree": {
    "root": ["neural networks"],
    "neural networks": ["neural networks architecture", "neural networks applications"]
  },
  "key_findings": [ ... ],
  "evidence": [ ... ],
  "confidence_score": 0.85,
  "research_time": 2.5,
  "exploration_paths": [ ... ]
}
```

## Progressive Loading

One of the key features of the token optimization system is progressive loading. You can start with a compact format and load additional details only when needed.

```python
# Start with compact format to minimize tokens
compact_result = deep_search("neural networks", format_type="compact")

# If the user wants details about a specific finding,
# load just those details instead of the full result
finding_idx = 0  # Index of the finding the user is interested in
finding_details = get_finding_details(original_result, finding_idx)
```

This approach allows for a significant token savings compared to always using the FULL format.

## Usage

### Command Line

```bash
# Get compact results (~120 tokens)
llm websearch deep-search "neural networks" --format-type compact

# Get summary results (~221 tokens)
llm websearch deep-search "neural networks" --format-type summary

# Get full results (~619 tokens)
llm websearch deep-search "neural networks" --format-type full
```

### Python API

```python
from llm_websearch import deep_search

# Get compact results
result = deep_search("neural networks", format_type="compact")

# Get summary results
result = deep_search("neural networks", format_type="summary")

# Get full results
result = deep_search("neural networks", format_type="full")
```

## Benefits

1. **Token Efficiency**: Dramatically reduces token usage, lowering costs and improving response times.
2. **Tiered Access**: Provides the right level of detail for different contexts.
3. **Progressive Loading**: Allows loading additional details only when needed.
4. **Customizable**: Format options can be customized for specific needs.

## Implementation

The token optimization system is implemented through three main components:

1. **FormatType Enum**: Defines the different format types (COMPACT, SUMMARY, FULL).
2. **FormatOptions Class**: Provides configuration for detailed control of output.
3. **ResearchResultFormatter Class**: Transforms research results into optimized formats.

This implementation allows for a flexible and extensible system that can be easily adapted for different use cases.
