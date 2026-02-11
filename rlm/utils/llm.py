"""
Google Gemini Client wrapper for RLM.
Replaces the original OpenAI implementation to use google.generativeai.
"""

import os
import google.generativeai as genai
from typing import Optional, List, Dict, Union
from dotenv import load_dotenv

load_dotenv()

class GeminiClient:
    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-2.0-flash"):
        self.api_key = api_key or os.getenv("GOOGLE_GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("Google Gemini API key is required. Set GOOGLE_GEMINI_API_KEY environment variable or pass api_key parameter.")
        
        genai.configure(api_key=self.api_key)
        self.model_name = model
        self.model = genai.GenerativeModel(self.model_name)

    def completion(
        self,
        messages: Union[List[Dict[str, str]], str],
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        try:
            # Convert OpenAI-style messages to Gemini history/prompt
            if isinstance(messages, str):
                prompt = messages
                history = []
            else:
                # Simple conversion: Concatenate history into a single prompt context or use chat session
                # For RLM/REPL, we often just need the last query with context.
                # Here we implement a basic chat session approach.
                
                history = []
                system_instruction = ""
                
                # Extract system prompt if present
                if messages and messages[0]['role'] == 'system':
                    system_instruction = messages[0]['content']
                    messages = messages[1:]
                
                # Configure model with system instruction if needed (Gemini 1.5+ supports system_instruction)
                if system_instruction:
                     self.model = genai.GenerativeModel(self.model_name, system_instruction=system_instruction)

                # Convert remaining messages to Gemini content format
                # Gemini expects alternating user/model roles. 
                # RLM might send multiple user messages in a row or complex structures.
                # For robustness in RLM (which relies heavily on "context" + "query"), 
                # we will concatenate the conversation into a single prompt if it's complex,
                # or try to map it to history if it's standard.
                
                # ROBUST APPROACH: Concatenate to avoid multi-turn validation errors common in complex agent loops
                full_prompt = ""
                for msg in messages:
                    role = msg['role'].upper()
                    content = msg['content']
                    full_prompt += f"\n\n[{role}]: {content}"
                
                prompt = full_prompt.strip()

            generation_config = genai.types.GenerationConfig(
                max_output_tokens=max_tokens,
                temperature=kwargs.get('temperature', 0.7)
            )

            response = self.model.generate_content(
                prompt,
                generation_config=generation_config
            )
            
            return response.text.strip()

        except Exception as e:
            raise RuntimeError(f"Error generating completion with Gemini: {str(e)}")
