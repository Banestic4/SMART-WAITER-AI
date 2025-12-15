import sys
import os
import time

# Add root to path
sys.path.append(os.path.dirname(__file__))

from agents.smart_waiter_agent import SmartWaiterAgent
from tools import kitchen_ops

def test_flow():
    print("Initializing Agent...")
    agent = SmartWaiterAgent()
    session_id = "test_verify_session_" + str(int(time.time()))
    
    print(f"Session ID: {session_id}")
    
    print("\n[0] Onboarding...")
    resp = agent.run("English", session_id=session_id)
    print(f"Agent: {resp}")
    
    print("\n[0.1] Mode Selection...")
    resp = agent.run("Message", session_id=session_id)
    print(f"Agent: {resp}")
    
    print("\n[0.2] Table Number...")
    resp = agent.run("5", session_id=session_id)
    print(f"Agent: {resp}")

    # 1. Order
    print("\n[1] Ordering Rice...")
    resp = agent.run("I want to order 2 Jollof Rice", session_id=session_id)
    print(f"Agent: {resp}")
    
    # 2. Confirm Order (if needed)
    print("\n[2] Confirming...")
    resp = agent.run("That is all. I want to pay.", session_id=session_id)
    print(f"Agent: {resp}")
    
    # 3. Pay via Transfer
    print("\n[3] Selecting Transfer...")
    resp = agent.run("I will pay via transfer", session_id=session_id)
    print(f"Agent: {resp}")
    
    # 4. Provide Details
    print("\n[4] Providing Details...")
    resp = agent.run("John Doe 5000", session_id=session_id)
    print(f"Agent: {resp}")
    
    if "Waiting for verification" not in resp:
        print("FAILED: Did not detect 'Waiting for verification' state.")
        return
        
    # 5. Admin Verify
    print("\n[5] Admin Verifying...")
    resp = agent.run("Admin: verified", session_id=session_id)
    print(f"Agent: {resp}")
    
    if "Payment confirmed" not in resp:
        print("FAILED: Payment verification failed.")
        return

    # 6. Delivery Disposition
    print("\n[6] Choosing Delivery...")
    resp = agent.run("Please deliver it to my house", session_id=session_id)
    print(f"Agent: {resp}")
    
    if "arrange for delivery" not in resp.lower():
        print("FAILED: Did not detect delivery confirmation.")
        # Continue to check DB anyway
        
    # 7. Check DB
    print("\n[7] Checking Kitchen Ticket...")
    # Find order ID from Agent state or just query last ticket
    from storage import db
    rows = db.execute_query("SELECT * FROM kitchen_tickets ORDER BY created_at DESC LIMIT 1")
    if not rows:
        print("FAILED: No ticket found.")
    else:
        ticket = rows[0]
        print(f"Ticket Found: ID={ticket['ticket_id']}, Status={ticket['status']}, Notes={ticket['notes']}")
        
        if ticket['notes'] == 'Delivery':
             print("SUCCESS: Delivery note found!")
        else:
             print(f"WARNING: Note mismatch. Expected 'Delivery', got '{ticket['notes']}'")

if __name__ == "__main__":
    test_flow()
