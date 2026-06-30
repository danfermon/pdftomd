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
    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-2.5-flash"):
        self.api_key = api_key or os.getenv("GOOGLE_GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("Google Gemini or OpenAI API key is required. Set GOOGLE_GEMINI_API_KEY or OPENAI_API_KEY environment variable or pass api_key parameter.")
        
        self.is_openai = self.api_key.startswith("sk-")
        if self.is_openai:
            self.model_name = "gpt-4o-mini"
        else:
            genai.configure(api_key=self.api_key)
            self.model_name = model
            self.model = genai.GenerativeModel(self.model_name)

    def completion(
        self,
        messages: Union[List[Dict[str, str]], str],
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        if self.is_openai:
            try:
                import requests
                import json
                
                # Format messages for OpenAI API
                if isinstance(messages, str):
                    formatted_messages = [{"role": "user", "content": messages}]
                else:
                    formatted_messages = []
                    for msg in messages:
                        role = msg['role']
                        if role == 'model':
                            role = 'assistant'
                        formatted_messages.append({
                            "role": role,
                            "content": msg['content']
                        })
                
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}"
                }
                
                payload = {
                    "model": self.model_name,
                    "messages": formatted_messages,
                }
                if max_tokens is not None:
                    payload["max_tokens"] = max_tokens
                if 'temperature' in kwargs:
                    payload["temperature"] = kwargs['temperature']
                
                response = requests.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=120
                )
                response.raise_for_status()
                res_data = response.json()
                return res_data["choices"][0]["message"]["content"].strip()
                
            except Exception as e:
                raise RuntimeError(f"Error generating completion with OpenAI (gpt-4o-mini): {str(e)}")

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

            import time
            from google.api_core.exceptions import ResourceExhausted

            generation_config = genai.types.GenerationConfig(
                max_output_tokens=max_tokens,
                temperature=kwargs.get('temperature', 0.7)
            )

            max_retries = 5
            backoff_factor = 2
            for attempt in range(max_retries):
                try:
                    response = self.model.generate_content(
                        prompt,
                        generation_config=generation_config
                    )
                    return response.text.strip()
                except ResourceExhausted as re_err:
                    if attempt == max_retries - 1:
                        raise re_err
                    sleep_time = (backoff_factor ** attempt) + 2
                    print(f"[WARN] Gemini Rate Limit hit (ResourceExhausted). Retrying in {sleep_time}s...")
                    time.sleep(sleep_time)
                except Exception as e:
                    if "429" in str(e) or "quota" in str(e).lower():
                        if attempt == max_retries - 1:
                            raise e
                        sleep_time = (backoff_factor ** attempt) + 2
                        print(f"[WARN] Gemini Rate Limit hit (429/quota). Retrying in {sleep_time}s...")
                        time.sleep(sleep_time)
                    else:
                        raise e

        except Exception as e:
            # Tenta Fallback para OpenAI se a chave estiver disponível no ambiente e não estivermos já usando OpenAI
            openai_key = os.getenv("OPENAI_API_KEY")
            if openai_key and not self.is_openai:
                print("[WARN] Gemini completion falhou. Tentando fallback para OpenAI (gpt-4o-mini)...")
                try:
                    import requests
                    import json
                    
                    if isinstance(messages, str):
                        formatted_messages = [{"role": "user", "content": messages}]
                    else:
                        formatted_messages = []
                        for msg in messages:
                            role = msg['role']
                            if role == 'model':
                                role = 'assistant'
                            formatted_messages.append({
                                "role": role,
                                "content": msg['content']
                            })
                    
                    headers = {
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {openai_key}"
                    }
                    
                    payload = {
                        "model": "gpt-4o-mini",
                        "messages": formatted_messages,
                    }
                    if max_tokens is not None:
                        payload["max_tokens"] = max_tokens
                    if 'temperature' in kwargs:
                        payload["temperature"] = kwargs['temperature']
                    
                    response = requests.post(
                        "https://api.openai.com/v1/chat/completions",
                        headers=headers,
                        json=payload,
                        timeout=120
                    )
                    response.raise_for_status()
                    res_data = response.json()
                    return res_data["choices"][0]["message"]["content"].strip()
                except Exception as e_fallback:
                    print(f"[ERROR] Fallback para OpenAI também falhou: {e_fallback}")
            
            raise RuntimeError(f"Error generating completion with Gemini: {str(e)}")
