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
            # 1. Aggressive Junk Stripping
            p_text = encoding_manager.strip_all_junk(run.text)
            if not p_text: continue
            
            p_text = unicodedata.normalize('NFC', p_text)
            
            req_font = run.font.name or "Normal"
            f_size = run.font.size.pt if (run.font and run.font.size) else 12
            
            res_path = font_registry.resolve_font(req_font, bold=run.bold, italic=run.italic)
            if not res_path:
                res_path = font_registry.resolve_font(req_font, ord(p_text.strip()[0]) if p_text.strip() else None)

            if res_path:
                f_id = res_path.stem
                if f_id not in registered_fonts:
                    try:
                        pdf.add_font(f_id, "", str(res_path))
                        registered_fonts[f_id] = f_id
                    except: continue
                
                pdf.set_font(f_id, size=f_size)
                
                script = "telu" if any(0x0C00 <= ord(c) <= 0x0C7F for c in p_text) else None
                if script:
                    pdf.set_text_shaping(use_shaping_engine=True, script=script)
                else:
                    pdf.set_text_shaping(False)
                
                pdf.write(h=f_size * 1.3, text=p_text)
            else:
                pdf.set_font("helvetica", size=f_size)
                pdf.write(h=f_size * 1.2, text=p_text)
        
        pdf.ln(14)

    pdf.output(str(pdf_output_path))
    return report
