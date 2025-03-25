"""Deep Research module for advanced recursive search capabilities."""

from dataclasses import dataclass
from typing import List, Dict, Optional, Set, Any
import concurrent.futures
import time
from datetime import datetime
import logging
from llm_websearch.fast_filter import FastFilter

logger = logging.getLogger(__name__)

@dataclass
class SearchPath:
    """Represents a search exploration path"""
    query: str
    parent_query: Optional[str]
    depth: int
    relevance_score: float
    timestamp: datetime

@dataclass
class ResearchContext:
    """Maintains context for the research session"""
    original_query: str
    explored_queries: Set[str]
    search_paths: List[SearchPath]
    max_depth: int
    start_time: datetime
    timeout: float

@dataclass
class ResearchResult:
    """Contains results from deep research"""
    query: str  # Original query
    query_tree: Dict[str, List[str]]
    key_findings: List[Dict]
    evidence: List[Dict]
    confidence_score: float
    research_time: float
    exploration_paths: List[SearchPath]

class DeepResearcher:
    """Advanced recursive search system"""
    
    def __init__(self,
                 search_function: Any,
                 max_depth: int = 3,
                 relevance_threshold: float = 0.7,
                 max_workers: int = 4,
                 timeout: float = 300.0,
                 generate_subqueries_function: Optional[Any] = None,
                 analyze_relevance_function: Optional[Any] = None,
                 extract_findings_function: Optional[Any] = None,
                 llm: Optional[Any] = None):
        """
        Initialize the DeepResearcher.
        
        Args:
            search_function: Function to perform web searches
            max_depth: Maximum depth for recursive exploration
            relevance_threshold: Minimum relevance score to continue exploration
            max_workers: Maximum number of concurrent workers
            timeout: Research timeout in seconds
            generate_subqueries_function: Optional custom function to generate subqueries
            analyze_relevance_function: Optional custom function to analyze relevance
            extract_findings_function: Optional custom function to extract findings
            llm: Optional LLM for enhanced analysis
        """
        self.search_function = search_function
        self.max_depth = max_depth
        self.relevance_threshold = relevance_threshold
        self.max_workers = max_workers
        self.timeout = timeout
        self.generate_subqueries_function = generate_subqueries_function
        self.analyze_relevance_function = analyze_relevance_function
        self.extract_findings_function = extract_findings_function
        self.llm = llm
        self.fast_filter = FastFilter()
    
    def _check_timeout(self, context: ResearchContext) -> None:
        """Check if research has exceeded timeout"""
        elapsed = (datetime.now() - context.start_time).total_seconds()
        if elapsed > context.timeout:
            raise TimeoutError("Deep research timeout exceeded")
    
    def _generate_subqueries(self, query: str, context: ResearchContext, search_results: List[Dict]) -> List[str]:
        """Generate relevant subqueries based on initial results"""
        self._check_timeout(context)  # Add timeout check
        
        if query in context.explored_queries:
            return []
        
        # If custom function provided, use it
        if self.generate_subqueries_function:
            return self.generate_subqueries_function(query, search_results)
            
        # Default implementation: extract potential subqueries from search results
        subqueries = []
        
        # Extract key phrases from search result snippets
        key_phrases = set()
        for result in search_results:
            # Simple extraction of potential key phrases from snippet
            if hasattr(result, 'snippet'):
                snippet = result.snippet
                # Split by common delimiters and filter reasonable length phrases
                for delim in ['.', ',', ';', ':', '(', ')', '[', ']']:
                    phrases = [p.strip() for p in snippet.split(delim)]
                    phrases = [p for p in phrases if 3 <= len(p.split()) <= 7]  # Reasonable phrase length
                    key_phrases.update(phrases)
        
        # Combine with original query to create subqueries
        for phrase in key_phrases:
            if len(phrase.split()) >= 2:  # Only use phrases with at least 2 words
                subquery = f"{query} {phrase}"
                if subquery not in context.explored_queries:
                    subqueries.append(subquery)
        
        # Add some standard variations if we don't have enough
        if len(subqueries) < 3:
            variations = [
                f"{query} benefits",
                f"{query} problems",
                f"{query} examples",
                f"{query} latest developments",
                f"{query} analysis"
            ]
            for variation in variations:
                if variation not in context.explored_queries and variation not in subqueries:
                    subqueries.append(variation)
        
        return subqueries[:5]  # Limit to top 5 subqueries
    
    def _analyze_path_relevance(self, 
                              current_query: str,
                              parent_query: str,
                              context: ResearchContext) -> float:
        """Analyze relevance of current search path"""
        self._check_timeout(context)  # Add timeout check
        
        # If custom function provided, use it
        if self.analyze_relevance_function:
            return self.analyze_relevance_function(current_query, parent_query)
        
        # Default implementation: analyze term overlap
        if not parent_query:
            return 1.0  # Root query is always fully relevant
            
        if current_query.startswith(parent_query):
            return 0.9  # High relevance if current is an extension of parent
            
        # Calculate term overlap
        parent_terms = set(parent_query.lower().split())
        current_terms = set(current_query.lower().split())
        
        if not parent_terms:
            return 0.5  # Default mid-range relevance if parent has no terms
            
        # Jaccard similarity between term sets
        intersection = parent_terms.intersection(current_terms)
        union = parent_terms.union(current_terms)
        
        jaccard_similarity = len(intersection) / len(union) if union else 0.0
        
        # Incorporate FastFilter score
        fast_filter_score = self.fast_filter.similarity(parent_query, current_query)
        
        # Combine Jaccard similarity and FastFilter score (weighted average)
        relevance_score = (0.7 * jaccard_similarity) + (0.3 * fast_filter_score)
        
        return relevance_score
    
    def _explore_query(self,
                      query: str,
                      context: ResearchContext,
                      parent_query: Optional[str] = None,
                      depth: int = 0) -> List[SearchPath]:
        """Recursively explore a query path"""
        self._check_timeout(context)
        
        if depth >= context.max_depth or query in context.explored_queries:
            return []
        
        logger.info(f"Exploring query at depth {depth}: {query}")
        
        context.explored_queries.add(query)
        relevance = self._analyze_path_relevance(query, parent_query or "", context)
        
        if relevance < self.relevance_threshold:
            logger.info(f"Query relevance {relevance:.2f} below threshold {self.relevance_threshold}, stopping exploration")
            return []
        
        # Perform actual search for this query
        try:
            search_results = self.search_function(query)
            logger.info(f"Found {len(search_results)} results for query: {query}")
            search_results_dict[query] = search_results  # Store results
        except Exception as e:
            logger.error(f"Search failed for query '{query}': {str(e)}")
            search_results = []
        
        current_path = SearchPath(
            query=query,
            parent_query=parent_query,
            depth=depth,
            relevance_score=relevance,
            timestamp=datetime.now()
        )
        
        paths = [current_path]
        
        # Generate subqueries only if we're not at max depth
        if depth < context.max_depth - 1:
            subqueries = self._generate_subqueries(query, context, search_results)
            logger.info(f"Generated {len(subqueries)} subqueries for: {query}")
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                future_to_query = {
                    executor.submit(self._explore_query, sq, context, query, depth + 1): sq
                    for sq in subqueries
                }
                
                for future in concurrent.futures.as_completed(future_to_query):
                    self._check_timeout(context)  # Check timeout during parallel execution
                    try:
                        paths.extend(future.result())
                    except TimeoutError:
                        # Cancel remaining futures and propagate the timeout
                        for f in future_to_query:
                            f.cancel()
                        raise
                    except Exception as e:
                        logger.error(f"Error exploring query: {str(e)}")
                    
        return paths
    
    def _extract_key_findings(self, paths: List[SearchPath], search_results_dict: Dict[str, List], context: ResearchContext) -> List[Dict]:
        """Extract key findings from explored paths and search results"""
        self._check_timeout(context)
        
        # If custom function provided, use it
        if self.extract_findings_function:
            return self.extract_findings_function(paths, search_results_dict)
        
        findings = []
        for path in paths:
            self._check_timeout(context)
            
            query = path.query
            if query in search_results_dict:
                # Use top results for this query path
                for i, result in enumerate(search_results_dict[query][:3]):  # Top 3 results per query
                    finding = {
                        "query": query,
                        "depth": path.depth,
                        "confidence": path.relevance_score * (0.9 - (i * 0.1)),  # Decrease confidence for lower ranked results
                        "finding": f"{result.title} - {result.snippet}",
                        "source": result.source,
                        "url": result.url
                    }
                    findings.append(finding)
        
        # Deduplicate findings
        unique_findings = {}
        for finding in findings:
            key = finding['finding'][:100]  # Use beginning of finding as deduplication key
            if key not in unique_findings or unique_findings[key]['confidence'] < finding['confidence']:
                unique_findings[key] = finding
        
        # Use LLM to refine and extract key insights
        if self.llm:
            refined_findings = []
            for finding in unique_findings.values():
                try:
                    prompt = f"Summarize the key insight from this finding in one sentence: {finding['finding']}"
                    llm_summary = self.llm(prompt)
                    finding['llm_summary'] = llm_summary
                    refined_findings.append(finding)
                except Exception as e:
                    logger.warning(f"LLM processing failed for finding: {e}")
                    refined_findings.append(finding) # Append original finding if LLM fails
            sorted_findings = sorted(refined_findings, key=lambda x: x['confidence'], reverse=True)
        else:
            # Sort by confidence and limit to top 20
            sorted_findings = sorted(unique_findings.values(), key=lambda x: x['confidence'], reverse=True)
            
        return sorted_findings[:20]
    
    def _gather_evidence(self, paths: List[SearchPath], search_results_dict: Dict[str, List], context: ResearchContext) -> List[Dict]:
        """Gather supporting evidence for findings"""
        self._check_timeout(context)
        
        evidence = []
        for path in paths:
            self._check_timeout(context)
            
            query = path.query
            if query in search_results_dict:
                for i, result in enumerate(search_results_dict[query]):
                    evidence_item = {
                        "query": query,
                        "source": result.source,
                        "url": result.url,
                        "title": result.title,
                        "evidence": result.snippet,
                        "confidence": path.relevance_score * (1.0 - (i * 0.05))  # Slight decrease in confidence for lower ranked
                    }
                    evidence.append(evidence_item)
        
        return evidence
    
    def research(self, query: str) -> ResearchResult:
        """Perform deep research on a query"""
        start_time = datetime.now()
        logger.info(f"Starting deep research for query: {query}")
        
        # Dictionary to store search results for each query
        search_results_dict = {}
        
        context = ResearchContext(
            original_query=query,
            explored_queries=set(),
            search_paths=[],
            max_depth=self.max_depth,
            start_time=start_time,
            timeout=self.timeout
        )
        
        try:
            # Initial search for the root query
            initial_results = self.search_function(query)
            search_results_dict[query] = initial_results
            logger.info(f"Initial search found {len(initial_results)} results")
            
            # Add initial timeout check
            self._check_timeout(context)
            
            # Explore query paths recursively
            exploration_paths = self._explore_query(query, context)
            logger.info(f"Exploration complete, found {len(exploration_paths)} paths")
            
            self._check_timeout(context)
            
            # Build query tree
            query_tree = {}
            for path in exploration_paths:
                self._check_timeout(context)
                parent = path.parent_query or "root"
                if parent not in query_tree:
                    query_tree[parent] = []
                query_tree[parent].append(path.query)
            
            # Extract findings and evidence
            key_findings = self._extract_key_findings(exploration_paths, search_results_dict, context)
            evidence = self._gather_evidence(exploration_paths, search_results_dict, context)
            
            logger.info(f"Extracted {len(key_findings)} key findings and {len(evidence)} evidence items")
            
            # Calculate overall confidence
            confidence_score = (
                sum(p.relevance_score for p in exploration_paths) / 
                len(exploration_paths) if exploration_paths else 0.0
            )
            
            research_time = (datetime.now() - start_time).total_seconds()
            logger.info(f"Deep research completed in {research_time:.2f} seconds")
            
            return ResearchResult(
                query=query,
                query_tree=query_tree,
                key_findings=key_findings,
                evidence=evidence,
                confidence_score=confidence_score,
                research_time=research_time,
                exploration_paths=exploration_paths
            )
            
        except TimeoutError:
            logger.warning(f"Research timeout exceeded after {(datetime.now() - start_time).total_seconds():.2f} seconds")
            raise
        except Exception as e:
            logger.error(f"Deep research failed: {str(e)}")
            raise RuntimeError(f"Deep research failed: {str(e)}")
