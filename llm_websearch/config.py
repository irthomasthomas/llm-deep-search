"""Configuration management for llm_websearch using Pydantic BaseSettings."""

import os
import logging
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, DirectoryPath, PositiveInt, PositiveFloat, NonNegativeFloat
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

# --- Determine Project Root ---
PROJECT_ROOT = Path(__file__).parent.parent
DEFAULT_CONFIG_FILE = PROJECT_ROOT / "llm_websearch_config.yaml"

class Settings(BaseSettings):
    """Loads config from environment variables, .env file, and a YAML config file.

    Priority order (highest first):
    1. Environment variables (using specified aliases)
    2. .env file (using specified aliases)
    3. llm_websearch_config.yaml file (using field names)

    See pydantic-settings documentation: https://docs.pydantic.dev/latest/concepts/pydantic_settings/
    """
    # --- API Keys ---
    # Loaded from YAML/ENV/.env
    # --- Start Change: Update validation_alias to match shell script env vars ---
    google_api_key: Optional[str] = Field(None, validation_alias='GOOGLE_SEARCH_KEY')
    google_cse_id: Optional[str] = Field(None, validation_alias='GOOGLE_SEARCH_ID')
    bing_api_key: Optional[str] = Field(None, validation_alias='BING_CUSTOM_SEARCH_KEY')
    bing_custom_config_id: Optional[str] = Field(None, validation_alias='BING_CUSTOM_CODE_SEARCH_CONF')
    # --- End Change ---
    # Allow generic LLM_API_KEY or fallback to GOOGLE_SEARCH_KEY for convenience
    llm_api_key: Optional[str] = Field(None, validation_alias='LLM_API_KEY')

    # --- LLM Config ---
    llm_model_default: str = Field("gemini-2.0-flash-exp", validation_alias='LLM_MODEL_DEFAULT')
    llm_temperature: NonNegativeFloat = Field(0.7, validation_alias='LLM_TEMPERATURE')
    llm_max_tokens: PositiveInt = Field(2048, validation_alias='LLM_MAX_TOKENS')
    llm_primary_models: List[str] = Field(default_factory=lambda: ["gemini-2.0-flash-exp", "gemini-2"])
    llm_fallback_models: List[str] = Field(default_factory=lambda: ["gemini-2.0-flash"])
    llm_api_rate: PositiveFloat = Field(5.0, validation_alias='LLM_API_RATE')
    llm_prompt_content_limit: PositiveInt = Field(4000) # Default limit for content in prompts

    # --- Search Config ---
    max_results_per_engine: PositiveInt = Field(10, validation_alias='MAX_RESULTS_PER_ENGINE')
    search_request_timeout: PositiveFloat = Field(10.0, validation_alias='SEARCH_REQUEST_TIMEOUT')
    google_search_rate: PositiveFloat = Field(8.0, validation_alias='GOOGLE_SEARCH_RATE')
    bing_search_rate: PositiveFloat = Field(2.0, validation_alias='BING_SEARCH_RATE')

    # --- Deep Research Config ---
    deep_search_max_iterations: PositiveInt = Field(3, validation_alias='DEEP_SEARCH_MAX_ITERATIONS')
    deep_search_max_branching: PositiveInt = Field(3, validation_alias='DEEP_SEARCH_MAX_BRANCHING')
    deep_search_relevance_threshold: NonNegativeFloat = Field(0.6, validation_alias='DEEP_SEARCH_RELEVANCE_THRESHOLD')
    deep_search_diminishing_returns: NonNegativeFloat = Field(0.1, validation_alias='DEEP_SEARCH_DIMINISHING_RETURNS')

    # --- Components ---
    fast_filter_enabled: bool = Field(True, validation_alias='FAST_FILTER_ENABLED')
    fast_filter_threshold: NonNegativeFloat = Field(0.6, validation_alias='FAST_FILTER_THRESHOLD')
    fast_filter_model: Optional[str] = Field(None, validation_alias='FAST_FILTER_MODEL') # Uses default LLM if None
    fast_filter_max_chars: PositiveInt = Field(500, validation_alias='FAST_FILTER_MAX_CHARS')

    detailed_analysis_relevance_threshold: NonNegativeFloat = Field(0.6, validation_alias='DETAILED_ANALYSIS_RELEVANCE_THRESHOLD')
    detailed_analysis_model: Optional[str] = Field(None, validation_alias='DETAILED_ANALYSIS_MODEL') # Uses default LLM if None
    detailed_analysis_max_chars_keypoints: PositiveInt = Field(3000)
    detailed_analysis_max_chars_relevance: PositiveInt = Field(2000)

    summarizer_short_length: PositiveInt = Field(75)
    summarizer_medium_length: PositiveInt = Field(200)
    summarizer_long_length: PositiveInt = Field(500)
    summarizer_min_confidence: NonNegativeFloat = Field(0.6)
    summarizer_model: Optional[str] = Field(None) # Uses default LLM if None
    summarizer_insight_model: Optional[str] = Field(None) # Uses default LLM if None
    summarizer_insight_max_chars: PositiveInt = Field(8000)
    summarizer_max_insights: PositiveInt = Field(7)
    summarizer_combine_max_chars_l1: PositiveInt = Field(4000)
    summarizer_combine_max_chars_l2: PositiveInt = Field(6000)
    summarizer_combine_max_chars_l3: PositiveInt = Field(8000)
    summarizer_fallback_max_len_multiplier: PositiveFloat = Field(4.0) # Multiplier for target_length in combined summary fallback

    # --- Cache ---
    cache_enabled: bool = Field(True, validation_alias='CACHE_ENABLED')
    cache_dir: DirectoryPath = Field(os.path.join(os.path.expanduser("~"), ".cache", "llm_websearch"), validation_alias='CACHE_DIR')
    cache_ttl_seconds: PositiveInt = Field(3600 * 24, validation_alias='CACHE_TTL_SECONDS') # 1 day

    # --- Concurrency ---
    max_concurrent_requests: PositiveInt = Field(5, validation_alias='MAX_CONCURRENT_REQUESTS')
    request_timeout_general: PositiveFloat = Field(30.0, validation_alias='REQUEST_TIMEOUT_GENERAL')

    # --- Logging ---
    log_level: str = Field("INFO", validation_alias='LOG_LEVEL')

    # --- Pydantic Settings Config ---
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        yaml_file=DEFAULT_CONFIG_FILE,
        yaml_file_encoding='utf-8',
        env_nested_delimiter='__',
        case_sensitive=False, # Important for environment variables
        extra='ignore'
    )

# Global settings instance
try:
    settings = Settings()
    log_level_name = settings.log_level.upper()
    # Ensure basicConfig is called only once, or use force=True if needed repeatedly
    logging.basicConfig(level=getattr(logging, log_level_name, logging.INFO), force=True) # Use force=True to allow reconfiguration
    logger.info(f"Settings loaded successfully. Log Level: {log_level_name}")
    logger.info(f"LLM Default: {settings.llm_model_default}, Cache: {settings.cache_enabled}")
    if settings.cache_enabled and settings.cache_dir:
        cache_dir_path = Path(settings.cache_dir)
        cache_dir_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Cache directory ensured: {cache_dir_path}")

    # Log status of required API keys after loading
    if not settings.google_api_key or not settings.google_cse_id:
        logger.warning("Google Search API keys/ID not fully configured (checked GOOGLE_SEARCH_KEY/ID).")
    if not settings.bing_api_key or not settings.bing_custom_config_id:
        logger.warning("Bing Search API keys/ID not fully configured (checked BING_CUSTOM_SEARCH_KEY/CODE_SEARCH_CONF).")
    # Use google_api_key as the primary key for Gemini if llm_api_key is not set
    llm_key_to_check = settings.llm_api_key or settings.google_api_key
    if not llm_key_to_check:
         logger.warning("LLM API key (LLM_API_KEY or GOOGLE_SEARCH_KEY) not configured.")

except Exception as e:
    logger.error(f"CRITICAL: Failed to load settings: {e}", exc_info=True)
    # Fallback: Create a default object without file loading
    settings_dict = {f.name: f.default for f in Settings.model_fields.values() if f.default is not None}
    # Manually set alias values if needed for default fallback? Or rely on defaults only?
    # Relying on class defaults for simplicity on error.
    settings = Settings(**settings_dict)
    logging.basicConfig(level=logging.INFO, force=True)
    logger.warning("Using default settings due to loading error.")

class ConfigError(Exception):
    """Custom exception for configuration errors."""
    pass
