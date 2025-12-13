from agents.smart_waiter_agent import SmartWaiterAgent
import os

print("--- Testing Payment Flow ---")

agent = SmartWaiterAgent()
session_id = "table-payment-test"

# 1. Create an order (to ensure we have something to pay)
print(f"\n[User]: I'll take a classic burger.")
res = agent.run("I'll take a classic burger.", session_id=session_id)
print(f"[Agent]: {res}")

# 2. Ask to pay
print(f"\n[User]: Check please.")
res = agent.run("Check please.", session_id=session_id)
print(f"[Agent]: {res}")

# 3. Confirm payment
print(f"\n[User]: Yes, confirmed.")
res = agent.run("Yes, confirmed.", session_id=session_id)
print(f"[Agent]: {res}")

print("\n--- Testing Re-payment (Should be empty or done) ---")
res = agent.run("Can I pay again?", session_id=session_id)
print(f"[Agent]: {res}")
