"""Summarization module for generating multi-level summaries and key insights."""

from typing import List, Dict, Optional, Union, Tuple, Any
from dataclasses import dataclass
import time
from datetime import datetime
import hashlib

@dataclass
class Summary:
    """Represents a summary with metadata."""
    content: str
    level: int  # 1: Short, 2: Medium, 3: Detailed
    source_indices: List[int]  # Indices of source content used
    confidence: float
    generation_time: float

@dataclass
class SummarizationResult:
    """Contains results of summarization."""
    original_content: List[str]
    summaries: List[Summary]
    total_time: float
    key_insights: List[str]

class Summarizer:
    """Advanced summarization system."""

    def __init__(self,
                llm_integration = None,
                short_summary_length: int = 50,
                medium_summary_length: int = 150,
                long_summary_length: int = 500,
                min_confidence: float = 0.7,
                cache_instance = None):
        """Initialize the summarizer."""

        self.llm = llm_integration
        self.short_length = short_summary_length
        self.medium_length = medium_summary_length
        self.long_length = long_summary_length
        self.min_confidence = min_confidence
        self.cache = cache_instance

    def _create_cache_key(self, content: List[str], level: int) -> str:
        """Create a deterministic cache key for summarization."""
        # Create a string representation that's hashable
        content_str = "\n".join([c[:500] for c in content])  # Use first 500 chars of each content item
        key_content = f"summarization:{level}:{hashlib.md5(content_str.encode()).hexdigest()}"
        return hashlib.md5(key_content.encode()).hexdigest()

    def _generate_summary(self,
                         content: str,
                         level: int,
                         context: Optional[Dict[str, Any]] = None) -> Summary:
        """Generate a summary of specified level using LLM."""

        start_time = time.time()

        if not content.strip():
            return Summary(
                content="",
                level=level,
                source_indices=[],
                confidence=0.0,
                generation_time=0.0
            )
            
        # Try cache first if available
        if self.cache:
            cache_key = self._create_cache_key([content], level)
            cached_result = self.cache.get(cache_key, default=None)
            if cached_result:
                return cached_result
        
        if level == 1:
            target_length = self.short_length
            prompt = f"Generate a concise summary (around {target_length} words) of the following text, focusing on the most important points:\n\n{content}"
            system_prompt = "You are a concise summarizer that extracts the core information in a very brief format."
        elif level == 2:
            target_length = self.medium_length
            prompt = f"Generate a medium-length summary (around {target_length} words) of the following text, balancing detail and conciseness:\n\n{content}"
            system_prompt = "You are a balanced summarizer that extracts important information while maintaining readability."
        elif level == 3:
            target_length = self.long_length
            prompt = f"Generate a detailed summary (around {target_length} words) of the following text, including all important information and supporting details:\n\n{content}"
            system_prompt = "You are a detailed summarizer that preserves important information and context."
        else:
            raise ValueError("Invalid summary level. Must be 1, 2, or 3.")
        
        if self.llm:
            response = self.llm.generate_response(
                prompt,
                system_prompt=system_prompt,
                task_type="summarization",
                required_capabilities=["summarization"]
            )

            if not response.error:
                result = Summary(
                    content=response.content,
                    level=level,
                    source_indices = [0], # Single content source
                    confidence=response.confidence_score,
                    generation_time=time.time() - start_time
                )
                
                # Cache the result if it's good
                if self.cache and result.confidence >= self.min_confidence:
                    cache_key = self._create_cache_key([content], level)
                    self.cache.set(cache_key, result, expire=24*60*60)  # 24 hour expiration
                
                return result
            else:
                return Summary(
                    content=f"Error generating summary: {response.error}",
                    level = level,
                    source_indices = [],
                    confidence=0.0,
                    generation_time=time.time() - start_time
                )
        else:
            # Mock Summary
            mock_summary = f"Mock {['short', 'medium', 'detailed'][level -1]} summary of the content."
            return Summary(
                content = mock_summary,
                level = level,
                source_indices = [0],
                confidence=0.9,
                generation_time=time.time() - start_time
                )
        
    def _extract_key_insights(self, content: List[str]) -> List[str]:
        """Extract key insights from content using LLM."""
        
        # Try cache first if available
        if self.cache:
            content_str = "\n".join([c[:300] for c in content])  # Use first 300 chars of each content item
            cache_key = f"key_insights:{hashlib.md5(content_str.encode()).hexdigest()}"
            cached_result = self.cache.get(cache_key, default=None)
            if cached_result:
                return cached_result
        
        if self.llm:
            combined_content = "\n\n".join(content)
            
            # Limit combined content to a reasonable size
            if len(combined_content) > 8000:
                combined_content = combined_content[:8000] + "... [content truncated for length]"
            
            prompt = f"""Analyze the following content and identify the 5-7 most important insights or takeaways.
Focus on key findings, unique perspectives, and valuable information.
Present each insight as a clear, standalone statement.

Content:
{combined_content}

Key Insights:"""

            system_prompt = "You are an analytical assistant that extracts and articulates key insights from complex information."

            response = self.llm.generate_response(
                prompt,
                system_prompt=system_prompt,
                task_type="key_insights",
                required_capabilities=["reasoning", "summarization"]
                )
                
            if not response.error:
                # Process the response to get insights
                insights_text = response.content
                insights = []
                
                # Parse insights, assuming each insight is on a new line
                lines = insights_text.split("\n")
                
                for line in lines:
                    line = line.strip()
                    
                    # Skip empty lines
                    if not line:
                        continue
                    
                    # Remove bullet points or numbering
                    if line.startswith("- "):
                        line = line[2:].strip()
                    elif line.startswith("* "):
                        line = line[2:].strip()
                    elif len(line) > 2 and line[0].isdigit() and line[1] == "." and line[2] == " ":
                        line = line[3:].strip()
                    
                    # Add cleaned insight
                    if line:
                        insights.append(line)
                
                # Cache the result
                if self.cache and insights:
                    content_str = "\n".join([c[:300] for c in content])
                    cache_key = f"key_insights:{hashlib.md5(content_str.encode()).hexdigest()}"
                    self.cache.set(cache_key, insights, expire=24*60*60)  # 24 hour expiration
                
                return insights[:7]  # Limit to 7 insights

        # Mock key insights if LLM not available or failed
        return ["Key Insight 1", "Key Insight 2", "Key Insight 3"]

    def _generate_combined_summary(self, 
                                 summaries: List[Summary], 
                                 level: int) -> Summary:
        """Generate a combined summary from multiple source summaries."""
        
        if not summaries:
            return Summary(
                content="",
                level=level,
                source_indices=[],
                confidence=0.0,
                generation_time=0.0
            )
        
        # If only one summary, just return it
        if len(summaries) == 1 and summaries[0].level == level:
            return summaries[0]
        
        # Combine summaries for LLM processing
        source_indices = []
        combined_content = ""
        for i, summary in enumerate(summaries):
            source_indices.extend(summary.source_indices)
            if combined_content:
                combined_content += "\n\n"
            combined_content += summary.content
        
        # Generate a new summary of the combined content
        start_time = time.time()
        
        # Try cache first if available
        if self.cache:
            cache_key = self._create_cache_key([s.content for s in summaries], level)
            cached_result = self.cache.get(cache_key, default=None)
            if cached_result:
                return cached_result
        
        if level == 1:
            target_length = self.short_length
            prompt = f"Synthesize a concise summary (around {target_length} words) from these summaries:\n\n{combined_content}"
            system_prompt = "You are a synthesis expert. Create a concise, unified summary from multiple sources."
        elif level == 2:
            target_length = self.medium_length
            prompt = f"Synthesize a medium-length summary (around {target_length} words) from these summaries:\n\n{combined_content}"
            system_prompt = "You are a synthesis expert. Create a balanced, unified summary from multiple sources."
        elif level == 3:
            target_length = self.long_length
            prompt = f"Synthesize a detailed summary (around {target_length} words) from these summaries:\n\n{combined_content}"
            system_prompt = "You are a synthesis expert. Create a detailed, unified summary from multiple sources."
        else:
            raise ValueError("Invalid summary level. Must be 1, 2, or 3.")
        
        if self.llm:
            response = self.llm.generate_response(
                prompt,
                system_prompt=system_prompt,
                task_type="summary_synthesis",
                required_capabilities=["summarization"]
            )

            if not response.error:
                result = Summary(
                    content=response.content,
                    level=level,
                    source_indices=source_indices,
                    confidence=response.confidence_score,
                    generation_time=time.time() - start_time
                )
                
                # Cache the result if it's good
                if self.cache and result.confidence >= self.min_confidence:
                    cache_key = self._create_cache_key([s.content for s in summaries], level)
                    self.cache.set(cache_key, result, expire=24*60*60)  # 24 hour expiration
                
                return result
            else:
                # If LLM fails, fallback to simple concatenation
                fallback_content = " ".join([s.content for s in summaries])
                if len(fallback_content) > target_length * 4:  # If too long, truncate
                    fallback_content = fallback_content[:target_length * 4] + "..."
                
                return Summary(
                    content=fallback_content,
                    level=level,
                    source_indices=source_indices,
                    confidence=0.5,  # Lower confidence for fallback
                    generation_time=time.time() - start_time
                )
                
        else:
            # Mock combined summary
            mock_content = f"Combined {['short', 'medium', 'detailed'][level - 1]} summary from {len(summaries)} sources."
            return Summary(
                content=mock_content,
                level=level,
                source_indices=source_indices,
                confidence=0.8,
                generation_time=time.time() - start_time
            )

    def summarize(self,
                content: List[str],
                context: Optional[Dict[str, Any]] = None) -> SummarizationResult:
        """Generate multi-level summaries and extract key insights."""
        
        start_time = datetime.now()
        summaries = []
        
        if not content:
            return SummarizationResult(
                original_content=[],
                summaries=[],
                total_time=0.0,
                key_insights=[]
            )
        
        # 1. Generate individual summaries for each content piece
        item_summaries = {1: [], 2: [], 3: []}
        for i, text in enumerate(content):
            for level in [1, 2, 3]:
                summary = self._generate_summary(text, level, context)
                # Update source indices to reflect the original content
                summary.source_indices = [i]
                summaries.append(summary)
                item_summaries[level].append(summary)
        
        # 2. Generate combined summaries for each level
        if len(content) > 1:
            for level in [1, 2, 3]:
                combined = self._generate_combined_summary(item_summaries[level], level)
                summaries.append(combined)
        
        # 3. Extract Key Insights
        key_insights = self._extract_key_insights(content)
        
        return SummarizationResult(
            original_content=content,
            summaries=summaries,
            total_time=(datetime.now() - start_time).total_seconds(),
            key_insights=key_insights
        )
    
    def summarize_research_result(self, research_result) -> Dict[str, Any]:
        """
        Summarize a ResearchResult object to enhance its output.
        
        Args:
            research_result: The ResearchResult object containing findings and evidence
            
        Returns:
            Dictionary with enhanced summary information
        """
        findings_text = []
        evidence_text = []
        
        # Extract text from findings
        for finding in research_result.key_findings:
            if isinstance(finding, dict) and 'finding' in finding:
                findings_text.append(finding['finding'])
        
        # Extract text from evidence
        for evidence in research_result.evidence:
            if isinstance(evidence, dict) and 'evidence' in evidence:
                evidence_text.append(evidence['evidence'])
        
        # Combine for a complete picture
        all_text = findings_text + evidence_text
        
        # Generate summaries
        if all_text:
            summary_result = self.summarize(all_text)
            
            # Create a structured output
            summary_data = {
                "tiered_summaries": {
                    "short": next((s.content for s in summary_result.summaries if s.level == 1 and len(s.source_indices) > 1), ""),
                    "medium": next((s.content for s in summary_result.summaries if s.level == 2 and len(s.source_indices) > 1), ""),
                    "detailed": next((s.content for s in summary_result.summaries if s.level == 3 and len(s.source_indices) > 1), "")
                },
                "key_insights": summary_result.key_insights,
                "generation_time": summary_result.total_time
            }
            
            return summary_data
        
        return {
            "tiered_summaries": {
                "short": "",
                "medium": "",
                "detailed": ""
            },
            "key_insights": [],
            "generation_time": 0.0
        }
