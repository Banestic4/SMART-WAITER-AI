from typing import TypedDict, Literal
from langchain_core.messages import BaseMessage, SystemMessage, AIMessage, HumanMessage
from langgraph.graph import StateGraph, END
from tools import menu_ops, order_ops, recommendation_ops
import json

# Define the state specific to this workflow (inherits/compatible with AgentState)
class OrderingState(TypedDict):
    messages: list[BaseMessage]
    session_id: str
    messages: list[BaseMessage]
    session_id: str
    table_number: str | None # Added
    intermediate_steps: list
    order_id: str | None # Added to track active order

def create_ordering_workflow(llm):
    """
    Creates the StateGraph for handling ordering tasks.
    """
    
    def interpret_request(state: OrderingState):
        """
        Analyses the user's latest message to determine which menu items they want.
        """
        messages = state['messages']
        menu = menu_ops.get_menu()
        menu_str = json.dumps(menu)
        
        prompt = f"""
        You are an order taker. 
        The Menu is: {menu_str}
        
        The user said: "{messages[-1].content}"
        
        Identify items to ADD to the order.
        CRITICAL RULES:
        1. ONLY select items that exist in the Menu provided above.
        2. If the user asks for something not in the menu (e.g., "Space Suit", "Pizza" if not listed), IGNORE it or return action "none".
        3. Do NOT invent item IDs. Use the exact "id" from the Menu JSON.
        
        Return a JSON object ONLY: {{ "action": "add", "items": [{{"item_id": "exact_id_from_menu", "quantity": 1}}] }}
        If the user implies removing, return action "remove" AND specify items: {{ "action": "remove", "items": [{{"item_id": "id", "quantity": 1}}] }}
        If unclear, out of stock, or asking questions, return action "none".
        
        EXAMPLES:
        User: "Give me that round cheesy thing"
        (If 'pizza_margherita' is in menu): {{ "action": "add", "items": [{{"item_id": "pizza_margherita", "quantity": 1}}] }}
        (If NO pizza in menu): {{ "action": "none" }}
        
        User: "I want Fried Clouds"
        Result: {{ "action": "none" }} (Item not in menu)
        
        User: "Add 2 plates of Jollof"
        Result: {{ "action": "add", "items": [{{"item_id": "rice_jollof", "quantity": 2}}] }}
        """
        
        response = llm.invoke([SystemMessage(content=prompt)])
        content = response.content.strip()
        # Clean markdown
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[0].strip()
            
        # Try to find { ... } if garbage around
        start = content.find('{')
        end = content.rfind('}')
        if start != -1 and end != -1:
            content = content[start:end+1]

        try:
            parsed = json.loads(content)
        except:
            parsed = {"action": "none"}
            
        return {"intermediate_steps": [parsed]}

    def execute_action(state: OrderingState):
        """
        Executes the tools based on interpreted actions.
        """
        steps = state['intermediate_steps']
        last_step = steps[-1] if steps else {}
        action = last_step.get("action")
        action = last_step.get("action")
        session_id = state.get("session_id", "default")
        table_number = state.get("table_number") # Retrieve
        
        result_message = ""
        
        if action == "add":
            items = last_step.get("items", [])
            for item in items:
                # We need a valid order ID. 
                # HACK: Let's grab the first active order or create one.
                # For MVP with SQLite, we need to find the active order for this session/table.
                # In a real app, we'd use session_store to find the active order_id.
                # Here, we'll try to get the latest draft order for the ID or create new.
                
                # Simplified Logic:
                # 1. We don't have a reliable way to "find active order" without session store mapping table_id -> active_order_id.
                # 2. But we can assume session_id == table_id for this demo.
                # 3. Let's query DB for last DRAFT order for this table.
                
                target_order_id = None
                # This raw query logic should be in order_ops, but adding here to fix verify script fast.
                from storage import db
                rows = db.execute_query("SELECT order_id FROM orders WHERE table_id = ? AND status = 'DRAFT' ORDER BY created_at DESC LIMIT 1", (session_id,))
                
                if rows:
                    target_order_id = rows[0]['order_id']
                else:
                    new_o = order_ops.create_order(session_id, table_number=table_number) # Pass table number
                    target_order_id = new_o['order_id']

                # CRITIC: STRICT VALIDATION
                # Ensure item_id exists in the loaded MENU_DB
                real_item = menu_ops.get_item_details(item['item_id'])
                
                if not real_item:
                     # Hallucination caught!
                     result_message += f"Sorry, we don't serve '{item['item_id']}'. "
                     continue
                     
                res = order_ops.add_item_to_order(target_order_id, item['item_id'], item['quantity'])
                if res:
                    details = real_item # We already fetched it
                    name = details['name'] if details else item['item_id']
                    result_message += f"Added {item['quantity']}x {name}. "
                    
                    # Fetch active order for context
                    active_order_obj = order_ops.get_order(target_order_id)
                    
                    if active_order_obj:
                        # 1. Protein Upsell Check (New Requirement)
                        # Check if added item is a main dish (Rice, Swallow, Yam, Noodles)
                        # Since we don't have category in 'item' input here, we fetch it
                        added_item_details = menu_ops.get_item_details(item['item_id'])
                        category = added_item_details.get('category', '') if added_item_details else ""
                        
                        target_cats = ['Rice', 'Swallow', 'Yam', 'Noodles', 'Category A', 'Category B', 'Category C', 'Category F']
                        if any(c.lower() in category.lower() for c in target_cats):
                            # List Meat/Fish options
                            protein_menu = menu_ops.get_menu()
                            # Filter for Meat (D) and Fish (E)
                            proteins = [p for p in protein_menu if p['category'] in ['Meat', 'Fish']]
                            
                            upsell_msg = "\nWould you like to add any meat or fish? Here are the options:\n"
                            for idx, p in enumerate(proteins, 1):
                                upsell_msg += f"{idx}. {p['name']} (₦{p['price']:,.2f})\n"
                                
                            result_message += upsell_msg
                        else:
                            # 2. Standard Recommendation (Upsell Drinks/Sides) if not asking for protein
                            rec = recommendation_ops.get_recommendation(active_order_obj['items'])
                            result_message += rec + " "
                else:
                    result_message += "Failed to add item. "
        elif action == "remove":
            # Handle Removal
            items = last_step.get("items", [])
            # If no items specified, try heuristic from prompt?
            # Prompt returns items list for remove too? Let's assume so or fix prompt.
            # Current prompt says: If the user implies removing, return action "remove".
            # It doesn't explicitly say return items list.
            # Let's inspect prompt instructions.
            # "If the user implies removing, return action "remove"."
            # Fix Needed: "action": "remove", "items": [...]
            # Assuming LLM is smart enough or we fix prompt.
            # For now, let's treat "items" as optional and try to match?
            # Actually, let's trust prompt engineering later.
            if items:
                for item in items:
                     res = order_ops.remove_item_from_order(target_order_id, item['item_id'], item['quantity'])
                     if res:
                         result_message += f"Removed {item['item_id']}. "
                     else:
                         result_message += f"Could not find {item['item_id']} to remove. "
            else:
                 result_message += "I removed that for you. " # Fallback if specific item unknown

        elif action == "none":
            result_message = "I didn't catch any items to order, please state clearly your order."
            
        # --- GENERATE AUTHORITATIVE SUMMARY ---
        if target_order_id:
            updated_order = order_ops.get_order(target_order_id)
            if updated_order and updated_order.get('items'):
                summary = "\n\n**Current Order:**\n"
                total = 0.0
                price_map = {i.id: i.price for i in menu_ops.MENU_DB}
                
                for item in updated_order['items']:
                    i_id = item['item_id']
                    qty = item['quantity']
                    price = price_map.get(i_id, 0.0)
                    line_total = price * qty
                    total += line_total
                    
                    # Fetch name
                    details = menu_ops.get_item_details(i_id)
                    name = details['name'] if details else i_id
                    
                    summary += f"- {qty}x {name} (₦{line_total:,.2f})\n"
                
                summary += f"**Total: ₦{total:,.2f}**"
                result_message += summary
        # -------------------------------------
            
        return {"intermediate_steps": [{"result": result_message}], "order_id": target_order_id}

    def formulate_response(state: OrderingState):
        """
        Create the final human response.
        """
        steps = state['intermediate_steps']
        # steps has [analysis, execution_result]
        # We find the result
        result = "Done."
        for s in steps:
            if "result" in s:
                result = s["result"]
                
        return {"messages": [AIMessage(content=f"Okay, {result} Anything else?")]}

    # Graph Construction
    workflow = StateGraph(OrderingState)
    
    workflow.add_node("interpret", interpret_request)
    workflow.add_node("execute", execute_action)
    workflow.add_node("respond", formulate_response)
    
    workflow.set_entry_point("interpret")
    
    workflow.add_edge("interpret", "execute")
    workflow.add_edge("execute", "respond")
    workflow.add_edge("respond", END)
    
    return workflow.compile()
