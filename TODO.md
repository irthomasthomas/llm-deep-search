
You are a highly skilled software development agent. Your task is to complete the `llm-websearch` plugin for the `llm` CLI, specifically implementing the `search` and `deep_search` functionalities, using the Bing and Google Search APIs. The plugin should also include a fallback mechanism, using a mock search if the APIs fail.

**Project Context:**

*   This is an `llm` plugin, so use the standard plugin structure.
*   You've previously worked on components of this, such as `deep_research.py`, `fast_filter.py`, `summarization.py`, and the `cache.py` module.  You *can* reuse code from these if appropriate, but the focus here is on the `search` and `deep_search` functions that integrate with web search APIs.
* The plugin must include comprehensive docstrings
* Code should follow a test-driven design.
  
The llm_search tool can be significantly enhanced by implementing a multi-tiered search architecture, optimizing caching, improving LLM integration, and refining the query expansion and summarization processes. Here's a comprehensive plan:

Multi-Tiered Search Architecture:

Tier 1 (Fast Filtering): Use lightweight LLMs to quickly assess the relevance of search results and filter out irrelevant content.
Tier 2 (Detailed Analysis): Employ more powerful LLMs to extract detailed quotes, analyze content, and perform initial summarization.
Tier 3 (Deep Research): Leverage advanced LLMs for iterative query refinement, comprehensive summarization, and synthesis of information.
Parallel Processing:

Utilize concurrent.futures.ThreadPoolExecutor to parallelize search API calls, content fetching, and LLM processing.
Implement parallel LLM calls within the call_llm function to reduce latency and improve efficiency.
Caching Improvements:

Implement cache expiration based on time and content freshness.
Use more precise cache keys that include parameters like search engine, date range, and other relevant factors.
Consider content-based caching to invalidate cache entries when webpage content changes significantly.
LLM Integration and Prompt Engineering:

Use fast and cheap LLMs for initial filtering, query expansion, and quick summarization.
Employ powerful LLMs for detailed analysis, comprehensive summarization, and report generation.
Design prompts to be concise and task-specific to maximize the effectiveness of LLMs.
Query Expansion and Refinement:

Use LLMs to expand and refine search queries, incorporating synonyms, related terms, and alternative phrasings.
Implement an iterative search loop where initial results and LLM analysis guide subsequent searches.
Summarization and Synthesis:

Implement a hierarchical summarization approach, summarizing individual pages and then synthesizing these summaries into a comprehensive report.
Use long-context LLMs for more coherent and comprehensive summaries.
Fallback Search:

Improve the fallback search mechanism by using more robust web scraping techniques or alternative search APIs.
Consider integrating with services like SerpAPI for more reliable search results.
DEEP RESEARCH Agent:

Develop a control loop that orchestrates the iterative search process, manages query refinement, and determines when to stop or iterate further.
Use concurrent.futures to parallelize tasks within the agent.
Maintain a "search trail" to keep track of the exploration process and ensure coherence in the research.
By implementing these improvements, the llm_search tool will become more efficient, effective, and capable of performing deep research tasks while adhering to the constraints of avoiding async and keeping dependencies minimal.


**Requirements:**

1.  **`search` Function:**
    *   **API Integration:**
        *   Implement search functionality using *both* the Bing Search API *and* the Google Custom Search JSON API. You'll need to obtain API keys for both.
        *   Use environment variables `BING_SEARCH_API_KEY` and `GOOGLE_SEARCH_API_KEY` for the API keys.  Also support `BING_SUBSCRIPTION_KEY` as an alias for `BING_SEARCH_API_KEY`.
        *   Use the `GOOGLE_CUSTOM_SEARCH_ENGINE_ID` environment variable for the Google Custom Search Engine ID.
        *   Prioritize using environment variables over any hard-coded values or configuration files.
    *   **Parameters:**
        *   `query`: (str) The search query.  (Required)
        *   `num_results`: (int, default=10) The maximum number of results to return.
        *   `timeout`: (float, default=30.0) Timeout for API requests.
    *   **Output:**  Return a list of dictionaries, where each dictionary represents a search result and has the following keys:
        *   `title`: (str) The title of the search result.
        *   `url`: (str) The URL of the search result.
        *   `snippet`: (str) A short snippet of text from the search result.
        *   `source`: (str) Indicate the search engine used ("bing" or "google").
    *   **Error Handling:**
        *   Handle API errors gracefully (e.g., invalid API keys, network issues, rate limiting).
        *   If one search engine fails, fall back to the other.
        *   If *both* search engines fail, use the existing `_mock_search_results` function (provided below) to return *mock* results, but *only* as a last resort.
        *   Raise a custom `SearchError` (you can define this) if all search attempts fail, including the mock fallback.
    *   **Asynchronous Execution:** Use `async` and `await` for making API requests to improve performance.
    *   **Caching:** (Optional, but highly recommended for later) Consider implementing caching of search results (you have a `cache.py` module). If implemented, prioritize cache hits. For now, focus on the core API integration, and we can add caching later.

2.  **`deep_search` Function:**
    *    For now, simply call search and return the result as a dict with "query", "results" and "analysis".
    *    Set analysis to "Coming soon".

3.  **Integration with `llm` CLI:**
    *   Create an `llm` plugin with a `search` and `deep-search` command.
    *   The `search` command should take the query as an argument.
    *   The `search` command should have options for `num_results` and `timeout`.
    *   The `deep-search` command should take the query as an argument.

**Existing Code (for reference/reuse - DO NOT BLINDLY COPY):**

```python
# From your existing search.py (SIMPLIFIED)
def google_search(query: str, num_results: int = 10, timeout: float = 30.0) -> List[Dict]:
    """Perform Google search"""
    start_time = time.time()
    check_timeout(start_time, timeout)
    
    results = []
    for i in range(num_results):
        check_timeout(start_time, timeout)
        results.append({
            "title": f"Result {i}",
            "link": f"https://example.com/{i}",
            "snippet": f"This is result {i} for query: {query}"
        })
    return results

def bing_search(query: str, num_results: int = 10, timeout: float = 30.0) -> List[Dict]:
    """Perform Bing search"""
    start_time = time.time()
    check_timeout(start_time, timeout)
    
    results = []
    for i in range(num_results):
        check_timeout(start_time, timeout)
        results.append({
            "title": f"Bing Result {i}",
            "link": f"https://example.com/bing/{i}",
            "snippet": f"This is Bing result {i} for query: {query}"
        })
    return results
```

**Example `__init__.py` Structure (Conceptual):**

```python
import click
import llm
import httpx  # Or your chosen HTTP library
import os
import json

# ... (Your exception classes) ...

@llm.hookimpl
def register_commands(cli):
    @cli.group()
    def websearch():
        """Web search commands using LLM"""
        pass

    @websearch.command()
    @click.argument("query", type=str)
    @click.option("-n", "--num-results", type=int, default=10, help="Number of results")
    @click.option("-t", "--timeout", type=float, default=30.0, help="Timeout in seconds")
    def search(query, num_results, timeout):
      """search"""
      # your implementation

    @websearch.command()
    @click.argument("query", type=str)
    def deep_search(query):
      """deep_search"""
        # Your implementation here

# ... (Your search functions: google_search, bing_search, search, deep_search) ...
```

**Example `pyproject.toml` (Conceptual):**
```
[project]
name = "llm-websearch"
version = "0.1.0"
description = "LLM plugin for web searching and deep searching."
readme = "README.md"
requires-python = ">=3.8"
dependencies = [
    "llm",
    "click",
    "httpx", #or requests
    "beautifulsoup4",  # For HTML parsing, if you do that.
    "python-dotenv" # For managing API keys in a .env file
]

[project.entry-points.llm]
websearch = "llm_websearch"

[project.optional-dependencies]
test = [
    "pytest",
    "pytest-asyncio",
]
```

**Testing**
Provide example tests in a `tests` directory.

**Deliverables:**

Provide the completed code for `llm_websearch/__init__.py` and `pyproject.toml` and `tests/test_websearch.py`, implementing the `search` and `deep-search` commands, using the `<WRITE_FILES>` tag. Ensure comprehensive docstrings are present.