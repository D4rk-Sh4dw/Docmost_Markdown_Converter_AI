import os
import shutil
import logging
import uuid
import re
from pathlib import Path
from typing import List

from fastapi import FastAPI, UploadFile, File, Request
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .docling_client import DoclingClient
from .ollama_client import OllamaClient
from .utils import save_images, create_zip_package

# Config
DOCLING_URL = os.getenv('DOCLING_SERVER_URL', 'http://docling:8080')
OLLAMA_URL = os.getenv('OLLAMA_SERVER_URL', 'http://ollama:11434')
OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'llama3')
OUTPUT_DIR = Path(os.getenv('OUTPUT_DIR', '/app/output'))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = FastAPI()

# Setup Static/Templates should be relative to file location
BASE_DIR = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")

# Clients
docling = DoclingClient(DOCLING_URL)
ollama = OllamaClient(OLLAMA_URL, OLLAMA_MODEL)

@app.get("/", response_class=HTMLResponse)
    })

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return JSONResponse(status_code=204)

@app.get("/status")
async def get_status():
    """
    Robust Status Check:
    - Ollama: Root Check ("Ollama is running")
    - Docling: UI Page Check (Look for "Docling Serve")
    """
    status = {
        "docling": "offline",
        "ollama": "offline"
    }
    
    # 1. Check Docling (UI Scraping)
    try:
        # User says: Check /ui for string "Docling Serve"
        # We try strict /ui first, then root if that fails/moves
        ui_url = f"{DOCLING_URL}/ui"
        
        logging.info(f"Checking Docling Status at {ui_url}")
        resp = requests.get(ui_url, timeout=5)
        
        if resp.status_code == 200 and "Docling Serve" in resp.text:
            status["docling"] = "online"
        else:
             # Fallback: maybe it's on root?
             logging.info("Docling /ui check failed, trying root...")
             resp_root = requests.get(DOCLING_URL, timeout=5)
             if resp_root.status_code == 200 and ("Docling Serve" in resp_root.text or "Swagger" in resp_root.text):
                 status["docling"] = "online"
                 
    except Exception as e:
        logging.error(f"Docling Status Check Failed: {e}")
        pass

    # 2. Check Ollama (Root Check)
    try:
        # User says: response to curl is "Ollama is running"
        logging.info(f"Checking Ollama Status at {OLLAMA_URL}")
        resp = requests.get(OLLAMA_URL, timeout=5)
        if resp.status_code == 200 and "Ollama is running" in resp.text:
             status["ollama"] = "online"
    except Exception as e:
        logging.error(f"Ollama Status Check Failed: {e}")
        pass
        
    return JSONResponse(status)

@app.post("/convert")
async def convert_files(files: List[UploadFile] = File(...)):
    job_id = str(uuid.uuid4())
    job_dir = Path(f"/tmp/{job_id}")
    job_dir.mkdir(parents=True, exist_ok=True)
    
    processed_dir = job_dir / "processed"
    processed_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        for file in files:
            # Save uploaded file
            file_path = job_dir / file.filename
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
                
            logging.info(f"Processing {file.filename}...")
            
            # 1. Extraction (Docling)
            raw_markdown, images_data = docling.extract(str(file_path))
            
            if not raw_markdown:
                logging.error(f"Skipping {file.filename} due to extraction failure.")
                continue
                
            # Create Doc Folder
            doc_name = os.path.splitext(file.filename)[0]
            doc_out_dir = processed_dir / doc_name
            doc_out_dir.mkdir(parents=True, exist_ok=True)
            
            # 2. Image Handling
            # Save images first to know their paths
            image_map = save_images(images_data, doc_out_dir)
            
            # Update Markdown Image References BEFORE sending to LLM?
            # User requirement: "Images: Behalte die Platzhalter ![...](images/image_xxx.png) EXAKT an ihrer semantischen Position bei."
            # So we should inject the correct relative paths into the raw markdown first, 
            # so Ollama just sees clear paths like ![desc](images/image_001.png).
            
            # Replace Docling's internal refs with our new paths
            # Images in Docling ZIP are typically in 'pictures/' or similar.
            # Our `images_data` keys are the filenames found in the ZIP.
            # We need to find where they are referenced in the markdown.
            # Regex is safer.
            current_markdown = raw_markdown
            
            # Prepend Title if missing (Docmost requires H1 for imports)
            if not current_markdown.strip().startswith('# '):
                 current_markdown = f"# {doc_name}\n\n{current_markdown}"

            for original_name, new_rel_path in image_map.items():
                # Regex to search for ![alt](...original_name) ignoring the path prefix
                # We interpret original_name as the filename (basename)
                
                # Escape the basename for regex use
                esc_name = re.escape(original_name)
                
                # Pattern: ! [ ... ] ( ... /original_name )  
                # We need to match the strict end of the URL to be the filename
                # Capture group 1: alt text
                
                pattern = r'(!\[.*?\])\(.*?' + esc_name + r'\)'
                
                # Debug logging
                logging.info(f"Regex replacing for image: {original_name} -> {new_rel_path}")
                
                # Replace with \1(new_rel_path)
                current_markdown = re.sub(pattern, r'\1(' + new_rel_path + ')', current_markdown)
            
            # Log Markdown before Ollama
            logging.info(f"Markdown before Ollama (first 500 chars):\n{current_markdown[:500]}")
            
            # 3. Refinement (Ollama)
            final_markdown = ollama.refine_markdown(current_markdown)
            
            # 4. Save
            with open(doc_out_dir / "document.md", "w", encoding="utf-8") as f:
                f.write(final_markdown)
                
        # Zip
        # Check if we actually processed anything
        if not any(processed_dir.iterdir()):
             raise Exception("No files were successfully processed. Check Docling server connection and logs.")

        zip_name = f"converted_{job_id}.zip"
        zip_path = job_dir / zip_name
        create_zip_package(processed_dir, str(zip_path))
        
        # Move to public output
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        final_zip_path = OUTPUT_DIR / zip_name
        shutil.move(str(zip_path), str(final_zip_path))
        
        return JSONResponse({"download_url": f"/download/{zip_name}", "status": "success"})
        
    except Exception as e:
        logging.error(f"Job failed: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)
    finally:
        # Cleanup
        # shutil.rmtree(job_dir, ignore_errors=True)
        pass

@app.get("/download/{filename}")
async def download_file(filename: str):
    file_path = OUTPUT_DIR / filename
    if file_path.exists():
        return FileResponse(file_path, filename=filename)
    return JSONResponse({"error": "File not found"}, status_code=404)
