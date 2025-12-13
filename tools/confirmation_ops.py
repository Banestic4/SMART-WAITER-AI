def requires_confirmation(amount: float) -> bool:
    """
    Determine if an action requires explicit human confirmation.
    For this app, all payments require confirmation.
    """
    return True

def format_confirmation_request(order_id: str, amount: float) -> str:
    """
    Generate the text to ask the user for confirmation.
    """
    return f"Please confirm payment of ₦{amount:,.2f} for Order {order_id}. (yes/no)"
