import logging
import unicodedata
from docx import Document
from fpdf import FPDF
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    from .font_manager import font_registry
    from .encoding_manager import encoding_manager
except (ImportError, ValueError):
    from font_manager import font_registry
    from encoding_manager import encoding_manager

class IndicPDF(FPDF):
    def header(self): pass
    def footer(self): pass

def process_docx_to_pdf_final(docx_path: Path, pdf_output_path: Path):
    """
    Scorched-earth simplified pipeline. 
    Strips ALL junk and uses standard fpdf2 write() for perfect spacing.
    """
    report = {"status": "success"}
    doc = Document(docx_path)
    pdf = IndicPDF(unit="pt", format="A4")
    pdf.set_auto_page_break(auto=True, margin=36)
    pdf.add_page()
    
    registered_fonts = {}

    for para in doc.paragraphs:
        # Strip junk from paragraph level too
        clean_para_text = encoding_manager.strip_all_junk(para.text)
        if not clean_para_text.strip():
            pdf.ln(12)
            continue

        for run in para.runs:
            req_font = run.font.name or "Normal"
            f_size = run.font.size.pt if (run.font and run.font.size) else 12
            
            input_text = run.text
            if not input_text: continue
            
            # Stage Logging
            logger.info(f"Processing Run: Font={req_font}, Chars={len(input_text)}")
            
            # 1. Detect and Intercept Legacy Encodings (Mantra Fix)
            legacy_encoding = encoding_manager.detect_legacy_encoding(req_font)
            if legacy_encoding:
                processed_text = encoding_manager.convert_to_unicode(input_text, legacy_encoding)
                logger.info(f"Legacy Conversion ({legacy_encoding}): {len(input_text)} -> {len(processed_text)}")
            else:
                processed_text = input_text
            
            # 2. Aggressive Junk Stripping
            processed_text = encoding_manager.strip_all_junk(processed_text)
            
            # 3. Unicode Normalization (NFC)
            processed_text = unicodedata.normalize('NFC', processed_text)
            
            if input_text and not processed_text.strip() and any(c.isalnum() for c in input_text):
                logger.error(f"DATA LOSS DETECTED: Input had alphanumeric text, output is empty. Input: {input_text[:20]}")
                # We don't necessarily raise here to avoid total failure, but we log it.
            
            # 4. Font Resolution
            res_path = font_registry.resolve_font(req_font, bold=run.bold, italic=run.italic)
            if not res_path:
                res_path = font_registry.resolve_font(req_font, ord(processed_text.strip()[0]) if processed_text.strip() else None)

            if res_path:
                f_id = res_path.stem
                if f_id not in registered_fonts:
                    try:
                        pdf.add_font(f_id, "", str(res_path))
                        registered_fonts[f_id] = f_id
                    except: continue
                
                pdf.set_font(f_id, size=f_size)
                
                # 5. Text Shaping Detection (Hindi Fix)
                script = None
                if any(0x0900 <= ord(c) <= 0x097F for c in processed_text):
                    script = "deva" # Devanagari
                elif any(0x0C00 <= ord(c) <= 0x0C7F for c in processed_text):
                    script = "telu" # Telugu
                elif any(0x0B80 <= ord(c) <= 0x0BFF for c in processed_text):
                    script = "taml" # Tamil
                
                if script:
                    pdf.set_text_shaping(use_shaping_engine=True, script=script)
                else:
                    pdf.set_text_shaping(False)
                
                # 6. Rendering (Layout Stability)
                pdf.write(h=f_size * 1.3, text=processed_text)
            else:
                pdf.set_font("helvetica", size=f_size)
                pdf.write(h=f_size * 1.2, text=processed_text)
        
        pdf.ln(14)

    pdf.output(str(pdf_output_path))
    return report

def process_txt_to_pdf(txt_path: Path, pdf_output_path: Path):
    """Convert a plain text file to PDF with full Indic shaping support."""
    report = {"status": "success"}
    
    try:
        with open(txt_path, "r", encoding="utf-8") as f:
            content = f.read()
    except UnicodeDecodeError:
        # Fallback to latin-1 if utf-8 fails
        with open(txt_path, "r", encoding="latin-1") as f:
            content = f.read()

    pdf = IndicPDF(unit="pt", format="A4")
    pdf.set_auto_page_break(auto=True, margin=36)
    pdf.add_page()
    
    # Default styling for TXT
    f_size = 12
    registered_fonts = {}
    
    # Split into paragraphs
    paragraphs = content.split('\n')
    
    for para_text in paragraphs:
        if not para_text.strip():
            pdf.ln(f_size * 1.2)
            continue
            
        # 1. Junk Stripping & Normalization
        processed_text = encoding_manager.strip_all_junk(para_text)
        processed_text = unicodedata.normalize('NFC', processed_text)
        
        # 2. Font Resolution (Using generic fallback)
        res_path = font_registry.resolve_font("Normal", ord(processed_text.strip()[0]) if processed_text.strip() else None)
        
        if res_path:
            f_id = res_path.stem
            if f_id not in registered_fonts:
                try:
                    pdf.add_font(f_id, "", str(res_path))
                    registered_fonts[f_id] = f_id
                except: pass
            
            pdf.set_font(f_id, size=f_size)
            
            # 3. Shaping
            script = None
            if any(0x0900 <= ord(c) <= 0x097F for c in processed_text): script = "deva"
            elif any(0x0C00 <= ord(c) <= 0x0C7F for c in processed_text): script = "telu"
            elif any(0x0B80 <= ord(c) <= 0x0BFF for c in processed_text): script = "taml"
            
            pdf.set_text_shaping(use_shaping_engine=True if script else False, script=script)
            pdf.write(h=f_size * 1.3, text=processed_text)
        else:
            pdf.set_font("helvetica", size=f_size)
            pdf.write(h=f_size * 1.2, text=processed_text)
            
        pdf.ln(f_size * 1.2)

    pdf.output(str(pdf_output_path))
    return report
