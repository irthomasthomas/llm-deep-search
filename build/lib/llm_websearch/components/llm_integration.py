"""LLM integration component using google-generativeai library with rate limiting."""

import time
import json
import logging
import asyncio
import hashlib
# Removed sys and traceback imports
from typing import List, Dict, Optional, Union, Tuple, Any, Type
from enum import Enum
from pydantic import BaseModel, Field # Keep BaseModel for LLMResponse field type hint

# Internal imports
from ..models import LLMResponse, LLMError, ParsingError, validate_llm_json # Keep validate_llm_json for callers
from ..config import settings, ConfigError
from ..utils import cache, get_limiter

# Google Generative AI library
try:
    import google.generativeai as genai
    from google.generativeai.types import GenerationConfig
    # Task 1/Correction: Import from correct location
    from google.api_core.exceptions import ResourceExhausted
    try:
         from google.generativeai.types import HarmCategory, HarmBlockThreshold
         DEFAULT_SAFETY_SETTINGS = {
             HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
             HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
             HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
             HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
         }
    except ImportError:
         # logger is not defined yet here, so cannot log
         DEFAULT_SAFETY_SETTINGS = {}

except ImportError:
    # Removed debug prints and traceback
    genai = None
    GenerationConfig = None
    DEFAULT_SAFETY_SETTINGS = {}
    # Define a dummy ResourceExhausted class for environments where google libraries might not be installed
    class ResourceExhausted(Exception):  # Task 1: Keep dummy class
        """Dummy exception for ResourceExhausted when google libraries are not installed."""
        pass
    # logger is not defined yet here, so cannot log error yet. It will be logged in __init__

logger = logging.getLogger(__name__)

class ModelCapability(Enum):
    """Enum for representing model capabilities."""
    TEXT = "text"; JSON_OUTPUT = "json_output"; REASONING = "reasoning"; CRITICAL_THINKING = "critical_thinking"

class LLMIntegration:
    """Manages interactions with Google Generative AI models."""
    def __init__(self, cache_instance=None):
        """Initialize LLM integration, configure API key."""
        self.cache = cache_instance if cache_instance is not None else cache
        self.api_key_configured = False
        # Check for genai library first
        if not genai:
            logger.error("Google GenAI library (google-generativeai) import failed. LLMIntegration disabled.")
            return
        # Also check for the critical exception class
        if 'ResourceExhausted' not in globals():
             logger.error("Required exception class ResourceExhausted could not be imported (check google-api-core?). LLMIntegration disabled.")
             return

        # --- Task 2: Update API Key Config ---
        api_key = settings.llm_api_key or settings.google_api_key
        key_source = "LLM_API_KEY" if settings.llm_api_key else ("GOOGLE_API_KEY" if settings.google_api_key else "None")

        if not api_key:
            logger.error("LLM API Key (LLM_API_KEY or GOOGLE_API_KEY) not found in settings.")
            return
        try:
            genai.configure(api_key=api_key)
            self.api_key_configured = True
            logger.info(f"Google GenAI client configured successfully using API key from {key_source}.")
        except Exception as e:
            logger.error(f"Failed to configure Google GenAI client using API key from {key_source}: {e}", exc_info=True)
        # --- End Task 2 ---

    # --- Task 3: Implement Model Sequence Generation ---
    def _get_model_sequence(self, requested_model: Optional[str] = None) -> List[str]:
        """
        Generates an ordered, unique list of valid Gemini models to try.
        Order: Requested -> Default -> Primary Fallback -> Secondary Fallback.
        """
        sequence = []
        models_to_consider = [
            requested_model,
            settings.llm_model_default,
            getattr(settings, 'llm_model_primary_fallback', None), # Use getattr for optional settings
            getattr(settings, 'llm_model_secondary_fallback', None)
        ]

        for model_name in models_to_consider:
            if model_name and isinstance(model_name, str) and model_name.startswith('gemini'):
                if model_name not in sequence:
                    sequence.append(model_name)
            elif model_name and model_name == requested_model:
                # Log if the specifically requested model is invalid
                logger.warning(f"Requested model '{model_name}' is invalid or not a Gemini model. Skipping.")

        if not sequence:
             # Fallback if no valid models were found (e.g., settings misconfigured)
             logger.error("No valid Gemini models found in settings or request. Cannot proceed.")
             # Returning an empty list will cause generate_response to fail gracefully later.
             return []

        logger.info(f"Generated model sequence for request: {sequence}")
        return sequence
    # --- End Task 3 ---

    def _create_cache_key(self, model: str, prompt: str, sys_prompt: Optional[str], task: str, fmt: Optional[str]) -> str:
        """Creates deterministic cache key."""
        key_content = f"sys:{sys_prompt}|prompt:{prompt}" if sys_prompt else prompt
        # Include model name in the key for model-specific caching
        key = f"genai:{model}|task:{task}|fmt:{fmt}|{key_content}"
        return hashlib.md5(key.encode('utf-8')).hexdigest()

    async def generate_response(
        self, prompt: str, system_prompt: Optional[str] = None, task_type: str = "general",
        requested_model: Optional[str] = None, response_format: Optional[str] = None,
        max_retries: int = 2, retry_delay_secs: int = 3,
        temperature: Optional[float] = None, max_output_tokens: Optional[int] = None,
        required_capabilities: Optional[List[ModelCapability]] = None
    ) -> LLMResponse:
        """
        Generates response from Google GenAI with caching, retries, rate limiting, and model fallback.
        """
        if not self.api_key_configured or not genai:
            # Check should have happened in init, but double-check
            if not genai: logger.error("Attempted to generate response, but GenAI library is not available.")
            if not self.api_key_configured: logger.error("Attempted to generate response, but API key is not configured.")
            raise LLMError(model="N/A", message="GenAI client not configured or library unavailable.")

        start_time = time.monotonic()
        overall_last_exc = None # Track last exception across all models for final error

        # Task 4: Call _get_model_sequence
        model_sequence = self._get_model_sequence(requested_model)
        if not model_sequence:
            raise LLMError(model="N/A", prompt=prompt, message="No valid Gemini models available to fulfill the request.")

        # Prepare content (prepend system prompt if needed) - do this once
        contents_arg = []
        if system_prompt:
             newline = chr(10)
             # Keep the original prompt separate for the LLMResponse object
             full_prompt_for_api = f"{system_prompt}{newline*2}---{newline*2}User Request:{newline}{prompt}"
             logger.debug("Prepending system prompt to user prompt for API call.")
             contents_arg.append(full_prompt_for_api)
        else:
            contents_arg.append(prompt)

        # Get Limiter - do this once
        limiter = await get_limiter("llm_api", rate=settings.llm_api_rate)

        # Task 4: Implement outer loop
        for current_model_name in model_sequence:
            logger.info(f"Attempting model: '{current_model_name}' for task '{task_type}'")
            model_start_time = time.monotonic()
            current_model_last_exc = None # Track last exception for *this* model's retries

            # Task 4: Move cache check inside loop
            cache_key = None
            if self.cache and settings.cache_enabled:
                cache_key = self._create_cache_key(current_model_name, prompt, system_prompt, task_type, response_format)
                try:
                    cached = await asyncio.to_thread(self.cache.get, cache_key)
                    if cached and isinstance(cached, LLMResponse):
                        cache_hit_time = time.monotonic() - model_start_time
                        logger.info(f"Cache hit for model '{current_model_name}', task='{task_type}' ({cache_hit_time:.2f}s). Key: {cache_key}")
                        return cached
                    else:
                        logger.debug(f"Cache miss for model '{current_model_name}', task='{task_type}'. Key: {cache_key}")
                except Exception as e:
                    logger.warning(f"Cache get failed for model '{current_model_name}': {e}")

            # Task 4: Adjust GenerationConfig setup
            gen_conf_dict = {
                "temperature": temperature if temperature is not None else settings.llm_temperature,
                "max_output_tokens": max_output_tokens if max_output_tokens is not None else settings.llm_max_tokens
            }
            if response_format == "json" and "1.5" in current_model_name:
                 try:
                     if GenerationConfig and hasattr(GenerationConfig(), 'response_mime_type'):
                         gen_conf_dict["response_mime_type"] = "application/json"
                         logger.debug(f"Requesting JSON output from model '{current_model_name}'")
                     else:
                          logger.warning(f"JSON response_mime_type might not be supported by GenerationConfig for model '{current_model_name}'. Attempting anyway.")
                          gen_conf_dict["response_mime_type"] = "application/json"
                 except Exception as e_mime:
                     logger.warning(f"Could not configure JSON output for model '{current_model_name}': {e_mime}.")

            try:
                 generation_config = GenerationConfig(**gen_conf_dict) if GenerationConfig else None
            except TypeError as te:
                 logger.warning(f"Failed to create GenerationConfig for model '{current_model_name}' with {gen_conf_dict}: {te}. Using defaults.")
                 generation_config = None

            # Task 4: Ensure retry logic is inner loop
            for attempt in range(max_retries + 1):
                try:
                    # Task 4: Update logging
                    logger.info(f"Attempt {attempt+1}/{max_retries+1}: Calling model '{current_model_name}' for task '{task_type}'")
                    model = genai.GenerativeModel(current_model_name)

                    async with limiter:
                        api_resp = await model.generate_content_async(
                            contents=contents_arg, # Use potentially modified prompt for API
                            generation_config=generation_config,
                            safety_settings=DEFAULT_SAFETY_SETTINGS
                        )

                    # Process response
                    if not hasattr(api_resp, 'candidates') or not api_resp.candidates:
                        reason = "Unknown"
                        if hasattr(api_resp, 'prompt_feedback') and api_resp.prompt_feedback and hasattr(api_resp.prompt_feedback, 'block_reason') and api_resp.prompt_feedback.block_reason:
                             reason = api_resp.prompt_feedback.block_reason.name
                        raise LLMError(model=current_model_name, prompt=prompt, message=f"Blocked or no candidates returned. Reason: {reason}")

                    candidate = api_resp.candidates[0]
                    finish_reason = candidate.finish_reason.name if hasattr(candidate, 'finish_reason') else "Unknown"
                    raw_text = ""
                    if candidate.content and candidate.content.parts:
                         raw_text = "".join(part.text for part in candidate.content.parts if hasattr(part, 'text'))

                    tokens = getattr(api_resp.usage_metadata, 'total_token_count', None) if hasattr(api_resp, 'usage_metadata') else None

                    if finish_reason not in ["STOP", "MAX_TOKENS"]: logger.warning(f"Model '{current_model_name}' finished with unexpected reason: {finish_reason}")
                    if not raw_text: logger.warning(f"Model '{current_model_name}' returned an empty response text (Finish Reason: {finish_reason}).")

                    # --- Task 7: Update LLMResponse Instantiation ---
                    resp_obj = LLMResponse(
                        raw_text=raw_text,
                        model_name=current_model_name,
                        prompt_used=prompt, # Pass original user prompt
                        system_prompt_used=system_prompt, # Add system prompt used
                        tokens_used=tokens,
                        finish_reason=finish_reason
                    )
                    # --- End Task 7 ---

                    # Task 4: Move cache set inside loop
                    if cache_key and self.cache and settings.cache_enabled:
                        try:
                            await asyncio.to_thread(self.cache.set, cache_key, resp_obj, expire=settings.cache_ttl_seconds)
                            logger.info(f"Cached LLM response for model '{current_model_name}', task '{task_type}'. Key: {cache_key}")
                        except Exception as e:
                            logger.warning(f"Cache set failed for LLM response (model '{current_model_name}'): {e}")

                    proc_time_total = time.monotonic() - start_time
                    proc_time_model = time.monotonic() - model_start_time
                    logger.info(f"Success with model '{current_model_name}' for task '{task_type}' on attempt {attempt+1} ({proc_time_model:.2f}s model / {proc_time_total:.2f}s total). Tokens: {tokens}")
                    # Task 4: Return response on success
                    return resp_obj # Success! Exit the function.

                # --- Task 5: Implement Rate Limit Handling (429) ---
                # Check if ResourceExhausted was successfully imported before trying to catch it
                except ResourceExhausted as e:
                    current_model_last_exc = e # Track error for this model
                    overall_last_exc = e       # Track last overall error
                    logger.warning(f"Rate limit hit for model '{current_model_name}' (Attempt {attempt+1}/{max_retries+1}). Skipping to next model. Error: {e}")
                    break # Exit the inner retry loop for this model immediately
                # --- End Task 5 ---

                # --- Task 6: Adjust General Exception Handling (Confirmed logic is okay) ---
                except Exception as e:
                    # Check if the exception is ResourceExhausted, in case the specific except block failed
                    # This is a safeguard in case the dummy class logic was triggered unexpectedly
                    if type(e).__name__ == 'ResourceExhausted':
                         current_model_last_exc = e
                         overall_last_exc = e
                         logger.warning(f"[Fallback Catch] Rate limit hit for model '{current_model_name}' (Attempt {attempt+1}/{max_retries+1}). Skipping to next model. Error: {e}")
                         break # Exit inner loop

                    current_model_last_exc = e # Track last exception for *this* model's retries
                    overall_last_exc = e # Track last exception across *all* models
                    err_msg = f"LLM API attempt {attempt+1}/{max_retries+1} failed for model '{current_model_name}': {type(e).__name__}: {e}"
                    logger.warning(err_msg)

                    if attempt < max_retries:
                        logger.info(f"Retrying model '{current_model_name}' in {retry_delay_secs}s...")
                        await asyncio.sleep(retry_delay_secs)
                    else:
                        logger.error(f"LLM API call failed after {max_retries+1} attempts for model '{current_model_name}'.")
                        break # Exit inner retry loop for this model, move to next model in outer loop

            # If we finished the inner loop for a model without returning (i.e., all retries failed),
            # log it and continue to the next model in the sequence.
            if current_model_last_exc: # Check if the inner loop failed for *any* reason
                 if not isinstance(current_model_last_exc, ResourceExhausted) and type(current_model_last_exc).__name__ != 'ResourceExhausted':
                     logger.warning(f"Failed to get response from model '{current_model_name}' after all retries. Trying next model.")

        # Task 4 & 6: End outer loop / Final error raise
        final_err_msg = f"LLM call failed for all models in sequence: {model_sequence} after retries."
        logger.error(final_err_msg)
        raise LLMError(
            model=f"Failed models: {model_sequence}", # Report all attempted models
            prompt=prompt,
            message=final_err_msg,
            original_exception=overall_last_exc # Include the very last exception encountered
        ) from overall_last_exc
