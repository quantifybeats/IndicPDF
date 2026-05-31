import zipfile
import logging
from pathlib import Path
from typing import List
from pypdf import PdfWriter
from docx import Document

logger = logging.getLogger(__name__)

def merge_pdfs(file_paths: List[Path], output_path: Path):
    """Merge multiple PDFs into one using pypdf."""
    logger.info(f"Merging {len(file_paths)} PDFs into {output_path}")
    writer = PdfWriter()
    for path in file_paths:
        if path.exists():
            writer.append(path)
        else:
            logger.warning(f"File not found during PDF merge: {path}")
    
    with output_path.open("wb") as f:
        writer.write(f)

def merge_docx(file_paths: List[Path], output_path: Path):
    """Merge multiple DOCX files into one using python-docx."""
    logger.info(f"Merging {len(file_paths)} DOCX files into {output_path}")
    if not file_paths:
        raise ValueError("No file paths provided for DOCX merge")
    
    merged_document = Document(file_paths[0])
    
    for path in file_paths[1:]:
        if not path.exists():
            logger.warning(f"File not found during DOCX merge: {path}")
            continue
        
        sub_doc = Document(path)
        # Add a page break between documents
        merged_document.add_page_break()
        
        for element in sub_doc.element.body:
            merged_document.element.body.append(element)
            
    merged_document.save(output_path)

def create_zip_archive(file_paths: List[Path], output_path: Path):
    """Create a ZIP archive of all files as a fallback."""
    logger.info(f"Creating ZIP archive with {len(file_paths)} files at {output_path}")
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for i, path in enumerate(file_paths):
            if path.exists():
                # Prefix with index to maintain order in ZIP
                zipf.write(path, arcname=f"{i+1:02d}_{path.name}")
            else:
                logger.warning(f"File not found during ZIP creation: {path}")
