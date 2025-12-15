from agents.smart_waiter_agent import SmartWaiterAgent
import uuid
import time

def verify_refinements():
    print("--- Verifying Refinements 1-6 ---")
    agent = SmartWaiterAgent()
    session_id = f"test-refine-{str(uuid.uuid4())[:4]}"
    print(f"Session: {session_id}")
    
    # 1. Onboarding Text Check
    print("\n[Step 1: Onboarding Welcome]")
    res1 = agent.run("Hi", session_id=session_id)
    print(f"[Agent]: {res1}")
    if "Hi, Welcome to Evolution Restaurant! Am Smart-Waiter" in res1:
        print(">>> SUCCESS: Welcome text matches.")
    else:
        print(">>> FAIL: Welcome text incorrect.")

    # 2. Mode Response Check
    print("\n[Step 2: Mode Selection]")
    agent.run("English", session_id=session_id) # Lang
    res2 = agent.run("Message", session_id=session_id) # Mode
    print(f"[Agent]: {res2}")
    if "Welcome once again! What can I get for you" in res2:
        print(">>> SUCCESS: Mode response matches.")
    else:
        print(">>> FAIL: Mode response incorrect.")

    # 3. Menu Logic Check
    print("\n[Step 3: Menu Intent]")
    res3 = agent.run("Would you like to see our menu?", session_id=session_id)
    if "MENU:" in res3:
        print(">>> SUCCESS: 'See menu' trigger works.")
    else:
        print(f">>> FAIL: Menu not shown. Got: {res3[:50]}...")
        
    # 4. Ordering
    print("\n[Step 4: Ordering]")
    res4 = agent.run("Get me a Coke (Small)", session_id=session_id)
    print(f"[Agent]: {res4}")
    
    # 5. Payment Proceed Check
    print("\n[Step 5: Payment Proceed]")
    res5 = agent.run("Proceed", session_id=session_id)
    print(f"[Agent]: {res5}")
    if "Cash, Card/POS or Transfer" in res5:
        print(">>> SUCCESS: 'Proceed' triggered payment method selection.")
    else:
        print(">>> FAIL: 'Proceed' did not trigger payment.")
        
    # 6. HITL Verification Check
    print("\n[Step 6: HITL & Transfer]")
    agent.run("Transfer", session_id=session_id) # Ask method -> Processing
    res6 = agent.run("Done", session_id=session_id) # Paid -> Verifying
    print(f"[Agent]: {res6}")
    
    if "Waiting for verification" in res6:
        print(">>> SUCCESS: Entered HITL state (Waiting).")
    else:
        print(">>> FAIL: Did not enter waiting state.")

    # Simulate Admin Verification
    print("\n[Step 7: Admin Verify]")
    res7 = agent.run("Verified", session_id=session_id)
    print(f"[Agent]: {res7}")
    if "Payment confirmed" in res7:
        print(">>> SUCCESS: Admin verification confirmed payment.")
    else:
        print(">>> FAIL: Verification failed.")

    # 7. Post-Dining Feedback Check
    print("\n[Step 8: Post-Dining Feedback]")
    agent.run("Eat in", session_id=session_id) # Disposition -> Serving
    
    # Simulate time pass / check status
    print("(Simulating 5 mins / Checking status)")
    res8 = agent.run("Any update?", session_id=session_id) 
    print(f"[Agent]: {res8}")
    
    if "Have you received your order" in res8:
        print(">>> SUCCESS: Agent asked if served.")
    else:
         print(">>> FAIL: Agent did not ask if served.")

    res9 = agent.run("Received", session_id=session_id) # Confirm Received
    print(f"[Agent]: {res9}")
    if "feedback" in res9.lower():
         print(">>> SUCCESS: Agent asked for feedback.")
    else:
         print(">>> FAIL: Agent did not ask for feedback.")
         
    res10 = agent.run("The food was amazing", session_id=session_id)
    print(f"[Agent]: {res10}")
    if "Thank you" in res10:
        print(">>> SUCCESS: Final thank you received.")

if __name__ == "__main__":
    verify_refinements()
