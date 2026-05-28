import unittest
from pathlib import Path
from backend.pdf_processor import normalize_font_name

class TestPdfProcessor(unittest.TestCase):
    def test_normalize_font_name_with_subset(self):
        self.assertEqual(normalize_font_name("AAAAAA+NotoSansTelugu"), "NotoSansTelugu")
        self.assertEqual(normalize_font_name("ABCDEF+Arial-Bold"), "Arial-Bold")

    def test_normalize_font_name_without_subset(self):
        self.assertEqual(normalize_font_name("NotoSansTelugu"), "NotoSansTelugu")
        self.assertEqual(normalize_font_name("Times-Roman"), "Times-Roman")

    def test_normalize_font_name_empty(self):
        self.assertEqual(normalize_font_name(""), "Normal")
        self.assertEqual(normalize_font_name(None), "Normal")

if __name__ == "__main__":
    unittest.main()
