import os
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
import shutil
from pathlib import Path

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from backend.processor import process_docx_to_pdf_final
from backend.font_manager import initialize_font_registry

app = FastAPI(title="IndicPDF API")

@app.on_event("startup")
async def startup_event():
    initialize_font_registry()

UPLOAD_DIR = Path("data/uploads")
OUTPUT_DIR = Path("data/outputs")
STATIC_DIR = Path("backend/static")

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

@app.get("/", response_class=HTMLResponse)
async def root():
    index_file = STATIC_DIR / "index.html"
    return index_file.read_text()

@app.post("/upload")
async def upload_docx(file: UploadFile = File(...)):
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


@app.get("/download/{filename}")
async def download_pdf(filename: str):
    file_path = OUTPUT_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path=file_path, filename=filename, media_type="application/pdf")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
