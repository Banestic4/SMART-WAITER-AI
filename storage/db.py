import sqlite3
import os
from typing import List, Dict, Optional, Any

DB_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'smart_waiter.db')

def get_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    c = conn.cursor()
    
    # Orders Table
    c.execute('''CREATE TABLE IF NOT EXISTS orders (
        order_id TEXT PRIMARY KEY,
        table_id TEXT,
        status TEXT,
        total_amount REAL,
        created_at TEXT
    )''')
    
    # Order Items Table
    c.execute('''CREATE TABLE IF NOT EXISTS order_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id TEXT,
        item_id TEXT,
        quantity INTEGER,
        FOREIGN KEY(order_id) REFERENCES orders(order_id)
    )''')
    
    # Kitchen Tickets Table
    c.execute('''CREATE TABLE IF NOT EXISTS kitchen_tickets (
        ticket_id TEXT PRIMARY KEY,
        order_id TEXT,
        status TEXT,
        created_at TEXT,
        FOREIGN KEY(order_id) REFERENCES orders(order_id)
    )''')
    
    # Inventory Table
    c.execute('''CREATE TABLE IF NOT EXISTS inventory (
        item_id TEXT PRIMARY KEY,
        quantity_available INTEGER
    )''')
    
    conn.commit()
    conn.close()
    
# Initialize on module load (safe for now)
init_db()

def execute_query(query: str, params: tuple = ()) -> List[dict]:
    conn = get_connection()
    c = conn.cursor()
    c.execute(query, params)
    rows = c.fetchall()
    conn.commit()
    conn.close()
    return [dict(row) for row in rows]

def execute_update(query: str, params: tuple = ()) -> int:
    conn = get_connection()
    c = conn.cursor()
    c.execute(query, params)
    conn.commit()
    affected = c.rowcount
    conn.close()
    return affected
