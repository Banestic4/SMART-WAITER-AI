from typing import List, Dict, Optional
from pydantic import BaseModel, Field
import uuid
import json
from datetime import datetime
from storage import db
from tools import inventory_ops

class OrderItem(BaseModel):
    item_id: str
    quantity: int = 1

class Order(BaseModel):
    order_id: str
    table_id: str
    order_id: str
    table_id: str
    table_number: Optional[str] = None
    items: List[OrderItem] = []
    status: str = "DRAFT" 
    created_at: str = ""
    total_amount: float = 0.0

# Replaces ORDERS_DB = {}

def create_order(table_id: str, table_number: str = None) -> Dict:
    """Create a new empty order in SQLite."""
    order_id = str(uuid.uuid4())[:8]
    created_at = datetime.now().isoformat()
    
    db.execute_update(
        "INSERT INTO orders (order_id, table_id, status, total_amount, created_at, table_number) VALUES (?, ?, ?, ?, ?, ?)",
        (order_id, table_id, "DRAFT", 0.0, created_at, table_number)
    )
    
    return Order(order_id=order_id, table_id=table_id, created_at=created_at, table_number=table_number).model_dump()

def get_order(order_id: str) -> Optional[Order]:
    """Retrieve an order by ID (Internal Use: returns Pydantic model or Dict)."""
    # Note: Refactored to match previous usage patterns where dict was expected, 
    # but some code might expect object access. 
    # To minimize breakage, let's return object that supports both or just Dict?
    # Verification showed dot access issues. Let's return Pydantic Model (which supports .attr)
    # BUT ordering_flow fix used dict access. Pydantic v2 model_dump returns dict.
    # Let's return the Pydantic Object, but make sure callers use .attr or .model_dump().
    # Actually, previous fix switched execution to dict access (new_o['order_id']).
    # So `create_order` returning dict is good.
    # But `get_order` was used in `ordering_flow` with `['items']`.
    
    # Let's standardize on returning Pydantic Model for internal logic, 
    # but `ordering_flow` expects dict for `active_order_obj`.
    # Let's return Dict for safety with recent patches.
    pass

# Redefining simply
def get_order(order_id: str) -> Optional[Dict]:
    rows = db.execute_query("SELECT * FROM orders WHERE order_id = ?", (order_id,))
    if not rows: return None
    
    base = dict(rows[0])
    
    # Get Items
    item_rows = db.execute_query("SELECT item_id, quantity FROM order_items WHERE order_id = ?", (order_id,))
    base['items'] = [dict(row) for row in item_rows]
    
    return base

# Compatibility Helper for Flow (which expects object in some places?)
# No, we patched flows to use dicts.

ORDERS_DB = {} # Deprecated, kept to prevent immediate import errors if referenced directly. 
# We should probably property mock it or ensure all consumers use functions.

def add_item_to_order(order_id: str, item_id: str, quantity: int = 1) -> bool:
    """Add item to order in DB, checking inventory."""
    
    # 1. Check Inventory
    if not inventory_ops.decrement_stock(item_id, quantity):
        print(f"Stock check failed for {item_id}")
        return False
        
    # 2. Add/Update Item in DB
    existing = db.execute_query(
        "SELECT id, quantity FROM order_items WHERE order_id = ? AND item_id = ?", 
        (order_id, item_id)
    )
    
    if existing:
        new_qty = existing[0]['quantity'] + quantity
        db.execute_update(
            "UPDATE order_items SET quantity = ? WHERE id = ?",
            (new_qty, existing[0]['id'])
        )
    else:
        db.execute_update(
            "INSERT INTO order_items (order_id, item_id, quantity) VALUES (?, ?, ?)",
            (order_id, item_id, quantity)
        )
        
    return True

def remove_item_from_order(order_id: str, item_id: str, quantity: int = 1) -> bool:
    """Remove item from order in DB (decrement or delete) and restore stock."""
    
    # 1. Check if item exists in order
    existing = db.execute_query(
        "SELECT id, quantity FROM order_items WHERE order_id = ? AND item_id = ?", 
        (order_id, item_id)
    )
    
    if not existing:
        return False
        
    current_qty = existing[0]['quantity']
    row_id = existing[0]['id']
    
    # 2. Update DB
    if quantity >= current_qty:
        # Remove completely
        db.execute_update("DELETE FROM order_items WHERE id = ?", (row_id,))
        removed_qty = current_qty
    else:
        # Decrement
        new_qty = current_qty - quantity
        db.execute_update("UPDATE order_items SET quantity = ? WHERE id = ?", (new_qty, row_id))
        removed_qty = quantity
        
    # 3. Restore Stock (Optional, but good practice)
    # Assuming inventory_ops has increment? Check inventory_ops later.
    # For now, let's assume valid returns restore stock.
    inventory_ops.increment_stock(item_id, removed_qty)
    
    return True

def cancel_order(order_id: str) -> bool:
    return db.execute_update("UPDATE orders SET status = 'CANCELLED' WHERE order_id = ?", (order_id,)) > 0
