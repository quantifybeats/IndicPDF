import logging
import unicodedata
import re
from docx import Document
from fpdf import FPDF
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    from .font_manager import font_registry
    from .encoding_manager import encoding_manager
    from .shaping_engine import shaping_engine
except (ImportError, ValueError):
    from font_manager import font_registry
    from encoding_manager import encoding_manager
    from shaping_engine import shaping_engine

class IndicPDF(FPDF):
    def header(self):
        pass
    def footer(self):
        pass

def get_shaped_clusters(text: str, font_path: Path, font_size: float) -> list:
    """
    Uses HarfBuzz to segment text into atomic visual clusters with precise widths.
    Each cluster is a dict: {'text': str, 'width': float}
    """
    if not text:
        return []
        
    glyphs = shaping_engine.shape_text(text, font_path, font_size)
    if not glyphs:
        # Fallback to character-level if shaping fails
        return [{'text': c, 'width': 0} for c in text]

    clusters = []
    # HarfBuzz clusters identify the starting index in the input string.
    # We sort by cluster index to handle RTL or complex reordering if necessary.
    sorted_glyphs = sorted(glyphs, key=lambda x: x['cluster'])
    
    # Identify unique cluster boundaries
    cluster_boundaries = sorted(list(set(g['cluster'] for r in [glyphs] for g in r)))
    cluster_boundaries.append(len(text)) # End of string
    
    # Group glyphs and text by these boundaries
    for i in range(len(cluster_boundaries) - 1):
        start = cluster_boundaries[i]
        end = cluster_boundaries[i+1]
        cluster_text = text[start:end]
        
        # Sum width of all glyphs belonging to this cluster
        # Note: multiple glyphs can have the same cluster index
        cluster_width = sum(g['x_advance'] for g in glyphs if g['cluster'] == start)
        
        clusters.append({
            'text': cluster_text,
            'width': cluster_width,
            'is_space': cluster_text.isspace()
        })
        
    return clusters

def render_run_low_level(pdf, text, font_id, font_path, font_size, script, language):
    """
    Renders text using absolute positioning and manual cluster-aware wrapping.
    Eliminates pdf.write() to prevent uncontrolled internal splitting.
    """
    if not text:
        return

    # 1. Normalize and Shape
    text = unicodedata.normalize('NFC', text)
    clusters = get_shaped_clusters(text, font_path, font_size)
    
    # 2. Set Font and Shaping for fpdf2 (measurement)
    pdf.set_font(font_id, size=font_size)
    pdf.set_text_shaping(use_shaping_engine=True, script=script, language=language)
    
    line_height = font_size * 1.4 if script else font_size * 1.2
    margin_right = pdf.w - pdf.r_margin
    margin_left = pdf.l_margin

    for cluster in clusters:
        cluster_text = cluster['text']
        cluster_width = cluster['width']
        
        # Check if cluster fits on current line
        if pdf.get_x() + cluster_width > margin_right:
            # Move to next line
            pdf.set_xy(margin_left, pdf.get_y() + line_height)
            
            # If it's a space at the start of a new line, skip it
            if cluster['is_space']:
                continue
        
        # Render at current position
        # We use pdf.text() with absolute coordinates to ensure no internal wrapping occurs
        pdf.text(pdf.get_x(), pdf.get_y(), cluster_text)
        
        # Advance cursor manually
        pdf.set_x(pdf.get_x() + cluster_width)

def process_docx_to_pdf_final(docx_path: Path, pdf_output_path: Path):
    """Production-grade pipeline using low-level cluster-aware layout."""
    report = {
        "font_substitutions": [],
        "legacy_conversions": [],
        "status": "success"
    }
    
    doc = Document(docx_path)
    pdf = IndicPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    
    registered_fonts = {}

    for para in doc.paragraphs:
        # Paragraph start position
        pdf.set_x(pdf.l_margin)
        
        max_font_size = 12
        
        for run in para.runs:
            if not run.text:
                continue
                
            requested_font = run.font.name or "Normal"
            is_bold = run.bold or False
            is_italic = run.italic or False
            font_size = run.font.size.pt if (run.font and run.font.size) else 12
            max_font_size = max(max_font_size, font_size)

            # 1. Encoding & Normalization
            encoding_type = encoding_manager.detect_legacy_encoding(requested_font)
            processed_text = run.text
            if encoding_type:
                processed_text = encoding_manager.convert_to_unicode(run.text, encoding_type)
                report["legacy_conversions"].append({"font": requested_font, "type": encoding_type})

            # 2. Font Resolution
            resolved_path = font_registry.resolve_font(requested_font, bold=is_bold, italic=is_italic)
            if not resolved_path and processed_text.strip():
                resolved_path = font_registry.resolve_font(requested_font, ord(processed_text.strip()[0]), bold=is_bold, italic=is_italic)
            
            if resolved_path:
                font_id = resolved_path.stem
                if font_id not in registered_fonts:
                    try:
                        pdf.add_font(font_id, "", str(resolved_path))
                        registered_fonts[font_id] = font_id
                    except Exception as e:
                        logger.error(f"Failed to add font {font_id}: {e}")
                        continue
                
                # Detect script
                script = None
                language = None
                if any(0x0900 <= ord(c) <= 0x097F for c in processed_text):
                    script = "deva"; language = "HIN"
                elif any(0x0C00 <= ord(c) <= 0x0C7F for c in processed_text):
                    script = "telu"; language = "TEL"
                
                # Low-level Rendering
                render_run_low_level(pdf, processed_text, font_id, resolved_path, font_size, script, language)
            else:
                pdf.set_font("helvetica", size=font_size)
                pdf.write(h=font_size * 1.2, text=processed_text)
        
        # New line after paragraph
        pdf.ln(max_font_size * 1.5)

    pdf.output(str(pdf_output_path))
    return report
