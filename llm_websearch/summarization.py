"""Summarization module for generating multi-level summaries and key insights."""

from typing import List, Dict, Optional, Union, Tuple, Any
from dataclasses import dataclass
import time
from datetime import datetime

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
                min_confidence: float = 0.7):
        """Initialize the summarizer."""

        self.llm = llm_integration
        self.short_length = short_summary_length
        self.medium_length = medium_summary_length
        self.long_length = long_summary_length
        self.min_confidence = min_confidence

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
        
        if level == 1:
            target_length = self.short_length
            prompt = f"Generate a short summary (around {target_length} words) of the following text:\n\n{content}"
        elif level == 2:
            target_length = self.medium_length
            prompt = f"Generate a medium-length summary (around {target_length} words) of the following text:\n\n{content}"
        elif level == 3:
            target_length = self.long_length
            prompt = f"Generate a detailed summary (around {target_length} words) of the following text:\n\n{content}"
        else:
            raise ValueError("Invalid summary level. Must be 1, 2, or 3.")
        
        if self.llm:
            response = self.llm.generate_response(
                prompt,
                task_type="summarization",
                required_capabilities=["summarization"]
            )

            if not response.error:
                return Summary(
                    content=response.content,
                    level=level,
                    source_indices = [0], # Mock for single content.
                    confidence=response.confidence_score,
                    generation_time=time.time() - start_time
                )
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
        
        if self.llm:
            combined_content = "\n".join(content)
            prompt = f"Identify the key insights and most important points from the following text:\n\n{combined_content}"

            response = self.llm.generate_response(
                prompt,
                task_type="key_insights",
                required_capabilities=["reasoning", "summarization"]
                )
            if not response.error:
                # Very simplified mock processing of response:
                return response.content.split(". ")[:3]

        # Mock key insights
        return ["Mock insight 1", "Mock insight 2", "Mock insight 3"]

    def summarize(self,
                content: List[str],
                context: Optional[Dict[str, Any]] = None) -> SummarizationResult:
        """Generate multi-level summaries and extract key insights."""
        
        start_time = datetime.now()
        summaries = []
        
        # 1. Generate individual summaries for each content piece
        for i, text in enumerate(content):
            for level in [1, 2, 3]:
                summary = self._generate_summary(text, level)
                # Update source indices to reflect the original content
                summary.source_indices = [i]
                summaries.append(summary)
        
        # 2. Combine short summaries, then medium, then long, to create hierarchical summaries.
        combined_short = " ".join([s.content for s in summaries if s.level == 1])
        combined_medium = " ".join([s.content for s in summaries if s.level == 2])
        #combined_long = " ".join([s.content for s in summaries if s.level == 3]) # No need to summarize the long summaries

        if len(content) > 1: # Create combined summaries only if we have multiple input items.
          # We re-use _generate_summary.  In a real implementation we might create a separate combine_summaries()
            summaries.append(self._generate_summary(combined_short, 2)) # Medium summary from shorts
            summaries.append(self._generate_summary(combined_medium, 3)) # Long summary from mediums


        # 3. Extract Key Insights
        key_insights = self._extract_key_insights(content)
        
        return SummarizationResult(
            original_content=content,
            summaries=summaries,
            total_time=(datetime.now() - start_time).total_seconds(),
            key_insights=key_insights
        )
