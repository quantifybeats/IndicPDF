import re
import unicodedata
from pathlib import Path
from docx import Document
from docx.shared import Pt
from pdfminer.high_level import extract_pages
from pdfminer.layout import LAParams, LTTextBoxHorizontal, LTTextLineHorizontal

try:
    from .font_manager import font_registry
    from .encoding_manager import encoding_manager
except (ImportError, ValueError):
    from font_manager import font_registry
    from encoding_manager import encoding_manager

def normalize_font_name(font_name: str) -> str:
    if not font_name:
        return "Normal"
    match = re.search(r'[A-Z]{6}\+(.+)', font_name)
    return match.group(1) if match else font_name

def process_pdf_to_docx(pdf_path: Path, docx_output_path: Path):
    """Production-grade PDF to DOCX extractor using line-level logic."""
    report = {"pages_processed": 0, "status": "success"}
    doc = Document()
    
    for section in doc.sections:
        section.top_margin = Pt(72); section.bottom_margin = Pt(72)
        section.left_margin = Pt(72); section.right_margin = Pt(72)

    try:
        laparams = LAParams(word_margin=0.1, line_margin=0.5, char_margin=2.0)
        pages = list(extract_pages(pdf_path, laparams=laparams))
        report["pages_processed"] = len(pages)

        for page_layout in pages:
            boxes = sorted([b for b in page_layout if isinstance(b, LTTextBoxHorizontal)],
                           key=lambda b: b.y1, reverse=True)

            for box in boxes:
                paragraph = doc.add_paragraph()
                
                for line in box:
                    if not isinstance(line, LTTextLineHorizontal): continue
                    
                    line_text = line.get_text()
                    # Use global aggressive stripper
                    clean_text = encoding_manager.strip_all_junk(line_text)
                    clean_text = unicodedata.normalize('NFC', clean_text)
                    
                    if not clean_text.strip(): continue

                    font_name = "Normal"
                    font_size = 12
                    for char in line:
                        if hasattr(char, 'fontname'):
                            font_name = normalize_font_name(char.fontname)
                            font_size = round(char.size, 1)
                            break
                    
                    run = paragraph.add_run(clean_text)
                    
                    metadata = font_registry.get_font_metadata(font_name)
                    if metadata:
                        run.font.name = metadata.family_name
                    elif clean_text.strip():
                        fallback = font_registry.resolve_font(font_name, ord(clean_text.strip()[0]))
                        if fallback:
                            run.font.name = fallback.stem
                    
                    run.font.size = Pt(font_size)

        doc.save(docx_output_path)
    except Exception as e:
        report["status"] = "error"
        raise e

    return report
