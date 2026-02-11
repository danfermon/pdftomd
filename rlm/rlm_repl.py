from typing import Any, Dict, List, Optional
from .repl import REPL
from .utils.llm import GeminiClient
from .utils.prompts import build_system_prompt, next_action_prompt
from .utils.utils import parse_code_blocks, parse_final_answer

class RLM_REPL:
    def __init__(
        self,
        model: str = "gemini-2.0-flash",
        recursive_model: str = "gemini-2.0-flash",
        enable_logging: bool = False,
        max_iterations: int = 10
    ):
        self.model = model
        self.recursive_model = recursive_model
        self.enable_logging = enable_logging
        self.max_iterations = max_iterations
        
        self.client = GeminiClient(model=self.model)
        # potentially separate client for recursive calls if needed

    def completion(self, context: Any, query: str) -> str:
        """
        Main entry point for RLM.
        """
        # Initialize REPL with context
        repl = REPL(context=context, llm_client=self.client)
        
        # Initialize History with System Prompt
        history = build_system_prompt()
        
        iteration = 0
        while iteration < self.max_iterations:
            if self.enable_logging:
                print(f"--- Iteration {iteration + 1} ---")

            # 1. Ask LLM for next action
            # We use a trick: we don't append every single step to the main history 
            # to avoid context window explosion, or we manage it carefully.
            # Here, we reconstruct the prompt state.
            
            current_prompt_msg = next_action_prompt(query, iteration)
            
            # Temporary history for this turn
            current_history = history + [current_prompt_msg]
            
            # Call LLM
            response_text = self.client.completion(current_history)
            
            if self.enable_logging:
                print(f"LLM Response: {response_text}")

            # 2. Parse Output
            # Check for FINAL answer first
            final_res = parse_final_answer(response_text)
            if final_res:
                if final_res['type'] == 'direct':
                    return final_res['value']
                elif final_res['type'] == 'variable':
                    # Retrieve variable from REPL scope (not implemented in simple REPL yet)
                    # For now, we assume simple string return or direct answer.
                    return f"Variable return not fully implemented: {final_res['value']}"
            
            # Check for Code Block to execute
            code_block = parse_code_blocks(response_text)
            
            if code_block:
                if self.enable_logging:
                    print(f"Executing Code:\n{code_block}")
                
                # Execute Code
                repl_result = repl.execute(code_block)
                
                if self.enable_logging:
                    print(f"REPL Output: {repl_result}")
                
                # Add interaction to history
                # User (Action Prompt) -> Assistant (Code) -> User (REPL Output)
                history.append(current_prompt_msg)
                history.append({"role": "model", "content": response_text})
                history.append({"role": "user", "content": f"REPL Execution Output:\n{repl_result}"})
                
            else:
                # No code, just reasoning. Add to history.
                history.append(current_prompt_msg)
                history.append({"role": "model", "content": response_text})
            
            iteration += 1
            
        return "Max iterations reached without a final answer."
