import re
import unicodedata
from pathlib import Path
from docx import Document
from docx.shared import Pt
from pdfminer.high_level import extract_pages
from pdfminer.layout import LTTextBoxHorizontal, LTTextLineHorizontal, LTChar

try:
    from .font_manager import font_registry
    from .encoding_manager import encoding_manager
except (ImportError, ValueError):
    from font_manager import font_registry
    from encoding_manager import encoding_manager

def normalize_font_name(font_name: str) -> str:
    """Strips PDF subset prefixes (e.g., 'AAAAAA+NotoSansTelugu' -> 'NotoSansTelugu')."""
    if not font_name:
        return "Normal"
    # Remove prefix like 'ABCDEF+'
    match = re.search(r'[A-Z]{6}\+(.+)', font_name)
    if match:
        return match.group(1)
    return font_name

def resolve_cid_patterns(text: str, font_name: str) -> str:
    """Finds (cid:N) patterns and attempts to resolve them using EncodingManager."""
    def replace_cid(match):
        try:
            cid_val = int(match.group(1))
            resolved = encoding_manager.resolve_cid(cid_val, font_name)
            if resolved is not None:
                return resolved
            return match.group(0) # Fallback to original (cid:N) if unresolvable
        except:
            return match.group(0)
            
    return re.sub(r'\(cid:(\d+)\)', replace_cid, text)

def process_pdf_to_docx(pdf_path: Path, docx_output_path: Path):
    """
    Converts a text-based PDF to DOCX with high fidelity for Telugu.
    Uses pdfminer.six for layout extraction and python-docx for generation.
    """
    report = {
        "font_matches": [],
        "font_substitutions": [],
        "pages_processed": 0,
        "status": "success"
    }

    doc = Document()
    
    # Remove default margin padding for better layout match
    sections = doc.sections
    for section in sections:
        section.top_margin = Pt(72)
        section.bottom_margin = Pt(72)
        section.left_margin = Pt(72)
        section.right_margin = Pt(72)

    try:
        pages = list(extract_pages(pdf_path))
        report["pages_processed"] = len(pages)

        for page_layout in pages:
            # Sort boxes by their vertical position (top to bottom)
            boxes = sorted(
                [b for b in page_layout if isinstance(b, LTTextBoxHorizontal)],
                key=lambda b: b.y1, reverse=True
            )

            for box in boxes:
                paragraph = doc.add_paragraph()
                
                # Iterate through lines and characters to maintain formatting runs
                for line in box:
                    if not isinstance(line, LTTextLineHorizontal):
                        continue
                    
                    current_run_text = ""
                    current_font_name = None
                    current_font_size = None

                    for char in line:
                        if isinstance(char, LTChar):
                            font_name = normalize_font_name(char.fontname)
                            font_size = round(char.size, 1)
                            
                            # If formatting changes, start a new run
                            if font_name != current_font_name or font_size != current_font_size:
                                if current_run_text:
                                    add_run_to_paragraph(paragraph, current_run_text, current_font_name, current_font_size, report)
                                
                                current_run_text = char.get_text()
                                current_font_name = font_name
                                current_font_size = font_size
                            else:
                                current_run_text += char.get_text()
                    
                    # Add the last run of the line
                    if current_run_text:
                        add_run_to_paragraph(paragraph, current_run_text, current_font_name, current_font_size, report)

        doc.save(docx_output_path)
    except Exception as e:
        report["status"] = "error"
        report["error_detail"] = str(e)
        raise e

    return report

def add_run_to_paragraph(paragraph, text, font_name, font_size, report):
    """Helper to add a formatted run to a paragraph with font resolution."""
    # 0. CID Resolution
    text = resolve_cid_patterns(text, font_name)
    
    # 1. Text Normalization
    normalized_text = unicodedata.normalize('NFC', text)
    
    # 2. Legacy Encoding Detection (using existing infrastructure)
    encoding_type = encoding_manager.detect_legacy_encoding(font_name)
    if encoding_type:
        normalized_text = encoding_manager.convert_to_unicode(normalized_text, encoding_type)

    run = paragraph.add_run(normalized_text)
    
    # 3. Font Resolution
    metadata = font_registry.get_font_metadata(font_name)
    resolved_path = None
    
    if metadata:
        resolved_path = metadata.path
    elif normalized_text.strip():
        # Try fallback by first character if direct metadata match fails
        resolved_path = font_registry.resolve_font(font_name, ord(normalized_text.strip()[0]))
        if resolved_path:
            # If we found a fallback path, try to get its metadata for the proper name
            metadata = font_registry.get_font_metadata(resolved_path.stem)

    if resolved_path:
        # Use the Family Name for the DOCX font name (most compatible with Word)
        display_name = metadata.family_name if metadata else resolved_path.stem
        run.font.name = display_name
        
        # Track for report
        match_entry = {"requested": font_name, "resolved": display_name}
        if match_entry not in report["font_matches"] and match_entry not in report["font_substitutions"]:
            if font_name.lower() in display_name.lower() or display_name.lower() in font_name.lower():
                report["font_matches"].append(match_entry)
            else:
                report["font_substitutions"].append(match_entry)
    else:
        run.font.name = "Arial Unicode MS" # Safe fallback for Indic scripts
        
    if font_size:
        run.font.size = Pt(font_size)
