from typing import List, Optional, Dict
from pydantic import BaseModel

class MenuItem(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    price: float
    category: str
    available: bool = True
    ingredients: List[str] = []

import json
import os

# Path to the external menu file
MENU_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'menu.json')

def load_menu_db() -> List[MenuItem]:
    """Load menu items from the JSON file."""
    if not os.path.exists(MENU_FILE):
        return []
    
    with open(MENU_FILE, 'r') as f:
        data = json.load(f)
        
    return [MenuItem(**item) for item in data]

# Load DB on module import (simulated caching)
MENU_DB = load_menu_db()

def get_menu(category: str = None) -> List[Dict]:
    """
    Retrieve menu items.
    
    Args:
        category: Optional category filter (e.g., 'Main', 'Side').
    """
    # Reload to catch updates (optional, good for dev)
    global MENU_DB
    MENU_DB = load_menu_db()
    
    if category:
        items = [item for item in MENU_DB if item.category.lower() == category.lower()]
    else:
        items = MENU_DB
        
    return [item.model_dump() for item in items]

def get_item_details(item_id: str) -> Optional[Dict]:
    """
    Get full details for a specific menu item.
    """
    # Ensure fresh data
    global MENU_DB
    MENU_DB = load_menu_db()
    
    for item in MENU_DB:
        if item.id == item_id:
            return item.model_dump()
    return None
