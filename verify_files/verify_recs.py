from agents.smart_waiter_agent import SmartWaiterAgent

def verify_recs_feedback():
    agent = SmartWaiterAgent()
    session_id = "table-recs-test"
    
    print("--- Testing Recommendations & Feedback ---")
    
    # 1. Order Burger (Expect Upsell)
    print("\n[User]: I'll have a classic burger.")
    res = agent.run("I'll have a classic burger.", session_id=session_id)
    print(f"[Agent]: {res}")
    
    # Check if response contains "drink" or "fries" recommendation
    if "fries" in res.lower() or "drink" in res.lower():
        print(">>> SUCCESS: Upsell triggered.")
    else:
        print(">>> FAILURE: No upsell.")
            
    # 2. Leave Feedback
    print("\n[User]: The burger was great!")
    res = agent.run("The burger was great!", session_id=session_id)
    print(f"[Agent]: {res}")
    
    # 3. Explicit Feedback Intent
    print("\n[User]: I want to verify the previous intent was FEEDBACK.")
    
if __name__ == "__main__":
    verify_recs_feedback()
