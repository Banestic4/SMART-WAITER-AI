from typing import TypedDict, Annotated, List, Union
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from config import Config
from tools.llm_manager import get_rotating_llm
from workflows.ordering_flow import create_ordering_workflow
from workflows.payment_flow import create_payment_workflow
from workflows.fulfillment_flow import create_fulfillment_workflow
from workflows.feedback_flow import create_feedback_workflow
from workflows.onboarding_flow import create_onboarding_workflow

class AgentState(TypedDict):
    """The state of the agent, tracking conversation and context."""
    messages: Annotated[List[BaseMessage], add_messages]
    intent: str
    session_id: str
    language: str | None
    interaction_mode: str | None
    payment_status: str | None
    payment_amount: float | None
    payment_order_id: str | None
    table_number: str | None
    intermediate_steps: List[dict] # Added for workflow compatibility logic
    
class SmartWaiterAgent:
    """Core reasoning & decision engine for the Smart Waiter."""
    
    def __init__(self):
        self._llm = get_rotating_llm()
        self.checkpointer = MemorySaver()
        self.graph = self._build_graph()

    def _decide_intent(self, state: AgentState):
        """Analyze the user's last message to determine intent."""
        messages = state['messages']
        
        # Get language from state, default to English if not set yet (though onboarding ensures it is)
        language = state.get('language', 'English')
        
        system_prompt = SystemMessage(content=f"""
        You are the brain of the Smart Waiter.
        Analyze the conversation.
        
        Context: The user might be replying to a previous question.
        Language: The user's preferred language is {language}. Reply in {language}.
        
        Classify the user's intent:
        Classify the user's intent:
        - MENU: User asks about menu or says "Would you like to see our menu?" (contextual yes/no).
        - ORDER: User wants to order (e.g., "Get me a coke", "I want a burger", "Add fries", "Give me rice").
          * NOTE: If user asks "How much is X?", classify as GENERAL so the general handler can quote the price. 
          * Wait, user requirement says "tell user price... and request if it should be added". 
          * Use GENERAL for price check -> The General Handler prompt already handles "How much is X -> tell price".
        - ORDER-CONFIRMATION: User gives final verdict on orders made (e.g., "thats all my order", "am done ordering", "am done", ").
        - PAYMENT: User wants to pay OR confirms payment (e.g., "Yes", "i want to pay", "thats all for now", "Confirm", "Ehen", "Proceed").
        - PAYMENT-STATUS: User asks for Payment status (e.g., "Is my payment recieved?", "please confirm my payment?").
        - FEEDBACK: User gives a review or feedback (e.g., "Good food", "Terrible service", "Thank you", "Great job").
        - GENERAL: General chat.
        
        Respond ONLY with the category name.
        
        CRITICAL RULES:
        1. You are NOT a generic assistant. You are ONLY a waiter for this specific restaurant (Evolution Restaurant Social Center ABU Zaria).
        2. If the user asks for anything not related to food, ordering, payment, or this restaurant (e.g., "buy rice on Amazon", "plan a vacation"), classify it as "GENERAL" but in your response (handled elsewhere), you must clearly refuse.
        3. Do NOT provide external links, recipes, or advice about other businesses.
        """)
        
        response = self._llm.invoke([system_prompt] + messages)
        intent = response.content.strip().upper()
        
        valid_intents = ["MENU", "ORDER", "ORDER-CONFIRMATION", "PAYMENT", "PAYMENT-STATUS", "FEEDBACK", "GENERAL"]
        if intent not in valid_intents:
            intent = "GENERAL"
        
        # Override: If we are deep in payment flow, keep routing to payment
        pay_status = state.get("payment_status")
        if pay_status and pay_status not in ["init", "complete", "cancelled", "paid_success", "no_order", None]:
             # "paid_success" leads to "finalize" -> "ask_disposition", so we need to capture "Eat in" response.
             # Actually "paid_success" is internal. The stopping state is "ask_disposition".
             # Let's list active states.
             if pay_status in ["ask_method", "processing_transfer", "verifying_transfer", "ask_disposition"]:
                 intent = "PAYMENT"

        # Simple override for confirmation keywords if context implies payment
        last_msg = messages[-1].content.lower()
        if "yes" in last_msg or "confirm" in last_msg:
             # Ideally we check if previous message was from Payment Workflow, 
             # but "PAYMENT" routing handles the "analyze" step which checks for confirmation.
             intent = "PAYMENT"
            
        return {"intent": intent}

    def _general_response(self, state: AgentState):
        """Handle general conversation with strict restriction."""
        messages = state['messages']
        
        # Fetch real menu data for accurate prices and items
        from tools import menu_ops
        menu = menu_ops.get_menu()
        
        # Format menu string for context
        menu_context = "MENU:\n"
        
        # Group by category
        grouped_menu = {}
        for item in menu:
            cat = item.get('category', 'Others')
            if cat not in grouped_menu:
                grouped_menu[cat] = []
            grouped_menu[cat].append(item)
            
        for category, items in grouped_menu.items():
            menu_context += f"\n**{category}**\n"
            for item in items:
                menu_context += f"- {item['name']}: ₦{item['price']:,.2f}\n"

        lang = state.get("language", "English")
        system_msg = f"""You are Smart-Waiter (Evolution Restaurant).
        Current Language: {lang}.
        CRITICAL INSTRUCTION: You MUST respond in {lang} language ONLY.
        
        Use the following menu information to answer:
        {menu_context}
        
        Short, polite, friendly.
        If asking for price, look it up in context or say you don't know but can check the menu.
        If ordering, confirm item availability from context (if any).
        """
        
        # Simple invocation
        response = self._llm.invoke([SystemMessage(content=system_msg)] + state['messages'])
        return {"messages": [response], "language": lang}

    def _build_graph(self):
        """Construct the state graph."""
        workflow = StateGraph(AgentState)

        # Subgraphs
        ordering_app = create_ordering_workflow(self._llm)
        payment_app = create_payment_workflow(self._llm)
        fulfillment_app = create_fulfillment_workflow(self._llm)
        feedback_app = create_feedback_workflow(self._llm)
        onboarding_app = create_onboarding_workflow(self._llm)
        
        def call_onboarding(state: AgentState):
            inputs = {
                "messages": state['messages'], 
                "session_id": state['session_id'],
                "language": state.get("language"),
                "interaction_mode": state.get("interaction_mode"),
                "table_number": state.get("table_number")
            }
            result = onboarding_app.invoke(inputs)
            
            # Map back state
            updates = {}
            if result.get("language"): updates["language"] = result["language"]
            if result.get("interaction_mode"): updates["interaction_mode"] = result["interaction_mode"]
            if result.get("table_number"): updates["table_number"] = result["table_number"]
            
            if result.get('messages') and isinstance(result['messages'][-1], AIMessage):
                 updates["messages"] = [result['messages'][-1]]
                 
            return updates

        def call_ordering(state: AgentState):
            inputs = {"messages": state['messages'], "session_id": state['session_id']}
            result = ordering_app.invoke(inputs)
            # Extract the last message (response) from the subgraph
            if result['messages'] and isinstance(result['messages'][-1], AIMessage):
                 return {"messages": [result['messages'][-1]]}
            return {}

        def call_payment(state: AgentState):
            # Pass existing payment state
            inputs = {
                "messages": state['messages'], 
                "session_id": state['session_id'], 
                "order_id": state.get("payment_order_id", ""), 
                "amount": state.get("payment_amount", 0.0), 
                "status": state.get("payment_status", "init")
            }
            result = payment_app.invoke(inputs)
            
            updates = {}
            # Map back state updates
            if "status" in result: updates["payment_status"] = result["status"]
            if "amount" in result: updates["payment_amount"] = result["amount"]
            if "order_id" in result: updates["payment_order_id"] = result["order_id"]
            
            if result.get('messages') and isinstance(result['messages'][-1], AIMessage):
                 updates["messages"] = [result['messages'][-1]]
            
            return updates

        def call_fulfillment(state: AgentState):
            inputs = {"messages": state['messages'], "session_id": state['session_id']}
            result = fulfillment_app.invoke(inputs)
            if result['messages'] and isinstance(result['messages'][-1], AIMessage):
                 return {"messages": [result['messages'][-1]]}
            return {}
            
        def call_feedback(state: AgentState):
            inputs = {"messages": state['messages'], "session_id": state['session_id']}
            result = feedback_app.invoke(inputs)
            if result['messages'] and isinstance(result['messages'][-1], AIMessage):
                 return {"messages": [result['messages'][-1]]}
            return {}

        def check_onboarding(state: AgentState):
            """Check if user has completed onboarding."""
            if not state.get("language") or not state.get("interaction_mode") or not state.get("table_number"):
                return "onboarding"
            return "router"

        # Nodes
        workflow.add_node("check_onboarding", lambda x: {}) # Dummy node for entry logic or just use conditional
        workflow.add_node("onboarding_subprocess", call_onboarding)
        workflow.add_node("router", self._decide_intent)
        workflow.add_node("general_handler", self._general_response)
        workflow.add_node("ordering_subprocess", call_ordering)
        workflow.add_node("payment_subprocess", call_payment)
        workflow.add_node("fulfillment_subprocess", call_fulfillment)
        workflow.add_node("feedback_subprocess", call_feedback)
        
        # Entry
        workflow.set_conditional_entry_point(
            check_onboarding,
            {
                "onboarding": "onboarding_subprocess",
                "router": "router"
            }
        )
        
        # Routing Logic
        workflow.add_conditional_edges(
            "router",
            lambda x: x['intent'],
            {
                "MENU": "general_handler", 
                "ORDER": "ordering_subprocess", 
                "PAYMENT": "payment_subprocess",
                "STATUS": "fulfillment_subprocess",
                "FEEDBACK": "feedback_subprocess",
                "GENERAL": "general_handler",
                "ORDER-CONFIRMATION": "general_handler",
                "PAYMENT-STATUS": "general_handler"
            }
        )
        
        workflow.add_edge("onboarding_subprocess", END)
        
        workflow.add_edge("ordering_subprocess", END)
        workflow.add_edge("payment_subprocess", END)
        workflow.add_edge("fulfillment_subprocess", END)
        workflow.add_edge("feedback_subprocess", END)
        workflow.add_edge("general_handler", END)
        
        return workflow.compile(checkpointer=self.checkpointer)
    
    async def astream_run(self, input_text: str, session_id: str = "default"):
        """
        Async streaming version of run.
        Yields tokens for the response.
        Handles translation:
        - If not English: Translates input -> English, Runs -> Buffers Result -> Translates Output -> Yields
        - If English: Yields tokens directly from LLM stream
        """
        from tools import translator as trans
        # 1. State Inspection (Sync or Async?)
        config = {"configurable": {"thread_id": session_id}}
        state_snapshot = self.graph.get_state(config)
        
        # Default language logic
        language = "English"
        if state_snapshot and state_snapshot.values:
             language = state_snapshot.values.get("language", "English")

        # 2. Translate Input
        eng_input = input_text
        if language and language.lower() != "english":
             # Note: trans.translate is synchronous. In async app, this blocks loop briefly.
             # Ideally run in threadpool, but for now direct call is acceptable.
             eng_input = trans.translate(input_text, src_lang=language, target_lang="english")
        
        inputs = {
            "messages": [HumanMessage(content=eng_input)],
            "session_id": session_id,
        }

        # 3. Stream
        if language and language.lower() == "english":
            # True Streaming
            async for event in self.graph.astream_events(inputs, config=config, version="v2"):
                kind = event["event"]
                # Look for chat model stream events
                if kind == "on_chat_model_stream":
                    content = event["data"]["chunk"].content
                    if content:
                        yield content
        else:
            # Simulated Streaming (Buffer -> Translate -> Yield)
            full_response = ""
            async for event in self.graph.astream_events(inputs, config=config, version="v2"):
                kind = event["event"]
                if kind == "on_chat_model_stream":
                    content = event["data"]["chunk"].content
                    if content:
                        full_response += content
            
            # Now translate
            translated_response = trans.translate(full_response, src_lang="english", target_lang=language)
            yield translated_response

    def run(self, input_text: str, session_id: str = "default") -> str:
        """Run the agent graph with translation middleware."""
        from tools import translator
        trans = translator.get_translator()
        
        # 1. Inspect state to find language (default English)
        config = {"configurable": {"thread_id": session_id}}
        state_snapshot = self.graph.get_state(config)
        language = "English"
        if state_snapshot and state_snapshot.values:
             language = state_snapshot.values.get("language", "English")
             
        # 2. Translate Input (User -> English)
        # Only translate if language is set and not English
        eng_input = input_text
        if language and language.lower() != "english":
            # print(f"DEBUG: Translating input from {language}...")
            eng_input = trans.translate(input_text, src_lang=language, target_lang="english")
            # print(f"DEBUG: Translated: {eng_input}")
            
        inputs = {
            "messages": [HumanMessage(content=eng_input)],
            "session_id": session_id,
        }
        
        # 3. Invoke Agent (English)
        result = self.graph.invoke(inputs, config=config)
        
        # Extract response
        raw_response = "Error: No response."
        if result["messages"]:
            raw_response = result["messages"][-1].content
            
        # 4. Translate Output (English -> User)
        final_response = raw_response
        # Check newly updated language (in case onboarding just finished)
        new_language = result.get("language", language)
        
        if new_language and new_language.lower() != "english":
             # print(f"DEBUG: Translating output to {new_language}...")
             final_response = trans.translate(raw_response, src_lang="english", target_lang=new_language)
             
        return final_response
