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


# Preferred installed family per script, so the emitted DOCX names a font the
# reader actually has (a PDF subset name like 'ABCDEF+Foo' opens as tofu in Word).
_SCRIPT_DOCX_FONT = {
    "devanagari": "Noto Sans Devanagari",
    "telugu":     "Noto Sans Telugu",
    "tamil":      "Noto Sans Tamil",
}

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
                    
                    # 1. Resolve CIDs before stripping remaining junk
                    def cid_replacer(match):
                        cid_val = int(match.group(1))
                        # We don't have the font name easily here for each char, 
                        # but we can try to get it from the line
                        resolved = encoding_manager.resolve_cid(cid_val, font_name)
                        return resolved if resolved is not None else match.group(0)

                    # Pre-extract font name for CID resolution context
                    font_name = "Normal"
                    for char in line:
                        if hasattr(char, 'fontname'):
                            font_name = normalize_font_name(char.fontname)
                            break
                    
                    processed_line = re.sub(r'\(cid\s*:\s*(\d+)\s*\)', cid_replacer, line_text)
                    processed_line = re.sub(r'cid\s*:\s*(\d+)', cid_replacer, processed_line)
                    
                    # 2. Junk Stripping & Normalization
                    clean_text = encoding_manager.strip_all_junk(processed_line)
                    clean_text = unicodedata.normalize('NFC', clean_text)
                    
                    if not clean_text.strip(): continue

                    # 3. Script Detection for Font Resolution
                    script = None
                    if any(0x0900 <= ord(c) <= 0x097F for c in clean_text): script = "devanagari"
                    elif any(0x0C00 <= ord(c) <= 0x0C7F for c in clean_text): script = "telugu"
                    elif any(0x0B80 <= ord(c) <= 0x0BFF for c in clean_text): script = "tamil"

                    # 4. Font Size Detection
                    font_size = 12
                    for char in line:
                        if hasattr(char, 'size'):
                            font_size = round(char.size, 1)
                            break
                    
                    run = paragraph.add_run(clean_text)

                    # For Indic runs, name an installed script font so the DOCX
                    # renders correctly in Word/LibreOffice instead of tofu.
                    pref = _SCRIPT_DOCX_FONT.get(script) if script else None
                    if pref and font_registry.get_font_metadata(pref):
                        run.font.name = pref
                    else:
                        metadata = font_registry.get_font_metadata(font_name)
                        if metadata:
                            run.font.name = metadata.family_name
                        elif clean_text.strip():
                            fallback = font_registry.resolve_font(font_name, ord(clean_text.strip()[0]), script=script)
                            if fallback:
                                run.font.name = fallback.stem
                    
                    run.font.size = Pt(font_size)

        doc.save(docx_output_path)
    except Exception as e:
        report["status"] = "error"
        raise e

    return report
