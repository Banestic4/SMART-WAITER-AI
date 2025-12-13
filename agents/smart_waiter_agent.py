from typing import TypedDict, Annotated, List, Union
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langchain_groq import ChatGroq
from langgraph.checkpoint.memory import MemorySaver
from config import Config
from workflows.ordering_flow import create_ordering_workflow
from workflows.payment_flow import create_payment_workflow
from workflows.fulfillment_flow import create_fulfillment_workflow
from workflows.feedback_flow import create_feedback_workflow

class AgentState(TypedDict):
    """The state of the agent, tracking conversation and context."""
    messages: Annotated[List[BaseMessage], add_messages]
    intent: str
    session_id: str
    intermediate_steps: List[dict] # Added for workflow compatibility logic
    
class SmartWaiterAgent:
    """Core reasoning & decision engine for the Smart Waiter."""
    
    def __init__(self):
        self._llm = self._initialize_llm()
        self.checkpointer = MemorySaver()
        self.graph = self._build_graph()
        
    def _initialize_llm(self):
        """Initialize the LLM based on configuration."""
        if Config.GROQ_API_KEY:
             return ChatGroq(
                 api_key=Config.GROQ_API_KEY, 
                 model_name="llama-3.3-70b-versatile",
                 temperature=0
             )
        else:
            raise ValueError("No GROQ_API_KEY found. This agent relies exclusively on Meta AI via Groq.")

    def _decide_intent(self, state: AgentState):
        """Analyze the user's last message to determine intent."""
        messages = state['messages']
        
        system_prompt = SystemMessage(content="""
        You are the brain of the Smart Waiter.
        Analyze the conversation.
        
        Context: The user might be replying to a previous question.
        Language: You understand and speak English and Nigerian languages (Yoruba, Igbo, Hausa, Pidgin). 
        Identify the language the user is speaking and reply in that same language (or English if unclear).
        
        Classify the user's intent:
        - MENU: User asks about menu.
        - ORDER: User wants to order.
        - PAYMENT: User wants to pay OR confirms payment (e.g., "Yes", "Confirm", "Ehen").
        - STATUS: User asks for order status (e.g., "Is my food ready?", "Where is my order?").
        - FEEDBACK: User gives a review or feedback (e.g., "Good food", "Terrible service", "Thank you", "Great job").
        - GENERAL: General chat.
        
        Respond ONLY with the category name.
        """)
        
        response = self._llm.invoke([system_prompt] + messages)
        intent = response.content.strip().upper()
        
        valid_intents = ["MENU", "ORDER", "PAYMENT", "STATUS", "FEEDBACK", "GENERAL"]
        if intent not in valid_intents:
            intent = "GENERAL"
        
        # Simple override for confirmation keywords if context implies payment
        last_msg = messages[-1].content.lower()
        if "yes" in last_msg or "confirm" in last_msg:
             # Ideally we check if previous message was from Payment Workflow, 
             # but "PAYMENT" routing handles the "analyze" step which checks for confirmation.
             intent = "PAYMENT"
            
        return {"intent": intent}

    def _general_response(self, state: AgentState):
        """Handle general conversation."""
        messages = state['messages']
        response = self._llm.invoke(messages)
        return {"messages": [response]}

    def _build_graph(self):
        """Construct the state graph."""
        workflow = StateGraph(AgentState)

        # Subgraphs
        ordering_app = create_ordering_workflow(self._llm)
        payment_app = create_payment_workflow(self._llm)
        fulfillment_app = create_fulfillment_workflow(self._llm)
        feedback_app = create_feedback_workflow(self._llm)
        
        def call_ordering(state: AgentState):
            inputs = {"messages": state['messages'], "session_id": state['session_id']}
            result = ordering_app.invoke(inputs)
            # Extract the last message (response) from the subgraph
            if result['messages'] and isinstance(result['messages'][-1], AIMessage):
                 return {"messages": [result['messages'][-1]]}
            return {}

        def call_payment(state: AgentState):
            # Payment flow handles its own state initialization mostly
            inputs = {"messages": state['messages'], "session_id": state['session_id'], "order_id": "", "amount": 0.0, "status": "init"}
            result = payment_app.invoke(inputs)
            if result.get('messages') and isinstance(result['messages'][-1], AIMessage):
                 return {"messages": [result['messages'][-1]]}
            return {}

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

        # Nodes
        workflow.add_node("router", self._decide_intent)
        workflow.add_node("general_handler", self._general_response)
        workflow.add_node("ordering_subprocess", call_ordering)
        workflow.add_node("payment_subprocess", call_payment)
        workflow.add_node("fulfillment_subprocess", call_fulfillment)
        workflow.add_node("feedback_subprocess", call_feedback)
        
        # Entry
        workflow.set_entry_point("router")
        
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
                "GENERAL": "general_handler"
            }
        )
        
        workflow.add_edge("ordering_subprocess", END)
        workflow.add_edge("payment_subprocess", END)
        workflow.add_edge("fulfillment_subprocess", END)
        workflow.add_edge("feedback_subprocess", END)
        workflow.add_edge("general_handler", END)
        
        return workflow.compile(checkpointer=self.checkpointer)
    
    def run(self, input_text: str, session_id: str = "default") -> str:
        """Run the agent graph."""
        # Use config to specify thread_id for persistence
        config = {"configurable": {"thread_id": session_id}}
        
        inputs = {
            "messages": [HumanMessage(content=input_text)],
            "session_id": session_id,
        }
        
        # invoke with config enabling memory
        result = self.graph.invoke(inputs, config=config)
        
        # Extract response from the last message in the list
        if result["messages"]:
            return result["messages"][-1].content
        else:
            return "Error: No response generated."
