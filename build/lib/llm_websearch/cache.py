"""
Cache module for the LLM WebSearch plugin.

This module provides a simple file-based caching system to store and retrieve
search results, reducing the number of API calls and improving performance.
"""

import os
import json
import time
from typing import Dict, Any, Optional

CACHE_DIR = os.path.join(os.path.expanduser("~"), ".cache", "llm_websearch")
CACHE_EXPIRATION = 3600  # 1 hour in seconds

def _ensure_cache_dir():
    """Ensure the cache directory exists."""
    os.makedirs(CACHE_DIR, exist_ok=True)

def _cache_key(query: str, source: str) -> str:
    """Generate a cache key based on the query and source."""
    return f"{query}_{source}".replace(" ", "_").lower()

def get_cached_results(query: str, source: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve cached results for a given query and source.

    Args:
        query (str): The search query.
        source (str): The search source (e.g., 'google', 'bing').

    Returns:
        Optional[Dict[str, Any]]: Cached results if found and not expired, None otherwise.
    """
    _ensure_cache_dir()
    cache_file = os.path.join(CACHE_DIR, f"{_cache_key(query, source)}.json")
    
    if os.path.exists(cache_file):
        with open(cache_file, 'r') as f:
            cached_data = json.load(f)
        
        if time.time() - cached_data['timestamp'] < CACHE_EXPIRATION:
            return cached_data['results']
    
    return None

def cache_results(query: str, source: str, results: Dict[str, Any]):
    """
    Cache the results for a given query and source.

    Args:
        query (str): The search query.
        source (str): The search source (e.g., 'google', 'bing').
        results (Dict[str, Any]): The search results to cache.
    """
    _ensure_cache_dir()
    cache_file = os.path.join(CACHE_DIR, f"{_cache_key(query, source)}.json")
    
    cached_data = {
        'timestamp': time.time(),
        'results': results
    }
    
    with open(cache_file, 'w') as f:
        json.dump(cached_data, f)

