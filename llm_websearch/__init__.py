"""LLM Websearch Plugin Package.

Provides commands for standard and deep web searches integrated with LLMs.
"""

__version__ = "0.1a0"

import llm
import logging

# Configure logging for the package
logger = logging.getLogger(__name__)

# Attempt to import core components directly. If these fail,
# registration below will likely fail and the plugin won't load.
from .core import search, deep_search
from .models import SearchResult, WebSearchError, SearchEngineError, LLMError

# LLM Plugin Registration Hook
@llm.hookimpl
def register_commands(cli):
    """Register CLI commands with the LLM tool."""
    try:
        # Attempt to import core components needed for registration
        from .cli import get_websearch_commands
        # Optionally, add a direct check for a core function if needed
        # from .core import search # Already imported above, but demonstrates the idea

        # If imports above failed, this point won't be reached.
        # If get_websearch_commands itself relies on failed imports in cli.py,
        # it might raise an error here too.
        websearch_group = get_websearch_commands()
        cli.add_command(websearch_group)
        logger.info("'websearch' command group registered.")

    except ImportError as e:
        logger.error(f"Plugin 'llm-websearch' NOT REGISTERED due to core module import failure: {e}", exc_info=True)
        return # Prevent registration if essential imports fail

    except Exception as e: # Catch other potential errors during registration itself
        logger.error(f"Unexpected error during CLI registration for 'llm-websearch': {e}", exc_info=True)

logger.debug(f"llm_websearch package (version {__version__}) loaded - registration attempted.")
