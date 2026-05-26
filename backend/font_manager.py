import os
from pathlib import Path
from fontTools.ttLib import TTFont
from typing import Dict, List, Set, Optional

class FontMetadata:
    def __init__(self, path: Path, postscript_name: str, full_name: str, family_name: str, unicode_ranges: Set[int], family_names: Set[str]):
        self.path = path
        self.postscript_name = postscript_name
        self.full_name = full_name
        self.family_name = family_name
        self.unicode_ranges = unicode_ranges
        self.family_names = family_names # Includes localized names

class FontRegistry:
    def __init__(self):
        self.registry: Dict[str, FontMetadata] = {}
        self.script_fallback: Dict[str, List[FontMetadata]] = {}

    def scan_directory(self, directory: Path):
        """Scans a directory for TTF/OTF/TTC fonts and extracts metadata."""
        if not directory.exists():
            return

        for font_file in directory.glob("**/*.[ot]t[fc]"):
            try:
                if font_file.suffix.lower() == ".ttc":
                    self._handle_ttc(font_file)
                else:
                    metadata = self._extract_metadata(font_file)
                    if metadata:
                        self._register_metadata(metadata)
            except Exception as e:
                print(f"Error processing font {font_file}: {e}")

    def _handle_ttc(self, ttc_path: Path):
        """Extracts faces from a TTC collection to individual TTF files for better compatibility."""
        from fontTools.ttLib import TTCollection
        try:
            collection = TTCollection(ttc_path)
            # Create a subfolder for extracted faces
            if "VERCEL" in os.environ:
                extract_dir = Path("/tmp/fonts_extracted") / ttc_path.stem
            else:
                extract_dir = ttc_path.parent / f"_{ttc_path.stem}_extracted"
            
            extract_dir.mkdir(parents=True, exist_ok=True)

            for i, font in enumerate(collection.fonts):
                metadata = self._extract_metadata_from_obj(font, ttc_path)
                if metadata:
                    # Save face as a standalone TTF
                    face_filename = f"{metadata.postscript_name or metadata.full_name or f'face_{i}'}.ttf"
                    face_path = extract_dir / face_filename
                    if not face_path.exists():
                        font.save(face_path)
                    
                    # Register the newly saved TTF instead of the TTC
                    extracted_metadata = self._extract_metadata(face_path)
                    if extracted_metadata:
                        self._register_metadata(extracted_metadata)
        except Exception as e:
            print(f"Failed to extract TTC {ttc_path}: {e}")

    def _register_metadata(self, metadata: FontMetadata):
        self.registry[metadata.postscript_name] = metadata
        self.registry[metadata.full_name] = metadata
        self.registry[metadata.family_name] = metadata
        self._map_to_scripts(metadata)

    def _extract_metadata(self, path: Path) -> Optional[FontMetadata]:
        font = TTFont(path)
        return self._extract_metadata_from_obj(font, path)

    def _extract_metadata_from_obj(self, font: TTFont, path: Path) -> Optional[FontMetadata]:
        name_table = font['name']
        
        postscript_name = ""
        full_name = ""
        family_name = ""
        family_names = set()

        for record in name_table.names:
            try:
                name = record.toUnicode()
                if record.nameID == 1:
                    family_name = name
                    family_names.add(name)
                elif record.nameID == 4:
                    full_name = name
                elif record.nameID == 6:
                    postscript_name = name
            except:
                continue

        # Extract Unicode ranges
        unicode_ranges = set()
        if 'cmap' in font:
            for table in font['cmap'].tables:
                unicode_ranges.update(table.cmap.keys())

        return FontMetadata(path, postscript_name, full_name, family_name, unicode_ranges, family_names)

    def _map_to_scripts(self, metadata: FontMetadata):
        # Simplified Unicode block detection for fallback mapping
        # Devanagari: 0900–097F
        # Telugu: 0C00–0C7F
        # Tamil: 0B80–0BFF
        # This list will be expanded in Path 3/4
        scripts = {
            "devanagari": range(0x0900, 0x0980),
            "telugu": range(0x0C00, 0x0C80),
            "tamil": range(0x0B80, 0x0C00),
        }

        for script_name, r in scripts.items():
            if any(code in metadata.unicode_ranges for code in r):
                if script_name not in self.script_fallback:
                    self.script_fallback[script_name] = []
                self.script_fallback[script_name].append(metadata)

    def resolve_font(self, font_name: str, char_code: Optional[int] = None) -> Optional[Path]:
        """Resolves a font name or character to a local file path."""
        # 1. Normalize and check direct/family matches
        norm_requested = font_name.lower().replace(" ", "").replace("-", "")
        
        # Priority 1: Exact or Normalized name match (PS name, Full name)
        for name, metadata in self.registry.items():
            if name.lower().replace(" ", "").replace("-", "") == norm_requested:
                return metadata.path
        
        # Priority 2: Family name match (including localized names)
        for name, metadata in self.registry.items():
            for fam in metadata.family_names:
                if fam.lower().replace(" ", "").replace("-", "") == norm_requested:
                    # Prefer Regular weight
                    if "regular" in metadata.postscript_name.lower() or "regular" in metadata.full_name.lower():
                        return metadata.path
                    return metadata.path

        # 2. Fallback by character/script
        if char_code:
            for script_name, fonts in self.script_fallback.items():
                # Check if char_code is in the script's range (heuristic)
                # For now, just return first font that supports the char
                for font in fonts:
                    if char_code in font.unicode_ranges:
                        return font.path
        
        return None

# Global registry instance
font_registry = FontRegistry()

def initialize_font_registry():
    base_fonts_path = Path("fonts")
    font_registry.scan_directory(base_fonts_path / "system")
    font_registry.scan_directory(base_fonts_path / "fallback")
    font_registry.scan_directory(base_fonts_path / "uploads")
    print(f"Font Registry initialized with {len(font_registry.registry)} entries.")
