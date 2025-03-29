# Deep Search Architecture Diagram

```mermaid
sequenceDiagram
    participant CLI
    participant Core (deep_search)
    participant QueryExpander
    participant DeepResearcher
    participant LLMIntegration
    participant SearchFunc (google/bing+filter)
    participant FastFilter
    participant DetailedAnalyzer
    participant Summarizer
    participant Cache
    CLI->>Core: deep_search(query, ...)
    Core->>QueryExpander: Instantiate
    Core->>QueryExpander: expand_query(query)
    QueryExpander-->>Core: expanded_queries
    Core->>DeepResearcher: Instantiate(search_function=SearchFunc, generate_subqueries_func=_llm_gen, llm_integration=LLMIntegration, ...)
    Core->>DeepResearcher: research(chosen_query)
    loop Exploration (Depth < MaxDepth, Relevance > Threshold)
        DeepResearcher->>SearchFunc: search(current_query)
        SearchFunc->>Cache: Check cache
        alt Cache Miss
            SearchFunc->>Google/Bing API: Perform search
            SearchFunc->>FastFilter: Instantiate
            SearchFunc->>FastFilter: filter_batch(results)
            FastFilter-->>SearchFunc: filtered_snippets
            SearchFunc->>Cache: Store filtered results
        end
        SearchFunc-->>DeepResearcher: search_results (filtered)
        opt Process Results
             DeepResearcher->>DetailedAnalyzer: analyze_batch(urls)
             DetailedAnalyzer->>LLMIntegration: generate_response (analysis)
             LLMIntegration-->>DetailedAnalyzer: analysis
             DetailedAnalyzer-->>DeepResearcher: detailed_results
        end
        DeepResearcher->>_llm_gen: Generate Subqueries (using LLMIntegration)
        _llm_gen->>LLMIntegration: generate_response (subqueries)
        LLMIntegration->>Cache: Check LLM Cache
        alt LLM Cache Miss
            LLMIntegration->>LLM API: Call model
            LLMIntegration->>Cache: Store LLM Response
        end
        LLMIntegration-->>_llm_gen: subqueries
        _llm_gen-->>DeepResearcher: subqueries
        DeepResearcher->>DeepResearcher: _explore_query(subquery) # Recursive call
    end
    DeepResearcher-->>Core: research_result (findings, evidence, etc.)
    Core->>Summarizer: Instantiate(llm_integration)
    Core->>Summarizer: summarize(research_result.findings/evidence)
    Summarizer->>LLMIntegration: generate_response (summaries)
    LLMIntegration-->>Summarizer: tiered_summaries
    Summarizer-->>Core: formatted_summary_output
    Core-->>CLI: Final Result (JSON with tiered summary)
```

## Task Progress Visualization
## Implementation Tasks Progress

- [x] 1. Implement LLM-Powered Subquery Generation
- [x] 2. Instantiate and Pass LLMIntegration
- [x] 3. Refactor Existing LLM Calls
- [x] 4. Provide LLMIntegration to DeepResearcher
- [x] 5. Remove cache.py
- [x] 6. Consolidate Caching on diskcache
- [x] 7. Integrate QueryExpander
- [x] 8. Integrate FastFilter
- [x] 9. Integrate DetailedAnalyzer
- [x] 10. Integrate Summarizer
- [x] 11. Refactor __init__.py
- [x] 12. Improve Relevance & Pruning
- [x] 13. Visualize Target Architecture
- [x] 14. Write Integration Tests
- [x] 15. Update Existing Tests

**Status:** All implementation tasks completed.
