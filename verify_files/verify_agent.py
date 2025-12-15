import os
import sys

# Ensure we can import from the root
sys.path.append(os.getcwd())

try:
    from agents.smart_waiter_agent import SmartWaiterAgent
    from config import Config
    
    # Mock API Key if missing for test
    if not os.getenv("GROQ_API_KEY"):
         print("WARNING: No GROQ_API_KEY found. Mocking for import test.")
    
    print("Successfully imported SmartWaiterAgent")
    
except Exception as e:
    print(f"Failed to import: {e}")
