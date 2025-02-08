import os
import json
import hashlib
import logging
import concurrent.futures
from typing import List, Dict, Optional
from pathlib import Path

import click  # Ensure click is imported
import requests
from bs4 import BeautifulSoup
from diskcache import Cache
from dotenv import load_dotenv
from html2text import html2text
from pdfminer.high_level import extract_text
from io import BytesIO
from requests_html import HTMLSession
import subprocess
import shlex
import llm

# Load environment variables
load_dotenv()

# --- Configuration ---
CACHE_DIR = Path(os.getenv("CACHE_DIR", "/tmp/search_cache"))
MAX_RESULTS = 100
DEFAULT_NUM_RESULTS = 10
GOOGLE_SEARCH_KEY = os.getenv("GOOGLE_SEARCH_KEY")
GOOGLE_SEARCH_ID = os.getenv("GOOGLE_SEARCH_ID")
BING_CUSTOM_SEARCH_KEY = os.getenv("BING_CUSTOM_SEARCH_KEY")
BING_CUSTOM_CONFIG_ID = os.getenv("BING_CUSTOM_CONFIG_ID")
AZURE_REGION = os.getenv("AZURE_REGION")
MAX_RETRIES = int(os.getenv("MAX_RETRIES", 3))
RETRY_DELAY = int(os.getenv("RETRY_DELAY", 1))
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", 2))

# New configuration for LLM models
DEFAULT_LLM_MODELS = ["cerebras-llama3.3-70b", "llama-3.3-70b-versatile", "gemini-2.0-flash-lite-preview-02-05"]
LLM_MODELS = os.getenv("LLM_MODELS", ",".join(DEFAULT_LLM_MODELS)).split(",")

# --- Logging Setup ---
logging.basicConfig(
    level=logging.ERROR, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# --- Cache Initialization ---
cache = Cache(CACHE_DIR)

# --- Helper Functions ---

def estimate_token_count(text: str) -> int:
    """Estimates the number of tokens in the given text."""
    word_count = len(text.split())
    estimated_tokens = word_count * 4 // 3
    return estimated_tokens

def fetch_content(url: str, retries: int = MAX_RETRIES) -> Optional[bytes]:
    """Fetches content from a URL with retries and web archive fallback."""
    logger.info(f"Fetching content from: {url}")
    session = HTMLSession()
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
    }
    try:
        response = session.get(url, timeout=REQUEST_TIMEOUT, headers=headers)
        response.raise_for_status()
        if "text/html" in response.headers.get("Content-Type", ""):
            try:
                response.html.render()
                return response.html.raw_html.encode()
            except Exception as e:
                logger.warning(f"Failed to render JavaScript for {url}: {e}")
        return response.content
    except requests.exceptions.RequestException as e:
        logger.warning(f"Request failed for {url}: {e}")
        if retries > 0:
            logger.info(f"Retrying ({retries} retries left)...")
            import time
            time.sleep(RETRY_DELAY)
            return fetch_content(url, retries - 1)
        else:
            logger.warning(f"Max retries reached for {url}. Trying web archive...")
            try:
                archived_url = f"https://web.archive.org/web/0/{url}"
                archived_response = requests.get(archived_url, timeout=REQUEST_TIMEOUT)
                archived_response.raise_for_status()
                return archived_response.content
            except requests.exceptions.RequestException as archive_e:
                logger.error(f"Failed to fetch from web archive for {url}: {archive_e}")
                return None

def extract_text(content: bytes, url: str) -> str:
    """Extracts text from HTML or PDF content."""
    try:
        if url.lower().endswith(".pdf"):
            return extract_text(BytesIO(content))
        else:
            return html2text(content.decode('utf-8', errors='ignore'))
    except Exception as e:
        logger.error(f"Error extracting text from {url}: {e}")
        return ""

def call_llm(prompt: str, system_prompt: str, models: List[str] = LLM_MODELS) -> str:
    """Calls the specified LLMs in sequence using the llm Python API."""
    for model in models:
        logger.info(f"Trying LLM model: {model}")
        try:
            client = llm.get_model(model)
            response = client.prompt(prompt, system=system_prompt)
            return response.text()
        except Exception as e:
            logger.warning(f"LLM call failed for model {model}: {e}")
    logger.error("All LLM models failed")
    return "Error: All LLM models failed to process the request."

def process_single_url(url: str, search_query: str) -> Dict[str, str]:
    """Processes a single URL, including fetching, extracting, and calling the LLM."""
    logger.info(f"Processing URL: {url}")
    cache_key = hashlib.md5(f"{url}:{search_query}".encode()).hexdigest()

    if cache_key in cache:
        logger.info(f"Using cached result for {url}")
        return cache[cache_key]

    content = fetch_content(url)
    if content is None:
        return {"url": url, "relevant_quotes": "Failed to fetch content."}

    page_text = extract_text(content, url)
    if not page_text:
        return {"url": url, "relevant_quotes": "Failed to extract text."}

    token_count = estimate_token_count(page_text)
    logger.info(f"Estimated token count for {url}: {token_count}")
    
    extract_prompt = f"""<QUERY>"{search_query}"</QUERY>
Extract only relevant quotes AND CODE that are useful to answering the query if they exist in the scraped page.
Include the source URL.
Provide a relevance score from LOW/MEDIUM/HIGH for each passage.
If two or more passages score MEDIUM or HIGH for relevance, provide the whole page.
Only return passages and code blocks and strip useless webpage text"""
    
    relevant_quotes = call_llm(
        f"""<url>
{url}
</url>

<page_text>
{page_text}
</page_text>""",
        extract_prompt
    )

    result = {"url": url, "relevant_quotes": relevant_quotes}
    cache[cache_key] = result
    return result

# --- Search Engine Implementations ---

def parse_advanced_operators(query: str) -> Dict[str, str]:
    """Parses advanced search operators from the query."""
    operators = {
        'site': None,
        'filetype': None,
        'inurl': None,
        'intitle': None,
    }
    
    words = query.split()
    new_query = []
    
    for word in words:
        for operator in operators:
            if word.startswith(f"{operator}:"):
                operators[operator] = word.split(':', 1)[1]
                break
        else:
            new_query.append(word)
    
    return {
        'query': ' '.join(new_query),
        'operators': operators
    }

def google_search(query: str, num_results: int, date_restrict: Optional[str] = None, 
                  language: Optional[str] = None, country: Optional[str] = None, 
                  safe_search: Optional[str] = None, file_type: Optional[str] = None) -> List[Dict]:
    """Performs a Google Custom Search with advanced options."""
    if not GOOGLE_SEARCH_KEY or not GOOGLE_SEARCH_ID:
        raise click.ClickException(
            "GOOGLE_SEARCH_KEY and GOOGLE_SEARCH_ID must be set."
        )

    parsed_query = parse_advanced_operators(query)
    query = parsed_query['query']
    operators = parsed_query['operators']

    results = []
    start = 1
    while len(results) < num_results:
        batch_size = min(10, num_results - len(results))
        url = (
            f"https://www.googleapis.com/customsearch/v1?key={GOOGLE_SEARCH_KEY}&cx={GOOGLE_SEARCH_ID}"
            f"&q={requests.utils.quote(query)}&num={batch_size}&start={start}"
        )

        # Add advanced operators
        if operators['site']:
            url += f"&siteSearch={operators['site']}"
        if operators['filetype']:
            url += f"&fileType={operators['filetype']}"
        if operators['inurl']:
            query += f" inurl:{operators['inurl']}"
        if operators['intitle']:
            query += f" intitle:{operators['intitle']}"

        # Add new parameters
        if date_restrict:
            url += f"&dateRestrict={date_restrict}"
        if language:
            url += f"&lr=lang_{language}"
        if country:
            url += f"&cr=country{country}"
        if safe_search:
            url += f"&safe={safe_search}"
        if file_type:
            url += f"&fileType={file_type}"

        try:
            response = requests.get(url, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            search_data = response.json()

            if "items" in search_data:
                results.extend(search_data["items"])
                start += 10
            else:
                logger.warning(f"No results found for query: {query}")
                break

            if len(results) >= num_results:
                break

        except requests.exceptions.RequestException as e:
            raise click.ClickException(f"Google Search API error: {e}")
    return results[:num_results]

def bing_search(query: str, num_results: int, freshness: Optional[str] = None, 
                market: Optional[str] = None, safe_search: Optional[str] = None) -> List[Dict]:
    """Performs a Bing Custom Search with advanced options."""
    if not BING_CUSTOM_SEARCH_KEY or not BING_CUSTOM_CONFIG_ID:
        raise click.ClickException(
            "BING_CUSTOM_SEARCH_KEY and BING_CUSTOM_CONFIG_ID must be set."
        )

    parsed_query = parse_advanced_operators(query)
    query = parsed_query['query']
    operators = parsed_query['operators']

    url = "https://api.bing.microsoft.com/v7.0/custom/search"
    headers = {"Ocp-Apim-Subscription-Key": BING_CUSTOM_SEARCH_KEY}
    if AZURE_REGION:
        headers["Ocp-Apim-Subscription-Region"] = AZURE_REGION
    params = {
        "q": query,
        "customconfig": BING_CUSTOM_CONFIG_ID,
        "count": min(50, num_results),
        "offset": 0,
    }

    # Add advanced operators
    if operators['site']:
        params['q'] += f" site:{operators['site']}"
    if operators['filetype']:
        params['q'] += f" filetype:{operators['filetype']}"
    if operators['inurl']:
        params['q'] += f" inurl:{operators['inurl']}"
    if operators['intitle']:
        params['q'] += f" intitle:{operators['intitle']}"

    # Add new parameters
    if freshness:
        params['freshness'] = freshness
    if market:
        params['mkt'] = market
    if safe_search:
        params['safeSearch'] = safe_search

    results = []
    while len(results) < num_results:
        try:
            response = requests.get(url, headers=headers, params=params, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            search_data = response.json()

            if "webPages" in search_data and "value" in search_data["webPages"]:
                results.extend(search_data["webPages"]["value"])
                if len(search_data["webPages"]["value"]) < params["count"]:
                    break  # No more pages
                params["offset"] += params["count"]  # Increment offset
            else:
                logger.warning(f"No results found for query: {query}")
                break

        except requests.exceptions.RequestException as e:
            raise click.ClickException(f"Bing Search API error: {e}")
    return results[:num_results]


def fallback_search(query: str, num_results: int = 5) -> bool:
    """Execute a web search using Python requests."""
    try:
    # First try DuckDuckGo
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
        }
        
        response = requests.get(
            f'https://html.duckduckgo.com/html/',
            params={'q': query},
            headers=headers,
            timeout=REQUEST_TIMEOUT
        )
        
        if response.ok:
            soup = BeautifulSoup(response.text, 'html.parser')
            results = soup.find_all('div', {'class': 'result'}, limit=num_results)
            
        if results:
            for result in results:
                title = result.find('a', {'class': 'result__a'})
                if title:
                    click.echo(title.text.strip())
            return True
            
        # Fall back to Google
        response = requests.get(
            'https://www.google.com/search',
            params={'q': query, 'num': num_results},
            headers=headers,
            timeout=REQUEST_TIMEOUT
        )
        
        if response.ok:
            soup = BeautifulSoup(response.text, 'html.parser')
            results = soup.find_all('div', {'class': 'g'}, limit=num_results)
            
        if results:
            for result in results:
                title = result.find('h3')
                if title:
                    click.echo(title.text.strip())
            return True
            
        click.echo("No results found")
        return False
        
    except Exception as e:
        click.echo(f"Search error: {str(e)}", err=True)
        return False

# --- LLM Summarization ---

def generate_summary(processed_results: List[Dict[str, str]], search_query: str) -> str:
    """Generates a summary of the search results using an LLM."""
    # Use json.dumps to properly escape the relevant quotes
    combined_results = "".join(
        [json.dumps(result["relevant_quotes"]) for result in processed_results]
    )
    if not combined_results:
        return "No relevant content found to summarize."

    token_count = estimate_token_count(combined_results)
    summary_prompt = f"""Summarize the key points from the search results related to '{search_query}'. Focus on the most relevant information. Provide a concise overview, including specific details and techniques where available.  Output ONLY the summary text, with no preamble or JSON formatting."""

    summary = call_llm(combined_results, summary_prompt)
    return summary

# --- Click CLI ---

@click.command()
@click.option("-q", "--query", required=True, help="Search query.")
@click.option(
    "-n",
    "--num-results",
    default=DEFAULT_NUM_RESULTS,
    help=f"Number of results to fetch (default: {DEFAULT_NUM_RESULTS}, max: {MAX_RESULTS}).",
)
@click.option(
    "-e",
    "--search-engine",
    default="google",
    type=click.Choice(["google", "bing"]),
    help="Search engine to use (default: google).",
)
@click.option("-o", "--output", help="Output file for results (default: stdout).")
@click.option("--date-restrict", help="Restrict results to a specific date range (Google only).")
@click.option("--language", help="Restrict search to documents in a specific language.")
@click.option("--country", help="Restrict search results to documents from a specific country (Google only).")
@click.option("--safe-search", type=click.Choice(["off", "medium", "high"]), help="SafeSearch filtering.")
@click.option("--file-type", help="Restrict results to a specific file type (Google only).")
@click.option("--freshness", type=click.Choice(["Day", "Week", "Month"]), help="Restrict results to a specific time frame (Bing only).")
@click.option("--market", help="Specifies the market/language for results (Bing only).")
@click.option("--models", help="Comma-separated list of LLM models to use.")
def search(query: str, num_results: int, search_engine: str, output: Optional[str],
           date_restrict: Optional[str], language: Optional[str], country: Optional[str],
           safe_search: Optional[str], file_type: Optional[str], freshness: Optional[str],
           market: Optional[str], models: Optional[str]):
    """Performs a search, scrapes results, extracts relevant information, and summarizes."""

    if num_results > MAX_RESULTS:
        logger.warning(f"Number of results capped at {MAX_RESULTS}")
        num_results = MAX_RESULTS

    if models:
        global LLM_MODELS
        LLM_MODELS = models.split(",")

    try:
        if search_engine == "google":
            search_results = google_search(query, num_results, date_restrict, language, country, safe_search, file_type)
        else:  # bing
            search_results = bing_search(query, num_results, freshness, market, safe_search)

        if not search_results:
            click.echo("No search results found.")
            return

        # Use "link" for Google and "url" for Bing
        if search_engine == "google":
            urls = [result["link"] for result in search_results]
        else:
            urls = [result["url"] for result in search_results]

        with concurrent.futures.ThreadPoolExecutor() as executor:
            processed_results = list(executor.map(process_single_url, urls, [query] * len(urls)))

        summary = generate_summary(processed_results, query)

        if output:
            with open(output, "w", encoding="utf-8") as f:
                f.write(f"Search Results for: {query}\n")
                f.write("==========================\n")
                for result in processed_results:
                    f.write(f"URL: {result['url']}\n")
                    f.write(f"Relevant Quotes:\n{result['relevant_quotes']}\n")
                f.write("\nSummary:\n")
                f.write("========\n")
                f.write(summary)
        else:
            click.echo(f"Search Results for: {query}")
            click.echo("==========================")
            for result in processed_results:
                click.echo(f"URL: {result['url']}")
                click.echo(f"Relevant Quotes:\n{result['relevant_quotes']}")
            click.echo("\nSummary:")
            click.echo("========")
            click.echo(summary)

    except click.ClickException as e:
        click.echo(str(e))
    except Exception as e:
        logger.exception("An unexpected error occurred:")
        click.echo(f"An unexpected error occurred: {e}")

@llm.hookimpl
def register_commands(cli):
    cli.add_command(search)

