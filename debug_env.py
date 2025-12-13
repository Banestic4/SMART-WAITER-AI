import sys
import os

print(f"Python Executable: {sys.executable}")
print(f"Python Version: {sys.version}")
print("System Path:")
for p in sys.path:
    print(f" - {p}")

print("\nAttempting import...")
try:
    import langchain_core
    print(f"SUCCESS: langchain_core imported from {langchain_core.__file__}")
except ImportError as e:
    print(f"FAILURE: {e}")
    
try:
    import pkg_resources
    # print installed packages as seen by this python
    # print([p.project_name for p in pkg_resources.working_set]) 
    pass
except:
    pass
