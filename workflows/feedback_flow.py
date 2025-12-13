from typing import TypedDict
from langchain_core.messages import BaseMessage, AIMessage
from langgraph.graph import StateGraph, END
from tools import feedback_ops

class FeedbackState(TypedDict):
    messages: list[BaseMessage]
    session_id: str

def create_feedback_workflow(llm):
    
    def process_feedback(state: FeedbackState):
        messages = state['messages']
        session_id = state['session_id']
        
        # The last human message contains the feedback
        feedback_text = messages[-1].content
        
        feedback_ops.save_feedback(session_id, feedback_text)
        
        return {"messages": [AIMessage(content="Thank you for your feedback! We appreciate it.")]}

    workflow = StateGraph(FeedbackState)
    workflow.add_node("process", process_feedback)
    workflow.set_entry_point("process")
    workflow.add_edge("process", END)
    
    return workflow.compile()
