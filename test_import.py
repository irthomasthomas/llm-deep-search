import importlib
import sys

print("Python version:", sys.version)
print("Python path:", sys.path)

try:
    import llm_websearch
    print("Successfully imported llm_websearch")
    print("llm_websearch file:", llm_websearch.__file__)
    
    if hasattr(llm_websearch, 'register_commands'):
        print("register_commands function found")
    else:
        print("register_commands function not found")
    
    if hasattr(llm_websearch, 'search'):
        print("search function found")
    else:
        print("search function not found")
    
    if hasattr(llm_websearch, 'deep_search'):
        print("deep_search function found")
    else:
        print("deep_search function not found")

except ImportError as e:
    print(f"Failed to import llm_websearch: {e}")
    
    # Try to find the module
    spec = importlib.util.find_spec("llm_websearch")
    if spec is not None:
        print(f"Module found at: {spec.origin}")
    else:
        print("Module not found in sys.path")

