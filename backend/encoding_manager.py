import unicodedata
import re
from typing import Dict, Optional

class EncodingManager:
    def __init__(self):
        # Maps for legacy encodings (Example: APS_Telugu, Anu_Telugu)
        # In a real production system, these would be large mapping tables.
        # For this implementation, we define the structure and a sample mapping.
        self.legacy_maps: Dict[str, Dict[int, str]] = {
            "APS": {
                # Dummy mapping for demonstration
                # 0x61 (a) -> Unicode Telugu A
                0x61: "\u0C05", 
            },
            "Anu": {
                # Dummy mapping
                0x61: "\u0C05",
            }
        }
        
        # CID Specific Mappings (for PDF extraction)
        self.cid_mappings: Dict[str, Dict[int, str]] = {
            "GLOBAL": {
                # Common control or non-printable glyphs often seen in Indic PDFs
                9: "",   # Tab/Junk
                12: "",  # Form Feed/Junk
                1: "",   # Often used for zero-width chars
                2: "",
                3: " ",  # Often used for space in some subsetted fonts
                # Expanded list from user feedback
                5: "", 30: "", 46: "", 57: "", 74: "", 77: "", 79: "", 85: "", 89: "", 102: "", 117: ""
            }
        }

    def detect_legacy_encoding(self, font_name: str) -> Optional[str]:
        """Detects if a font name suggests a legacy encoding."""
        if not font_name:
            return None
            
        font_upper = font_name.upper()
        for encoding in self.legacy_maps.keys():
            if encoding in font_upper:
                return encoding
        return None

    def convert_to_unicode(self, text: str, encoding_type: str) -> str:
        """Converts text from a legacy encoding to Unicode."""
        if encoding_type not in self.legacy_maps:
            return text
            
        mapping = self.legacy_maps[encoding_type]
        converted = []
        for char in text:
            code = ord(char)
            if code in mapping:
                converted.append(mapping[code])
            else:
                converted.append(char)
        
        # Normalize the result to NFC
        return unicodedata.normalize('NFC', "".join(converted))

    def resolve_cid(self, cid_val: int, font_name: str) -> Optional[str]:
        """Resolves a CID value to a Unicode character based on font context."""
        # 1. Check font-specific CID mapping
        if font_name in self.cid_mappings:
            if cid_val in self.cid_mappings[font_name]:
                return self.cid_mappings[font_name][cid_val]
        
        # 2. Check global/common mappings
        if cid_val in self.cid_mappings["GLOBAL"]:
            return self.cid_mappings["GLOBAL"][cid_val]
            
        # 3. Check legacy maps if font suggests it
        encoding_type = self.detect_legacy_encoding(font_name)
        if encoding_type and encoding_type in self.legacy_maps:
            if cid_val in self.legacy_maps[encoding_type]:
                return self.legacy_maps[encoding_type][cid_val]
                
        return None

    def strip_all_junk(self, text: str) -> str:
        """Aggressively removes (cid:N), ( : N), and other PDF extraction artifacts."""
        if not text:
            return ""
        # Matches (cid:5), (cid : 5), ( : 5), (cid: 5), etc.
        text = re.sub(r'\(cid\s*:\s*\d+\s*\)', '', text)
        text = re.sub(r'\(\s*:\s*\d+\s*\)', '', text)
        # Matches stray lone cid markers
        text = re.sub(r'cid\s*:\s*\d+', '', text)
        # Matches characters often mangled by extraction
        text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text) 
        return text

# Global instance
encoding_manager = EncodingManager()
