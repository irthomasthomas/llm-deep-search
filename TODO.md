**Task:** Enhance the `llm-websearch` plugin to match the functionality of the reference implementation in `llm-deep-search-v3`.  This involves adding several command-line options for finer-grained control over web searches and integrating those options into the search logic.

**Current Status:**

*   **Completed:**
    *   The basic structure of the `llm-websearch` plugin is set up, including core functions for Google and Bing search, caching, and rate limiting.
    *   The following command-line options have been added and are *mostly* functional (see "Issues" below):
        *   `-n`, `--num-results`: Specifies the number of results to return.
        *   `-t`, `--timeout`: Sets a timeout for search requests.
        *   `-e`, `--search-engine`: Allows the user to choose between "google" and "bing".
        *   `--date-restrict`: (Google only) Restricts results to a specific date range (e.g., `d1` for the past day, `w2` for the past two weeks).
        *   `--language`: (Google only) Restricts results to a specific language (e.g., `es` for Spanish).
        *   `--safe-search`:  Filters results based on safety level ("off", "medium", "high").  Case-insensitive.
        *   `--file-type`: (Google only) Restricts results to a specific file type (e.g., `pdf`).
        *   `--freshness`: (Bing only) Restricts results to a specific time frame ("Day", "Week", "Month"). Case-insensitive.
        *   `--market`: (Bing only) Specifies the market/language for results (e.g., `en-GB`).
        *   `-v`, `--verbose`: Enables verbose logging.

*   **In Progress:**
    * `--country` is not reliably working,

* **Files Modified:**
    *   `llm_websearch/__init__.py`:  This is the main file containing the plugin logic.  All changes so far have been made to this file.
    * `.env`: added to the project
    * `.env.example`: added to the project

**Issues and Next Steps:**

1.  **Bing API Endpoint** 
   We only have an api for bing custom search. Change the urls and anything else needed to accomodate this.
    **Troubleshooting Steps:**
    *   **url = "https://api.bing.microsoft.com/v7.0/custom/search"
    headers = {"Ocp-Apim-Subscription-Key": BING_CUSTOM_SEARCH_KEY}
    if AZURE_REGION:
        headers["Ocp-Apim-Subscription-Region"] = AZURE_REGION
    params = {
        "q": query,
        "customconfig": BING_CUSTOM_CONFIG_ID,
        "count": min(50, num_results),
        "offset": 0,
    }**

2.  **`--country` Option (Google):** The `--country` option for Google searches is not consistently filtering results.  The URL construction has been corrected multiple times, and the issue likely lies with the Google Custom Search Engine (CSE) configuration or the specific country codes being used.
    **Troubleshooting Steps:**
    *   **CSE Configuration:**  If you have access to the Google Custom Search Engine control panel used by this plugin (identified by the `GOOGLE_SEARCH_ID` in the `.env` file), *verify that the CSE is configured to allow filtering by country/region*.  This is the most likely cause of the problem.
    *   **Country Codes:**  Experiment with different country codes. The correct codes are two-letter ISO 3166-1 alpha-2 codes (e.g., `US`, `GB`, `CA`).  The code should be prefixed with `country`. So the param should be, for example, `cr=countryUS`.
    *   **API Documentation:** If the problem persists, consult the official Google Custom Search JSON API documentation to ensure the `cr` parameter is being used correctly: [https://developers.google.com/custom-search/v1/reference/rest/v1/cse/list](https://developers.google.com/custom-search/v1/reference/rest/v1/cse/list)

3.  **Remaining Command-Line Options:** None.

4.  **Testing:** Once the Bing API key and country filter issues are resolved, conduct thorough testing of *all* command-line options, in various combinations, to ensure they work correctly and interact properly.

5. **Deep Search:** The `deep_search` function exists in the current code, but I haven't started integrating/testing it. I'd recommend you complete and test the basic search functionality in `search_cmd` before working on the deep search functionality.

**Example Commands (for testing after fixing the issues):**

*   `llm websearch search-cmd "python tutorials" --search-engine google --date-restrict w1 --language en` (Google, past week, English)
*   `llm websearch search-cmd "financial news" --search-engine bing --freshness day --market en-US` (Bing, past day, US market)
*   `llm websearch search-cmd "linux kernel" --search-engine google --file-type pdf --safe-search high` (Google, PDFs, high safe search)
*  `llm websearch search-cmd "example" --country US`
*   `llm websearch search-cmd "example" --country GB`

**Code Overview:**

*   `llm_websearch/__init__.py`:
    *   `google_search()`:  Handles Google searches, including retries and parameter handling.
    *   `bing_search()`:  Handles Bing searches, including retries and parameter handling.
    *   `search()`:  A unified search function that calls either `google_search()` or `bing_search()` based on the `--search-engine` option. Includes fallback to mock results.
    *   `fetch_and_summarize()`:  Fetches content from a URL, extracts text, and summarizes it using an LLM.  (Currently uses a default LLM model.)
    *   `register_commands()`:  Registers the `websearch` command group and the `search_cmd` and `deep_search_cmd` commands with the `llm` CLI, using `click` for option parsing.
    *   `RateLimiter`: A simple rate limiter class to avoid exceeding API rate limits.
    *   `_cache_key`: helper function for generating cache keys.

**Key Libraries:**

*   `llm`:  The core `llm` library for interacting with LLMs.
*   `click`:  For creating the command-line interface.
*   `httpx`:  For making HTTP requests (to Google and Bing APIs).
*   `dotenv`:  For loading environment variables from a `.env` file.
*   `diskcache`:  For caching search results and fetched content.
*   `bs4`: (Beautiful Soup) For parsing HTML content.

This handoff document should provide all the necessary information to continue development and resolve the remaining issues. Good luck!