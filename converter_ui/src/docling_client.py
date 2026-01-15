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
        url = f"{self.server_url}/v1/convert/file" # Verified in docling-serve source code
        
        logging.info(f"Sending {file_path} to Docling at {url}")
        
        try:
            with open(file_path, 'rb') as f:
                # API expects 'files' (plural) as iter of UploadFile
                # Using list of tuples is safer for requests to handle multiple files/lists
                files = [('files', (os.path.basename(file_path), f, 'application/octet-stream'))]
                
                # Check if we need options
                response = requests.post(url, files=files)
                
            response.raise_for_status()
            data = response.json()
            
            # Docling Serve v1 returns ConvertDocumentResponse:
            # { "document": { "markdown": "...", ... }, "status": "success", ... }
            
            doc = data.get('document', {})
            markdown = doc.get('md_content', '')
            
            # If markdown is still empty, try to log the keys to help debugging
            if not markdown:
                 logging.warning(f"Markdown not found in response. Available keys in 'document': {list(doc.keys())}, Keys in root: {list(data.keys())}")
            
            # Images extraction - check where images are located.
            # Usually docling exports images separately or embedded.
            # Assuming 'images' might be in root or under document.
            images = data.get('images', {})
            if not images:
                images = doc.get('images', {})
            
            if images is None:
                images = {}
                
            logging.info(f"Extracted images type: {type(images)}")
            if isinstance(images, dict):
                 logging.info(f"Image keys: {list(images.keys())}")
            elif isinstance(images, list):
                 logging.info(f"Images list length: {len(images)}")
                 # Attempt conversion if it's a list (unlikely based on typical docling, but possible)
                 # Converting list to dict not trivial without keys.
            else:
                 logging.warning(f"Unexpected images structure: {images}")
                 images = {}
                
            return markdown, images
            
        except Exception as e:
            import traceback
            logging.error(f"Docling extraction failed: {e}")
            logging.error(traceback.format_exc())
            if 'response' in locals() and hasattr(response, 'text'):
                logging.error(f"Server response: {response.text}")
            return None, {}
