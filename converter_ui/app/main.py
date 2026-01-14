import os
import httpx
import logging
from fastapi import FastAPI, UploadFile, File, Request, HTTPException
from fastapi.responses import HTMLResponse, Response
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from .utils import create_docmost_zip

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Converter UI")

# Templates
templates = Jinja2Templates(directory="app/templates")

# Config - Default to port 5001 to match docling-serve default
DOCLING_SERVER_URL = os.getenv("DOCLING_SERVER_URL", "http://docling-server:5001")

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/upload")
async def handle_upload(file: UploadFile = File(...)):
    """
    Handles file upload, forwards to docling-server, processes result, returns ZIP.
    """
    logger.info(f"Received upload: {file.filename}")
    
    # 1. Forward to Docling Server
    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            # Read file content
            file_content = await file.read()
            
            # Prepare multipart request for /v1/convert/file check
            # Official API expects 'files' list
            files = [('files', (file.filename, file_content, file.content_type))]
            
            # If using official docling-serve, we might need to send options too?
            # For now sending just files. 
            
            logger.info(f"Sending to Docling Server at {DOCLING_SERVER_URL}/v1/convert/file...")
            
            # Options to ensure best quality / layout analysis
            # We enable OCR and Table Structure to match 'full' docling capabilities
            options = {
                "do_ocr": "true",
                "do_table_structure": "true", 
                "ocr_engine": "easyocr" # Explicitly request easyocr to be safe
            }
            
            response = await client.post(f"{DOCLING_SERVER_URL}/v1/convert/file", files=files, data=options)
            
            if response.status_code != 200:
                logger.error(f"Docling Server Error: {response.text}")
                raise HTTPException(status_code=response.status_code, detail=f"Conversion service failed: {response.text}")
            
            data = response.json()
            logger.info(f"Response Keys: {list(data.keys())}")
            if "document" in data:
                 doc_keys = list(data["document"].keys())
                 logger.info(f"Document Keys: {doc_keys}")
                 # Log first 500 chars of document for inspection
                 import json
                 logger.info(f"Document Snippet: {json.dumps(data['document'], default=str)[:500]}")
            
    except httpx.RequestError as e:
        logger.error(f"Connection error: {e}")
        raise HTTPException(status_code=503, detail=f"Could not connect to conversion service: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    # 2. Process Result
    # Log revealed structure: data['document']['md_content']
    document = data.get("document", {})
    markdown_content = document.get("md_content")
    
    if not markdown_content:
        # Fallback check
        logger.warning(f"md_content not found. Document keys: {list(document.keys())}")
        markdown_content = ""

    # Images are embedded in markdown as data-uris, so we pass empty list here
    # and let create_docmost_zip extract them.
    images = []

    # 4. Prepare Output Filename & Title
    filename_stem = os.path.splitext(file.filename)[0]

    # 3. Create ZIP
    try:
        zip_bytes = create_docmost_zip(markdown_content, images, title=filename_stem)
    except Exception as e:
        logger.error(f"Post-processing failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate ZIP: {str(e)}")

    # 4. Return ZIP
    output_filename = f"{filename_stem}_docmost.zip"
    
    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={output_filename}"}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3000)
