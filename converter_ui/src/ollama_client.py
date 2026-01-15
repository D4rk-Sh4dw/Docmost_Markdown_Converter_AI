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
            "Du bist ein technischer Redakteur. Überarbeite dieses Roh-Markdown für ein IT-Wiki (Docmost):\n"
            "- Code-Blöcke: Erkenne Bash-Befehle, JSON-Configs und Skripte. Umschließe sie mit ``` und Sprach-ID.\n"
            "- Inline-Tech: Setze Pfade, IPs und Hostnames in Backticks.\n"
            "- Header-Cleanup: Entferne Seitenzahlen, Firmen-Header und Footer.\n"
            "- Struktur: Erzeuge eine saubere Hierarchie (Beginnend mit #).\n"
            "- Bilder: Behalte die Platzhalter ![...](images/image_xxx.png) EXAKT an ihrer semantischen Position bei. Ändere die Bildpfade NICHT.\n"
            "Output: Gib NUR das korrigierte Markdown aus, keine Einleitung, keine Kommentare."
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
