# LLM Search

## Installation

[Keep existing installation instructions]

## Configuration

Set the following environment variables:

- `GOOGLE_SEARCH_KEY`: Your Google Custom Search API key
- `GOOGLE_SEARCH_ID`: Your Google Custom Search Engine ID
- `BING_CUSTOM_SEARCH_KEY`: Your Bing Custom Search API key
- `BING_CUSTOM_CONFIG_ID`: Your Bing Custom Search Configuration ID
- `CACHE_DIR`: Directory for caching search results (default: `/tmp/search_cache`)
- `MAX_RETRIES`: Maximum number of retries for failed requests (default: 3)
- `RETRY_DELAY`: Delay between retries in seconds (default: 1)
- `REQUEST_TIMEOUT`: Timeout for HTTP requests in seconds (default: 10)
- `LLM_MODELS`: Comma-separated list of LLM models to use (default: "cerebras-llama3.3-70b,gemini-2")

You can set these in a `.env` file in your project directory.

## Usage

```bash
llm search -q "Your search query" -n 5 -e google -o results.txt
```

Options:
- `-q, --query`: Search query (required)
- `-n, --num-results`: Number of results to fetch (default: 10, max: 100)
- `-e, --search-engine`: Search engine to use (choices: google, bing; default: google)
- `-o, --output`: Output file for results (default: stdout)
- `--models`: Comma-separated list of LLM models to use (overrides `LLM_MODELS` environment variable)

To specify custom models, use the `--models` option:

```bash
llm search -q "Your query" --models "model1,model2,model3"
```

## Features

- Web search using Google Custom Search or Bing Custom Search
- Content extraction from web pages and PDFs
- JavaScript rendering for dynamic web pages
- Relevant quote extraction using LLMs
- Result summarization using LLMs
- Caching of search results and processed content
- Configurable LLM model selection

## Development

[Keep existing development instructions]

