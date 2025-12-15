from tools import order_ops
from storage import db
import uuid

def test_db_persistence():
    test_id = str(uuid.uuid4())
    table_num = "12"
    
    print(f"Creating order for session {test_id} with table {table_num}...")
    order = order_ops.create_order(test_id, table_number=table_num)
    order_id = order['order_id']
    
    print(f"Order created: {order_id}")
    
    # Verify via direct DB query
    rows = db.execute_query("SELECT table_number FROM orders WHERE order_id = ?", (order_id,))
    if rows:
        saved_num = rows[0]['table_number']
        print(f"DB Record: table_number={saved_num}")
        if saved_num == table_num:
            print("SUCCESS: Table number persisted correctly.")
        else:
            print(f"FAILURE: Expected {table_num}, got {saved_num}")
    else:
        print("FAILURE: Order not found in DB.")

if __name__ == "__main__":
    test_db_persistence()
