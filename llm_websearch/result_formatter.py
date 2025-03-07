"""
Tiered Result Format System for DeepResearcher.

This module provides classes and utilities for formatting research results
at different levels of detail to optimize token usage in LLM contexts.
"""

from enum import Enum
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import json


class FormatType(Enum):
    """Enum representing different result format types."""
    COMPACT = "compact"   # Minimal representation with core findings only
    SUMMARY = "summary"   # Moderate detail with key findings and brief evidence
    FULL = "full"         # Complete representation with all details


class FormatOptions:
    """Configuration options for result formatting."""
    
    def __init__(self,
                 include_metadata: bool = True,
                 max_findings: Optional[int] = None,
                 max_evidence_per_finding: Optional[int] = None,
                 confidence_threshold: float = 0.0,
                 include_exploration_paths: bool = False):
        """
        Initialize format options.
        
        Args:
            include_metadata: Whether to include timing and confidence metadata
            max_findings: Maximum number of findings to include (None = all)
            max_evidence_per_finding: Maximum evidence items per finding (None = all)
            confidence_threshold: Minimum confidence score for included findings
            include_exploration_paths: Whether to include exploration path details
        """
        self.include_metadata = include_metadata
        self.max_findings = max_findings
        self.max_evidence_per_finding = max_evidence_per_finding
        self.confidence_threshold = confidence_threshold
        self.include_exploration_paths = include_exploration_paths


class ResearchResultFormatter:
    """
    Formatter for research results with support for different detail levels.
    
    This class can convert ResearchResult objects to different format types
    to optimize for token usage while preserving essential information.
    """
    
    def __init__(self, format_type: FormatType = FormatType.FULL, options: Optional[FormatOptions] = None):
        """
        Initialize the formatter.
        
        Args:
            format_type: The format type to use (COMPACT, SUMMARY, FULL)
            options: Optional configuration for the formatter
        """
        self.format_type = format_type
        self.options = options or FormatOptions()
        
    def format_result(self, result) -> Dict[str, Any]:
        """
        Format a ResearchResult object according to the specified format type.
        
        Args:
            result: A ResearchResult object containing deep research findings
            
        Returns:
            A dictionary with the formatted result
        """
        if self.format_type == FormatType.COMPACT:
            return self._format_compact(result)
        elif self.format_type == FormatType.SUMMARY:
            return self._format_summary(result)
        else:  # FormatType.FULL
            return self._format_full(result)
            
    def _format_compact(self, result) -> Dict[str, Any]:
        """
        Create a compact representation with minimal token usage.
        
        Args:
            result: A ResearchResult object
            
        Returns:
            A dictionary with compact representation
        """
        # Filter findings by confidence threshold
        filtered_findings = [
            f for f in result.key_findings 
            if f.get("confidence", 0) >= self.options.confidence_threshold
        ]
        
        # Limit number of findings if specified
        if self.options.max_findings is not None:
            filtered_findings = filtered_findings[:self.options.max_findings]
        
        # Extract just the finding text
        finding_texts = [f.get("finding", "") for f in filtered_findings]
        
        compact_result = {
            "query": result.query,
            "key_conclusions": finding_texts
        }
        
        # Add metadata if requested
        if self.options.include_metadata:
            compact_result["confidence"] = result.confidence_score
            compact_result["sources_count"] = len(result.evidence)
            
        return compact_result
        
    def _format_summary(self, result) -> Dict[str, Any]:
        """
        Create a summary representation with moderate detail.
        
        Args:
            result: A ResearchResult object
            
        Returns:
            A dictionary with summary representation
        """
        # Filter findings by confidence threshold
        filtered_findings = [
            f for f in result.key_findings 
            if f.get("confidence", 0) >= self.options.confidence_threshold
        ]
        
        # Limit number of findings if specified
        if self.options.max_findings is not None:
            filtered_findings = filtered_findings[:self.options.max_findings]
        
        # Extract finding details
        findings_with_metadata = []
        for f in filtered_findings:
            finding_data = {
                "finding": f.get("finding", ""),
                "confidence": f.get("confidence", 0)
            }
            # Include source URL if available
            if "url" in f:
                finding_data["url"] = f["url"]
            findings_with_metadata.append(finding_data)
        
        # Gather evidence summaries
        evidence_summary = self._summarize_evidence(result.evidence)
        
        summary_result = {
            "query": result.query,
            "key_findings": findings_with_metadata,
            "evidence_summary": evidence_summary
        }
        
        # Add metadata if requested
        if self.options.include_metadata:
            # Calculate the max depth from exploration paths
            max_depth = max([p.depth for p in result.exploration_paths]) if result.exploration_paths else 0
            
            summary_result["exploration_stats"] = {
                "depth": max_depth,
                "paths_explored": len(result.exploration_paths),
                "total_time": result.research_time
            }
            
        return summary_result
        
    def _format_full(self, result) -> Dict[str, Any]:
        """
        Create a full representation with all details.
        
        Args:
            result: A ResearchResult object
            
        Returns:
            A dictionary with full representation
        """
        # Start with a complete representation
        full_result = {
            "query": result.query,
            "query_tree": result.query_tree,
            "key_findings": result.key_findings,
            "evidence": result.evidence,
            "confidence_score": result.confidence_score,
            "research_time": result.research_time,
        }
        
        # Include exploration paths if requested
        if self.options.include_exploration_paths:
            # Convert SearchPath objects to dictionaries
            full_result["exploration_paths"] = [
                {
                    "query": p.query,
                    "parent_query": p.parent_query,
                    "depth": p.depth,
                    "relevance_score": p.relevance_score,
                    "timestamp": p.timestamp.isoformat()
                }
                for p in result.exploration_paths
            ]
            
        return full_result
        
    def _summarize_evidence(self, evidence: List[Dict]) -> str:
        """
        Create a textual summary of evidence items.
        
        Args:
            evidence: List of evidence dictionaries
            
        Returns:
            A string summarizing the evidence
        """
        if not evidence:
            return "No supporting evidence found."
            
        # Count evidence by source
        source_counts = {}
        for e in evidence:
            source = e.get("source", "Unknown")
            source_counts[source] = source_counts.get(source, 0) + 1
            
        # Generate summary text
        summary_parts = [
            f"Evidence collected from {len(evidence)} items across {len(source_counts)} sources."
        ]
        
        # Add top sources
        top_sources = sorted(source_counts.items(), key=lambda x: x[1], reverse=True)[:3]
        if top_sources:
            source_text = ", ".join([f"{source} ({count})" for source, count in top_sources])
            summary_parts.append(f"Top sources: {source_text}.")
            
        # Add confidence info
        confidences = [e.get("confidence", 0) for e in evidence]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0
        summary_parts.append(f"Average evidence confidence: {avg_confidence:.2f}.")
        
        return " ".join(summary_parts)
        
    def get_finding_details(self, result, finding_idx: int) -> Dict[str, Any]:
        """
        Get detailed information about a specific finding.
        
        This allows progressive loading of details without including everything
        in the initial result.
        
        Args:
            result: A ResearchResult object
            finding_idx: Index of the finding to get details for
            
        Returns:
            A dictionary with detailed information about the finding
        """
        if finding_idx < 0 or finding_idx >= len(result.key_findings):
            return {"error": "Finding index out of range"}
            
        finding = result.key_findings[finding_idx]
        
        # Get related evidence for this finding
        related_evidence = [
            e for e in result.evidence
            if e.get("query", "") == finding.get("query", "")
        ]
        
        # Limit evidence items if specified
        if self.options.max_evidence_per_finding is not None:
            related_evidence = related_evidence[:self.options.max_evidence_per_finding]
            
        return {
            "finding": finding,
            "evidence": related_evidence,
            "related_queries": self._get_related_queries(result, finding.get("query", ""))
        }
        
    def _get_related_queries(self, result, query: str) -> List[str]:
        """
        Find queries related to a specific query in the query tree.
        
        Args:
            result: A ResearchResult object
            query: The query to find related queries for
            
        Returns:
            A list of related query strings
        """
        related = []
        
        # Look for children queries
        children = result.query_tree.get(query, [])
        if children:
            related.extend(children)
            
        # Look for sibling queries (with same parent)
        for parent, children in result.query_tree.items():
            if query in children:
                # Add siblings but not the query itself
                related.extend([q for q in children if q != query])
                
        return related
