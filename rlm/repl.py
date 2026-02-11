import sys
from io import StringIO
import contextlib
import traceback
from typing import Any, Dict, List, Optional
from .utils.llm import GeminiClient

class REPL:
    def __init__(self, context: Any, recursive_turn_limit: int = 3, llm_client: GeminiClient = None):
        self.context = context
        self.recursive_turn_limit = recursive_turn_limit
        self.llm_client = llm_client or GeminiClient()
        self.history = []

    def llm_query(self, query: str) -> str:
        """
        Allows the REPL to query an LLM (Simulated Sub-RLM or direct LLM).
        In a full recursive implementation, this would instantiate a new RLM.
        For depth=1 or simple RLM, this queries the base LLM.
        """
        # Simple Direct LLM query for now (Depth-1)
        # To make it truly recursive, we would call RLM_REPL here.
        try:
             # Basic context injection if needed, or just raw query
             return self.llm_client.completion(messages=query)
        except Exception as e:
            return f"Error querying LLM: {str(e)}"

    def execute(self, code: str) -> str:
        """
        Executes Python code in the REPL environment.
        Captures stdout and returns it.
        """
        # Create a buffer to capture output
        f = StringIO()
        
        # Define the execution scope
        # We inject 'context' and 'llm_query' into the scope
        scope = {
            "context": self.context,
            "llm_query": self.llm_query,
            "print": print, # Ensure print is available (though we capture stdout)
            # Add other safe built-ins if needed
        }
        
        try:
            with contextlib.redirect_stdout(f):
                exec(code, scope)
            
            output = f.getvalue()
            return output if output else "(No output)"
            
        except Exception as e:
            return f"Runtime Error: {traceback.format_exc()}"
