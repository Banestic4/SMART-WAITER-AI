from tools import order_ops, kitchen_ops, inventory_ops
from storage import db
import time

def verify_storage_inventory():
    print("--- Testing Storage & Inventory ---")
    
    # 1. Reset (For clean test)
    # We won't drop tables, but let's reset stock for 'test_burger'
    inventory_ops.set_stock("test_burger", 2)
    print("Stock set to 2.")
    
    # 2. Order 1 (Should Succeed)
    print("\n--- Order 1 ---")
    order = order_ops.create_order("table-storage-test")
    # New create_order returns dict (Pydantic dump)
    order_id = order['order_id']
    
    success = order_ops.add_item_to_order(order_id, "test_burger", 1)
    print(f"Adding 1st Burger: {'Success' if success else 'Failed'}")
    
    # 3. Order 2 (Should Succeed - Stock becomes 0)
    print("\n--- Order 2 ---")
    success = order_ops.add_item_to_order(order_id, "test_burger", 1)
    print(f"Adding 2nd Burger: {'Success' if success else 'Failed'}")

    # 4. Order 3 (Should Fail - Out of Stock)
    print("\n--- Order 3 (Expect Failure) ---")
    success = order_ops.add_item_to_order(order_id, "test_burger", 1)
    print(f"Adding 3rd Burger: {'Success' if success else 'Failed'}")
    
    if not success:
        print(">>> SUCCESS: Inventory blocked out-of-stock item.")
        
    # 5. Verify Persistence
    print("\n--- Verifying Persistence ---")
    # Fetch from DB freshly
    fetched_order = order_ops.get_order(order_id)
    if fetched_order:
        item_count = sum(i['quantity'] for i in fetched_order['items'] if i['item_id'] == 'test_burger')
        print(f"Fetched Order Items: {item_count} (Expected 2)")
        if item_count == 2:
            print(">>> SUCCESS: Data persisted in SQLite.")
    else:
        print(">>> FAILURE: Could not fetch order.")

if __name__ == "__main__":
    verify_storage_inventory()
