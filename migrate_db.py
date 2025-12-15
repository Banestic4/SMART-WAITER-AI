import sqlite3
import os

DB_FILE = os.path.join(os.path.dirname(__file__), 'data', 'smart_waiter.db')

def migrate():
    print(f"Migrating database at {DB_FILE}...")
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    try:
        # Check if column exists
        c.execute("PRAGMA table_info(kitchen_tickets)")
        columns = [row[1] for row in c.fetchall()]
        
        if 'notes' not in columns:
            print("Adding 'notes' column to kitchen_tickets...")
            c.execute("ALTER TABLE kitchen_tickets ADD COLUMN notes TEXT")
            print("Column added successfully.")
        else:
            print("'notes' column already exists.")
            
        conn.commit()
    except Exception as e:
        print(f"Migration failed: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
