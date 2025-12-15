from typing import List, Dict, Optional
from pydantic import BaseModel
import uuid
import datetime
from storage import db

class KitchenTicket(BaseModel):
    ticket_id: str
    order_id: str
    status: str = "PENDING"
    created_at: str
    estimated_time: int = 15
    notes: Optional[str] = None

# Replaces KITCHEN_DB

def send_ticket(order_id: str, notes: str = None) -> Dict:
    """Send an order to the kitchen (SQLite)."""
    ticket_id = str(uuid.uuid4())[:8]
    created_at = datetime.datetime.now().isoformat()
    
    db.execute_update(
        "INSERT INTO kitchen_tickets (ticket_id, order_id, status, created_at, notes) VALUES (?, ?, ?, ?, ?)",
        (ticket_id, order_id, "PREPARING", created_at, notes)
    )
    
    return KitchenTicket(
        ticket_id=ticket_id, 
        order_id=order_id, 
        status="PREPARING",
        created_at=created_at,
        notes=notes
    ).model_dump()

def get_ticket_status(order_id: str) -> str:
    """Get the status of an order ticket."""
    rows = db.execute_query("SELECT status FROM kitchen_tickets WHERE order_id = ?", (order_id,))
    if not rows:
        return "UNKNOWN"
    return rows[0]['status']

def complete_ticket(order_id: str) -> Dict:
    """Mark a ticket as READY (Simulated Chef Action)."""
    rows = db.execute_query("SELECT ticket_id, created_at FROM kitchen_tickets WHERE order_id = ?", (order_id,))
    if not rows: return None
    
    ticket_data = rows[0]
    db.execute_update("UPDATE kitchen_tickets SET status = 'READY' WHERE order_id = ?", (order_id,))
    
    return KitchenTicket(
        ticket_id=ticket_data['ticket_id'],
        order_id=order_id,
        status="READY",
        created_at=ticket_data['created_at']
    ).model_dump()
