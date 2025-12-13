from storage import db
from typing import Optional

def check_stock(item_id: str) -> int:
    """Check available stock for an item. Returns 0 if not found."""
    rows = db.execute_query("SELECT quantity_available FROM inventory WHERE item_id = ?", (item_id,))
    if rows:
        # print(f"DEBUG: Stock for {item_id} is {rows[0]['quantity_available']}")
        return rows[0]['quantity_available']
    # print(f"DEBUG: Stock for {item_id} NOT FOUND")
    return 0 # Treat unknown items as 0 stock for safety, or we could default to 100 for dev

def set_stock(item_id: str, quantity: int):
    """Set stock level for an item."""
    # Upsert logic
    exists = db.execute_query("SELECT 1 FROM inventory WHERE item_id = ?", (item_id,))
    if exists:
        db.execute_update("UPDATE inventory SET quantity_available = ? WHERE item_id = ?", (quantity, item_id))
    else:
        db.execute_update("INSERT INTO inventory (item_id, quantity_available) VALUES (?, ?)", (item_id, quantity))

def decrement_stock(item_id: str, quantity: int) -> bool:
    """
    Decrement stock if sufficient quantity exists.
    Returns True if successful, False if out of stock.
    """
    current_stock = check_stock(item_id)
    if current_stock >= quantity:
        new_stock = current_stock - quantity
        db.execute_update("UPDATE inventory SET quantity_available = ? WHERE item_id = ?", (new_stock, item_id))
        return True
    return False

# Initialize meaningful defaults for demo
def seed_inventory():
    print("Seeding Inventory...")
    # Assume IDs match what we use (simplified names or IDs from menu.json)
    # We should really sync with menu.json IDs.
    # For now, let's map common items.
    # If menu_ops loaded IDs properly, we'd iterate.
    # Updated to match data/menu.json IDs
    set_stock("b1", 50) # Classic Burger
    set_stock("b2", 50) # Veggie Burger
    set_stock("s1", 50) # Fries
    set_stock("d1", 50) # Coke

# Auto-seed on load if empty (for dev convenience)
if not db.execute_query("SELECT 1 FROM inventory LIMIT 1"):
    seed_inventory()
