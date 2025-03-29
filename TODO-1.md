1.  **Implement LLM-Powered Subquery Generation Function:**
    *   **File:** `llm_websearch/__init__.py`
    *   **Action:** Create a new internal function (e.g., `_generate_llm_subqueries`) within `__init__.py`. This function should take `original_query`, `combined_summaries`, `themes` (similar to the existing `generate_refined_queries`), and an `llm_integration_instance` as input. It should use `llm_integration_instance.generate_response` to call an appropriate LLM to generate relevant subqueries based on the input context. Adapt logic from the existing `generate_refined_queries` but ensure it uses the `LLMIntegration` instance.
    *   **Deliverable:** Python function `_generate_llm_subqueries` in `llm_websearch/__init__.py`.
2.  **Instantiate and Pass LLMIntegration:**
    *   **File:** `llm_websearch/__init__.py` (within `deep_search` function or a setup area)
    *   **Action:** Instantiate the `LLMIntegration` class from `llm_integration.py` *once*.
    *   **Action:** Modify the instantiation of `DeepResearcher` within the `deep_search` function to pass the newly created `_generate_llm_subqueries` function as the `generate_subqueries_function` argument. Also, pass the `llm_integration` instance to `DeepResearcher` via the `llm_integration` argument.
    *   **Deliverable:** Updated `deep_search` function in `llm_websearch/__init__.py` correctly initializing `LLMIntegration` and `DeepResearcher`.
3.  **Refactor Existing LLM Calls in `__init__.py`:**
    *   **File:** `llm_websearch/__init__.py`
    *   **Action:** Modify `fetch_and_summarize`, `extract_themes`, `detect_contradictions`, and the original `generate_refined_queries` (if still used elsewhere, otherwise it might be redundant) to use the single `llm_integration` instance created in Task 2, calling its `generate_response` method instead of `llm.get_model(...).prompt(...)`. Adjust prompts and parameters as needed for the `generate_response` method signature.
    *   **Deliverable:** Updated functions in `llm_websearch/__init__.py` using the central `LLMIntegration` instance.
4.  **Provide LLMIntegration to DeepResearcher Internals:**
    *   **File:** `llm_websearch/deep_research.py`
    *   **Action:** Ensure the `DeepResearcher` class correctly stores the passed `llm_integration` instance (e.g., `self.llm_integration`).
    *   **Action:** Modify internal methods within `DeepResearcher` that might benefit from LLM calls in the future (e.g., `_analyze_path_relevance`, `_extract_key_findings`, `_detect_contradictions`, `_extract_entities`) to check for and potentially use `self.llm_integration.generate_response(...)` if a custom function isn't provided or if enhanced logic is desired. (Initially, focus on ensuring the passed `generate_subqueries_function` works).
    *   **Deliverable:** Updated `DeepResearcher` class in `llm_websearch/deep_research.py`.
5.  **Remove `cache.py`:**
    *   **File:** `llm_websearch/cache.py`
    *   **Action:** Delete the entire `llm_websearch/cache.py` file.
    *   **Action:** Remove any import statements related to `llm_websearch.cache` from other files.
    *   **Deliverable:** Project structure without `llm_websearch/cache.py`.
6.  **Consolidate Caching on `diskcache`:**
    *   **File:** `llm_websearch/__init__.py`
    *   **Action:** Ensure the `diskcache.Cache` instance (`cache`) is initialized appropriately.
    *   **Action:** Verify and update caching logic within `google_search`, `bing_search`, and `fetch_and_summarize` to use the `diskcache` instance (`cache.get`, `cache.set`) with robust keys (including query, num_results, model name where applicable). Remove any remnants of the old `cache.py` usage.
    *   **Action:** Consider adding caching within the `LLMIntegration.generate_response` method (using the `diskcache` instance passed during initialization or accessed globally/via config) to cache LLM query results. Ensure cache keys include prompt, system prompt, task type, etc.
    *   **Deliverable:** Consistent use of `diskcache` for all relevant caching operations.
7.  **Integrate `QueryExpander`:**
    *   **File:** `llm_websearch/__init__.py` (within `deep_search`) and `llm_websearch/query_expansion.py`
    *   **Action:** Instantiate `QueryExpander` (from `query_expansion.py`) within the `deep_search` function, passing the `llm_integration` instance and the `diskcache` instance.
    *   **Action:** Before calling `researcher.research(query)`, use the `query_expander` instance to expand the initial `query`. Decide how to handle multiple expanded queries (e.g., run research for the top N, or pass context to the subquery generator). *Initial approach: Use the top expanded query or the original if expansion fails.*
    *   **Alternatively:** Modify the LLM-based `_generate_llm_subqueries` function (Task 1) to incorporate logic inspired by `QueryExpander` for generating *follow-up* queries.
    *   **Deliverable:** `QueryExpander` used in the `deep_search` flow or its logic integrated into subquery generation.
8.  **Integrate `FastFilter`:**
    *   **File:** `llm_websearch/__init__.py` (within `search` function) and `llm_websearch/fast_filter.py`.
    *   **Action:** Instantiate `FastFilter` within the main `search` function.
    *   **Action:** After collecting results from `google_search` and `bing_search` but *before* returning, use `fast_filter.filter_batch` on the snippets/content to remove irrelevant results quickly. Return only the filtered results.
    *   **Action:** Ensure `FastFilter` can use `llm_integration` for its lightweight model if needed (refactor `_score_content` in `fast_filter.py`).
    *   **Deliverable:** `FastFilter` integrated into the `search` function to pre-filter results.
9.  **Integrate `DetailedAnalyzer`:**
    *   **File:** `llm_websearch/deep_research.py`
    *   **Action:** Consider replacing or augmenting the call to `fetch_and_summarize` (which might be implicitly used via the `search_function` results or called separately) within `DeepResearcher` or its data processing steps. Instantiate `DetailedAnalyzer` (passing `llm_integration`).
    *   **Action:** When processing results for a query path (e.g., within `_extract_key_findings` or a dedicated processing step), fetch full content for promising URLs and use `detailed_analyzer.analyze_content` or `analyze_batch` to get richer analysis instead of just a basic summary. This richer data can feed into finding extraction and relevance.
    *   **Deliverable:** `DetailedAnalyzer` used within `DeepResearcher` for deeper content analysis of search results.
10. **Integrate `Summarizer`:**
    *   **File:** `llm_websearch/__init__.py` (within `deep_search`) and `llm_websearch/summarization.py`
    *   **Action:** Instantiate `Summarizer` (passing `llm_integration`) at the end of the `deep_search` function.
    *   **Action:** After `researcher.research(query)` returns the `research_result`, extract the `key_findings` or `evidence` text.
    *   **Action:** Pass this extracted text content to `summarizer.summarize`.
    *   **Action:** Use the output from `summarizer.summarize` (e.g., tiered summaries, key insights) to structure the final output returned by the `deep_search` function, potentially replacing the simple `summary` field generated previously.
    *   **Deliverable:** `Summarizer` used to process and structure the final output of `deep_search`.
11. **Refactor `__init__.py`:**
    *   **File:** `llm_websearch/__init__.py`
    *   **Action:** Create a new file, e.g., `llm_websearch/core.py`.
    *   **Action:** Move the main logic of the `search` and `deep_search` functions (including helper functions like `_generate_llm_subqueries`) from `__init__.py` to `core.py`.
    *   **Action:** Update `__init__.py`: Keep plugin registration (`register_commands`), necessary imports, potentially config loading, and the Click command definitions. The command functions should now primarily call the corresponding functions imported from `core.py`.
    *   **Deliverable:** Slimmed-down `__init__.py` and new `core.py` containing orchestration logic.
12. **Improve Relevance & Pruning:**
    *   **File:** `llm_websearch/deep_research.py` and `llm_websearch/__init__.py` (or `core.py`)
    *   **Action:** Add CLI options to `deep_search_cmd` for `relevance-threshold` and `diminishing-returns-threshold`. Pass these values to the `DeepResearcher` constructor.
    *   **Action:** Implement an optional LLM-based relevance analysis function. Create `_analyze_llm_relevance` in `core.py` using `llm_integration`. Pass this function to `DeepResearcher` via `analyze_relevance_function`. Add a CLI flag to enable/disable this.
    *   **Deliverable:** Configurable thresholds and optional LLM-based relevance checking.
13. **Visualize Target Architecture:**
    *   **Action:** Create a sequence diagram illustrating the intended flow of `deep_search` after refactoring.
    *   **Deliverable:** Mermaid sequence diagram embedded below.
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
14. **Write Integration Tests for Iteration:**
    *   **File:** `llm_websearch/tests/test_deep_search_integration.py` (new file)
    *   **Action:** Create new integration tests for `deep_search` (or the core logic in `core.py`).
    *   **Action:** Mock *only* the external dependencies:
        *   `httpx.Client.get` calls for Google/Bing.
        *   The actual LLM API call within `LLMIntegration` (or mock `llm.get_model` if `LLMIntegration` still uses it internally).
        *   Potentially mock `diskcache.Cache.get/set` if needed to control test flow.
    *   **Action:** Define mock responses for search and LLM calls that simulate generating relevant subqueries for the first iteration.
    *   **Action:** Assert that when `max_iterations` > 1:
        *   The `search_function` (mocked) is called multiple times with different queries (original + subqueries).
        *   The subquery generation function (`_generate_llm_subqueries`) is called.
        *   The resulting `query_tree` in the `ResearchResult` has a depth greater than 1.
    *   **Deliverable:** New integration test file with tests verifying the recursive behavior.
15. **Update Existing Tests:**
    *   **File:** `llm_websearch/tests/test_websearch.py`
    *   **Action:** Review and update existing unit tests to reflect the refactored code structure (e.g., changes in function signatures, use of `LLMIntegration`, removal of `cache.py`).
    *   **Action:** Ensure tests for helper modules (`FastFilter`, `QueryExpander`, etc.) are present and cover their core functionality.
    *   **Deliverable:** Updated `test_websearch.py` and potentially new test files for integrated modules.
