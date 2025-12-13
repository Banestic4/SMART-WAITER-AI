from agents.smart_waiter_agent import SmartWaiterAgent
from config import Config
import time

def verify_fulfillment():
    agent = SmartWaiterAgent()
    session_id = "table-kitchen-test"
    
    print("--- Testing Kitchen Flow ---")
    
    # 1. Order
    print("\n[User]: I'll have a classic burger.")
    res = agent.run("I'll have a classic burger.", session_id=session_id)
    print(f"[Agent]: {res}")

    # 2. Pay (Trigger Kitchen)
    print("\n[User]: Check please.")
    res = agent.run("Check please.", session_id=session_id)
    print(f"[Agent]: {res}")
    
    print("\n[User]: Yes, confirmed.")
    res = agent.run("Yes, confirmed.", session_id=session_id)
    print(f"[Agent]: {res}")
    
    # 3. Check Status
    print("\n[User]: Is my food ready?")
    res = agent.run("Is my food ready?", session_id=session_id)
    print(f"[Agent]: {res}")
    
    # 4. Simulate Kitchen Update (Manual Mock Update)
    print("\n... Chef is cooking ...")
    from tools import kitchen_ops, order_ops
    # Find the order ID
    order = [o for o in order_ops.ORDERS_DB.values() if o.table_id == session_id][-1]
    kitchen_ops.complete_ticket(order.order_id)
    
    # 5. Check Status Again
    print("\n[User]: Where is my order now?")
    res = agent.run("Where is my order now?", session_id=session_id)
    print(f"[Agent]: {res}")

if __name__ == "__main__":
    verify_fulfillment()
