"""Tests for the caching system."""

import pytest
import time
from datetime import datetime, timedelta
import tempfile
from pathlib import Path
import pickle
import threading
from llm_search.cache import SearchCache, CacheEntry

@pytest.fixture
def cache():
    """Create a temporary cache for testing"""
    with tempfile.TemporaryDirectory() as temp_dir:
        cache = SearchCache(
            cache_dir=temp_dir,
            default_ttl=3600,
            max_entries=100,
            persist=True
        )
        yield cache

def test_thread_safety(cache):
    """Test thread safety of cache operations"""
    results = {'success': True}
    lock = threading.Lock()
    
    def worker(tid, cache):
        try:
            for i in range(50):  # Reduced iterations for faster test
                key = f"key_{tid}_{i}"
                value = f"value_{tid}_{i}"
                
                # Test set operation
                cache.set(key, value)
                assert cache.get(key) == value
                
                # Test invalidate operation
                if i % 2 == 0:
                    cache.invalidate(key)
                    assert cache.get(key) is None
                
                # Small delay to increase chance of thread interleaving
                time.sleep(0.001)
        except Exception as e:
            with lock:
                results['success'] = False
                print(f"Thread {tid} failed: {str(e)}")
    
    # Create and start threads
    threads = []
    for i in range(4):
        t = threading.Thread(target=worker, args=(i, cache))
        threads.append(t)
        t.start()
    
    # Wait for all threads to complete
    for t in threads:
        t.join()
    
    assert results['success'], "Thread safety test failed"
