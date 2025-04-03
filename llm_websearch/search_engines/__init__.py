"""Search Engines sub-package for llm_websearch.

Contains modules for interacting with different search engine APIs (Google, Bing, etc.).
"""

# Expose the primary search functions for easier import in core.py
from .google import google_search
from .bing import bing_search

# Potentially add other search engines here
# from .duckduckgo import duckduckgo_search

__all__ = [
    "google_search",
    "bing_search",
    # "duckduckgo_search",
]
