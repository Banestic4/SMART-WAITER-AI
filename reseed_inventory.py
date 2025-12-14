from tools import inventory_ops, menu_ops
from storage import db

def reseed_inventory():
    print("--- Reseeding Inventory ---")
    
    # Clear old inventory
    db.execute_update("DELETE FROM inventory")
    print("Old inventory cleared.")
    
    # Load new menu
    menu = menu_ops.MENU_DB
    print(f"Loaded {len(menu)} items from Menu DB.")
    
    # Seed
    for item in menu:
        # Give 100 stock for everything for testing
        inventory_ops.set_stock(item.id, 100)
        print(f"Seeded {item.id} -> 100")
        
    print(">>> Inventory Reseed Complete.")

if __name__ == "__main__":
    reseed_inventory()
