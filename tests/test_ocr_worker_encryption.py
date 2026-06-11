"""Test that process_ocr encrypts output and /download decrypts it correctly."""
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))


def test_process_ocr_output_is_encrypted_not_plaintext(tmp_path):
    """Output file must not be readable as plain UTF-8 text (it must be encrypted)."""
    import worker as ocr_worker

    input_enc = tmp_path / "job123_input.png"
    output_file = tmp_path / "data" / "outputs" / "job123_ocr.txt"

    fake_plaintext = "This is OCR output text"

    def fake_decrypt_to_file(src, dst):
        dst.write_bytes(b"fake_image_bytes")

    def fake_run_ocr(path, lang):
        return fake_plaintext

    encrypted_content = b"\xde\xad\xbe\xef\x00\x01\x02\x03"

    def fake_encrypt_file(src, dst):
        dst.write_bytes(encrypted_content)

    with (
        patch.object(ocr_worker.security_manager, "decrypt_to_file", side_effect=fake_decrypt_to_file),
        patch.object(ocr_worker.security_manager, "encrypt_file", side_effect=fake_encrypt_file),
        patch("worker.run_ocr", side_effect=fake_run_ocr),
        patch.object(ocr_worker, "BASE_DIR", tmp_path),
    ):
        result = ocr_worker.process_ocr(str(input_enc), lang="auto", ocr_job_id="job123")

    assert result["ocr"] is True
    assert result["char_count"] == len(fake_plaintext)
    assert output_file.exists()
    # Output must not be the raw plaintext — it should be the encrypted bytes
    assert output_file.read_bytes() == encrypted_content
    assert output_file.read_bytes() != fake_plaintext.encode()


def test_process_ocr_cleans_up_input_on_success(tmp_path):
    """Input file must be deleted after successful OCR."""
    import worker as ocr_worker

    input_enc = tmp_path / "job456_input.pdf"
    input_enc.write_bytes(b"encrypted_input")
    output_dir = tmp_path / "data" / "outputs"

    def fake_decrypt_to_file(src, dst):
        dst.write_bytes(b"fake_pdf_bytes")

    def fake_encrypt_file(src, dst):
        dst.write_bytes(b"encrypted_output")

    with (
        patch.object(ocr_worker.security_manager, "decrypt_to_file", side_effect=fake_decrypt_to_file),
        patch.object(ocr_worker.security_manager, "encrypt_file", side_effect=fake_encrypt_file),
        patch("worker.run_ocr", return_value="text"),
        patch.object(ocr_worker, "BASE_DIR", tmp_path),
    ):
        ocr_worker.process_ocr(str(input_enc), lang="auto", ocr_job_id="job456")

    assert not input_enc.exists(), "Encrypted input must be deleted after OCR"
