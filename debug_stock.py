from tools import inventory_ops
from storage import db

def debug_stock():
    print("--- Debugging Stock ---")
    
    # 1. Force Reseed
    # db.execute_update("DELETE FROM inventory")
    inventory_ops.seed_inventory()
    
    # 2. Check 'b1'
    stock = inventory_ops.check_stock("b1")
    print(f"Stock for 'b1': {stock}")
    
    # 3. Check 'classic_burger' (old key)
    stock_old = inventory_ops.check_stock("classic_burger")
    print(f"Stock for 'classic_burger': {stock_old}")

if __name__ == "__main__":
    debug_stock()
