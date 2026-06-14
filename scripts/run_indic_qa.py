#!/usr/bin/env python3
"""Run the Indic rendering-correctness self-test and print a matrix.

    python3 scripts/run_indic_qa.py [txt,docx]

Prints one line per (script x format) with the verdict and per-signal flags,
then a summary. Exit code is non-zero if anything FAILed or ERRORed, so it can
gate CI / a deploy smoke test.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from font_manager import initialize_font_registry  # noqa: E402
import indic_qa  # noqa: E402


def main():
    formats = tuple((sys.argv[1] if len(sys.argv) > 1 else "txt,docx").split(","))
    initialize_font_registry()
    report = indic_qa.run_self_test(formats=formats)

    for r in report["results"]:
        sig = " ".join(
            f"{k}={'·' if v.get('ok') is None else ('PASS' if v['ok'] else 'X')}"
            for k, v in r.get("signals", {}).items()
        )
        extra = f"  ERROR: {r['error']}" if r["verdict"] == "ERROR" else ""
        print(f"[{r['verdict']:6}] {r['label']:26} {sig}{extra}")

    s = report["summary"]
    print(f"\nsummary: {s['pass']} pass / {s['fail']} fail / {s['error']} error "
          f"(of {s['total']})")
    if s["needs_review"]:
        print("needs human review (low OCR):", ", ".join(s["needs_review"]))
    print(json.dumps(s))
    sys.exit(0 if (s["fail"] == 0 and s["error"] == 0) else 1)


if __name__ == "__main__":
    main()
