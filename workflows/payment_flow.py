from typing import TypedDict
from langchain_core.messages import BaseMessage, AIMessage
from langgraph.graph import StateGraph, END
from tools import order_ops, payment_ops, confirmation_ops, menu_ops, kitchen_ops

class PaymentState(TypedDict):
    messages: list[BaseMessage]
    session_id: str
    order_id: str
    amount: float
    status: str

def create_payment_workflow(llm):
    
    def analyze_payment_state(state: PaymentState):
        """
        Determine if this is a new payment request or a confirmation of an existing one.
        """
        messages = state['messages']
        last_human_msg = messages[-1].content.lower()
        
        if "yes" in last_human_msg or "confirm" in last_human_msg:
             return {"status": "confirmed"}
        elif "no" in last_human_msg or "cancel" in last_human_msg:
             return {"status": "cancelled"}
        else:
             return {"status": "init"}

    def fetch_order_details(state: PaymentState):
        session_id = state['session_id']
        
        # Check active order
        order = None
        for oid, o in order_ops.ORDERS_DB.items():
            if o.table_id == session_id and o.status != "PAID" and o.status != "CANCELLED":
                order = o
                break
        
        if not order:
            return {"status": "no_order", "amount": 0.0, "messages": [AIMessage(content="I can't find an active order for you to pay.")]}
        
        total = 0.0
        price_map = {item.id: item.price for item in menu_ops.MENU_DB}
        for item in order.items:
            price = price_map.get(item.item_id, 0.0)
            total += price * item.quantity
            
        return {"order_id": order.order_id, "amount": total}

    def ask_for_confirmation(state: PaymentState):
        if state.get('status') == "no_order": return {}
        
        msg = confirmation_ops.format_confirmation_request(state['order_id'], state['amount'])
        return {"messages": [AIMessage(content=msg)]}

    def execute_payment(state: PaymentState):
        """Run the payment."""
        if state['status'] != "confirmed":
            return {}
            
        result = payment_ops.process_payment(state['order_id'], state['amount'])
        
        if result['success']:
            # Update Order Status
            if state['order_id'] in order_ops.ORDERS_DB:
                order_ops.ORDERS_DB[state['order_id']].status = "PAID"
            
            # Auto-Send to Kitchen
            kitchen_ops.send_ticket(state['order_id'])
                
            return {"status": "paid", "messages": [AIMessage(content=f"Payment of ₦{state['amount']:,.2f} successful! Your order has been sent to the kitchen.")]}
        else:
            return {"status": "failed", "messages": [AIMessage(content="Payment failed. Please try again.")]}

    workflow = StateGraph(PaymentState)
    
    workflow.add_node("analyze", analyze_payment_state)
    workflow.add_node("prepare_bill", fetch_order_details)
    workflow.add_node("ask", ask_for_confirmation)
    workflow.add_node("pay", execute_payment)
    
    workflow.set_entry_point("analyze")
    
    # Conditional Edges
    workflow.add_conditional_edges(
        "analyze",
        lambda x: x['status'],
        {
            "init": "prepare_bill",
            "confirmed": "prepare_bill",
            "cancelled": END
        }
    )
    
    workflow.add_conditional_edges(
        "prepare_bill",
        lambda x: "pay" if x.get('status') == "confirmed" else "ask",
        {
            "pay": "pay",
            "ask": "ask"
        }
    )
    
    workflow.add_edge("ask", END)
    workflow.add_edge("pay", END)
    
    return workflow.compile()
