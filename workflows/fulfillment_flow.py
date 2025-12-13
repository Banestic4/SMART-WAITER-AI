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
                 # Should have been sent, maybe error or just created
                 return {"messages": [AIMessage(content="Your order is paid and should be in the kitchen.")]}
             else:
                 return {"messages": [AIMessage(content=f"Your order status is: {order.status}")]}
        
        return {"messages": [AIMessage(content=f"Kitchen Update: Your order is currently {kitchen_status}.")]}

    workflow = StateGraph(FulfillmentState)
    workflow.add_node("check_status", check_order_status)
    workflow.set_entry_point("check_status")
    workflow.add_edge("check_status", END)
    
    return workflow.compile()
