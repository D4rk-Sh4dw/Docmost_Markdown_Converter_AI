import requests
import logging
import json

class OllamaClient:
    def __init__(self, server_url: str, model: str = "llama3"):
        self.server_url = server_url.rstrip('/')
        self.model = model
        
    def refine_markdown(self, raw_markdown: str) -> str:
        """
        Sends markdown to Ollama for IT-Refinement.
        """
        system_instruction = (
            "SYSTEM INSTRUCTION: You are a strict Markdown formatter. Your ONLY job is to fix syntax errors (like indentation, broken lists, code blocks).\n"
            "CRITICAL RULES:\n"
            "1. DO NOT DELETE ANY TEXT. PRESERVE EVERY SINGLE WORD.\n"
            "2. DO NOT SUMMARIZE OR SHORTEN CONTENT.\n"
            "3. FIX spelling mistakes (German/English), but ONLY if you are 100% sure.\n"
            "4. Preserve image links exactly as provided: ![...](images/...).\n"
            "5. Ensure headers (#) are hierarchical.\n"
            "6. If a section is unclear, leave it EXACTLY as is.\n"
            "7. Output ONLY the markdown code. NO conversation."
        )
        
        payload = {
            "model": self.model,
            "prompt": f"{system_instruction}\n\nRohdaten:\n{raw_markdown}",
            "stream": False,
            "options": {
                "temperature": 0.2, # Low temp for precision
                "num_ctx": 8192 # Large context for documents
            }
        }
        
        url = f"{self.server_url}/api/generate"
        
        logging.info(f"Sending text to Ollama at {url} (Model: {self.model})")
        
        try:
            response = requests.post(url, json=payload, timeout=120) # Long timeout for LLM
            response.raise_for_status()
            
            result = response.json()
            refined_text = result.get('response', '')
            
            if not refined_text:
                logging.warning("Ollama returned empty response. Using raw text.")
                return raw_markdown
                
            return refined_text
            
        except Exception as e:
            logging.error(f"Ollama refinement failed: {e}")
            return raw_markdown # Graceful fallback
