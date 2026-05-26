from docx import Document
from fpdf import FPDF
from pathlib import Path
try:
    from .font_manager import font_registry
    from .encoding_manager import encoding_manager
except (ImportError, ValueError):
    from font_manager import font_registry
    from encoding_manager import encoding_manager

class IndicPDF(FPDF):
    def header(self):
        pass
    def footer(self):
        pass

def process_docx_to_pdf_final(docx_path: Path, pdf_output_path: Path):
    """Final production pipeline using fpdf2 for native shaping support."""
    report = {
        "font_substitutions": [],
        "legacy_conversions": [],
        "status": "success"
    }
    
    doc = Document(docx_path)
    pdf = IndicPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    
    registered_fonts = {} # Mapping of font_name -> font_id

    for para in doc.paragraphs:
        # Determine paragraph alignment if needed (omitted for MVP)
        
        for run in para.runs:
            if not run.text.strip() and not run.text == " ":
                continue
                
            requested_font = run.font.name or "Normal"

            # 1. Encoding
            encoding_type = encoding_manager.detect_legacy_encoding(requested_font)
            processed_text = run.text
            if encoding_type:
                processed_text = encoding_manager.convert_to_unicode(run.text, encoding_type)
                report["legacy_conversions"].append({
                    "font": requested_font,
                    "type": encoding_type
                })

            # 2. Font Resolution
            resolved_path = font_registry.resolve_font(requested_font)
            if not resolved_path and processed_text:
                resolved_path = font_registry.resolve_font(requested_font, ord(processed_text[0]))
            
            if resolved_path:
                # Only report as substitution if it's actually a different font
                res_name = resolved_path.stem
                req_norm = requested_font.lower().replace(" ", "").replace("-", "")
                res_norm = res_name.lower().replace(" ", "").replace("-", "")
                
                # Check if resolved name contains requested name or vice-versa
                if req_norm not in res_norm and res_norm not in req_norm:
                    if requested_font != "Normal": # Don't flag default style resolution as substitution
                        report["font_substitutions"].append({
                            "requested": requested_font,
                            "resolved": res_name
                        })

            # 3. Rendering with fpdf2
            if resolved_path:
                font_id = resolved_path.stem
                if font_id not in registered_fonts:
                    pdf.add_font(font_id, "", str(resolved_path))
                    registered_fonts[font_id] = font_id
                
                pdf.set_font(font_id, size=12)
                
                # Detect script for shaping
                script = None
                if any(0x0900 <= ord(c) <= 0x097F for c in processed_text):
                    script = "deva"
                elif any(0x0C00 <= ord(c) <= 0x0C7F for c in processed_text):
                    script = "telu"
                
                # Set shaping for this run
                pdf.set_text_shaping(use_shaping_engine=True, script=script, direction="ltr")
                pdf.write(h=10, text=processed_text)
            else:
                pdf.set_font("helvetica", size=12)
                pdf.write(h=10, text=processed_text)
        
        pdf.ln(10) # Line break after paragraph

    pdf.output(str(pdf_output_path))
    return report
