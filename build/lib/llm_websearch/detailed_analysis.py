"""Detailed content analysis module for Tier 2 processing."""

from dataclasses import dataclass
from typing import List, Dict, Optional, Union
import concurrent.futures
from datetime import datetime
import time
import hashlib

@dataclass
class ContentMetadata:
    """Metadata about analyzed content"""
    word_count: int
    date_detected: Optional[datetime]
    language: str
    content_type: str
    quality_score: float

@dataclass
class DetailedAnalysis:
    """Container for detailed content analysis results"""
    content: str
    metadata: ContentMetadata
    relevance_score: float
    key_points: List[str]
    citations: List[Dict[str, str]]
    confidence: float
    analysis_time: float

class DetailedAnalyzer:
    """Advanced content analysis system"""
    
    def __init__(self,
                 relevance_threshold: float = 0.7,
                 max_workers: int = 4,
                 llm_integration = None,
                 cache_instance = None):
        """
        Initialize the detailed analyzer.
        
        Args:
            relevance_threshold: Minimum relevance score for content to be included
            max_workers: Maximum number of concurrent workers
            llm_integration: LLMIntegration instance for LLM-based analysis
            cache_instance: Cache instance for caching analysis results
        """
        self.relevance_threshold = relevance_threshold
        self.max_workers = max_workers
        self.llm = llm_integration
        self.cache = cache_instance
    
    def _create_cache_key(self, content: str, query: str) -> str:
        """Create a deterministic cache key for content analysis."""
        # Create a string representation that's hashable
        key_content = f"detailed_analysis:{query}:{content[:1000]}"  # Use first 1000 chars for key
        return hashlib.md5(key_content.encode()).hexdigest()
    
    def extract_metadata(self, content: str) -> ContentMetadata:
        """Extract metadata from content"""
        word_count = len(content.split())
        
        # Detect language (simplified mock implementation)
        language = "en"  # Default to English
        
        # Determine content type
        content_type = "text/plain"
        
        # Calculate quality score based on content length and structure
        quality_score = min(1.0, word_count / 500)  # Higher score for longer content
        
        return ContentMetadata(
            word_count=word_count,
            date_detected=datetime.now(),
            language=language,
            content_type=content_type,
            quality_score=quality_score
        )
    
    def extract_key_points(self, content: str, query: str) -> List[str]:
        """Extract key points from content using LLM if available"""
        if self.llm:
            try:
                prompt = f"""Extract the key points from the following content that are relevant to the query "{query}".
                Return 3-5 concise bullet points:
                
                Content:
                {content[:3000]}  # Limit to 3000 chars
                """
                
                system_prompt = "You are an analytical assistant that extracts key points from content."
                
                response = self.llm.generate_response(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    task_type="key_points_extraction"
                )
                
                # Extract key points from response
                key_points = [point.strip() for point in response.content.split("\n") if point.strip()]
                return key_points[:5]  # Limit to 5 key points
                
            except Exception as e:
                # Fall back to simple extraction on failure
                print(f"Error extracting key points with LLM: {e}")
        
        # Simple extraction fallback
        points = []
        sentences = content.split('. ')
        for sentence in sentences[:3]:
            if sentence and len(sentence.split()) > 5:  # Only include substantial sentences
                points.append(sentence.strip())
        return points
    
    def extract_citations(self, content: str) -> List[Dict[str, str]]:
        """Extract citations and references"""
        citations = []
        
        # Find citation-like patterns in the content
        citation_markers = ["cited in", "according to", "as mentioned in", "reference:"]
        
        for marker in citation_markers:
            idx = content.lower().find(marker)
            if idx != -1:
                # Extract the text around the citation marker
                start = max(0, idx - 20)
                end = min(len(content), idx + 100)
                citation_text = content[start:end].strip()
                
                citations.append({
                    "text": citation_text,
                    "source": "document",
                    "context": marker
                })
        
        # If no citations found, use a default entry
        if not citations:
            citations.append({
                "text": content[:100] + "...",
                "source": "document",
                "context": "general"
            })
            
        return citations
    
    def calculate_relevance(self, content: str, query: str) -> float:
        """Calculate detailed relevance score using LLM if available"""
        if self.llm:
            try:
                prompt = f"""Evaluate the relevance of the following content to the query: "{query}"
                
                Content:
                {content[:2000]}  # Limit to 2000 chars
                
                Rate the relevance from 0.0 to 1.0, where:
                - 0.0 means completely irrelevant
                - 1.0 means directly relevant and important
                
                Return only the numerical score:"""
                
                system_prompt = "You are an AI assistant that evaluates content relevance."
                
                response = self.llm.generate_response(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    task_type="relevance_analysis"
                )
                
                # Extract the score from the response
                try:
                    # Try to find a float value in the response
                    score_text = response.content.strip()
                    score = float(score_text)
                    # Ensure score is in valid range
                    return max(0.0, min(1.0, score))
                except ValueError:
                    # Fall back to term-based relevance on parsing failure
                    print(f"Could not parse relevance score from LLM response: {response.content}")
            except Exception as e:
                print(f"Error calculating relevance with LLM: {e}")
        
        # Term-based relevance calculation fallback
        query_terms = query.lower().split()
        content_lower = content.lower()
        
        # Calculate term frequency
        term_matches = sum(1 for term in query_terms if term in content_lower)
        
        # Calculate basic relevance score
        base_score = term_matches / len(query_terms) if query_terms else 0
        
        # Boost score based on term proximity
        proximity_bonus = 0.0
        for i in range(len(query_terms) - 1):
            if i + 1 < len(query_terms):
                term1 = query_terms[i]
                term2 = query_terms[i + 1]
                if term1 in content_lower and term2 in content_lower:
                    idx1 = content_lower.find(term1)
                    idx2 = content_lower.find(term2)
                    distance = abs(idx2 - idx1)
                    if distance < 50:  # Terms are close together
                        proximity_bonus += 0.1
        
        # Combine scores and ensure within valid range
        return min(1.0, base_score + proximity_bonus)
    
    def analyze_content(self, content: str, query: str) -> DetailedAnalysis:
        """Perform detailed content analysis"""
        # Try cache first
        if self.cache:
            cache_key = self._create_cache_key(content, query)
            cached_result = self.cache.get(cache_key, default=None)
            if cached_result:
                return cached_result
        
        start_time = time.time()
        
        # Extract metadata
        metadata = self.extract_metadata(content)
        
        # Calculate relevance
        relevance = self.calculate_relevance(content, query)
        
        # Only proceed with further analysis if relevance meets threshold
        if relevance >= self.relevance_threshold:
            # Extract key points
            key_points = self.extract_key_points(content, query)
            
            # Extract citations
            citations = self.extract_citations(content)
        else:
            # Minimal analysis for low-relevance content
            key_points = []
            citations = []
        
        # Create analysis result
        result = DetailedAnalysis(
            content=content,
            metadata=metadata,
            relevance_score=relevance,
            key_points=key_points,
            citations=citations,
            confidence=0.8 * relevance,  # Scale confidence by relevance
            analysis_time=time.time() - start_time
        )
        
        # Cache result if it's relevant
        if self.cache and relevance >= self.relevance_threshold:
            cache_key = self._create_cache_key(content, query)
            self.cache.set(cache_key, result, expire=24*60*60)  # 24 hour expiration
        
        return result
    
    def analyze_batch(self,
                     contents: List[str],
                     query: str,
                     timeout: float = 30.0) -> List[DetailedAnalysis]:
        """Analyze a batch of content in parallel"""
        start_time = time.time()
        results = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_content = {
                executor.submit(self.analyze_content, content, query): content
                for content in contents
            }
            
            for future in concurrent.futures.as_completed(future_to_content):
                if time.time() - start_time > timeout:
                    for f in future_to_content:
                        f.cancel()
                    raise TimeoutError("Batch analysis timed out")
                    
                try:
                    result = future.result()
                    if result.relevance_score >= self.relevance_threshold:
                        results.append(result)
                except Exception as e:
                    print(f"Analysis failed for content: {str(e)}")
                    continue
                
        return results
    
    def analyze_search_results(self, 
                              search_results: List, 
                              query: str, 
                              timeout: float = 30.0) -> List[DetailedAnalysis]:
        """
        Analyze a batch of search results.
        
        Args:
            search_results: List of search result objects with snippet/content
            query: The search query
            timeout: Maximum time for analysis in seconds
            
        Returns:
            List of detailed analysis results
        """
        # Extract content from search results
        contents = []
        
        for result in search_results:
            if hasattr(result, 'snippet'):
                contents.append(result.snippet)
        
        # Analyze the extracted content
        return self.analyze_batch(contents, query, timeout)
