from agents.smart_waiter_agent import SmartWaiterAgent
from tools.llm_manager import RotatingGroqLLM
import uuid

def verify_wrapper():
    print("--- Verifying Rotating LLM Wrapper ---")
    
    # 1. Initialize Agent
    try:
        agent = SmartWaiterAgent()
        print(">>> Agent Initialized Successfully.")
    except Exception as e:
        print(f">>> FAIL: Agent Init failed: {e}")
        return

    # 2. Check Wrapper Internals
    if isinstance(agent._llm, RotatingGroqLLM):
        print(">>> SUCCESS: Agent is using RotatingGroqLLM.")
    else:
        print(f">>> FAIL: Agent is using {type(agent._llm)}")
        
    # 3. Simple Run (Transparency Test)
    session_id = f"test-rot-{str(uuid.uuid4())[:4]}"
    print(f"\nRunning Session: {session_id}")
    
    res = agent.run("Hi", session_id=session_id)
    print(f"[Agent]: {res}")
    
    if res and "Error" not in res:
        print(">>> SUCCESS: Wrapper correctly proxies invoke calls.")
    else:
        print(">>> FAIL: Wrapper failed usage.")

if __name__ == "__main__":
    verify_wrapper()
