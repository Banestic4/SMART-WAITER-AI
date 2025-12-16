from storage import db
import sys

session_id = "b4147bc8"
print(f"Checking orders for session {session_id}...")

rows = db.execute_query("SELECT * FROM orders WHERE table_id = ?", (session_id,))
for row in rows:
    print(f"Order: {row['order_id']}, Status: {row['status']}, Amount: {row['total_amount']}")
    items = db.execute_query("SELECT * FROM order_items WHERE order_id = ?", (row['order_id'],))
    for item in items:
        print(f"  - Item: {item['item_id']}, Qty: {item['quantity']}")

if not rows:
    print("No orders found.")
