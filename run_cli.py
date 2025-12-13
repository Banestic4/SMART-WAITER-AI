from agents.smart_waiter_agent import SmartWaiterAgent
import uuid

def run_chat_loop():
    print("--- Smart Waiter Agent CLI ---")
    print("Type 'exit' to quit.")
    
    agent = SmartWaiterAgent()
    session_id = str(uuid.uuid4())[:8]
    print(f"Session ID: {session_id}\n")
    
    while True:
        try:
            user_input = input("You: ")
            if user_input.lower() in ["exit", "quit"]:
                print("Goodbye!")
                break
            if not user_input.strip():
                continue
                
            response = agent.run(user_input, session_id=session_id)
            print(f"Agent: {response}\n")
            
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    run_chat_loop()
