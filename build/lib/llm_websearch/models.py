"""Data models (Pydantic) and custom exceptions for llm_websearch."""

import json
import uuid
import logging 
from datetime import datetime
from pydantic import BaseModel, Field, HttpUrl, ValidationError, confloat, field_validator, field_serializer
from typing import List, Optional, Dict, Any, Union, Type

logger = logging.getLogger(__name__)

# === Custom Exceptions ===
class WebSearchError(Exception): """Base exception."""; pass
class ConfigError(WebSearchError): """Config error."""; pass
class SearchEngineError(WebSearchError): 
    """Search engine API error."""
    def __init__(self, engine: str, query: str, status_code: Optional[int] = None, message: Optional[str] = None, original_exception: Optional[Exception] = None):
        self.engine=engine; self.query=query; self.status_code=status_code; self.original_exception=original_exception
        self.message = message or f"Search Engine '{engine}' failed query '{query}'"
        super().__init__(self.message)
class LLMError(WebSearchError): 
    """LLM interaction error."""
    def __init__(self, model: str, prompt: Optional[str] = None, message: Optional[str] = None, original_exception: Optional[Exception] = None):
        self.model=model; self.prompt=prompt; self.original_exception=original_exception
        self.message = message or f"LLM '{model}' failed."
        super().__init__(self.message)
class ParsingError(WebSearchError): """Parsing error."""; pass
class ContentProcessingError(WebSearchError): """Content processing error."""; pass

# === Core Data Models ===
class SearchResult(BaseModel):
    """A single search result."""
    title: str; url: Union[HttpUrl, str]
    snippet: Optional[str] = None; query: Optional[str] = None; engine: Optional[str] = None
    raw_content: Optional[str] = Field(None, exclude=True)
    processed_content: Optional[str] = None
    relevance_score: Optional[confloat(ge=0.0, le=1.0)] = None
    key_points: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    @field_validator('url', mode='before')
    def check_url_scheme(cls, v): return v

class SearchPath(BaseModel):
    """Node in the exploration tree."""
    path_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    query: str; parent_path_id: Optional[str] = None
    child_path_ids: List[str] = Field(default_factory=list)
    search_results: List[SearchResult] = Field(default_factory=list)
    relevance_score: confloat(ge=0.0, le=1.0) = 0.0
    has_been_explored: bool = False
    key_insights: List[Dict[str, Any]] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    depth: int = 0

class ExplorationMetrics(BaseModel):
    """Deep research session metrics."""
    start_time: datetime; end_time: Optional[datetime] = None
    total_paths_explored: int = 0; max_depth_reached: int = 0
    total_search_results_collected: int = 0
    total_llm_calls: int = 0; total_tokens_used: int = 0
    exploration_parameters: Dict[str, Any] = Field(default_factory=dict)
    @field_serializer('start_time', 'end_time', when_used='json')
    def serialize_dt(self, dt: Optional[datetime]): return dt.isoformat() if dt else None

class ResearchResult(BaseModel):
    """Complete deep research result."""
    original_query: str; root_path_id: Optional[str] = None
    paths: Dict[str, SearchPath] = Field(default_factory=dict)
    key_findings: List[Dict[str, Any]] = Field(default_factory=list)
    contradictions: List[Dict[str, Any]] = Field(default_factory=list)
    tiered_summaries: Dict[str, str] = Field(default_factory=dict)
    key_insights_summary: List[str] = Field(default_factory=list)
    exploration_metrics: Optional[ExplorationMetrics] = None
    status: str = "Initialized"; error_message: Optional[str] = None

# === LLM Interaction Models ===
class LLMResponse(BaseModel):
    """Standardized LLM response."""
    raw_text: str; model_name: str
    prompt_used: Optional[str] = Field(None, exclude=True)
    parsed_data: Optional[Any] = None; tokens_used: Optional[int] = None
    finish_reason: Optional[str] = None

# --- Structured LLM Output Models --- 
class SubqueryList(BaseModel): """LLM output for subqueries."""; subqueries: List[str] = Field(..., min_length=1)
class RelevanceScore(BaseModel): """LLM output for relevance."""; score: confloat(ge=0.0, le=1.0); reasoning: Optional[str] = None
class InsightItem(BaseModel): """LLM insight item."""; insight: str; confidence: confloat(ge=0.0, le=1.0)
class InsightList(BaseModel): """LLM insights list."""; insights: List[InsightItem]
class FindingItem(BaseModel): """LLM finding item."""; finding: str; confidence: confloat(ge=0.0, le=1.0)
class FindingList(BaseModel): """LLM findings list."""; findings: List[FindingItem]
class ContradictionItem(BaseModel): """LLM contradiction item."""; description: str; conflicting_claims: List[str]; source_path_ids: List[str]
class ContradictionList(BaseModel): """LLM contradictions list."""; contradictions: List[ContradictionItem]
class ThemeList(BaseModel): """LLM themes list."""; themes: List[str] = Field(...)

# --- JSON Parsing/Validation --- 
def safe_json_loads(text: str) -> Optional[Union[Dict[str, Any], List[Any]]]:
    """Safely loads JSON, cleaning common LLM artifacts."""
    text = text.strip()
    if text.startswith("```json") and text.endswith("```"): text = text[7:-3].strip()
    elif text.startswith("```") and text.endswith("```"): text = text[3:-3].strip()
    try: return json.loads(text)
    except json.JSONDecodeError: logger.warning(f"JSON decode failed. Preview: {text[:100]}..."); return None

def validate_llm_json(raw_json_text: str, model_class: Type[BaseModel]) -> BaseModel:
    """Parses and validates JSON against a Pydantic model."""
    parsed = safe_json_loads(raw_json_text)
    if parsed is None:
        preview = raw_json_text.strip()[:200];dots='...' if len(raw_json_text.strip())>200 else ''
        raise ParsingError(f"Failed JSON decode. Preview: '{preview}{dots}'")
    try: return model_class.model_validate(parsed)
    except ValidationError as e: raise ParsingError(f"Validation fail {model_class.__name__}. Err: {e.errors()}. Data: {parsed}") from e
