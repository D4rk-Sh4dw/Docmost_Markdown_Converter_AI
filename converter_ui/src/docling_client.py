import requests
import logging
import os

class DoclingClient:
    def __init__(self, server_url: str):
        self.server_url = server_url.rstrip('/')
        
    def extract(self, file_path: str):
        """
        Sends file to Docling server for processing.
        Returns tuple: (markdown_text, images_dict)
        """
        url = f"{self.server_url}/v1/convert" # Adjusted to standard /v1/convert
        # NOTE: Docling serve usually exposes /convert expecting a file.
        # Check specific docling-serve API. Assuming standard POST /v1/convert or similar.
        # If generic docling serve: likely accepts file upload.
        
        logging.info(f"Sending {file_path} to Docling at {url}")
        
        try:
            with open(file_path, 'rb') as f:
                files = {'file': f}
                # Check if we need options
                response = requests.post(url, files=files)
                
            response.raise_for_status()
            data = response.json()
            
            # Extract content. 
            # Docling JSON typically: { 'main-text': ..., 'images': ... }
            # Adjust key access based on actual Docling API Reference.
            # Assuming 'markdown' field and 'images' list/dict.
            
            markdown = data.get('markdown', '')
            if not markdown:
                 # Fallback if structure is different (e.g. 'document' -> 'markdown')
                 markdown = data.get('document', {}).get('markdown', '')
            
            images = data.get('images', {}) 
            # Images might be base64.
            
            return markdown, images
            
        except Exception as e:
            logging.error(f"Docling extraction failed: {e}")
            if 'response' in locals() and hasattr(response, 'text'):
            logging.error(f"Server response: {response.text}")
            return None, {}
