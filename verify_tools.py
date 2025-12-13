from tools.menu_ops import get_menu, get_item_details
from tools.order_ops import create_order, add_item_to_order, get_order

print("--- Testing Menu Ops ---")
menu = get_menu("Main")
print(f"Main Items: {[item['name'] for item in menu]}")
item = get_item_details("b1")
print(f"Detail for b1: {item['name']} - ${item['price']}")

print("\n--- Testing Order Ops ---")
order = create_order("Table-5")
print(f"Created Order: {order['order_id']} for {order['table_id']}")

order = add_item_to_order(order['order_id'], "b1", 2)
print(f"Added Items. Order Items: {len(order['items'])}")
print(f"First Item ID: {order['items'][0]['item_id']} Qty: {order['items'][0]['quantity']}")
