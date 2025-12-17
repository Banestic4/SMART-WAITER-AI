from langchain_core.tools import tool

@tool
def calculate(expression: str) -> str:
    """
    Evaluates a mathematical expression.
    Useful for calculating prices, totals, or performing basic arithmetic.
    Supports +, -, *, /, and parentheses ().
    Example: "500 * 5", "(10 + 5) * 200"
    """
    try:
        # allowed chars
        allowed = set("0123456789+-*/(). ")
        if not all(c in allowed for c in expression):
            return "Error: Invalid characters in expression."
            
        result = eval(expression, {"__builtins__": None}, {})
        return str(result)
    except Exception as e:
        return f"Error: {str(e)}"
