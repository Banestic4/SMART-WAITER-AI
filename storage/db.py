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
    
    
    # User Sessions Table (for Context Rotation)
    c.execute('''CREATE TABLE IF NOT EXISTS user_sessions (
        user_id TEXT PRIMARY KEY,
        session_version INTEGER
    )''')
    
    conn.commit()
    conn.close()
    
# Initialize on module load (safe for now)
init_db()

def execute_query(query: str, params: tuple = ()) -> List[dict]:
    with get_connection() as conn:
        c = conn.cursor()
        c.execute(query, params)
        rows = c.fetchall()
        # conn.commit() is not strictly needed for SELECT but harmless
    # Connection closes automatically here
    return [dict(row) for row in rows]

def execute_update(query: str, params: tuple = ()) -> int:
    with get_connection() as conn:
        c = conn.cursor()
        c.execute(query, params)
        # Context manager handles commit automatically on exit? 
        # sqlite3 connection context manager commits on success, rollbacks on error.
        # But we need to ensure it's committed.
        conn.commit()
        affected = c.rowcount
    return affected

def get_session_version(user_id: str) -> int:
    """Get current session version for user to rotate context."""
    rows = execute_query("SELECT session_version FROM user_sessions WHERE user_id = ?", (user_id,))
    if rows:
        return rows[0]['session_version']
    else:
        # Init
        execute_update("INSERT INTO user_sessions (user_id, session_version) VALUES (?, 1)", (user_id,))
        return 1

def increment_session_version(user_id: str):
    """Rotate the session to clear context."""
    execute_update("UPDATE user_sessions SET session_version = session_version + 1 WHERE user_id = ?", (user_id,))
