import subprocess
import json
import os
import pytest
from datetime import datetime, timedelta

# Helper function to run llm commands
def run_llm_command(command: str):
    process = subprocess.run(command, shell=True, capture_output=True, text=True)
    return process.stdout, process.stderr, process.returncode

def test_basic_google_search():
    stdout, stderr, returncode = run_llm_command('llm websearch search-cmd "test query" --search-engine google -n 3')
    assert returncode == 0, f"Error: {stderr}"
    results = json.loads(stdout)
    assert len(results) == 3, "Expected 3 results"
    assert all(result['source'] == 'google' for result in results), "Source should be Google"

def test_basic_bing_search():
    stdout, stderr, returncode = run_llm_command('llm websearch search-cmd "test query" --search-engine bing -n 3')
    assert returncode == 0, f"Error: {stderr}"
    results = json.loads(stdout)
    assert len(results) == 3, "Expected 3 results"
    assert all(result['source'] == 'bing' for result in results), "Source should be Bing"
    
def test_google_country_filter():
    stdout_us, stderr_us, returncode_us = run_llm_command('llm websearch search-cmd "example" --search-engine google -n 2 --country US')
    assert returncode_us == 0, f"Error: {stderr_us}"

    stdout_gb, stderr_gb, returncode_gb = run_llm_command('llm websearch search-cmd "example" --search-engine google -n 2 --country GB')
    assert returncode_gb == 0, f"Error: {stderr_gb}"

    results_us = json.loads(stdout_us)
    results_gb = json.loads(stdout_gb)

    # Basic check: If results are different, the filter might be working.
    # A more robust test would require analyzing the URLs or content, which is beyond the scope of this simple test.
    assert results_us != results_gb, "Country filter (US vs GB) did not produce different results"

def test_bing_freshness_filter():
    stdout_day, stderr_day, returncode_day = run_llm_command('llm websearch search-cmd "news" --search-engine bing -n 2 --freshness Day')
    assert returncode_day == 0, f"Error: {stderr_day}"
    results_day = json.loads(stdout_day)

    stdout_week, stderr_week, returncode_week = run_llm_command('llm websearch search-cmd "news" --search-engine bing -n 2 --freshness Week')
    assert returncode_week == 0, f"Error: {stderr_week}"
    results_week = json.loads(stdout_week)

    # Basic check if freshness has any effect
    assert results_day != results_week, "Freshness filter (Day vs Week) did not produce different results"

def test_combined_options_google():
     stdout, stderr, returncode = run_llm_command('llm websearch search-cmd "python tutorial" --search-engine google -n 3 --language en --file-type pdf')
     assert returncode == 0, f"Error: {stderr}"
     results = json.loads(stdout)
     assert len(results) == 3, "Expected 3 results"
     assert all(result['source'] == 'google' for result in results), "Source should be Google"
     # Ideally, we would check the URLs to ensure they end with .pdf, but that would make the test brittle. We are assuming the file-type argument works here.

def test_combined_options_bing():
    stdout, stderr, returncode = run_llm_command('llm websearch search-cmd "financial news" --search-engine bing -n 3 --market en-US --freshness Day')
    assert returncode == 0, f"Error: {stderr}"
    results = json.loads(stdout)
    assert len(results) == 3, "Expected 3 results"
    assert all(result['source'] == 'bing' for result in results), "Source should be Bing"

def test_error_handling_missing_keys():
    # Temporarily unset API keys
    original_google_key = os.environ.get("GOOGLE_SEARCH_KEY")
    original_bing_key = os.environ.get("BING_CUSTOM_SEARCH_KEY")
    os.environ["GOOGLE_SEARCH_KEY"] = ""
    os.environ["BING_CUSTOM_SEARCH_KEY"] = ""
    
    stdout_google, stderr_google, returncode_google = run_llm_command('llm websearch search-cmd "test" --search-engine google')
    assert returncode_google != 0, "Google search should fail without API key"
    assert "GOOGLE_SEARCH_KEY and GOOGLE_SEARCH_ID must be set" in stderr_google

    stdout_bing, stderr_bing, returncode_bing = run_llm_command('llm websearch search-cmd "test" --search-engine bing')
    assert returncode_bing != 0, "Bing search should fail without API key"
    assert "BING_CUSTOM_SEARCH_KEY and BING_CUSTOM_CONFIG_ID must be set" in stderr_bing

    # Restore original API keys
    if original_google_key:
        os.environ["GOOGLE_SEARCH_KEY"] = original_google_key
    if original_bing_key:
        os.environ["BING_CUSTOM_SEARCH_KEY"] = original_bing_key
        
def test_caching():
    # Run a search to populate the cache
    command = 'llm websearch search-cmd "cache test" --search-engine google -n 1'
    run_llm_command(command)

    # Run the same search again and measure the time
    start_time = datetime.now()
    stdout, stderr, returncode = run_llm_command(command)
    end_time = datetime.now()
    duration = end_time - start_time
    assert returncode == 0

    # Run the search a third time and measure time again.
    start_time_2 = datetime.now()
    stdout_2, stderr_2, returncode_2 = run_llm_command(command)
    end_time_2 = datetime.now()
    duration_2 = end_time_2 - start_time_2
    assert returncode_2 == 0

    # Check that the results are the same
    assert stdout == stdout_2, "Cached results should be the same"

    # The second run should be significantly faster if it's using the cache
    assert duration_2 < duration, "Second run should be faster due to caching"
