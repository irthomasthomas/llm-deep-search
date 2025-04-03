# TODO - llm-websearch Rate Limit Fallback Implementation

This document tracks the tasks needed to implement the model fallback mechanism for handling rate limits in `llm-websearch`, based on the proposal in `REVIEW.md`.

## Tasks

-   [ ] **1. Modify Imports:**
    -   Import `ResourceExhausted` from `google.generativeai.errors` in `llm_websearch/components/llm_integration.py`.
    -   Define a dummy `ResourceExhausted` class in the `except ImportError` block.
-   [ ] **2. Update API Key Config:**
    -   Prioritize `settings.llm_api_key` over `settings.google_api_key` for `genai` configuration in `LLMIntegration.__init__`.
    -   Update related error/warning messages.
-   [ ] **3. Implement Model Sequence Generation:**
    -   Create `_get_model_sequence(self, requested_model: Optional[str] = None) -> List[str]` method.
    -   Ensure it generates an ordered, unique list of valid Gemini models (requested, default, primary, fallback).
    -   Add logging for the generated sequence.
-   [ ] **4. Refactor `generate_response` Method:**
    -   Call `_get_model_sequence` at the start.
    -   Implement the outer `for current_model_name in model_sequence:` loop.
    -   Move the cache check inside the outer loop, using `current_model_name` in the key.
    -   Ensure the retry logic (`for attempt...`) is the inner loop.
    -   Update logging to show current model and attempt.
    -   Adjust `GenerationConfig` setup (e.g., `response_mime_type`).
-   [ ] **5. Implement Rate Limit Handling (429):**
    -   Add `except ResourceExhausted as e:` block within the inner loop's `try...except`.
    -   Log a warning about the rate limit for the specific model.
    -   Use `break` to exit the *inner* loop and try the next model.
-   [ ] **6. Adjust General Exception Handling:**
    -   Ensure the generic `except Exception:` handles non-429 errors and breaks the inner loop after retries fail for a given model.
    -   After the outer loop, check if a response was obtained. If not, raise a final `LLMError` summarizing the failure across all models.
-   [ ] **7. Update `LLMResponse` Instantiation:**
    -   Add the `system_prompt_used=system_prompt` argument.
-   [ ] **8. Testing & Validation:**
    -   Define conceptual test cases (simulate errors, check fallback, verify caching).
    -   Perform tests to confirm logic.
-   [ ] **9. Test Plugin:**
    -   Test installation: `.venv/bin/llm install /home/thomas/Projects/llm/plugins/Utilities/llm-search/llm-deep-search-v4`
    -   Test execution: `.venv/bin/llm websearch deep-search "anthropic 2025 api prompt caching"`
    -   Use uninstall command if needed: `LLM_LOAD_PLUGINS='' .venv/bin/llm uninstall llm-websearch` -y
-   [ ] **10. Review Context Scripts (Optional):**
    -   Review `/home/thomas/Projects/claude.sh/utils/search/bing-search.sh`
    -   Review `/home/thomas/Projects/claude.sh/utils/search/google-search-llm.sh`

## Plan Visualization (Mermaid)
