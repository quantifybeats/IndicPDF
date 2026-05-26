import uharfbuzz as hb
from pathlib import Path
from typing import List, Dict, Any, Optional

class ShapingEngine:
    def __init__(self):
        self.font_cache = {}

    def shape_text(self, text: str, font_path: Path, font_size: float = 12.0) -> Optional[List[Dict[str, Any]]]:
        """
        Shapes text using HarfBuzz.
        Returns a list of glyph information including IDs and positions.
        """
        if not font_path.exists():
            return None

        # Load font into HarfBuzz
        if font_path not in self.font_cache:
            with open(font_path, 'rb') as f:
                font_data = f.read()
            face = hb.Face(font_data)
            font = hb.Font(face)
            # Scale factors for HarfBuzz (usually 64 for subpixel precision, but here we map to PDF points)
            # We'll keep it at font UPEM or a standard scale and normalize later.
            upem = face.upem
            font.scale = (upem, upem)
            self.font_cache[font_path] = (font, upem)
        
        font, upem = self.font_cache[font_path]
        
        # Create and populate buffer
        buf = hb.Buffer()
        buf.add_str(text)
        buf.guess_segment_properties()
        
        # Shape
        hb.shape(font, buf, {})
        
        infos = buf.glyph_infos
        positions = buf.glyph_positions
        
        shaped_glyphs = []
        # Scale factor from UPEM to PDF points (1/72 inch)
        scale = font_size / upem
        
        for info, pos in zip(infos, positions):
            shaped_glyphs.append({
                "glyph_id": info.codepoint,
                "cluster": info.cluster,
                "x_advance": pos.x_advance * scale,
                "y_advance": pos.y_advance * scale,
                "x_offset": pos.x_offset * scale,
                "y_offset": pos.y_offset * scale
            })
            
        return shaped_glyphs

# Global instance
shaping_engine = ShapingEngine()
