"""OCR processing module using Tesseract for Indic script support."""
import pytesseract
from pdf2image import convert_from_path
from PIL import Image
from pathlib import Path

LANG_MAP = {
    "hindi": "hin", "telugu": "tel", "tamil": "tam", "bengali": "ben",
    "gujarati": "guj", "kannada": "kan", "malayalam": "mal", "odia": "ori",
    "punjabi": "pan", "sanskrit": "san", "english": "eng", "auto": None,
}
AUTO_LANG = "hin+tel+tam+ben+guj+kan+mal+ori+san+eng"

def _resolve_lang(lang: str) -> str:
    tess_code = LANG_MAP.get(lang.lower())
    if tess_code is None and lang.lower() != "auto":
        return "eng"
    return tess_code or AUTO_LANG

def ocr_image_to_text(file_path: str, lang: str = "auto") -> str:
    tess_lang = _resolve_lang(lang)
    img = Image.open(file_path)
    return pytesseract.image_to_string(img, lang=tess_lang)

def ocr_pdf_to_text(file_path: str, lang: str = "auto") -> str:
    tess_lang = _resolve_lang(lang)
    images = convert_from_path(file_path, dpi=300)
    page_texts = [pytesseract.image_to_string(img, lang=tess_lang) for img in images]
    return "\n\n--- Page Break ---\n\n".join(page_texts)

def run_ocr(file_path: str, lang: str = "auto") -> str:
    ext = Path(file_path).suffix.lower()
    if ext == ".pdf":
        return ocr_pdf_to_text(file_path, lang)
    elif ext in {".jpg", ".jpeg", ".png", ".tiff", ".tif", ".bmp"}:
        return ocr_image_to_text(file_path, lang)
    else:
        raise ValueError(f"Unsupported file type for OCR: {ext}")
