from typing import List, Optional
from tools import menu_ops, order_ops

def get_recommendation(current_order_items: List[order_ops.OrderItem]) -> str:
    """
    Suggest an item based on the current order.
    Simple Rule: If Burger/Sandwich but no Drink/Side -> Suggest Drink/Side.
    """
    has_main = False
    has_drink = False
    has_side = False
    
    # Analyze current cart
    # Note: In a real app, we'd check item categories from menu_ops.
    # For MVP, we check keywords in item_id or name.
    
    for item in current_order_items:
        # data is likely dict if coming from model_dump
        item_id = item['item_id'] if isinstance(item, dict) else item.item_id
        
        details = menu_ops.get_item_details(item_id)
        if not details: continue
        
        cat = details['category'].lower()
        name = details['name'].lower()
        
        if cat == "main" or "burger" in name: has_main = True
        if cat == "drinks" or "coke" in name or "water" in name: has_drink = True
        if cat == "sides" or "fries" in name: has_side = True
        
    if has_main:
        if not has_side and not has_drink:
            return "Would you like to add some fries and a coke to make it a meal?"
        if not has_side:
            return "How about some fries on the side?"
        if not has_drink:
            return "Would you like a drink with that?"
            
    # Default generic upselling
    return "Would you like to see our dessert menu?"
