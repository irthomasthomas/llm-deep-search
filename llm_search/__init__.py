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
from typing import List, Dict, Optional

# Load environment variables
load_dotenv()
class SearchResult:
    def __init__(self, url: str, title: str, snippet: str, rank: int, source: str):
        self.url = url
        self.title = title
        self.snippet = snippet
        self.rank = rank
        self.source = source  # "google", "bing", "duckduckgo", "fallback_google"

class ProcessedResult:
    def __init__(self, url: str, raw_content: Optional[bytes] = None,
                    clean_text: str = "", relevant_quotes: str = "",
                    relevance_score: float = 0.0, summary: str = "",
                    entities: List[str] = [], llm_used: str = ""):
        self.url = url
        self.raw_content = raw_content  # Cache the raw content separately
        self.clean_text = clean_text
        self.relevant_quotes = relevant_quotes
        self.relevance_score = relevance_score
        self.summary = summary
        self.entities = entities
        self.llm_used = llm_used

class ResearchState:
    def __init__(self, original_query: str, refined_queries: List[str] = [],
                    search_results: List[SearchResult] = [],
                    processed_results: List[ProcessedResult] = [],
                    current_iteration: int = 0, summary: str = "",
                    information_gaps: List[str] = [], stop_reason: str = "",
                    user_feedback: str = ""):
        self.original_query = original_query
        self.refined_queries = refined_queries
        self.search_results = search_results
        self.processed_results = processed_results
        self.current_iteration = current_iteration
        self.summary = summary
        self.information_gaps = information_gaps
        self.stop_reason = stop_reason
        self.user_feedback = user_feedback
        

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
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", 10))

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
LLM_TIERS = {
    "fast": {
        "models": ["gemini-2.0-flash"],  # Example: Fast, smaller context
        "max_tokens": 1000000,
    },
    "medium": {
        "models": ["cerebras-llama3.3-70b"],  # Example: Medium speed, larger context
        "max_tokens": 100000,
    },
    "powerful": {
        "models": ["llama-3.3-70b-versatile"],  # Example: Slower, largest context
        "max_tokens": 100000,
    },
}

def get_llm_for_tier(tier: str):
    """Selects an LLM from the specified tier."""
    if tier not in LLM_TIERS:
        raise ValueError(f"Invalid LLM tier: {tier}")
    return LLM_TIERS[tier]["models"][0]

def estimate_token_count(text: str) -> int:
    """Estimates the number of tokens in the given text."""
    word_count = len(text.split())
    estimated_tokens = word_count * 4 // 3
    return estimated_tokens


def fetch_content(url: str, retries: int = MAX_RETRIES) -> Optional[bytes]:
    """Fetches content from a URL with retries and web archive fallback, caching raw content."""
    logger.info(f"Fetching content from: {url}")
    cache_key_raw = hashlib.md5(f"{url}:raw".encode()).hexdigest()

    if cache_key_raw in cache:
        logger.info(f"Using cached raw content for {url}")
        return cache[cache_key_raw]

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
                content = response.html.raw_html.encode()
                cache[cache_key_raw] = content #Cache raw content
                return content
            except Exception as e:
                logger.warning(f"Failed to render JavaScript for {url}: {e}")
        content = response.content
        cache[cache_key_raw] = content #Cache raw content
        return content
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
                content = archived_response.content
                cache[cache_key_raw] = content #Cache raw content
                return content
            except requests.exceptions.RequestException as archive_e:
                logger.error(f"Failed to fetch from web archive for {url}: {archive_e}")
                return None


def analyze_content(url: str, page_text: str, search_query: str, tier: str) -> ProcessedResult:
    """Analyzes the content of a page using an LLM."""
    model_name = get_llm_for_tier(tier)
    llm_client = llm.get_model(model_name)
    max_tokens = LLM_TIERS[tier]["max_tokens"]

    # --- 1. Quote Extraction ---
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
{page_text[:max_tokens]}
</page_text>""",
        extract_prompt,
        models=[model_name]
    )

    # --- 2. Relevance Scoring (Simplified - could be enhanced) ---
    # This is a placeholder.  A real implementation would combine LLM judgment,
    # keyword density, and entity matching.

    relevance_score = 0.5 #Default
    if "HIGH" in relevant_quotes:
        relevance_score = 0.9
    if "MEDIUM" in relevant_quotes:
        relevance_score = 0.7
    # --- 3. Summarization (for later use in overall synthesis) ---

    if tier != "fast":
        summary_prompt = f"""Summarize the key points from the following text that are relevant to the query '{search_query}'. Focus on the most relevant information. Be concise, and output ONLY the summary text:
{page_text[:max_tokens]}"""
        summary = llm_client.prompt(summary_prompt).text()
    else:
        summary = ""

    # --- 4. Entity Extraction (Placeholder - could use a dedicated NER model) ---
    entities = []  #  Example:  Could use spaCy or other NER tools

    return ProcessedResult(
        url=url,
        clean_text=page_text,
        relevant_quotes=relevant_quotes,
        relevance_score=relevance_score,
        summary=summary,
        entities=entities,
        llm_used=model_name,
    )

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


def process_single_url(url: str, search_query: str, tier: str = "fast") -> ProcessedResult:
    """Processes a single URL, fetching and analyzing content."""
    logger.info(f"Processing URL: {url} with tier {tier}")
    cache_key_processed = hashlib.md5(f"{url}:{search_query}:{tier}".encode()).hexdigest()

    if cache_key_processed in cache:
        logger.info(f"Using cached processed result for {url} (tier: {tier})")
        return cache[cache_key_processed]

    content = fetch_content(url)
    if content is None:
        return ProcessedResult(url, relevant_quotes="Failed to fetch content.")

    page_text = extract_text(content, url)
    if not page_text:
        return ProcessedResult(url, relevant_quotes="Failed to extract text.")

    processed_result = analyze_content(url, page_text, search_query, tier)
    processed_result.raw_content = content #Store raw content
    cache[cache_key_processed] = processed_result
    return processed_result

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
                    safe_search: Optional[str] = None, file_type: Optional[str] = None) -> List[SearchResult]:
    """Performs a Google Custom Search, returning SearchResult objects."""
    if not GOOGLE_SEARCH_KEY or not GOOGLE_SEARCH_ID:
        raise click.ClickException("GOOGLE_SEARCH_KEY and GOOGLE_SEARCH_ID must be set.")

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

        if operators['site']:
            url += f"&siteSearch={operators['site']}"
        if operators['filetype']:
            url += f"&fileType={operators['filetype']}"
        if operators['inurl']:
            query += f" inurl:{operators['inurl']}"
        if operators['intitle']:
            query += f" intitle:{operators['intitle']}"

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
                for item in search_data["items"]:
                    results.append(SearchResult(
                        url=item["link"],
                        title=item["title"],
                        snippet=item["snippet"],
                        rank=start,  #  Use the start value as a proxy for rank
                        source="google"
                    ))
                    start += 1
            else:
                logger.warning(f"No results found for query: {query}")
                break
            if len(results) >= num_results:
                break

        except requests.exceptions.RequestException as e:
            raise click.ClickException(f"Google Search API error: {e}")

    return results[:num_results]


def bing_search(query: str, num_results: int, freshness: Optional[str] = None,
                market: Optional[str] = None, safe_search: Optional[str] = None) -> List[SearchResult]:
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

    if operators['site']:
        params['q'] += f" site:{operators['site']}"
    if operators['filetype']:
        params['q'] += f" filetype:{operators['filetype']}"
    if operators['inurl']:
        params['q'] += f" inurl:{operators['inurl']}"
    if operators['intitle']:
        params['q'] += f" intitle:{operators['intitle']}"

    if freshness:
        params['freshness'] = freshness
    if market:
        params['mkt'] = market
    if safe_search:
        params['safeSearch'] = safe_search

    results = []
    rank = 0
    while len(results) < num_results:
        try:
            response = requests.get(url, headers=headers, params=params, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            search_data = response.json()

            if "webPages" in search_data and "value" in search_data["webPages"]:
                for item in search_data["webPages"]["value"]:
                    results.append(SearchResult(
                        url=item["url"],
                        title=item["name"],
                        snippet=item["snippet"],
                        rank=rank,
                        source="bing"
                    ))
                    rank+=1
                if len(search_data["webPages"]["value"]) < params["count"]:
                    break
                params["offset"] += params["count"]
            else:
                logger.warning(f"No results found for query: {query}")
                break

        except requests.exceptions.RequestException as e:
            raise click.ClickException(f"Bing Search API error: {e}")
    return results[:num_results]

def fallback_search(query: str, num_results: int = 5) -> List[SearchResult]:
    """Execute a web search using Python requests."""
    results = []
    rank = 0
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
            ddg_results = soup.find_all('div', {'class': 'result'}, limit=num_results)

        if ddg_results:
            for result in ddg_results:
                title_tag = result.find('a', {'class': 'result__a'})
                if title_tag:
                    title = title_tag.text.strip()
                    url = title_tag['href']
                    snippet_tag = result.find('a', {'class': 'result__snippet'})
                    snippet = snippet_tag.text.strip() if snippet_tag else ""

                    results.append(SearchResult(
                        url=url,
                        title=title,
                        snippet=snippet,
                        rank=rank,
                        source="duckduckgo"
                    ))
                    rank+=1
        if len(results) >= num_results:
            return results

        response = requests.get(
            'https://www.google.com/search',
            params={'q': query, 'num': num_results},
            headers=headers,
            timeout=REQUEST_TIMEOUT
        )

        if response.ok:
            soup = BeautifulSoup(response.text, 'html.parser')
            google_results = soup.find_all('div', {'class': 'g'}, limit=num_results)

        if google_results:
            for result in google_results:
                title_tag = result.find('h3')
                if title_tag:
                    title = title_tag.text.strip()
                    link_tag = result.find('a')
                    url = link_tag['href'] if link_tag else ""

                    snippet_tag = result.find('div', {'class': 'IsZvec'})  #This may change
                    snippet = snippet_tag.text.strip() if snippet_tag else ""

                    results.append(SearchResult(
                        url=url,
                        title=title,
                        snippet=snippet,
                        rank=rank,
                        source="fallback_google"  # Differentiate from API Google
                    ))
                    rank+=1
        return results

    except Exception as e:
        click.echo(f"Search error: {str(e)}", err=True)
        return []

# --- LLM Summarization ---


def generate_summary(research_state: ResearchState) -> str:
    """Generates a summary of the search results using an LLM, taking into account processed results."""
    combined_summaries = ""
    for result in research_state.processed_results:
        if result.summary:
            combined_summaries += f"Source: {result.url}\nSummary: {result.summary}\n\n"

    if not combined_summaries:
        return "No relevant content found to summarize."

    model_name = get_llm_for_tier("powerful")
    summary_prompt = f"""Synthesize the following summaries into a concise overview that addresses the original query: '{research_state.original_query}'.
Focus on the most relevant information, resolving any contradictions.
Include specific details and techniques where available. Output ONLY the summary text.

Summaries:
{combined_summaries}"""

    summary = call_llm(summary_prompt, "", models=[model_name])
    return summary


def refine_queries(research_state: ResearchState) -> List[str]:
    """Generates refined search queries based on information gaps and the current summary."""
    model_name = get_llm_for_tier("medium")  # Use a medium-tier LLM
    prompt = f"""Based on the original query '{research_state.original_query}', the current summary '{research_state.summary}', and identified information gaps:

{research_state.information_gaps}

Generate a JSON list of refined search queries that will help fill these gaps. The queries should be diverse and specific.

Output ONLY a valid JSON array of strings, e.g., ["query 1", "query 2", "query 3"]
"""
    response_text = call_llm(prompt, system_prompt="", models=[model_name])

    try:
        refined_queries = json.loads(response_text)
        if not isinstance(refined_queries, list):
            logger.error(f"refine_queries did not return a list: {response_text}")
            return []
        return refined_queries
    except json.JSONDecodeError:
        logger.error(f"Failed to parse refine_queries response as JSON: {response_text}")
        return []

def identify_information_gaps(research_state: ResearchState) -> List[str]:
    """Identifies information gaps using an LLM."""
    model_name = get_llm_for_tier("medium")
    prompt = f"""Based on the original query '{research_state.original_query}' and the current summary:

{research_state.summary}

Identify key information gaps that need to be filled to comprehensively address the query. Output the gaps as a JSON list of concise statements or questions.

Output ONLY a valid JSON array of strings, e.g., ["gap 1", "gap 2", "gap 3"].
"""
    response_text = call_llm(prompt, system_prompt="", models=[model_name])
    try:
        gaps = json.loads(response_text)
        if not isinstance(gaps, list):
            logger.error(f"Information gaps did not return a list: {response_text}")
            return []
        return gaps
    except json.JSONDecodeError:
        logger.error(f"Failed to parse gaps response as JSON: {response_text}")
        return []
    
def calculate_relevance(search_result: SearchResult, processed_result: ProcessedResult) -> float:
    """Combines search rank and LLM-assigned relevance."""
    search_rank_score = 1.0 / (search_result.rank + 1)  # Higher rank = better
    llm_score = processed_result.relevance_score

    combined_score = 0.6 * search_rank_score + 0.4 * llm_score
    return combined_score
    
import concurrent.futures
import multiprocessing

def deep_research(query: str, num_results: int = 10, max_iterations: int = 3):
    """Performs deep research using iterative search and LLM analysis."""

    research_state = ResearchState(original_query=query)
    research_state.refined_queries.append(query)  # Start with the original query

    for iteration in range(max_iterations):
        research_state.current_iteration = iteration
        logger.info(f"Starting iteration {iteration + 1}")

        all_search_results = []

        with concurrent.futures.ProcessPoolExecutor() as executor:
            future_to_query = {}
            for refined_query in research_state.refined_queries:
                future = executor.submit(google_search, refined_query, num_results)
                future_to_query[future] = refined_query
                future = executor.submit(bing_search, refined_query, num_results)
                future_to_query[future] = refined_query

            for future in concurrent.futures.as_completed(future_to_query):
                query_used = future_to_query[future]
                try:
                    results = future.result()
                    all_search_results.extend(results)
                except Exception as e:
                    logger.error(f"Search for query '{query_used}' failed: {e}")

        if not all_search_results:
            with concurrent.futures.ProcessPoolExecutor() as executor:
                future_to_query = {}
                for refined_query in research_state.refined_queries:
                    future = executor.submit(fallback_search, refined_query, num_results)
                    future_to_query[future] = refined_query
                for future in concurrent.futures.as_completed(future_to_query):
                    query_used = future_to_query[future]
                    try:
                        results = future.result()
                        all_search_results.extend(results)
                    except Exception as e:
                        logger.error(f"Fallback search for '{query_used}' failed: {e}")

        research_state.search_results = all_search_results
        if not research_state.search_results:
            logger.warning("No search results found in any search engine.")
            research_state.stop_reason = "No results found"
            break

        with concurrent.futures.ProcessPoolExecutor() as executor:
            future_to_url = {}
            for result in research_state.search_results:
                future = executor.submit(process_single_url, result.url, query, "fast")
                future_to_url[future] = result.url

            processed_results_temp = []
            for future in concurrent.futures.as_completed(future_to_url):
                url_processed = future_to_url[future]
                try:
                    processed_result = future.result()
                    search_result = next((r for r in research_state.search_results if r.url == processed_result.url), None)
                    if search_result:
                        processed_result.relevance_score = calculate_relevance(search_result, processed_result)
                    processed_results_temp.append(processed_result)

                except Exception as e:
                    logger.error(f"Processing URL '{url_processed}' failed: {e}")
            research_state.processed_results = processed_results_temp
            research_state.processed_results.sort(key=lambda x: x.relevance_score, reverse=True)
        research_state.summary = generate_summary(research_state)

        research_state.information_gaps = identify_information_gaps(research_state)
        if not research_state.information_gaps:
                research_state.stop_reason = "Information saturation"
                break

        research_state.refined_queries = refine_queries(research_state)
        if not research_state.refined_queries:
            research_state.stop_reason = "Query refinement failed"
            break

        logger.info(f"Iteration {iteration + 1} complete.")
        logger.info(f"Current Summary: {research_state.summary}")
        logger.info(f"Information Gaps: {research_state.information_gaps}")

    logger.info(f"Deep research complete. Stop reason: {research_state.stop_reason}")
    return research_state 
    
# --- Click CLI ---

@click.command()
@click.option("-q", "--query", required=True, help="Search query.")
@click.option("-n", "--num-results", default=DEFAULT_NUM_RESULTS, help="Number of results per search.")
@click.option("-i", "--max-iterations", default=3, help="Maximum number of iterations.")
def deepsearch(query: str, num_results: int, max_iterations: int):
    """Performs a deep research using iterative search and LLM analysis."""
    research_state = deep_research(query, num_results, max_iterations)
    click.echo(research_state.summary)

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
    cli.add_command(deepsearch)