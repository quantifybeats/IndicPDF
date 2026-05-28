import os
import sys
import shutil
import logging
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, Response

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Absolute path resolution
BASE_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = BASE_DIR / "backend"
sys.path.append(str(BACKEND_DIR))

try:
    from processor import process_docx_to_pdf_final
    from pdf_processor import process_pdf_to_docx
    from font_manager import initialize_font_registry
except ImportError:
    from .processor import process_docx_to_pdf_final
    from .pdf_processor import process_pdf_to_docx
    from .font_manager import initialize_font_registry

app = FastAPI(title="IndicPDF API")

# Lazy loading flag
_fonts_initialized = False

def ensure_fonts():
    global _fonts_initialized
    if not _fonts_initialized:
        try:
            initialize_font_registry()
            _fonts_initialized = True
            logger.info("Font Registry initialized successfully.")
        except Exception as e:
            logger.error(f"FAILED to initialize font registry: {e}")

@app.on_event("startup")
async def startup_event():
    # Attempt early init but don't block if it's slow
    logger.info("Application starting up...")

IS_VERCEL = "VERCEL" in os.environ
UPLOAD_DIR = Path("/tmp/uploads") if IS_VERCEL else BASE_DIR / "data" / "uploads"
OUTPUT_DIR = Path("/tmp/outputs") if IS_VERCEL else BASE_DIR / "data" / "outputs"
STATIC_DIR = BACKEND_DIR / "static"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return Response(status_code=204)

@app.get("/", response_class=HTMLResponse)
async def root():
    index_file = STATIC_DIR / "index.html"
    if not index_file.exists():
        logger.error(f"index.html not found at {index_file}")
        return HTMLResponse(content="<h1>Front-end assets missing</h1>", status_code=404)
    return FileResponse(index_file)

@app.post("/upload")
async def upload_docx(file: UploadFile = File(...)):
    ensure_fonts() # Ensure fonts are ready before processing
    if not file.filename.endswith(".docx"):
        raise HTTPException(status_code=400, detail="Only .docx files are supported")

    file_path = UPLOAD_DIR / file.filename
    with file_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Trigger Final Processing (Font Aware + Legacy Conversion + Shaping)
    output_filename = file_path.stem + ".pdf"
    output_path = OUTPUT_DIR / output_filename
    report = process_docx_to_pdf_final(file_path, output_path)

    return {
        "filename": file.filename, 
        "output": output_filename,
        "report": report,
        "status": "processed"
    }


@app.post("/upload-pdf")
async def upload_pdf(file: UploadFile = File(...)):
    ensure_fonts()
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only .pdf files are supported")

    file_path = UPLOAD_DIR / file.filename
    with file_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    output_filename = file_path.stem + ".docx"
    output_path = OUTPUT_DIR / output_filename
    
    try:
        report = process_pdf_to_docx(file_path, output_path)
    except Exception as e:
        logger.error(f"PDF processing failed: {e}")
        raise HTTPException(status_code=500, detail=f"PDF processing failed: {str(e)}")

    return {
        "filename": file.filename,
        "output": output_filename,
        "report": report,
        "status": "processed"
    }


@app.get("/download/{filename}")
async def download_pdf(filename: str):
    file_path = OUTPUT_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path=file_path, filename=filename, media_type="application/pdf")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
