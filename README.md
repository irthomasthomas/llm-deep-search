# LLM-WebSearch Plugin

This plugin integrates web search capabilities directly into the `llm` CLI tool, allowing LLMs to perform standard web searches and deep, iterative research based on initial queries.

## Features

- **Standard Search (`llm websearch search ...`)**:
    - Combines results from configured search engines (Google Custom Search, Bing Custom Search).
    - Deduplicates results based on URL.
    - Optional fast relevance filtering using LLMs.
    - Sorts results by rank.
    - Formatted output in the terminal.
- **Deep Search (`llm websearch deep-search ...`)**:
    - Performs an initial search and analysis.
    - Iteratively explores promising sub-queries based on findings (controlled by `max_iterations`).
    - Analyzes content relevance using LLMs or keyword fallbacks.
    - Extracts key insights and findings from explored paths.
    - Identifies potential contradictions between different information sources.
    - Generates multi-level summaries (short, medium, detailed) of the research.
    - Provides formatted Markdown output summarizing the research process and results.
- **Configurable**: Control API keys, models, search parameters, component behavior, and more via a YAML file (`llm_websearch_config.yaml`) and environment variables.
- **Asynchronous**: Uses `asyncio` for concurrent operations (search engine requests, LLM calls).
- **Caching**: Utilizes `diskcache` to cache search results and LLM responses, speeding up subsequent identical requests.

## Installation

1.  **From PyPI (Stable Version - Not Yet Available):**
    ```bash
    llm install llm-websearch
    # or
    pip install llm-websearch
    ```
2.  **From Source (Development):**
    Clone the repository and install in editable mode:
    ```bash
    git clone <repository_url> llm-websearch
    cd llm-websearch
    pip install -e .
    ```
    This requires having `llm` installed (`pip install llm`). Using a virtual environment is recommended.

## Configuration

The plugin requires API keys for search engines and potentially the LLM provider. Configuration is loaded from the following sources (highest priority first):

1.  **Environment Variables**
2.  **.env file** in the current working directory
3.  **`llm_websearch_config.yaml`** file in the project root directory

An example configuration file (`llm_websearch_config.yaml`) is provided. You **must** replace the placeholder values with your actual API keys and IDs.

**Key Configuration Variables:**

| Setting Name            | Environment Variable              | YAML Key                  | Description                                     | Default              |
| ----------------------- | --------------------------------- | ------------------------- | ----------------------------------------------- | -------------------- |
| Google API Key          | `GOOGLE_SEARCH_KEY`               | `google_api_key`          | Google Cloud API Key                            | `None`               |
| Google CSE ID           | `GOOGLE_SEARCH_ID`                | `google_cse_id`           | Google Programmable Search Engine ID          | `None`               |
| Bing API Key            | `BING_CUSTOM_SEARCH_KEY`          | `bing_api_key`            | Bing Custom Search Subscription Key             | `None`               |
| Bing Custom Config ID | `BING_CUSTOM_CODE_SEARCH_CONF`    | `bing_custom_config_id` | Bing Custom Search Configuration ID           | `None`               |
| LLM API Key             | `LLM_API_KEY` or `GOOGLE_SEARCH_KEY` | `llm_api_key`           | API Key for the LLM (uses Google key if unset) | `None`               |
| Default LLM Model       | `LLM_MODEL_DEFAULT`             | `llm_model_default`       | Default model name (e.g., `gemini-1.5-flash-latest`) | `gemini-1.5-flash..` |
| Max Results/Engine      | `MAX_RESULTS_PER_ENGINE`        | `max_results_per_engine`  | Results per search engine per query/iteration   | `10`                 |
| Deep Search Iterations  | `DEEP_SEARCH_MAX_ITERATIONS`      | `deep_search_max_iterations` | Max recursion depth for deep search             | `3`                  |
| Cache Enabled           | `CACHE_ENABLED`                   | `cache_enabled`           | Enable/disable disk caching                     | `True`               |
| Log Level               | `LOG_LEVEL`                       | `log_level`               | Logging level (DEBUG, INFO, WARNING, ERROR)   | `INFO`               |

*(See `llm_websearch/config.py` and `llm_websearch_config.yaml` for a full list of configurable settings.)*

**Example `llm_websearch_config.yaml`:**
```yaml
# llm-websearch Configuration File
# Environment variables (e.g., GOOGLE_SEARCH_KEY) will override values set here.

# Google Search API (Custom Search Engine)
google_api_key: "YOUR_GOOGLE_API_KEY_HERE"
google_cse_id: "YOUR_GOOGLE_CSE_ID_HERE"

# Bing Search API (Custom Search)
bing_api_key: "YOUR_BING_API_KEY_HERE"
bing_custom_config_id: "YOUR_BING_CONFIG_ID_HERE"

# Optional: Override default LLM model
# llm_model_default: "gemini-1.5-pro-latest"

# Optional: Adjust search/research parameters
# max_results_per_engine: 15
# deep_search_max_iterations: 2
```

## Usage (CLI)

Once installed and configured, the plugin adds commands under the `llm websearch` group.

### Standard Search

Performs a basic web search using configured engines.

```bash
llm websearch search "Your search query here" [OPTIONS]
```

**Options:**
- `-n <number>`: Number of results (default combines engine limits).
- `-t <seconds>`: Timeout per search engine request.
- `--filter`: Enable fast LLM-based relevance filtering (requires LLM API key).
- `--verbose`: Enable detailed debug logging.

**Example:**
```bash
llm websearch search "python asyncio tutorial" -n 5
```
*(Output will be a formatted list of search results)*

### Deep Search

Performs an iterative, multi-level research process.

```bash
llm websearch deep-search "Your research topic here" [OPTIONS]
```

**Options:**
- `-n <number>`: Number of results per search *iteration*.
- `-t <seconds>`: General timeout for the entire deep search process.
- `-i <number>`: Maximum number of exploration iterations (depth).
- `-f [compact|summary|full]`: Output format (default: `summary`).
- `--verbose`: Enable detailed debug logging.

**Example:**
```bash
llm websearch deep-search "anthropic 2025 api prompt caching" -f full -n 10 -i 2 --verbose
```
*(Output will be a Markdown formatted report summarizing the research)*

## Usage (Python API - Basic Example)

While primarily intended as an `llm` CLI plugin, the core functions can be imported and used.

```python
import asyncio
from llm_websearch.core import deep_search, search
from llm_websearch.config import settings # Settings are loaded automatically on import

async def main():
    # Ensure API keys are set in environment or config file
    if not settings.google_api_key or not settings.bing_api_key:
        print("Warning: Search requires configured API keys!")
        # return # Optionally exit if keys missing

    print("--- Standard Search ---")
    standard_results = await search("Benefits of prompt caching", num_results=5)
    if standard_results:
        for i, res in enumerate(standard_results):
            print(f"{i+1}. {res.title} ({res.url})")
    else:
        print("Standard search returned no results.")

    print("
--- Deep Search ---")
    # Deep search returns Markdown string on success, dict on error
    deep_result_output = await deep_search(
        "Benefits of prompt caching",
        num_results=5, # Results per iteration
        max_iterations=1 # Limit depth for example
    )

    if isinstance(deep_result_output, str):
        print("Deep Search Results (Markdown):")
        print(deep_result_output)
    else: # Error dictionary returned
        print(f"Deep Search Failed: {deep_result_output.get('error_message')}")

if __name__ == "__main__":
    asyncio.run(main())
```
*(Note: The internal structure, component initialization, and result objects are subject to change. Relying on the core `search` and `deep_search` functions is recommended for stability.)*

## License

MIT