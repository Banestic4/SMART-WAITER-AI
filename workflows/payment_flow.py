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
        Determine flow based on user's last message.
        Statuses: init -> ask_method -> processing_transfer -> paid -> ask_disposition -> complete
        """
        messages = state.get('messages', [])
        current_status = state.get('status', 'init')
        last_msg = messages[-1].content.lower() if messages else ""
        
        updates = {}
        
        # 1. Method Selection
        if current_status == "ask_method":
            if "transfer" in last_msg:
                return {"status": "processing_transfer"}
            elif "card" in last_msg or "pos" in last_msg:
                 return {"status": "processing_card"}
            elif "cash" in last_msg:
                 return {"status": "processing_cash"}
            elif "proceed" in last_msg or "pay" in last_msg: # User persists on paying
                 return {"status": "ask_method"} # Stick to ask method
            else:
                 return {"status": "ask_method"} 
                 
        # 2. Transfer Confirmation & HITL
        if current_status == "processing_transfer":
            if "paid" in last_msg or "done" in last_msg or "proceed" in last_msg:
                return {"status": "verifying_transfer"}
        
        # 3. HITL Verification Check
        if current_status == "verifying_transfer":
            # Real HITL check
            # For now, we simulate the "Wait" message.
            # If user says "verify" or "verified" (Simulating Admin), we proceed.
            # Or if strict simulation, we just toggle it automatically after a message?
            # User requirement: "wait for human... before asking for next action".
            # The Agent should say "Waiting for verification..." and effectively Pause.
            # But in this loop, unless we have an external signal, we need a trigger.
            # Let's assume the user (admin) or the user themselves waiting triggers a check.
            if "verified" in last_msg or "confirmed" in last_msg:
                 return {"status": "paid_success"}
            else:
                 # Keep waiting
                 return {"status": "verifying_transfer"}

        # 4. Post-Payment Disposition (Eat in / Takeaway)
        if current_status == "ask_disposition":
            if "take" in last_msg or "go" in last_msg:
                return {"status": "complete", "messages": [AIMessage(content="Okay, we will package it for takeaway. Please wait a moment.")]}
            else:
                 return {"status": "complete", "messages": [AIMessage(content="Great, please have a seat. Your food will be served shortly.")]}
                 
        return {"status": "init"} # Default fall-through for start

    def prepare_bill_and_ask_method(state: PaymentState):
        """Fetch bill and ask for payment method."""
        session_id = state['session_id']
        current_status = state.get('status')
        
        # Skip if already past this stage
        if current_status not in ["init", "ask_method"]:
            return {}
            
        # Check active order via SQLite
        from storage import db
        rows = db.execute_query(
            "SELECT * FROM orders WHERE table_id = ? AND status != 'PAID' AND status != 'CANCELLED' ORDER BY created_at DESC LIMIT 1",
            (session_id,)
        )
        
        if not rows:
            return {"status": "no_order", "messages": [AIMessage(content="I can't find an active order for you to pay.")]}
        
        order_data = rows[0]
        order_id = order_data['order_id']
        
        # Calculate Total
        item_rows = db.execute_query("SELECT item_id, quantity FROM order_items WHERE order_id = ?", (order_id,))
        total = 0.0
        price_map = {item.id: item.price for item in menu_ops.MENU_DB}
        for row in item_rows:
            price = price_map.get(row['item_id'], 0.0)
            total += price * row['quantity']
            
        msg = f"Your total is ₦{total:,.2f}. How would you like to pay? (Card, Cash, or Transfer)"
        return {"order_id": order_id, "amount": total, "status": "ask_method", "messages": [AIMessage(content=msg)]}

    def process_method(state: PaymentState):
        """Handle specific payment methods."""
        status = state.get('status')
        amount = state.get('amount')
        
        if status == "processing_transfer":
            msg = "Please proceed with the transfer to:\nBank: First Bank\nAcct: 3123456789\nName: Evolution Restaurant\n\nWhen done, please say 'Done' or 'Paid'."
            return {"messages": [AIMessage(content=msg)], "status": "processing_transfer"}
            
        elif status == "verifying_transfer":
            # HITL Simulation
            # If we just entered this state, we tell user to wait.
            # If we are already here (looping), we verify.
            # For simplicity, we just say waiting until logic flips status (via admin input simulation).
            msg = "Payment initiated. Waiting for verification... (Admin: say 'verified' to confirm)"
            return {"messages": [AIMessage(content=msg)], "status": "verifying_transfer"}
            
        elif status == "processing_card":
            msg = "I've alerted the kitchen/staff to bring the POS machine to you."
            kitchen_ops.send_ticket(state['order_id']) # Notify kitchen
            return {"status": "paid_success", "messages": [AIMessage(content=msg)]}
            
        elif status == "processing_cash":
             msg = "A waiter will be with you shortly to collect the cash."
             kitchen_ops.send_ticket(state['order_id'])
             return {"status": "paid_success", "messages": [AIMessage(content=msg)]}
             
        return {}

    def finalize_payment(state: PaymentState):
        """Mark as paid and ask disposition."""
        if state.get('status') != "paid_success":
            return {}
            
        # Update DB
        from storage import db
        db.execute_update("UPDATE orders SET status = 'PAID' WHERE order_id = ?", (state['order_id'],))
        
        # Send ticket if not sent (for transfer flow)
        kitchen_ops.send_ticket(state['order_id'])
        
        return {"status": "ask_disposition", "messages": [AIMessage(content="Payment confirmed! Thank you. Will you be eating here or taking it away?")]}

    workflow = StateGraph(PaymentState)
    
    workflow.add_node("analyze", analyze_payment_state)
    workflow.add_node("itemise_bill", prepare_bill_and_ask_method)
    workflow.add_node("process", process_method)
    workflow.add_node("finalize", finalize_payment)
    
    workflow.set_entry_point("analyze")
    
    workflow.add_conditional_edges(
        "analyze",
        lambda x: x['status'],
        {
            "init": "itemise_bill",
            "ask_method": "itemise_bill", # Loop back if method unclear, but ideally we wait for input. 
            # Actually, "ask_method" returns from analyze implies we just asked it. 
            # Wait, analyze is called AFTER user input.
            "processing_transfer": "process",
            "processing_card": "process",
            "processing_cash": "process",
            "verifying_transfer": "process",
            "ask_disposition": "analyze", # Wait for user input on disposition
            "complete": END,
            "no_order": END
        }
    )
    
    # Logic fix:
    # 1. Start -> analyze (status=init) -> itemise_bill -> END (user replies)
    # 2. User replies "Card" -> analyze (status=processing_card) -> process -> finalize -> END (User replies eat/take)
    # 3. User replies "Eat in" -> analyze (status=complete) -> END
    
    # We need edges from nodes to END to wait for user input?
    # LangGraph waits at END.
    
    workflow.add_edge("itemise_bill", END)
    
    workflow.add_conditional_edges(
        "process",
        lambda x: "finalize" if x.get('status') == "paid_success" else "stop",
        {
            "finalize": "finalize",
            "stop": END
        }
    )
    
    workflow.add_edge("finalize", END)
    
    return workflow.compile()
