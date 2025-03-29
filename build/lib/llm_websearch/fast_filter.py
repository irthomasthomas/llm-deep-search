"""Fast filtering module for initial content relevance assessment."""
from typing import List, Dict, Union, Optional
import concurrent.futures
from dataclasses import dataclass
import time

@dataclass
class FilterResult:
    """Container for filter results"""
    content: str
    relevance_score: float
    confidence: float
    filtering_time: float

class FastFilter:
    """Fast filtering system using lightweight LLMs"""
    
    def __init__(self, 
                 threshold: float = 0.7,
                 max_workers: int = 4,
                 lightweight_model: str = "gemini-2.0-flash",
                 llm_integration = None): # Added LLMIntegration parameter
        self.threshold = threshold
        self.max_workers = max_workers
        self.model = lightweight_model
        self.llm_integration = llm_integration
        
    def _score_content(self, content: str, query: str) -> FilterResult:
        """Score individual content piece for relevance"""
        start_time = time.time()
        
        # If LLMIntegration is available, use it for enhanced relevance scoring
        if self.llm_integration:
            try:
                prompt = f"""Evaluate the relevance of the following content to the search query.
                
                Search Query: "{query}"
                
                Content:
                {content[:500]}  # Limit content to 500 chars to keep it lightweight
                
                Return only a single number between 0.0 and 1.0, where:
                - 0.0 means completely irrelevant
                - 1.0 means highly relevant
                """
                
                system_prompt = "You are a relevance scoring system. Respond with only a single numerical value between 0.0 and 1.0."
                
                response = self.llm_integration.generate_response(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    task_type="relevance_scoring",
                    required_capabilities=[]  # No special capabilities needed for this simple task
                )
                
                # Try to extract a float from the response
                try:
                    # Remove any non-numeric characters except period and minus sign
                    import re
                    score_text = re.sub(r'[^0-9.-]', '', response.content)
                    score = float(score_text)
                    
                    # Clamp to valid range
                    score = max(0.0, min(1.0, score))
                    confidence = response.confidence_score
                    
                    return FilterResult(
                        content=content,
                        relevance_score=score,
                        confidence=confidence,
                        filtering_time=time.time() - start_time
                    )
                except (ValueError, TypeError):
                    # If we can't parse a float, fall back to keyword matching
                    pass
            
            except Exception as e:
                # If LLM fails, fall back to keyword matching
                pass
        
        # Fallback: simple keyword matching approach 
        if any(term.lower() in content.lower() for term in query.split()):
            score = 0.8
            confidence = 0.9
        else:
            score = 0.3
            confidence = 0.7
            
        return FilterResult(
            content=content,
            relevance_score=score,
            confidence=confidence,
            filtering_time=time.time() - start_time
        )
    
    def filter_batch(self, 
                    contents: List[str], 
                    query: str) -> List[FilterResult]:
        """Filter a batch of content in parallel"""
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [
                executor.submit(self._score_content, content, query)
                for content in contents
            ]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
            
        return [r for r in results if r.relevance_score >= self.threshold]

    def filter_stream(self, content_stream, query: str):
        """Filter content as it streams in"""
        for content in content_stream:
            result = self._score_content(content, query)
            if result.relevance_score >= self.threshold:
                yield result
