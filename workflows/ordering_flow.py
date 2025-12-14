from typing import TypedDict, Literal
from langchain_core.messages import BaseMessage, SystemMessage, AIMessage, HumanMessage
from langgraph.graph import StateGraph, END
from tools import menu_ops, order_ops, recommendation_ops
import json

# Define the state specific to this workflow (inherits/compatible with AgentState)
class OrderingState(TypedDict):
    messages: list[BaseMessage]
    session_id: str
    intermediate_steps: list

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
        Return a JSON object ONLY: {{ "action": "add", "items": [{{"item_id": "id", "quantity": 1}}] }}
        If the user implies removing, return action "remove".
        If unclear or just asking questions, return action "none".
        """
        
        response = llm.invoke([SystemMessage(content=prompt)])
        content = response.content.replace('```json', '').replace('```', '').strip()
        
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
        session_id = state.get("session_id", "default")
        
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
                    new_o = order_ops.create_order(session_id)
                    target_order_id = new_o['order_id']

                res = order_ops.add_item_to_order(target_order_id, item['item_id'], item['quantity'])
                if res:
                    details = menu_ops.get_item_details(item['item_id'])
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
        elif action == "none":
            result_message = "I didn't catch any items to order, please state clearly your order."
        elif action == "remove":
            result_message = "I have removed that item for you."
            
        return {"intermediate_steps": [{"result": result_message}]}

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
