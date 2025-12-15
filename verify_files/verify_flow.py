from agents.smart_waiter_agent import SmartWaiterAgent
import os

print("--- Testing Smart Waiter Agent Flow ---")
try:
    # Use mock simple implementation if dependencies missing, 
    # but strictly we are testing the graph logic here.
    agent = SmartWaiterAgent()
    
    print("\n[User]: I'll take a classic burger and a coke.")
    # Assuming config has valid Key or we mocked it in agent init if needed.
    # We rely on previous steps providing valid env.
    
    response = agent.run("I'll take a classic burger and a coke.", session_id="table-1")
    print(f"[Agent]: {response}")
    
    print("\n[User]: Actually, make that 2 burgers.")
    response = agent.run("Actually, make that 2 burgers.", session_id="table-1")
    print(f"[Agent]: {response}")
    
except Exception as e:
    print(f"Agent Execution Failed: {e}")
