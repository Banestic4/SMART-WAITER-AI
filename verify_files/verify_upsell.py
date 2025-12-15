from agents.smart_waiter_agent import SmartWaiterAgent
import uuid

def verify_upsell():
    print("--- Verifying Menu Update & Protein Upsell ---")
    agent = SmartWaiterAgent()
    session_id = f"test-upsell-{str(uuid.uuid4())[:4]}"
    print(f"Session: {session_id}")
    
    # 1. Onboarding
    print("\n[Step 1: Onboarding]")
    agent.run("English", session_id=session_id)
    agent.run("Message", session_id=session_id)
    
    # 2. Main Dish Order (Should Trigger Upsell)
    print("\n[Step 2: Order Jollof Rice (Expect Protein Upsell)]")
    res = agent.run("Get me Jollof Rice", session_id=session_id)
    print(f"[Agent]: {res}")
    
    if "meat or fish" in res.lower() and "1. Beef" in res:
        print(">>> SUCCESS: Protein Upsell triggered with numbered list.")
    else:
        print(">>> FAIL: Did not trigger Protein Upsell correctly.")

    # 3. Drink Order (Should NOT Trigger Protein Upsell, but standard rec)
    print("\n[Step 3: Order Coke (Expect Standard Rec)]")
    res = agent.run("Get me a Coke", session_id=session_id)
    print(f"[Agent]: {res}")
    
    if "meat or fish" in res.lower():
        print(">>> FAIL: Started Protein Upsell for a Drink!")
    else:
        print(">>> SUCCESS: Standard flow for Drinks.")

if __name__ == "__main__":
    verify_upsell()
