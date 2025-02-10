"""Tests for the detailed analysis module."""

import pytest
from datetime import datetime
from llm_search.detailed_analysis import DetailedAnalyzer, DetailedAnalysis, ContentMetadata

def test_analyzer_initialization():
    """Test DetailedAnalyzer initialization"""
    analyzer = DetailedAnalyzer(relevance_threshold=0.8)
    assert analyzer.relevance_threshold == 0.8
    assert analyzer.max_workers == 4

def test_metadata_extraction():
    """Test content metadata extraction"""
    analyzer = DetailedAnalyzer()
    content = "This is a test content for metadata extraction."
    metadata = analyzer.extract_metadata(content)
    
    assert isinstance(metadata, ContentMetadata)
    assert metadata.word_count == 8
    assert isinstance(metadata.date_detected, datetime)
    assert metadata.language == "en"
    assert 0 <= metadata.quality_score <= 1

def test_key_points_extraction():
    """Test key points extraction"""
    analyzer = DetailedAnalyzer()
    content = "First key point. Second important point. Third relevant point. Extra info."
    points = analyzer.extract_key_points(content)
    
    assert len(points) == 3
    assert "First key point" in points[0]
    assert "Second important point" in points[1]
    assert "Third relevant point" in points[2]

def test_citations_extraction():
    """Test citations extraction"""
    analyzer = DetailedAnalyzer()
    content = "This is a test content with a potential citation."
    citations = analyzer.extract_citations(content)
    
    assert isinstance(citations, list)
    assert len(citations) > 0
    assert "text" in citations[0]
    assert "source" in citations[0]

def test_relevance_calculation():
    """Test relevance score calculation"""
    analyzer = DetailedAnalyzer()
    content = "Python is a great programming language for data analysis"
    query = "python programming"
    
    score = analyzer.calculate_relevance(content, query)
    assert 0 <= score <= 1
    assert score > 0.5  # Should be relevant for this query

def test_single_content_analysis():
    """Test analysis of single content piece"""
    analyzer = DetailedAnalyzer()
    content = "Python is great for data analysis and machine learning"
    query = "python data analysis"
    
    result = analyzer.analyze_content(content, query)
    assert isinstance(result, DetailedAnalysis)
    assert result.content == content
    assert result.relevance_score >= 0.7
    assert len(result.key_points) > 0
    assert len(result.citations) > 0
    assert result.analysis_time > 0

def test_batch_analysis():
    """Test parallel batch analysis"""
    analyzer = DetailedAnalyzer()
    contents = [
        "Python is great for data analysis",
        "Weather is sunny today",
        "Machine learning with Python",
        "Random unrelated content"
    ]
    query = "python data analysis"
    
    results = analyzer.analyze_batch(contents, query)
    assert len(results) > 0
    assert all(isinstance(r, DetailedAnalysis) for r in results)
    assert all(r.relevance_score >= analyzer.relevance_threshold for r in results)

def test_batch_analysis_timeout():
    """Test batch analysis timeout handling"""
    analyzer = DetailedAnalyzer()
    contents = ["Test content"] * 100  # Large batch
    query = "test"
    
    with pytest.raises(TimeoutError):
        analyzer.analyze_batch(contents, query, timeout=0.001)

def test_irrelevant_content_filtering():
    """Test filtering of irrelevant content"""
    analyzer = DetailedAnalyzer(relevance_threshold=0.8)
    content = "This is completely unrelated content"
    query = "python data analysis"
    
    result = analyzer.analyze_content(content, query)
    assert result.relevance_score < analyzer.relevance_threshold
