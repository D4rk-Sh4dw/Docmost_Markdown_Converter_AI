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
            "SYSTEM INSTRUCTION: Prepare this text for import into 'Docmost' (Wiki Software).\n"
            "OBJECTIVE: Create a clean, structured Markdown document without losing information.\n"
            "\n"
            "RULES:\n"
            "1. **Header Hierarchy**: Ensure proper nesting (# H1, ## H2, ### H3). Fix broken headers.\n"
            "2. **Lists & Tables**: Fix indentation in lists. Ensure Markdown tables are syntactically correct.\n"
            "3. **Code Blocks**: Detect code snippets (Shell, JSON, Python) and wrap them in ```language blocks.\n"
            "4. **Images**: RETAIN ALL IMAGE LINKS EXACTLY AS THEY ARE. Do not modify the path or filename. Do not add prefixes.\n"
            "5. **Cleanup**: Remove artifacts like 'Page 1 of 5', repetitive footers, or random line breaks that break sentences.\n"
            "6. **Content Safety**: Do NOT summarize. Do NOT delete informational text. Only remove layout noise.\n"
            "7. **Formatting**: Use bold/italics to highlight key terms (IPs, Paths, Menu Items).\n"
            "8. **Output**: Return ONLY the valid Markdown string. No conversational filler."
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
