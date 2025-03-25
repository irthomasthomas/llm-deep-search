import subprocess
import sys

def run_command(command):
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    output, error = process.communicate()
    return output.decode('utf-8'), error.decode('utf-8'), process.returncode

def test_search():
    print("Testing search command...")
    output, error, returncode = run_command("llm websearch search 'Python programming'")
    print(f"Output: {output}")
    print(f"Error: {error}")
    print(f"Return code: {returncode}")
    assert returncode == 0, "Search command failed"
    assert "Title:" in output, "Search results not found in output"

def test_deep_search():
    print("Testing deep-search command...")
    output, error, returncode = run_command("llm websearch deep-search 'Climate change'")
    print(f"Output: {output}")
    print(f"Error: {error}")
    print(f"Return code: {returncode}")
    assert returncode == 0, "Deep-search command failed"
    assert "Analysis:" in output, "Analysis not found in output"

if __name__ == "__main__":
    test_search()
    test_deep_search()
    print("All tests passed successfully!")

