from agents.smart_waiter_agent import SmartWaiterAgent
import uuid

def verify_payment_fix():
    print("--- Verifying Payment Fix ---")
    agent = SmartWaiterAgent()
    session_id = f"test-pay-{str(uuid.uuid4())[:4]}"
    print(f"Session: {session_id}")
    
    # 1. Order Coke
    print("\n[User]: Get me a coke")
    res = agent.run("Get me a coke", session_id=session_id)
    print(f"[Agent]: {res}")
    
    if "Added 1x Coke" in res or "Added 1x" in res:
        print(">>> Order placed successfully.")
    else:
        print(">>> FAILED to place order.")
        return

    # 2. Pay
    print("\n[User]: I want to pay")
    res = agent.run("I want to pay", session_id=session_id)
    print(f"[Agent]: {res}")
    
    if "confirm payment" in res.lower():
        print(">>> SUCCESS: Agent found order and asked for confirmation.")
    elif "can't find" in res:
        print(">>> FAILURE: Agent still cannot find order.")
    else:
        print(f">>> UNKNOWN Response: {res}")

if __name__ == "__main__":
    verify_payment_fix()
