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
                files = [('files', (os.path.basename(file_path), f, 'application/octet-stream'))]
                
                # Request ZIP output with referenced images
                data = {
                    "image_export_mode": "referenced", 
                    "to_formats": ["md"], # We only need markdown
                    "target_type": "zip",
                    "do_ocr": "true",
                    "do_table_structure": "true"
                }

                response = requests.post(url, files=files, data=data)
            
            response.raise_for_status()
            
            # Save ZIP response to a temporary file
            import zipfile
            import tempfile
            from pathlib import Path
            
            markdown = ""
            images = {}
            
            with tempfile.TemporaryDirectory() as temp_dir:
                zip_path = Path(temp_dir) / "response.zip"
                with open(zip_path, 'wb') as zf:
                    zf.write(response.content)
                
                # Extract ZIP
                with zipfile.ZipFile(zip_path, 'r') as zf:
                    zf.extractall(temp_dir)
                    
                    # Find markdown file
                    for root, dirs, extracted_files in os.walk(temp_dir):
                        for file in extracted_files:
                            if file.endswith(".md"):
                                with open(os.path.join(root, file), 'r', encoding='utf-8') as mdf:
                                    markdown = mdf.read()
                            elif file.lower().endswith(('.png', '.jpg', '.jpeg')):
                                # Read image bytes
                                with open(os.path.join(root, file), 'rb') as imgf:
                                    images[file] = imgf.read()

            if not markdown:
                logging.warning("No markdown file found in Docling ZIP response.")
            
            logging.info(f"Extracted {len(images)} images from ZIP.")
            
            return markdown, images
            
        except Exception as e:
            import traceback
            logging.error(f"Docling extraction failed: {e}")
            logging.error(traceback.format_exc())
            if 'response' in locals() and hasattr(response, 'text'):
                # In case of error (non-zip), text might be available
                logging.error(f"Server response: {response.text[:500]}")
            return None, {}
