import os
from typing import List, Any, Optional
from langchain_groq import ChatGroq
from langchain_core.messages import BaseMessage
from langchain_core.language_models import BaseChatModel
from config import Config
import time

class RotatingGroqLLM:
    """
    A wrapper around ChatGroq that rotates API keys on RateLimitError.
    Duck-types enough of BaseChatModel to work with LangGraph/LangChain.
    """
    def __init__(self, model_name: str = Config.GROQ_MODEL):
        self.keys = Config.GROQ_API_KEYS
        self.current_key_val = 0
        self.model_name = model_name
        self._initialize_llm()
        
    def _initialize_llm(self):
        if not self.keys:
            raise ValueError("No Groq API Keys found in config.")
        
        api_key = self.keys[self.current_key_val]
        # print(f"DEBUG: Initializing Groq with Key Ending: ...{api_key[-4:]}")
        self._llm = ChatGroq(
            api_key=api_key,
            model_name=self.model_name,
            temperature=0.3
        )

    def rotate_key(self):
        """Switch to the next available API key."""
        if len(self.keys) <= 1:
            print("Warning: Only one key available. Cannot rotate.")
            return
            
        self.current_key_val = (self.current_key_val + 1) % len(self.keys)
        print(f"--- Rotating API Key to Index {self.current_key_val} ---")
        self._initialize_llm()

    def invoke(self, input: Any, config: Optional[dict] = None, **kwargs):
        """Pass through invoke calls with error handling."""
        max_retries = len(self.keys) + 1
        attempts = 0
        
        while attempts < max_retries:
            try:
                return self._llm.invoke(input, config=config, **kwargs)
            except Exception as e:
                # Basic check for 429 or Rate Limit string
                error_str = str(e).lower()
                if "429" in error_str or "rate limit" in error_str or "401" in error_str or "invalid api key" in error_str:
                    print(f"Key Error Hit: {e}")
                    self.rotate_key()
                    attempts += 1
                    time.sleep(1) # Brief pause
                else:
                    # Reraise other errors
                    raise e
                    
        raise Exception("Rate Limit exceeded on ALL keys.")

    def stream(self, input: Any, config: Optional[dict] = None, **kwargs):
        """Pass through stream calls with error handling."""
        max_retries = len(self.keys) + 1
        attempts = 0
        
        while attempts < max_retries:
            try:
                # We yield from the stream
                for chunk in self._llm.stream(input, config=config, **kwargs):
                    yield chunk
                return # Success
            except Exception as e:
                error_str = str(e).lower()
                if "429" in error_str or "rate limit" in error_str or "401" in error_str or "invalid api key" in error_str:
                    print(f"Key Error Hit during stream: {e}")
                    self.rotate_key()
                    attempts += 1
                    time.sleep(1)
                else:
                    raise e
                    
        raise Exception("Rate Limit exceeded on ALL keys (stream).")

    async def astream(self, input: Any, config: Optional[dict] = None, **kwargs):
        """Pass through async stream calls with error handling."""
        max_retries = len(self.keys) + 1
        attempts = 0
        
        while attempts < max_retries:
            try:
                # We yield from the async stream
                async for chunk in self._llm.astream(input, config=config, **kwargs):
                    yield chunk
                return # Success
            except Exception as e:
                error_str = str(e).lower()
                if "429" in error_str or "rate limit" in error_str or "401" in error_str or "invalid api key" in error_str:
                    print(f"Key Error Hit during astream: {e}")
                    self.rotate_key()
                    attempts += 1
                    # Async sleep? We usually can just run the loop
                else:
                    raise e
                    
        raise Exception("Rate Limit exceeded on ALL keys (astream).")

    def bind_tools(self, tools: list):
        """Pass through bind_tools."""
        # This returns a Runnable, we need to wrap that too? 
        # Actually for this agent we mostly use raw invoke or structured output?
        # If the agent uses .bind_tools(), it returns a Bound object which executes .invoke()
        # That .invoke() eventually calls our _llm.invoke(). 
        # BUT _llm.bind_tools() returns a new object unrelated to 'self'.
        # So we must verify usage.
        # SmartWaiter uses direct `.invoke()` mostly via LangGraph nodes.
        # If we use `bind_tools`, we might lose the rotation wrapper if we just return self._llm.bind_tools(...)
        # Correct approach: Return a new Wrapper that holds the bound LLM?
        # For Smart Waiter, we don't heavily use bind_tools in the Router/Nodes, we use prompts.
        # Let's see if we need it. 
        return self._llm.bind_tools(tools)
        
    # Proxy all other attribute access to the underlying LLM
    def __getattr__(self, name):
        return getattr(self._llm, name)

# Singleton or Factory
def get_rotating_llm():
    return RotatingGroqLLM()
