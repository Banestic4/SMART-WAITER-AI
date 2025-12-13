from typing import Optional, Dict
import uuid

def process_payment(order_id: str, amount: float, method: str = "credit_card") -> Dict:
    """
    Process a payment for an order.
    In a real system, this would integrate with Stripe/Square.
    """
    # Mock Processing
    transaction_id = str(uuid.uuid4())
    success = True # Mock success
    
    return {
        "success": success,
        "transaction_id": transaction_id,
        "order_id": order_id,
        "amount": amount,
        "method": method,
        "status": "COMPLETED" if success else "FAILED"
    }
