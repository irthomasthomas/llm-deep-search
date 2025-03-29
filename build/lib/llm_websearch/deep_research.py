"""Deep Research module for detailed recursive exploration of topics."""

import logging 
import time
import json
import uuid
import re
from typing import List, Dict, Any, Callable, Optional, Tuple, Set 
from datetime import datetime
import concurrent.futures
from copy import deepcopy

from .llm_integration import LLMIntegration, LLMResponse, ModelTier

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SearchPath:
    """
    Represents a path in the search exploration tree, containing a query
    and all data associated with that search path.
    """
    
    def __init__(self, query: str, parent_path_id: Optional[str] = None):
        """
        Initialize a search path with a query.
        
        Args:
            query: The search query for this path
            parent_path_id: ID of parent path (if any)
        """
        self.path_id = str(uuid.uuid4())
        self.query = query
        self.parent_path_id = parent_path_id
        self.child_path_ids: List[str] = []
        self.search_results: List[Any] = []
        self.relevance_score: float = 0.0
        self.has_been_explored: bool = False
        self.key_insights: List[Dict[str, Any]] = []
        self.created_at = datetime.now()
        
    def add_child(self, child_path_id: str) -> None:
        """Add a child path ID to this path."""
        self.child_path_ids.append(child_path_id)
    
    def mark_as_explored(self) -> None:
        """Mark this path as having been explored."""
        self.has_been_explored = True
    
    def add_search_results(self, results: List[Any]) -> None:
        """
        Add search results to this path.
        
        Args:
            results: List of search result objects
        """
        self.search_results = results
    
    def add_key_insights(self, insights: List[Dict[str, Any]]) -> None:
        """
        Add key insights extracted from the search results.
        
        Args:
            insights: List of insight dictionaries
        """
        self.key_insights.extend(insights)
    
    def get_child_paths(self, paths_dict: Dict[str, 'SearchPath']) -> List['SearchPath']:
        """
        Get all child paths of this path.
        
        Args:
            paths_dict: Dictionary mapping path IDs to SearchPath objects
        
        Returns:
            List of child SearchPath objects
        """
        return [paths_dict[child_id] for child_id in self.child_path_ids 
                if child_id in paths_dict]
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert this path to a dictionary representation.
        
        Returns:
            Dictionary representation of this path
        """
        return {
            "path_id": self.path_id,
            "query": self.query,
            "parent_path_id": self.parent_path_id,
            "child_path_ids": self.child_path_ids,
            "relevance_score": self.relevance_score,
            "has_been_explored": self.has_been_explored,
            "created_at": str(self.created_at),
            "num_search_results": len(self.search_results),
            "key_insights": self.key_insights
        }

class ResearchResult:
    """
    Represents the result of a deep research session, containing
    the entire search tree and aggregated insights.
    """
    
    def __init__(self, original_query: str):
        """
        Initialize a research result with the original query.
        
        Args:
            original_query: The original user query
        """
        self.original_query = original_query
        self.paths: Dict[str, SearchPath] = {}
        self.root_path_id: Optional[str] = None
        self.key_findings: List[Dict[str, Any]] = []
        self.evidence: List[Dict[str, Any]] = []
        self.contradictions: List[Dict[str, Any]] = []
        self.exploration_metrics: Dict[str, Any] = {
            "start_time": datetime.now(),
            "end_time": None,
            "total_paths_explored": 0,
            "max_depth_reached": 0,
            "total_search_results": 0,
            "exploration_parameters": {}
        }
    
    def add_path(self, path: SearchPath) -> None:
        """
        Add a search path to the research result.
        
        Args:
            path: The SearchPath to add
        """
        self.paths[path.path_id] = path
        
        # If this is the first path, set it as the root
        if self.root_path_id is None:
            self.root_path_id = path.path_id
    
    def add_key_finding(self, finding: str, confidence: float, source_path_ids: List[str]) -> None:
        """
        Add a key finding to the research result.
        
        Args:
            finding: The text of the finding
            confidence: Confidence score for the finding
            source_path_ids: IDs of paths that led to this finding
        """
        self.key_findings.append({
            "finding": finding,
            "confidence": confidence,
            "source_path_ids": source_path_ids
        })
    
    def add_evidence(self, evidence: str, source_path_id: str) -> None:
        """
        Add a piece of evidence to the research result.
        
        Args:
            evidence: The text of the evidence
            source_path_id: ID of the path that led to this evidence
        """
        self.evidence.append({
            "evidence": evidence,
            "source_path_id": source_path_id
        })
    
    def add_contradiction(self, description: str, conflicting_claims: List[str], 
                         source_path_ids: List[str]) -> None:
        """
        Add a contradiction to the research result.
        
        Args:
            description: Description of the contradiction
            conflicting_claims: List of conflicting claims
            source_path_ids: IDs of paths involved in this contradiction
        """
        self.contradictions.append({
            "description": description,
            "conflicting_claims": conflicting_claims,
            "source_path_ids": source_path_ids
        })
    
    def finalize(self, exploration_parameters: Dict[str, Any]) -> None:
        """
        Finalize the research result with exploration statistics.
        
        Args:
            exploration_parameters: Parameters used for the exploration
        """
        self.exploration_metrics["end_time"] = datetime.now()
        self.exploration_metrics["total_paths_explored"] = sum(
            1 for p in self.paths.values() if p.has_been_explored
        )
        self.exploration_metrics["total_search_results"] = sum(
            len(p.search_results) for p in self.paths.values()
        )
        self.exploration_metrics["exploration_parameters"] = exploration_parameters
        
        # Calculate max depth
        if self.root_path_id:
            self.exploration_metrics["max_depth_reached"] = self._calculate_max_depth()
    
    def _calculate_max_depth(self) -> int:
        """
        Calculate the maximum depth of the search tree.
        
        Returns:
            Maximum depth as an integer
        """
        if not self.root_path_id:
            return 0
        
        max_depth = 0
        path_queue = [(self.root_path_id, 0)]  # (path_id, depth)
        visited = set()
        
        while path_queue:
            path_id, depth = path_queue.pop(0)
            
            if path_id in visited:
                continue
                
            visited.add(path_id)
            max_depth = max(max_depth, depth)
            
            if path_id in self.paths:
                path = self.paths[path_id]
                for child_id in path.child_path_ids:
                    if child_id in self.paths:
                        path_queue.append((child_id, depth + 1))
        
        return max_depth
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert this research result to a dictionary representation.
        
        Returns:
            Dictionary representation of this research result
        """
        return {
            "original_query": self.original_query,
            "paths": {path_id: path.to_dict() for path_id, path in self.paths.items()},
            "root_path_id": self.root_path_id,
            "key_findings": self.key_findings,
            "evidence": self.evidence,
            "contradictions": self.contradictions,
            "exploration_metrics": self.exploration_metrics
        }
    
    def get_path_tree(self) -> Dict[str, Any]:
        """
        Generate a hierarchical tree representation of the search paths.
        
        Returns:
            Nested dictionary representing the path tree
        """
        if not self.root_path_id:
            return {}
            
        def build_tree(path_id: str) -> Dict[str, Any]:
            if path_id not in self.paths:
                return {}
                
            path = self.paths[path_id]
            children = []
            
            for child_id in path.child_path_ids:
                if child_id in self.paths:
                    children.append(build_tree(child_id))
            
            return {
                "query": path.query,
                "relevance_score": path.relevance_score,
                "has_been_explored": path.has_been_explored,
                "num_results": len(path.search_results),
                "children": children
            }
        
        return build_tree(self.root_path_id)

class DeepResearcher:
    """Recursively researches a topic by exploring multiple search paths."""
    
    def __init__(
        self, 
        search_function: Callable[[str], List[Any]],
        generate_subqueries_function: Optional[Callable] = None,
        analyze_relevance_function: Optional[Callable] = None,
        max_iterations: int = 3,
        max_branching: int = 3,
        relevance_threshold: float = 0.7,
        diminishing_returns_threshold: float = 0.2,
        llm_integration: Optional[LLMIntegration] = None,
        detailed_analyzer: Any = None
    ):
        """
        Initialize the DeepResearcher.
        
        Args:
            search_function: Function to perform searches (takes query string, returns list of results)
            generate_subqueries_function: Optional custom function to generate subqueries
            analyze_relevance_function: Optional custom function to analyze relevance
            max_iterations: Maximum depth for recursive searching
            max_branching: Maximum number of branches to explore from each node
            relevance_threshold: Minimum relevance score to continue exploring a path
            diminishing_returns_threshold: Minimum improvement in relevance required to explore a path
            llm_integration: Optional LLMIntegration instance for LLM calls
            detailed_analyzer: Optional DetailedAnalyzer instance for detailed content analysis
        """
        self.search_function = search_function
        self.generate_subqueries_function = generate_subqueries_function or self._generate_subqueries
        self.analyze_relevance_function = analyze_relevance_function or self._analyze_path_relevance
        self.max_iterations = max_iterations
        self.max_branching = max_branching
        self.relevance_threshold = relevance_threshold
        self.diminishing_returns_threshold = diminishing_returns_threshold
        self.llm = llm_integration
        self.detailed_analyzer = detailed_analyzer
    
    def research(self, query: str) -> ResearchResult:
        """
        Recursively research a topic by exploring multiple search paths.
        
        Args:
            query: The initial search query
        
        Returns:
            A ResearchResult containing the entire search tree and findings
        """
        start_time = time.time()
        logger.info(f"Starting deep research on query: {query}")
        
        # Initialize the research result
        result = ResearchResult(query)
        
        # Create root path
        root_path = SearchPath(query)
        result.add_path(root_path)
        
        # Explore the root path
        self._explore_path(root_path, result, 0)
        
        # Finalize the result with metadata
        exploration_parameters = {
            "max_iterations": self.max_iterations,
            "max_branching": self.max_branching,
            "relevance_threshold": self.relevance_threshold,
            "diminishing_returns_threshold": self.diminishing_returns_threshold
        }
        result.finalize(exploration_parameters)
        
        # Extract key findings across all paths
        self._extract_key_findings(result)
        
        # Detect contradictions
        self._detect_contradictions(result)
        
        logger.info(f"Deep research completed in {time.time() - start_time:.2f} seconds.")
        logger.info(f"Explored {result.exploration_metrics['total_paths_explored']} paths.")
        logger.info(f"Maximum depth reached: {result.exploration_metrics['max_depth_reached']}")
        
        return result
    
    def _explore_path(self, path: SearchPath, research_result: ResearchResult, 
                     current_depth: int) -> None:
        """
        Explore a search path, performing searches and generating subqueries.
        
        Args:
            path: The SearchPath to explore
            research_result: The ResearchResult to update
            current_depth: Current exploration depth
        """
        if current_depth >= self.max_iterations:
            logger.info(f"Maximum depth reached for query: {path.query}")
            return
        
        logger.info(f"Exploring path at depth {current_depth}: {path.query}")
        
        # Perform search
        try:
            search_results = self.search_function(path.query)
            path.add_search_results(search_results)
            
            # Mark the path as explored
            path.mark_as_explored()
            
            # Extract insights from search results
            self._extract_insights_from_search_results(path, search_results)
            
            # Skip subquery generation if we've reached the max depth
            if current_depth == self.max_iterations - 1:
                return
                
            # Generate subqueries
            try:
                # Extract snippets from search results
                snippets = []
                for result in search_results:
                    if hasattr(result, 'snippet'):
                        snippets.append(result.snippet)
                
                combined_content = "\n".join(snippets)
                
                # Generate a prompt for subquery generation
                prompt = f"""Based on the original query '{path.query}' and the following search results, 
                generate 3-5 specific subqueries that would help explore this topic more deeply:
                
                SEARCH RESULTS:
                {combined_content}
                
                Return each subquery as a string in a JSON list format.
                """
                
                # Generate subqueries
                subqueries = self.generate_subqueries_function(
                    path.query, 
                    combined_content, 
                    max_queries=self.max_branching
                )
                
                # Create child paths for each subquery
                parent_relevance = path.relevance_score
                for subquery in subqueries:
                    child_path = SearchPath(subquery, parent_path_id=path.path_id)
                    research_result.add_path(child_path)
                    path.add_child(child_path.path_id)
                    
                    # Analyze relevance of the child path
                    relevance = self.analyze_relevance_function(
                        original_query=research_result.original_query,
                        current_query=subquery,
                        parent_relevance=parent_relevance
                    )
                    child_path.relevance_score = relevance
                    
                    # Only explore the path if it meets our relevance criteria
                    should_explore = relevance >= self.relevance_threshold
                    
                    # Check if there's enough improvement over the parent path
                    if should_explore and parent_relevance > 0:
                        relevance_change = relevance - parent_relevance
                        should_explore = relevance_change >= -self.diminishing_returns_threshold
                    
                    if should_explore:
                        # Recursively explore this path
                        self._explore_path(child_path, research_result, current_depth + 1)
                    else:
                        logger.info(f"Skipping exploration of subquery due to low relevance: {subquery} (score: {relevance:.2f})")
                
            except Exception as e:
                logger.error(f"Error generating subqueries: {str(e)}")
        
        except Exception as e:
            logger.error(f"Error searching for query '{path.query}': {str(e)}")
    
    def _generate_subqueries(self, query: str, search_results_content: str, 
                            max_queries: int = 3) -> List[str]:
        """
        Generate subqueries based on search results.
        
        Args:
            query: Original query
            search_results_content: Text of search results
            max_queries: Maximum number of subqueries to generate
        
        Returns:
            List of subquery strings
        """
        # Use LLM if available
        if self.llm:
            try:
                prompt = f"""Based on the original query '{query}' and the following search results, 
                generate {max_queries} specific subqueries that would help explore this topic more deeply:
                
                SEARCH RESULTS:
                {search_results_content}
                
                Return each subquery as a string in a JSON list format.
                """
                
                system_prompt = """You are an expert research assistant. Your task is to generate targeted subqueries 
                that will explore different aspects of a topic based on the original query and initial search results.
                Focus on specificity, diversity, and relevance. Return your response as a valid JSON list of strings."""
                
                response = self.llm.generate_response(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    task_type="subquery_generation",
                    required_capabilities=["creative", "structured"]
                )
                
                if response.error:
                    logger.error(f"Error from LLM during subquery generation: {response.error}")
                    return self._fallback_subqueries(query, max_queries)
                
                try:
                    # Parse the response as a JSON list
                    content = response.content.strip()
                    if not (content.startswith('[') and content.endswith(']')):
                        # Add brackets if they're missing
                        content = f"[{content}]"
                    
                    subqueries = json.loads(content)
                    
                    # Ensure we have a list of strings
                    subqueries = [str(q).strip() for q in subqueries if q]
                    
                    # Limit to the maximum number
                    subqueries = subqueries[:max_queries]
                    
                    if not subqueries:
                        return self._fallback_subqueries(query, max_queries)
                    
                    return subqueries
                
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse LLM response as JSON: {response.content}")
                    
                    # Try to extract queries directly from the text
                    lines = response.content.strip().split('\n')
                    extracted_queries = []
                    
                    for line in lines:
                        # Remove numbering, quotes and other common formatting
                        cleaned = line.strip()
                        cleaned = cleaned.lstrip("0123456789.-) *\"'").strip()
                        
                        if cleaned and len(cleaned) > 5:  # Minimum length for a meaningful query
                            extracted_queries.append(cleaned)
                    
                    if extracted_queries:
                        return extracted_queries[:max_queries]
                    
                    return self._fallback_subqueries(query, max_queries)
            
            except Exception as e:
                logger.error(f"Error in subquery generation: {str(e)}")
                return self._fallback_subqueries(query, max_queries)
        
        # Fallback method if LLM is not available or fails
        return self._fallback_subqueries(query, max_queries)
    
    def _fallback_subqueries(self, query: str, max_queries: int = 3) -> List[str]:
        """
        Generate fallback subqueries when LLM generation fails.
        
        Args:
            query: Original query
            max_queries: Maximum number of subqueries to generate
        
        Returns:
            List of subquery strings
        """
        # Very basic query expansion with common research angles
        subqueries = [
            f"{query} definition",
            f"{query} examples",
            f"{query} advantages disadvantages",
            f"{query} recent developments",
            f"{query} history",
            f"{query} future trends",
            f"{query} applications"
        ]
        
        # Return at most max_queries unique subqueries
        used = set()
        result = []
        
        for sq in subqueries:
            if sq not in used and sq != query:
                used.add(sq)
                result.append(sq)
                if len(result) >= max_queries:
                    break
        
        return result
    
    def _analyze_path_relevance(self, original_query: str, current_query: str, 
                               parent_relevance: float = 0.0) -> float:
        """
        Analyze the relevance of a search path to the original query.
        
        Args:
            original_query: The original user query
            current_query: The current path's query
            parent_relevance: Relevance score of the parent path
        
        Returns:
            Relevance score between 0.0 and 1.0
        """
        # Use LLM if available for more accurate relevance analysis
        if self.llm:
            return self._analyze_llm_relevance(original_query, current_query, parent_relevance)
        
        # Fallback to simple keyword matching
        return self._analyze_keyword_relevance(original_query, current_query)
    
    def _analyze_llm_relevance(self, original_query: str, current_query: str, 
                              parent_relevance: float) -> float:
        """
        Use LLM to analyze the relevance of a query to the original query.
        
        Args:
            original_query: Original user query
            current_query: Current path's query
            parent_relevance: Parent path's relevance score
        
        Returns:
            Relevance score between 0.0 and 1.0
        """
        try:
            prompt = f"""Original query: "{original_query}"
            Current query being evaluated: "{current_query}"
            
            On a scale from 0.0 to 1.0, how relevant is the current query to the original query?
            Consider:
            - Is it a logical exploration path from the original query?
            - Does it add valuable depth or breadth to the research?
            - Is it specific enough to yield useful results?
            
            Return ONLY a single number between 0.0 and 1.0 representing the relevance score.
            """
            
            system_prompt = """You are an expert research assistant evaluating the relevance of potential 
            research paths. Your task is to analyze how relevant a potential subquery is to the original 
            research topic. Respond with ONLY a single number between 0.0 (completely irrelevant) and 
            1.0 (highly relevant)."""
            
            response = self.llm.generate_response(
                prompt=prompt,
                system_prompt=system_prompt,
                task_type="relevance_analysis",
                required_capabilities=["analytical"],
                model_tier=ModelTier.FAST  # Use faster model for this simple task
            )
            
            if response.error:
                logger.error(f"Error from LLM during relevance analysis: {response.error}")
                return self._analyze_keyword_relevance(original_query, current_query)
            
            try:
                # Extract the relevance score from the response
                text = response.content.strip()
                
                # Find a floating point number in the response
                import re
                match = re.search(r'(\d+\.\d+|\d+)', text)
                if match:
                    score = float(match.group(1))
                    # Ensure the score is between 0 and 1
                    score = max(0.0, min(1.0, score))
                    return score
                else:
                    logger.warning(f"Could not extract relevance score from: {text}")
                    return self._analyze_keyword_relevance(original_query, current_query)
            
            except ValueError:
                logger.error(f"Failed to parse relevance score: {response.content}")
                return self._analyze_keyword_relevance(original_query, current_query)
        
        except Exception as e:
            logger.error(f"Error in LLM relevance analysis: {str(e)}")
            return self._analyze_keyword_relevance(original_query, current_query)
    
    def _analyze_keyword_relevance(self, original_query: str, current_query: str) -> float:
        """
        Analyze relevance based on keyword matching.
        
        Args:
            original_query: Original user query
            current_query: Current path's query
        
        Returns:
            Relevance score between 0.0 and 1.0
        """
        # Simple relevance based on keyword overlap
        original_words = set(original_query.lower().split())
        current_words = set(current_query.lower().split())
        
        # Count shared words
        shared_words = original_words.intersection(current_words)
        
        # If current query is entirely contained in original query, high relevance
        if current_words.issubset(original_words):
            return 0.95
        
        # If original query is entirely contained in current query, good relevance
        if original_words.issubset(current_words):
            return 0.85
        
        # Otherwise base on overlap ratio
        if not original_words or not current_words:
            return 0.5
        
        overlap_ratio = len(shared_words) / max(len(original_words), len(current_words))
        return 0.5 + (overlap_ratio * 0.5)  # Scale to 0.5-1.0 range
    
    def _extract_insights_from_search_results(self, path: SearchPath, 
                                            search_results: List[Any]) -> None:
        """
        Extract key insights from search results.
        
        Args:
            path: The SearchPath being explored
            search_results: List of search result objects
        """
        # Skip if there are no results
        if not search_results:
            return
        
        # Extract snippets from search results
        snippets = []
        for result in search_results:
            if hasattr(result, 'snippet'):
                snippets.append(result.snippet)
        
        if not snippets:
            return
        
        try:
            # Use the detailed analyzer if available
            if self.detailed_analyzer:
                detailed_results = self.detailed_analyzer.analyze_content(snippets, path.query)
                
                for item in detailed_results.get('key_points', []):
                    path.add_key_insights([{
                        "insight": item,
                        "source": "detailed_analyzer",
                        "confidence": 0.8
                    }])
                
                return
            
            # Use LLM if available
            if self.llm:

                
                prompt = f"""Extract 3-5 key insights about "{path.query}" from these search results:
                
                {combined_content}
                
                For each insight, provide the insight itself and your confidence level (low, medium, or high).
                """
                
                system_prompt = """You are an expert research assistant. Extract the most important insights 
                from the provided search results. Focus on factual, specific information that directly relates 
                to the query. Identify patterns, key findings, and important details."""
                
                response = self.llm.generate_response(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    task_type="insight_extraction",
                    required_capabilities=["analytical", "precise"]
                )
                
                if response.error:
                    logger.error(f"Error from LLM during insight extraction: {response.error}")
                    return
                
                # Process the response to extract insights
                lines = response.content.strip().split('\n')
                insights = []
                
                current_insight = ""
                confidence = 0.7  # Default confidence
                
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    
                    # If line starts with a number or bullet, it's likely a new insight
                    if re.match(r'^(\d+[\.\):-]|\*|\-|\•)', line):
                        # Save the previous insight if it exists
                        if current_insight:
                            insights.append({
                                "insight": current_insight,
                                "source": "llm",
                                "confidence": confidence
                            })
                        
                        # Start a new insight
                        current_insight = re.sub(r'^(\d+[\.\):-]|\*|\-|\•)\s*', '', line)
                        confidence = 0.7  # Reset confidence
                        
                        # Look for confidence indicators
                        if "high confidence" in line.lower():
                            confidence = 0.9
                        elif "medium confidence" in line.lower():
                            confidence = 0.7
                        elif "low confidence" in line.lower():
                            confidence = 0.5
                    else:
                        # Continue the current insight
                        current_insight += " " + line
                        
                        # Update confidence if mentioned
                        if "high confidence" in line.lower():
                            confidence = 0.9
                        elif "medium confidence" in line.lower():
                            confidence = 0.7
                        elif "low confidence" in line.lower():
                            confidence = 0.5
                
                # Add the last insight
                if current_insight:
                    insights.append({
                        "insight": current_insight,
                        "source": "llm",
                        "confidence": confidence
                    })
                
                if insights:
                    path.add_key_insights(insights)
        
        except Exception as e:
            logger.error(f"Error extracting insights: {str(e)}")
    
    def _extract_key_findings(self, result: ResearchResult) -> None:
        """
        Extract key findings across all search paths.
        
        Args:
            result: The ResearchResult to update
        """
        # Collect all insights from all paths
        all_insights = []
        for path_id, path in result.paths.items():
            for insight in path.key_insights:
                all_insights.append({
                    "text": insight.get("insight", ""),
                    "confidence": insight.get("confidence", 0.5),
                    "source_path_id": path_id
                })
        
        # If we have detailed analyzer, use it for cross-path analysis
        if self.detailed_analyzer and all_insights:
            try:
                insights_text = "\n".join([i["text"] for i in all_insights])
                
                cross_path_analysis = self.detailed_analyzer.analyze_content(
                    [insights_text], 
                    result.original_query,
                    analysis_type="synthesis"
                )
                
                for finding in cross_path_analysis.get('key_findings', []):
                    # Look for supporting paths
                    supporting_paths = []
                    for insight in all_insights:
                        if self._is_related_to_finding(finding, insight["text"]):
                            supporting_paths.append(insight["source_path_id"])
                    
                    result.add_key_finding(
                        finding=finding,
                        confidence=0.8,
                        source_path_ids=supporting_paths or list(result.paths.keys())
                    )
                
                return
            except Exception as e:
                logger.error(f"Error in detailed analysis for key findings: {str(e)}")
        
        # Use LLM if available
        if self.llm and all_insights:
            try:
                # Prepare insights for the prompt
                insights_text = ""
                for idx, insight in enumerate(all_insights, 1):
                    confidence = "High" if insight["confidence"] >= 0.8 else "Medium" if insight["confidence"] >= 0.6 else "Low"
                    insights_text += f"{idx}. {insight['text']} (Confidence: {confidence})"
                
                prompt = f"""Based on these collected insights from multiple search paths about "{result.original_query}":
                
                {insights_text}
                
                Extract 5-7 key findings that represent the most important, well-supported information about the topic.
                Consolidate similar insights, identify patterns, and highlight well-supported conclusions.
                
                For each finding, provide:
                1. The finding itself (a clear, concise statement)
                2. Your confidence level (high, medium, or low)
                """
                
                system_prompt = """You are an expert research analyst. Your task is to synthesize insights from multiple 
                research paths into a coherent set of key findings. Focus on identifying the most important, well-supported 
                information. Combine similar insights, eliminate noise, and present a clear picture of what we know about 
                the topic with appropriate confidence levels."""
                
                response = self.llm.generate_response(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    task_type="finding_synthesis",
                    required_capabilities=["analytical", "precise", "synthesizing"]
                )
                
                if response.error:
                    logger.error(f"Error from LLM during finding synthesis: {response.error}")
                    # Fall back to using the top insights directly
                    self._fallback_key_findings(result, all_insights)
                    return
                
                # Process the response to extract findings
                lines = response.content.strip().split('\n')
                current_finding = ""
                confidence = 0.7  # Default confidence
                
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    
                    # If line starts with a number or bullet, it's likely a new finding
                    if re.match(r'^(\d+[\.\):-]|\*|\-|\•)', line):
                        # Save the previous finding if it exists
                        if current_finding:
                            # Find supporting paths
                            supporting_paths = []
                            for insight in all_insights:
                                if self._is_related_to_finding(current_finding, insight["text"]):
                                    supporting_paths.append(insight["source_path_id"])
                            
                            result.add_key_finding(
                                finding=current_finding,
                                confidence=confidence,
                                source_path_ids=supporting_paths or list(result.paths.keys())
                            )
                        
                        # Start a new finding
                        current_finding = re.sub(r'^(\d+[\.\):-]|\*|\-|\•)\s*', '', line)
                        confidence = 0.7  # Reset confidence
                        
                        # Look for confidence indicators
                        if "high confidence" in line.lower():
                            confidence = 0.9
                        elif "medium confidence" in line.lower():
                            confidence = 0.7
                        elif "low confidence" in line.lower():
                            confidence = 0.5
                    else:
                        # Continue the current finding
                        current_finding += " " + line
                        
                        # Update confidence if mentioned
                        if "high confidence" in line.lower():
                            confidence = 0.9
                        elif "medium confidence" in line.lower():
                            confidence = 0.7
                        elif "low confidence" in line.lower():
                            confidence = 0.5
                
                # Add the last finding
                if current_finding:
                    # Find supporting paths
                    supporting_paths = []
                    for insight in all_insights:
                        if self._is_related_to_finding(current_finding, insight["text"]):
                            supporting_paths.append(insight["source_path_id"])
                    
                    result.add_key_finding(
                        finding=current_finding,
                        confidence=confidence,
                        source_path_ids=supporting_paths or list(result.paths.keys())
                    )
                
                # If we couldn't extract any findings, fall back to top insights
                if not result.key_findings:
                    self._fallback_key_findings(result, all_insights)
            
            except Exception as e:
                logger.error(f"Error extracting key findings: {str(e)}")
                self._fallback_key_findings(result, all_insights)
        else:
            # If LLM is not available, use the top insights directly
            self._fallback_key_findings(result, all_insights)
    
    def _is_related_to_finding(self, finding: str, insight: str) -> bool:
        """
        Check if an insight is related to a finding.
        
        Args:
            finding: The finding text
            insight: The insight text
        
        Returns:
            True if related, False otherwise
        """
        # Simple implementation based on keyword overlap
        finding_words = set(finding.lower().split())
        insight_words = set(insight.lower().split())
        
        # Remove common stop words
        stop_words = {'a', 'an', 'the', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 
                     'and', 'or', 'but', 'if', 'then', 'else', 'when', 'at', 'from', 'by', 
                     'for', 'with', 'about', 'to', 'of', 'in', 'on', 'that', 'this', 'these', 
                     'those', 'it', 'its'}
        
        finding_words = finding_words - stop_words
        insight_words = insight_words - stop_words
        
        # If either is empty after removing stop words, they're not related
        if not finding_words or not insight_words:
            return False
        
        # Calculate overlap
        shared_words = finding_words.intersection(insight_words)
        overlap_ratio = len(shared_words) / min(len(finding_words), len(insight_words))
        
        # Consider related if significant overlap
        return overlap_ratio >= 0.3
    
    def _fallback_key_findings(self, result: ResearchResult, all_insights: List[Dict[str, Any]]) -> None:
        """
        Generate key findings using a simple fallback method.
        
        Args:
            result: The ResearchResult to update
            all_insights: List of all insights from all paths
        """
        # Sort insights by confidence
        sorted_insights = sorted(all_insights, key=lambda x: x.get("confidence", 0), reverse=True)
        
        # Take top insights
        used_insights = set()
        for insight in sorted_insights:
            # Skip if we already have similar insights
            insight_text = insight["text"].lower()
            if any(self._is_similar_text(insight_text, used) for used in used_insights):
                continue
            
            used_insights.add(insight_text)
            result.add_key_finding(
                finding=insight["text"],
                confidence=insight.get("confidence", 0.5),
                source_path_ids=[insight["source_path_id"]]
            )
            
            # Stop after a reasonable number of findings
            if len(result.key_findings) >= 7:
                break
    
    def _is_similar_text(self, text1: str, text2: str) -> bool:
        """
        Check if two texts are similar.
        
        Args:
            text1: First text
            text2: Second text
        
        Returns:
            True if similar, False otherwise
        """
        # Simple implementation based on word overlap
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        # Calculate Jaccard similarity
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        if union == 0:
            return False
        
        similarity = intersection / union
        return similarity > 0.6
    
    def _detect_contradictions(self, result: ResearchResult) -> None:
        """
        Detect contradictions across research paths.
        
        Args:
            result: The ResearchResult to update
        """
        # Skip if we don't have enough paths
        if len(result.paths) < 2:
            return
        
        # Collect key insights from all paths
        path_insights = {}
        for path_id, path in result.paths.items():
            if path.key_insights:
                path_insights[path_id] = [i.get("insight", "") for i in path.key_insights]
        
        # Skip if we don't have enough insights
        if len(path_insights) < 2:
            return
        
        # Use the LLM if available
        if self.llm:
            try:
                # Prepare insights by path for the prompt
                insights_text = ""
                for path_id, insights in path_insights.items():
                    path_query = result.paths[path_id].query
                    insights_text += f"Path Query: {path_query}\n"
                    for idx, insight in enumerate(insights, 1):
                        insights_text += f"- {insight}\n"
                    insights_text += "\n"
                
                prompt = f"""Analyze the following insights from different research paths about "{result.original_query}":
                
                {insights_text}
                
                Identify any contradictions between these insights. A contradiction exists when two or more insights 
                make opposing claims about the same aspect of the topic.
                
                For each contradiction you find, please provide:
                1. A brief description of the contradiction
                2. The specific conflicting claims
                3. The path queries where the contradiction appears
                
                If you don't find any significant contradictions, respond with "No significant contradictions found."
                """
                
                system_prompt = """You are an expert research analyst specializing in identifying inconsistencies 
                and contradictions. Your task is to carefully examine insights from different research paths and 
                identify any meaningful contradictions. Focus on substantive disagreements about facts or interpretations, 
                not minor differences in wording or emphasis."""
                
                response = self.llm.generate_response(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    task_type="contradiction_detection",
                    required_capabilities=["analytical", "precise", "critical"]
                )
                
                if response.error:
                    logger.error(f"Error from LLM during contradiction detection: {response.error}")
                    return
                
                # If no contradictions found, return
                if "no significant contradictions" in response.content.lower():
                    return
                
                # Process the response to extract contradictions
                contradiction_sections = re.split(r'\n\s*?\d+[\.\)]', response.content)
                
                for section in contradiction_sections:
                    if not section.strip():
                        continue
                    
                    # Extract description
                    description = section.strip().split('\n')[0].strip()
                    
                    # Extract conflicting claims
                    conflicting_claims = []
                    claims_section = re.search(r'conflicting claims:?\s*\n(.*?)(?:\n\s*path quer|$)', 
                                             section, re.DOTALL | re.IGNORECASE)
                    if claims_section:
                        claims_text = claims_section.group(1).strip()
                        claims = re.findall(r'[\-\*]\s*(.*?)(?:\n[\-\*]|$)', claims_text + '\n-', re.DOTALL)
                        conflicting_claims = [claim.strip() for claim in claims if claim.strip()]
                    
                    # Extract path queries/IDs
                    path_ids = []
                    for path_id, path in result.paths.items():
                        if path.query.lower() in section.lower():
                            path_ids.append(path_id)
                    
                    # If we couldn't find the paths directly, try to match based on insights
                    if not path_ids:
                        for path_id, insights in path_insights.items():
                            for insight in insights:
                                if insight.lower() in section.lower():
                                    path_ids.append(path_id)
                                    break
                    
                    # If we still don't have path IDs, include all paths
                    if not path_ids:
                        path_ids = list(path_insights.keys())
                    
                    # Add the contradiction if we have enough information
                    if description and conflicting_claims:
                        result.add_contradiction(
                            description=description,
                            conflicting_claims=conflicting_claims,
                            source_path_ids=path_ids
                        )
            
            except Exception as e:
                logger.error(f"Error detecting contradictions: {str(e)}")
