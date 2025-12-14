from agents.smart_waiter_agent import SmartWaiterAgent
import uuid

def verify_enhanced_flow():
    print("--- Verifying Enhanced Interaction & Payment ---")
    agent = SmartWaiterAgent()
    session_id = f"test-enhanced-{str(uuid.uuid4())[:4]}"
    print(f"Session: {session_id}")
    
    # 1. Onboarding
    print("\n[Step 1: Onboarding]")
    res = agent.run("Hello", session_id=session_id)
    print(f"[Agent]: {res}")
    if "preferred language" not in res.lower() and "select" not in res.lower():
        print(">>> FAIL: Did not ask for language.")
        return
        
    res = agent.run("I prefer English", session_id=session_id)
    print(f"[Agent]: {res}")
    if "voice or message" not in res.lower():
        print(">>> FAIL: Did not ask for mode.")
        return
        
    res = agent.run("Message", session_id=session_id)
    print(f"[Agent]: {res}")
    
    # 2. Menu
    print("\n[Step 2: Menu Request]")
    res = agent.run("Show me the menu", session_id=session_id)
    print(f"[Agent]: {res}")
    if "-" not in res and "₦" not in res:
         print(">>> WARNING: Menu formatting might be off (expected bullets and prices).")

    # 3. Order
    print("\n[Step 3: Ordering]")
    res = agent.run("Get me a Coke", session_id=session_id)
    print(f"[Agent]: {res}")
    
    # 4. Payment - Ask Method
    print("\n[Step 4: Payment - Init]")
    res = agent.run("I want to pay", session_id=session_id)
    print(f"[Agent]: {res}")
    if "Card, Cash, or Transfer" not in res:
        print(">>> FAIL: Did not offer payment methods.")
        return
        
    # 5. Payment - Transfer Flow
    print("\n[Step 5: Payment - Transfer]")
    res = agent.run("I will do a transfer", session_id=session_id)
    print(f"[Agent]: {res}")
    if "First Bank" not in res:
        print(">>> FAIL: Did not show bank details.")
        return
        
    # 6. Payment - Confirmation
    print("\n[Step 6: Payment - Done]")
    res = agent.run("Done", session_id=session_id)
    print(f"[Agent]: {res}")
    if "eating here or taking it away" not in res.lower():
        print(">>> FAIL: Did not ask disposition.")
        return
        
    # 7. Finalize
    print("\n[Step 7: Disposition]")
    res = agent.run("Eat in", session_id=session_id)
    print(f"[Agent]: {res}")
    if "have a seat" not in res.lower():
        print(">>> FAIL: Final response incorrect.")
        return

    print("\n>>> SUCCESS: All enhanced flows verified.")

if __name__ == "__main__":
    verify_enhanced_flow()
