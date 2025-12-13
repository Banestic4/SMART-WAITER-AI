import datetime

FEEDBACK_FILE = "data/feedback.log"

def save_feedback(session_id: str, content: str):
    """Save user feedback to a file."""
    timestamp = datetime.datetime.now().isoformat()
    entry = f"[{timestamp}] Session: {session_id} | Feedback: {content}\n"
    
    try:
        with open(FEEDBACK_FILE, "a") as f:
            f.write(entry)
        return True
    except Exception as e:
        print(f"Error saving feedback: {e}")
        return False
