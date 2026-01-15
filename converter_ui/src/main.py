import os
import shutil
import logging
import uuid
import re
import requests
from pathlib import Path
from typing import List

from fastapi import FastAPI, UploadFile, File, Request
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse, Response

# ...

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return Response(status_code=204)

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

# Legacy convert endpoint replaced by job system
    
@app.post("/job/init")
async def init_job():
    """Starts a new conversion job session"""
    job_id = str(uuid.uuid4())
    job_dir = Path(f"/tmp/{job_id}")
    processed_dir = job_dir / "processed"
    processed_dir.mkdir(parents=True, exist_ok=True)
    return JSONResponse({"job_id": job_id})

@app.post("/job/{job_id}/process")
async def process_chunk(job_id: str, file: UploadFile = File(...)):
    """Processes a single file within a job context"""
    job_dir = Path(f"/tmp/{job_id}")
    processed_dir = job_dir / "processed"
    
    if not job_dir.exists():
         return JSONResponse({"error": "Job session expired or invalid"}, status_code=404)

    try:
        logging.info(f"Received chunk for Job {job_id}: {file.filename}")
        
        # Save uploaded file
        file_path = job_dir / file.filename
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        logging.info(f"Processing {file.filename}...")
        
        # 1. Extraction (Docling)
        raw_markdown, images_data = docling.extract(str(file_path))
        
        if not raw_markdown:
            logging.error(f"Skipping {file.filename} due to extraction failure.")
            return JSONResponse({"status": "skipped", "reason": "extraction_failed"})
            
        # Create Doc Folder
        doc_name = os.path.splitext(file.filename)[0]
        doc_out_dir = processed_dir / doc_name
        doc_out_dir.mkdir(parents=True, exist_ok=True)
        
        # 2. Image Handling
        image_map = save_images(images_data, doc_out_dir)
        
        # Replace Docling's internal refs with our new paths
        current_markdown = raw_markdown
        
        # Prepend Title if missing (Docmost requires H1 for imports)
        if not current_markdown.strip().startswith('# '):
                current_markdown = f"# {doc_name}\n\n{current_markdown}"

        for original_name, new_rel_path in image_map.items():
            esc_name = re.escape(original_name)
            pattern = r'(!\[.*?\])\(.*?' + esc_name + r'\)'
            current_markdown = re.sub(pattern, r'\1(' + new_rel_path + ')', current_markdown)
        
        logging.info(f"Markdown prepared for Ollama (Job {job_id}, File {file.filename})")
        
        # 3. Refinement (Ollama)
        final_markdown = current_markdown
        try:
            final_markdown = ollama.refine_markdown(current_markdown)
        except Exception as e:
            logging.error(f"Ollama refinement failed for {file.filename}: {e}")
            logging.warning("Falling back to original Docling markdown.")
            final_markdown += "\n\n> [!WARNING]\n> AI Refinement failed (Timeout/Error). This is the raw extraction."

        # 4. Save
        with open(doc_out_dir / "document.md", "w", encoding="utf-8") as f:
            f.write(final_markdown)
            
        return JSONResponse({"status": "complated", "file": file.filename})

    except Exception as e:
        logging.error(f"Chunk processing failed: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)

@app.post("/job/{job_id}/finalize")
async def finalize_job(job_id: str):
    """Zips the processed files and returns download URL"""
    job_dir = Path(f"/tmp/{job_id}")
    processed_dir = job_dir / "processed"
    
    if not processed_dir.exists() or not any(processed_dir.iterdir()):
         return JSONResponse({"error": "No files were successfully processed."}, status_code=400)

    try:
        zip_name = f"converted_{job_id}.zip"
        zip_path = job_dir / zip_name
        create_zip_package(processed_dir, str(zip_path))
        
        # Move to public output
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        final_zip_path = OUTPUT_DIR / zip_name
        shutil.move(str(zip_path), str(final_zip_path))
        
        return JSONResponse({"download_url": f"/download/{zip_name}", "status": "success"})
        
    except Exception as e:
        logging.error(f"Finalization failed: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)
    finally:
        # Cleanup temp dir? Maybe keep for a bit for debug.
        # shutil.rmtree(job_dir, ignore_errors=True)
        pass

# Legacy endpoint removed/replaced by job logic
# @app.post("/convert") ...

@app.get("/download/{filename}")
async def download_file(filename: str):
    file_path = OUTPUT_DIR / filename
    if file_path.exists():
        return FileResponse(file_path, filename=filename)
    return JSONResponse({"error": "File not found"}, status_code=404)
