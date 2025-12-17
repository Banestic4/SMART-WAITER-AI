from typing import TypedDict
from langchain_core.messages import BaseMessage, AIMessage
from langgraph.graph import StateGraph, END
from tools import order_ops, payment_ops, confirmation_ops, menu_ops, kitchen_ops
import requests
from config import Config

class PaymentState(TypedDict):
    messages: list[BaseMessage]
    session_id: str
    order_id: str
    amount: float
    status: str
    account_name: str
    transfer_amount: str
    disposition: str

def create_payment_workflow(llm):
    
    
    def analyze_payment_state(state: PaymentState):
        """
        Determine flow based on user's last message.
        Determine flow based on user's last instructions.
        Statuses: init -> ask_method -> processing_transfer -> collecting_transfer_details -> verifying_payment -> waiting_for_admin -> paid_success -> ask_disposition -> complete
        """
        messages = state.get('messages', [])
        current_status = state.get('status', 'init')
        last_msg = messages[-1].content.lower() if messages else ""
        
        updates = {}
        
        # 1. Method Selection
        if current_status in ["ask_method", "method_clarification"]:
            # Quick Keyword Checks
            if "transfer" in last_msg: return {"status": "processing_transfer"}
            if "card" in last_msg or "pos" in last_msg: return {"status": "processing_card"}
            if "cash" in last_msg: return {"status": "processing_cash"}
            if any(w in last_msg for w in ["cancel", "stop", "change", "no"]):
                 return {"status": "cancelled", "messages": [AIMessage(content="Payment cancelled.")]}

            # LLM Semantic Check for "Intent to Pay" vs "Confusion"
            prompt = f"User said: '{last_msg}'. Context: Choosing payment method. If user wants to pay/proceed, return 'PROCEED'. If card/cash/transfer mentioned, return method. Else 'UNKNOWN'."
            response = llm.invoke([AIMessage(content=prompt)]).content.upper()
            
            if "PROCEED" in response or "PAY" in response:
                 return {"status": "ask_method"} # Loop to re-ask method
            else:
                 return {"status": "method_clarification", "messages": [AIMessage(content="Please select: **Card**, **Cash**, or **Transfer**.")]}

        # 2. Transfer: Payment Confirmation
        if current_status == "processing_transfer":
            # Semantic Check for "I have paid"
            if any(w in last_msg for w in ["paid", "done", "transferred", "sent", "receipt"]):
                 return {"status": "collecting_transfer_details"}
                 
            # Fallback LLM Check
            prompt = f"User said: '{last_msg}'. Context: User asked to transfer money. Did they confirm they finished paying? Return 'YES' or 'NO'."
            response = llm.invoke([AIMessage(content=prompt)]).content.strip().upper()
            
            if "YES" in response:
                return {"status": "collecting_transfer_details"}
            elif "cancel" in last_msg:
                 return {"status": "ask_method"}

        # 3. Transfer: Collection -> Verification
        if current_status == "collecting_transfer_details":
            return {"status": "verifying_payment", "account_name": last_msg, "transfer_amount": "CHECK"}

        # 4. Verification Check
        """
        Admin Verification simple means that if admin comfirms the transaction then proceed to the next stage.
        If admin did not confirm the transaction then proceed to the previous stage by notifying the client admin is yet to confrim the transaction.
        If admin cancel the transaction notify the client that tarnsaction is cancelled.
        """
        if current_status in ["verifying_payment", "waiting_for_admin"]:
            if "system_event: admin_verified" in last_msg.lower():
                 return {"status": "paid_success"}
            elif "system_event: admin_denied" in last_msg.lower():
                 return {"status": "init", "messages": [AIMessage(content="Payment verification failed. Please try again or ask staff for help.")]}
            else:
                 # Interaction Loop Fix:
                 # If user types something else, do NOT go back to 'verifying_payment' (which triggers 'process' node and resends alert).
                 # Instead, go to a quiet state.
                 return {"status": "waiting_for_admin", "messages": [AIMessage(content="We are still waiting for confirmation. Please accept our apologies for the little delay.")]}


        # 4. Post-Payment Disposition (Eat in / Takeaway)
        if current_status == "ask_disposition":
            msg_content = ""
            disposition = "Eat In" # default
            
            # LLM Semantic Check for Disposition
            prompt = f"User said: '{last_msg}'. Context: Done eating/paying. Options: Eat In, Takeaway, Pickup, Delivery. Classify user intent. Return category name only."
            class_resp = llm.invoke([AIMessage(content=prompt)]).content.upper()
            
            if "TAKE" in class_resp or "GO" in class_resp:
                disposition = "Takeaway"
                msg_content = "Okay, we will package it for takeaway. Please wait a moment."
            elif "PICKUP" in class_resp:
                disposition = "Pickup"
                msg_content = "Okay, your order will be ready for pickup shortly."
            elif "DELIVER" in class_resp:
                disposition = "Delivery"
                msg_content = "Okay, we will arrange for delivery to your location."
            else:
                 msg_content = "Great, please have a seat. Your food will be served shortly."
                 disposition = "Eat In"
            
            # Send ticket to kitchen NOW, with the correct disposition
            kitchen_ops.send_ticket(state['order_id'], notes=disposition)
                 
            return {"status": "complete", "disposition": disposition, "messages": [AIMessage(content=msg_content)]}
                 
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
            msg = "Please proceed with the transfer to:\nBank: Monie point\nAcct: 123456789\nName: Evolution Restaurant\n\nWhen done, please say 'Done' or 'Paid'."
            return {"messages": [AIMessage(content=msg)], "status": "processing_transfer"}
            
        elif status == "collecting_transfer_details":
            msg = "Thank you. Please provide the Account Name and Amount sent (e.g., 'John Doe 5000')."
            return {"messages": [AIMessage(content=msg)], "status": "collecting_transfer_details"}

        elif status == "verifying_payment":
            # Notify Admin
            user_details = state.get('account_name', 'Unknown')
            order_id = state.get('order_id', 'Unknown')
            amount = state.get('amount', 0.0)
            
            # Send Notification to Admin via Telegram API
            admin_chat_id = Config.TELEGRAM_ADMIN_CHAT_ID
            print(f"DEBUG: Processing verification. Admin ID: {admin_chat_id}, Order: {order_id}, Amount: {amount}")
            
            if admin_chat_id:
                try:
                    text = f"🚨 **Payment Alert**\nOrder Hash: `{order_id}`\nAmount: ₦{amount:,.2f}\nUser Details: {user_details}"
                    
                    if user_details == 'Card Request':
                         text = f"💳 **Card Payment Request**\nOrder: `{order_id}`\nAmount: ₦{amount:,.2f}\nAction: Please bring POS to customer."
                    elif user_details == 'Cash Request':
                         text = f"💵 **Cash Payment Request**\nOrder: `{order_id}`\nAmount: ₦{amount:,.2f}\nAction: Please collect cash from customer."
                    
                    # Create Inline Keyboard Payload
                    # Telegram API requires `reply_markup` as JSON string
                    import json
                    reply_markup = {
                        "inline_keyboard": [
                            [
                                {"text": "✅ Confirm Payment", "callback_data": f"approve_{order_id}"},
                                {"text": "❌ Deny / Cancel", "callback_data": f"deny_{order_id}"}
                            ]
                        ]
                    }
                    
                    url = f"https://api.telegram.org/bot{Config.TELEGRAM_TOKEN}/sendMessage"
                    requests.post(url, json={
                        "chat_id": admin_chat_id, 
                        "text": text, 
                        "parse_mode": "Markdown",
                        "reply_markup": reply_markup # Sends buttons!
                    })
                    print(f"DEBUG: Notification sent to {admin_chat_id}. Status Code: {requests.post}") 
                except Exception as e:
                    print(f"Failed to notify admin: {e}")
            else:
                 print("WARNING: TELEGRAM_ADMIN_CHAT_ID not set.")

            if user_details == 'Card Request':
                msg = "I've alerted the staff to bring the POS machine. \nOne moment please..."
            elif user_details == 'Cash Request':
                msg = "A waiter will be with you shortly to collect the cash. \nOne moment please..."
            else:
                msg = f"Payment details received: '{user_details}'.\nWe have notified the administrator. Your payment is pending approval. You will receive a confirmation message shortly."
            
            return {"messages": [AIMessage(content=msg)], "status": "verifying_payment"}

            
        elif status == "processing_card":
            # Trigger verification (notification) with flags
            return {"status": "verifying_payment", "account_name": "Card Request"}
            
        elif status == "processing_cash":
             # Trigger verification (notification) with flags
             return {"status": "verifying_payment", "account_name": "Cash Request"}
             
        return {}

    def finalize_payment(state: PaymentState):
        """Mark as paid and ask disposition."""
        # Note: finalize sets status to 'ask_disposition', so the NEXT user message 
        # is processed by 'analyze' which sees 'ask_disposition'.
        # But 'finalize' is called automatically after 'process' (if paid_success).
        
        if state.get('status') != "paid_success":
            return {}
            
        # Update DB
        from storage import db
        db.execute_update("UPDATE orders SET status = 'PAID' WHERE order_id = ?", (state['order_id'],))
        
        # Send ticket logic moved to 'analyze' (after user confirms disposition)
        # kitchen_ops.send_ticket(state['order_id'], notes=disposition)
        
        return {"status": "ask_disposition", "messages": [AIMessage(content="Payment confirmed! Thank you. Will you be eating here, taking it away, picking it up, or do you want delivery?")]}

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
            "ask_method": "itemise_bill", 
            "method_clarification": END, # Don't re-itemise, just return the clarification message
            "processing_transfer": "process",
            "collecting_transfer_details": "process",
            "processing_card": "process",
            "processing_cash": "process",
            "verifying_payment": "process",
            "waiting_for_admin": END, # Quiet wait
            "ask_disposition": "analyze",
            "paid_success": "process",
            "complete": END,
            "cancelled": END,
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
