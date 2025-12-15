import sqlite3
import os

DB_FILE = os.path.join(os.path.dirname(__file__), 'data', 'smart_waiter.db')

def migrate():
    print(f"Migrating database at {DB_FILE}...")
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    try:
        # Check if column exists
        c.execute("PRAGMA table_info(orders)")
        columns = [row[1] for row in c.fetchall()]
        
        if 'table_number' not in columns:
            print("Adding 'table_number' column to orders...")
            c.execute("ALTER TABLE orders ADD COLUMN table_number TEXT")
            print("Column added successfully.")
        else:
            print("'table_number' column already exists.")
            
        conn.commit()
    except Exception as e:
        print(f"Migration failed: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
