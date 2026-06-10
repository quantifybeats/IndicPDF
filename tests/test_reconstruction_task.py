import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from reconstruction_engine import EngineResult, OCRSegment
from tasks import engine_result_to_payload


def test_payload_has_v2_contract_fields_and_success_flag():
    result = EngineResult(
        filename="తెలుగు.docx", source_type="docx",
        text="తెలుగు పరీక్ష", original_text="తెలుగు పరీక్ష",
        segments=[OCRSegment(text="తెలుగు పరీక్ష", confidence=0.99,
                             engine="docx_xml", line_number=1)],
        aggregate_confidence=0.99, detected_language="telugu",
        script="telugu", quality_score=0.98,
    )
    payload = engine_result_to_payload(result)
    assert payload["success"] is True
    assert payload["clean_text"] == "తెలుగు పరీక్ష"
    assert payload["confidence_scores"]["document"] == 0.99
    assert payload["layout_structure"][0]["type"] == "paragraph"
    assert payload["language_metadata"]["detected_language"] == "telugu"
    assert payload["quality_assessment"]["status"] == "usable"


def test_failure_payload_is_marked_unsuccessful():
    result = EngineResult(
        filename="bad.docx", source_type="docx", text="", original_text="",
        segments=[], aggregate_confidence=0.0, detected_language="unknown",
        script="unknown", quality_score=0.0,
        detected_issues=["docx_extraction_failed"],
        warnings=["processing_incomplete"],
    )
    payload = engine_result_to_payload(result)
    assert payload["success"] is False
    assert payload["quality_assessment"]["status"] == "processing_incomplete"
    assert "docx_extraction_failed" in payload["quality_assessment"]["detected_issues"]
