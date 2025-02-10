"""Enhanced LLM integration with model selection, validation, and fallback handling."""

from typing import List, Dict, Optional, Union, Tuple
from dataclasses import dataclass
import time
from datetime import datetime
import json
import threading
from enum import Enum

class ModelTier(Enum):
    """LLM model tiers based on capabilities and cost"""
    FAST = "fast"
    STANDARD = "standard"
    PREMIUM = "premium"

@dataclass
class ModelConfig:
    """Configuration for an LLM model"""
    name: str
    tier: ModelTier
    max_tokens: int
    typical_latency: float
    cost_per_token: float  # Keeping this, even though it's 0 in the screenshots
    capabilities: List[str]
    supports_batch: bool = False
    context_window: int = 4096

@dataclass
class LLMResponse:
    """Container for LLM responses with metadata"""
    content: str
    model_used: str
    tokens_used: int
    processing_time: float
    confidence_score: float
    quality_metrics: Dict[str, float]
    timestamp: datetime
    error: Optional[str] = None

class LLMIntegration:
    """Enhanced LLM integration system"""
    
    def __init__(self,
                 primary_models: Optional[List[str]] = None,
                 fallback_models: Optional[List[str]] = None,
                 cache_instance = None):
        """Initialize LLM integration"""
        self.primary_models = primary_models or [
            "gemini-2.0-pro-exp-02-05",
            "gemini-2.0-flash-thinking-exp-01-21"
        ]
        
        self.fallback_models = fallback_models or [
            "gemini-2.0-flash-exp",
            "gemini-2.0-flash"
        ]
        
        # Initialize with default model configs
        self.model_configs = {
            "gemini-2.0-pro-exp-02-05": ModelConfig(
                name="gemini-2.0-pro-exp-02-05",
                tier=ModelTier.PREMIUM,
                max_tokens=128000,  # Example - adjust as needed
                typical_latency=2.5,
                cost_per_token=0.00,  # Updated from screenshots
                capabilities=["multimodal", "streaming", "tool_use", "code"], # Based on screenshot
                supports_batch=True,
                context_window=128000
            ),
            "gemini-2.0-flash-thinking-exp-01-21": ModelConfig(
                name="gemini-2.0-flash-thinking-exp-01-21",
                tier=ModelTier.STANDARD,
                max_tokens=128000, # Example
                typical_latency=1.5,
                cost_per_token=0.00, # Updated
                capabilities=["multimodal", "reasoning", "coding"], # Based on screenshot
                supports_batch=False,
                context_window=128000
            ),
            "gemini-2.0-flash-exp": ModelConfig(
                name="gemini-2.0-flash-exp",
                tier=ModelTier.FAST,
                max_tokens=128000,  # Example
                typical_latency=0.5,
                cost_per_token=0.00,  # Updated
                capabilities=["multimodal", "tool_use", "text_and_images"], # Based on screenshot
                supports_batch=False,
                context_window=128000),
            "gemini-2.0-flash": ModelConfig(
                name="gemini-2.0-flash",
                tier=ModelTier.FAST,
                max_tokens=128000, # Example
                typical_latency = 0.5,
                cost_per_token=0.10, #Updated from screenshot
                capabilities=["multimodal", "streaming", "tool_use"], #Based on screenshot
                supports_batch=False,
                context_window=128000
            )
        }
        
        self.cache = cache_instance
        self._lock = threading.RLock()
        self._usage_stats: Dict[str, Dict] = {}
    
    def _select_model(self,
                     task_type: str,
                     content_length: int,
                     required_capabilities: List[str]) -> str:
        """Select appropriate model based on task requirements"""
        # Try primary models first in specified order
        for model_name in self.primary_models:
            if model_name in self.model_configs:
                config = self.model_configs[model_name]
                if content_length <= config.context_window:
                    if not required_capabilities or all(cap in config.capabilities for cap in required_capabilities):
                        return model_name
        
        # Try fallback models in specified order
        for model_name in self.fallback_models:
            if model_name in self.model_configs:
                config = self.model_configs[model_name]
                if content_length <= config.context_window:
                    if not required_capabilities or all(cap in config.capabilities for cap in required_capabilities):
                        return model_name
        
        # If no suitable model found, return first primary model (will fail gracefully)
        return self.primary_models[0]
    
    def _handle_rate_limits(self, model_name: str) -> None:
        """Handle rate limiting for models"""
        with self._lock:
            if model_name not in self._usage_stats:
                self._usage_stats[model_name] = {
                    "requests": 0,
                    "last_reset": datetime.now(),
                    "errors": 0
                }
            
            stats = self._usage_stats[model_name]
            
            # Reset counters if needed
            now = datetime.now()
            if (now - stats["last_reset"]).total_seconds() > 60:
                stats["requests"] = 0
                stats["last_reset"] = now
            
            # Check rate limits -  PLACEHOLDER LIMITS!
            if stats["requests"] >= 50:  # Example limit
                time.sleep(1)  # Basic backoff
            
            stats["requests"] += 1
    
    def _validate_response(self, 
                          response: str, 
                          expected_format: Optional[str] = None,
                          required_elements: Optional[List[str]] = None) -> Tuple[bool, float, Dict[str, float]]:
        """Validate LLM response quality"""
        quality_metrics = {}
        
        # Check response length
        length_score = min(len(response) / 100, 1.0)
        quality_metrics["length_score"] = length_score
        
        # Check format if specified
        format_score = 1.0
        if expected_format:
            if expected_format == "json":
                try:
                    json.loads(response)
                except json.JSONDecodeError:
                    format_score = 0.0
        quality_metrics["format_score"] = format_score
        
        # Check required elements
        elements_score = 1.0
        if required_elements:
            found_elements = sum(1 for elem in required_elements if elem in response)
            elements_score = found_elements / len(required_elements)
        quality_metrics["elements_score"] = elements_score
        
        # Calculate overall confidence score
        confidence_score = (length_score + format_score + elements_score) / 3
        
        # Response is valid if confidence score meets threshold
        is_valid = confidence_score >= 0.7
        
        return is_valid, confidence_score, quality_metrics
    
    def _process_with_fallback(self,
                             prompt: str,
                             system_prompt: str,
                             model_name: str,
                             max_retries: int = 3) -> LLMResponse:
        """Process request with fallback handling"""
        start_time = time.time()
        errors = []
        
        try:
            # Check if model exists in configs
            if model_name not in self.model_configs:
                raise ValueError(f"Unknown model: {model_name}")
            
            self._handle_rate_limits(model_name)
            
            # Mock LLM call
            response_content = f"Response from {model_name}: {prompt[:50]}..."
            tokens_used = len(prompt.split())
            
            # Validate response
            is_valid, confidence_score, quality_metrics = self._validate_response(
                response_content
            )
            
            if not is_valid:
                raise ValueError("Response validation failed")
            
            return LLMResponse(
                content=response_content,
                model_used=model_name,
                tokens_used=tokens_used,
                processing_time=time.time() - start_time,
                confidence_score=confidence_score,
                quality_metrics=quality_metrics,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            errors.append(f"{model_name}: {str(e)}")
            
            # Try remaining models in order
            all_models = [m for m in self.primary_models + self.fallback_models if m != model_name]
            
            for next_model in all_models:
                try:
                    if next_model not in self.model_configs:
                        raise ValueError(f"Unknown model: {next_model}")
                    
                    self._handle_rate_limits(next_model)
                    response_content = f"Response from {next_model}: {prompt[:50]}..."
                    tokens_used = len(prompt.split())
                    
                    is_valid, confidence_score, quality_metrics = self._validate_response(
                        response_content
                    )
                    
                    if is_valid:
                        return LLMResponse(
                            content=response_content,
                            model_used=next_model,
                            tokens_used=tokens_used,
                            processing_time=time.time() - start_time,
                            confidence_score=confidence_score,
                            quality_metrics=quality_metrics,
                            timestamp=datetime.now()
                        )
                except Exception as e:
                    errors.append(f"{next_model}: {str(e)}")
            
            # All models failed
            return LLMResponse(
                content="",
                model_used="none",
                tokens_used=0,
                processing_time=time.time() - start_time,
                confidence_score=0.0,
                quality_metrics={},
                timestamp=datetime.now(),
                error=f"All models failed: {'; '.join(errors)}"
            )
    
    def generate_response(self,
                         prompt: str,
                         system_prompt: str = "",
                         task_type: str = "general",
                         required_capabilities: Optional[List[str]] = None) -> LLMResponse:
        """Generate response using appropriate model with fallback handling"""
        required_capabilities = required_capabilities or []
        content_length = len(prompt) + len(system_prompt)
        
        # Try cache first
        if self.cache:
            cache_key = {
                "prompt": prompt,
                "system_prompt": system_prompt,
                "task_type": task_type,
                "capabilities": required_capabilities
            }
            cached_response = self.cache.get(cache_key, None)
            if cached_response:
                return cached_response
        
        # Select appropriate model
        model_name = self._select_model(
            task_type,
            content_length,
            required_capabilities
        )
        
        # Generate response with fallback
        response = self._process_with_fallback(
            prompt,
            system_prompt,
            model_name
        )
        
        # Cache successful response
        if self.cache and not response.error:
            self.cache.set(cache_key, response)
        
        return response