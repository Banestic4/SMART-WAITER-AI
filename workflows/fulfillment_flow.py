from typing import TypedDict
from langchain_core.messages import BaseMessage, AIMessage
from langgraph.graph import StateGraph, END
from tools import order_ops, kitchen_ops

class FulfillmentState(TypedDict):
    messages: list[BaseMessage]
    session_id: str

def create_fulfillment_workflow(llm):
    
    def check_order_status(state: FulfillmentState):
        session_id = state['session_id']
        
        # Find active or recently paid order
        order = None
        # Look for most recent order
        candidates = [o for o in order_ops.ORDERS_DB.values() if o.table_id == session_id]
        if not candidates:
             return {"messages": [AIMessage(content="You haven't placed an order yet.")]}
        
        # Sort by creation (mock: just take last)
        order = candidates[-1]
        
        kitchen_status = kitchen_ops.get_ticket_status(order.order_id)
        
        if kitchen_status == "UNKNOWN":
             if order.status == "DRAFT":
                 return {"messages": [AIMessage(content="Your order hasn't been placed yet. Say 'I want to order' to proceed.")]}
             elif order.status == "PAID":
                 first_msg = True
                 if messages:
                     last_msg = messages[-1].content.lower()
                     first_msg = False
                     
                     # Check for "received" response
                     if "received" in last_msg or "yes" in last_msg:
                          return {"status": "ask_feedback", "messages": [AIMessage(content="Great! How was our service and the food? We'd love your feedback.")]}
                     elif "waiting" in last_msg or "no" in last_msg:
                          return {"status": "waiting", "messages": [AIMessage(content="I apologize for the delay. I will alert the waiter again immediately.")]}
                     
                 # Default initial message (Simulating 5 min timer)
                 if first_msg or state.get("status") != "ask_feedback":
                     msg = "Have you received your order yet? (Please reply 'Received' or 'Am waiting')"
                     return {"status": "waiting", "messages": [AIMessage(content=msg)]}
                     
                 return {"status": "waiting"}
             else:
                 return {"messages": [AIMessage(content=f"Your order status is: {order.status}")]}
        
        return {"messages": [AIMessage(content=f"Kitchen Update: Your order is currently {kitchen_status}.")]}

    def collect_feedback_node(state: FulfillmentState):
        """Collect feedback and thank user."""
        messages = state.get("messages", [])
        last_msg = messages[-1].content
        
        # Save feedback (mock)
        # feedback_ops.save_feedback(last_msg)
        
        msg = "Thank you so much for patronizing us! We would love to have you around again. Enjoy your meal!"
        # End of session
        return {"status": "complete", "messages": [AIMessage(content=msg)]}

    workflow = StateGraph(FulfillmentState)
    workflow.add_node("check_status", check_order_status)
    workflow.add_node("collect_feedback", collect_feedback_node)
    
    workflow.set_entry_point("check_status")
    
    # Conditional edge
    workflow.add_conditional_edges(
        "check_status",
        lambda x: "collect_feedback" if x.get("status") == "ask_feedback" else END,
        {
            "collect_feedback": "collect_feedback",
            "END": END
        }
    )
    workflow.add_edge("collect_feedback", END)
    
    return workflow.compile()
