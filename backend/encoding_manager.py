import unicodedata
import re
from typing import Dict, Optional

class EncodingManager:
    def __init__(self):
        # Maps for legacy encodings (Example: APS_Telugu, Anu_Telugu, Kruti Dev)
        # In a real production system, these would be large mapping tables.
        self.legacy_maps: Dict[str, Dict[int, str]] = {
            "APS": {
                0x61: "\u0C05", 
            },
            "Anu": {
                0x61: "\u0C05",
            },
            "KRUTI DEV": {
                # Placeholder for Kruti Dev mapping.
            },
            "SHUSHA": {
                # Placeholder for Shusha mapping.
            }
        }
        
        # CID Specific Mappings (for PDF extraction)
        self.cid_mappings: Dict[str, Dict[int, str]] = {
            "GLOBAL": {
                9: "",   # Tab/Junk
                12: "",  # Form Feed/Junk
                1: "",   
                2: "",
                3: " ",  
                5: "", 30: "", 46: "", 57: "", 74: "", 77: "", 79: "", 85: "", 89: "", 102: "", 117: ""
            }
        }

    def detect_legacy_encoding(self, font_name: str) -> Optional[str]:
        """Detects if a font name suggests a legacy encoding."""
        if not font_name:
            return None
            
        font_upper = font_name.upper()
        # Handle "Kruti Dev 010" etc.
        if "KRUTI" in font_upper or ("DEV" in font_upper and any(x in font_upper for x in ["010", "011", "020"])):
            return "KRUTI DEV"
        if "SHUSHA" in font_upper:
            return "SHUSHA"
            
        for encoding in self.legacy_maps.keys():
            if encoding.upper() in font_upper:
                return encoding
        return None

    def convert_to_unicode(self, text: str, encoding_type: str) -> str:
        """Converts text from a legacy encoding to Unicode."""
        if encoding_type not in self.legacy_maps:
            return text
            
        mapping = self.legacy_maps[encoding_type]
        if not mapping:
            # If mapping is empty (stubbed), we return as is but could log
            return text
            
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
        if font_name in self.cid_mappings:
            if cid_val in self.cid_mappings[font_name]:
                return self.cid_mappings[font_name][cid_val]
        
        if cid_val in self.cid_mappings["GLOBAL"]:
            return self.cid_mappings["GLOBAL"][cid_val]
            
        encoding_type = self.detect_legacy_encoding(font_name)
        if encoding_type and encoding_type in self.legacy_maps:
            if cid_val in self.legacy_maps[encoding_type]:
                return self.legacy_maps[encoding_type][cid_val]
                
        return None

    def strip_all_junk(self, text: str) -> str:
        """Aggressively removes (cid:N), ( : N), and other PDF extraction artifacts."""
        if not text:
            return ""
        text = re.sub(r'\(cid\s*:\s*\d+\s*\)', '', text)
        text = re.sub(r'\(\s*:\s*\d+\s*\)', '', text)
        text = re.sub(r'cid\s*:\s*\d+', '', text)
        text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text) 
        return text

# Global instance
encoding_manager = EncodingManager()
