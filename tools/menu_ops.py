from typing import List, Dict, Optional

# Structured Menu Data
FULL_MENU = {
    "Rice 🍚": {
        "White Rice": 500, "Jollof Rice": 500, "Fried Rice": 500, "Rice with Beans": 800
    },
    "Swallow 🥣": {
        "Semovita": 500, "Fufu / Akpu": 500, "Amala": 500, "Pounded Yam": 500
    },
    "Yam & Sides 🍠": {
        "Golden Yam": 1000, "Egg": 300, "Liver Sauce": 300, "Potato Chips": 700, "Plantain Chips": 200
    },
    "Proteins 🍖": {
        "Beef": 200, "Goat Meat": 400, "Chicken": 2000, "Fish (Small)": 300, "Fish (Big)": 500, "Mackerel": 1000
    },
    "Soup & Noodles 🍜": {
        "Pepper Soup": 1000, "Spaghetti": 800, "Indomie": 600
    },
    "Snacks & Cakes 🍰": {
        "Meat Pie": 700, "Fish Pie": 700, "Burger (Reg)": 1700, "Burger (Large)": 2500, "Doughnut": 300, "Egg Roll": 500
    },
    "Drinks & Tea ☕": {
        "Zobo (S)": 400, "Zobo (B)": 800, "Water": 200, "Small Tea": 700, "Large Tea": 2000
    }
}

def get_menu() -> List[Dict]:
    """
    Legacy compatibility: Convert FULL_MENU to flat list expected by agent.
    """
    flat_menu = []
    for category, items in FULL_MENU.items():
        # Remove Emoji for cleaner internal category name if needed, but keeping it is fine.
        clean_cat = category.split(' ')[0] 
        for name, price in items.items():
            flat_menu.append({
                "id": name.lower().replace(" ", "_"),
                "name": name,
                "price": price,
                "category": category, # Use full display name for grouping
                "available": True
            })
    return flat_menu

def get_categories() -> List[str]:
    return list(FULL_MENU.keys())

def get_category_items(category: str) -> Dict[str, int]:
    return FULL_MENU.get(category, {})
