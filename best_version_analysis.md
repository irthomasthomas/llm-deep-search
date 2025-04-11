# Finding the Best Working Version of llm-search Plugin

This document tracks the process of identifying the most stable and functional version of the `llm-search` plugin within the Git history of the `llm-deep-search-v4-copy` project.

## Plan Overview

The goal is to systematically test different versions (branches/commits) of the plugin to find the one that works best according to the specified criteria.

**Task Diagram / Workflow:**

```mermaid
graph TD
    A[Start] --> B{Clean Working Directory};
    B --> C{List Branches/Commits};
    C --> D{Select Version};
    D --> E[Checkout Version];
    E --> F{Identify Plugin Name};
    F --> G[Uninstall Previous Plugin (if any)];
    G --> H[Install Current Version];
    H -- Success --> I{Verify Installation};
    H -- Failure --> J[Document Installation Failure];
    I -- Success --> K{Test Basic Search};
    I -- Failure --> L[Document Verification Failure];
    K -- Success --> M{Test Deep Search (if available)};
    K -- Failure --> N[Document Basic Search Failure];
    M -- Success --> O{Evaluate Results};
    M -- Failure --> P[Document Deep Search Failure];
    O --> Q[Document Version Findings];
    J --> Q;
    L --> Q;
    N --> Q;
    P --> Q;
    Q --> R{More Versions to Test?};
    R -- Yes --> B;
    R -- No --> S[Identify Best Version];
    S --> T[Final Documentation];
    T --> Z[End];
```

## Testing Workflow Steps (for each version)

1.  **Clean Directory:** Run `git status` to check for untracked/modified files. Remove specific files/dirs (`build`, `*.egg-info`, `**/__pycache__`) and potentially run `git clean -fdx` if needed after checking status.
2.  **Switch Version:** `git checkout [branch-name or commit-hash]`
3.  **Identify Plugin Name:** Check `setup.py` or `pyproject.toml` for the plugin's registered name (e.g., `websearch`, `deep-search`).
4.  **Uninstall Existing:** Run `LLM_LOAD_PLUGINS='' llm uninstall [plugin-name]` (use the name identified in step 3). Ignore errors if the plugin wasn't previously installed.
5.  **Install Current:** Run `llm install -U .`
6.  **Verify Installation:** Run `llm plugins` and check if the plugin is listed correctly.
7.  **Test Basic Search:** Run `llm search -q 'knowledge cutoff date for gemini-2.5' -e bing -n 5` and `llm search -q 'knowledge cutoff date for gemini-2.5' -e google -n 5`. Capture output.
8.  **Test Deep Search (if applicable):** Run `llm search --deep -q 'knowledge cutoff date for gemini-2.5'`. Capture output.
9.  **Evaluate Results:** Redirect search output to an LLM for evaluation.
    *   Capture conversation ID: `llm logs list -n 1 --json | jq -r '.[0].conversation_id' > search_cid.txt`
    *   Evaluate: `cat search_output.txt | llm -m gemini-2.5 'Evaluate the quality and relevance of these search results for the query "knowledge cutoff date for gemini-2.5". Are they helpful?'`
    *   Use CID for follow-up if needed: `llm -c --cid $(cat search_cid.txt) 'Further analysis...'`
10. **Document:** Record findings, outputs, and any issues in the "Version Testing Results" section below.

## Version Testing Results

*(This section will be populated as versions are tested)*

### Version: `[Branch/Commit Name]`
*   **Commit Hash:** `[git rev-parse HEAD]`
*   **Plugin Name:** `[Name from setup.py/pyproject.toml]`
*   **Clean Directory:** [Success/Failure, commands used]
*   **Checkout:** [Success/Failure]
*   **Uninstall:** [Success/Command Output/Notes]
*   **Installation:** [Success/Failure, command output]
*   **Verification (`llm plugins`):** [Success/Failure, output]
*   **Basic Search (Bing):** [Success/Failure, output snippet, evaluation notes]
*   **Basic Search (Google):** [Success/Failure, output snippet, evaluation notes]
*   **Deep Search:** [NA/Success/Failure, output snippet, evaluation notes]
*   **Evaluation Summary:** [Overall quality assessment]
*   **Issues Encountered:** [Any problems during the process]

---

*(Repeat structure for each tested version)*

## Best Working Version

*(To be determined after testing)*

*   **Branch/Commit:**
*   **Plugin Name:**
*   **Reasoning:**
*   **Key Features:**
*   **Installation Steps:**
*   **Usage Examples:**

## Conclusion & Lessons Learned

*(Summary of the process, challenges, and final outcome)*
