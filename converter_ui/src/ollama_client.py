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
            "SYSTEM INSTRUCTION: You are a text processing engine. Your task is to formatting the provided markdown.\n"
            "STRICT RULES:\n"
            "1. Output ONLY the refined markdown. NO introductory text, NO comparisons, NO comments.\n"
            "2. Preserve image links exactly: ![...](images/image_xxx.png).\n"
            "3. Format code blocks with correct language identifiers (bash, yaml, etc.).\n"
            "4. Enclose file paths, IP addresses, and hostnames in backticks.\n"
            "5. Remove page numbers and headers/footers.\n"
            "6. If the input is empty or unclear, output the input exactly as is.\n"
            "7. Do NOT ask for clarification. Do NOT saying 'Here is the refined text'. JUST OUTPUT THE CODE."
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
