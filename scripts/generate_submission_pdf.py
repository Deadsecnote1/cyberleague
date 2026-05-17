#!/usr/bin/env python3
"""Generate Cyber League Cursor Buildathon submission PDF via HTML + LibreOffice."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import markdown

ROOT = Path(__file__).resolve().parents[1]
MD_PATH = ROOT / "docs" / "CURSOR_BUILDATHON_SUBMISSION.md"
OUT_DIR = ROOT / "docs" / "submissions"
HTML_PATH = OUT_DIR / "Cyber_League_Cursor_Buildathon_Submission.html"
OUT_PDF = OUT_DIR / "Cyber_League_Cursor_Buildathon_Submission.pdf"

CSS = """
body { font-family: Liberation Sans, Arial, sans-serif; font-size: 11pt; line-height: 1.45;
       max-width: 800px; margin: 2cm auto; color: #111; }
h1 { font-size: 18pt; border-bottom: 2px solid #0891b2; padding-bottom: 0.3em; }
h2 { font-size: 14pt; margin-top: 1.4em; color: #0e7490; }
h3 { font-size: 12pt; margin-top: 1em; }
table { border-collapse: collapse; width: 100%; margin: 0.8em 0; font-size: 10pt; }
th, td { border: 1px solid #ccc; padding: 6px 8px; text-align: left; vertical-align: top; }
th { background: #f0f4f8; }
code { background: #f3f4f6; padding: 1px 4px; border-radius: 3px; font-size: 9.5pt; }
pre { background: #f8fafc; border: 1px solid #e2e8f0; padding: 10px; font-size: 9pt; overflow-x: auto; }
hr { border: none; border-top: 1px solid #ddd; margin: 1.5em 0; }
.footer { font-size: 9pt; color: #666; margin-top: 2em; }
"""


def main() -> int:
    if not MD_PATH.is_file():
        print(f"Missing {MD_PATH}", file=sys.stderr)
        return 1
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    body = markdown.markdown(
        MD_PATH.read_text(encoding="utf-8"),
        extensions=["tables", "fenced_code", "nl2br"],
    )
    html = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<title>Cyber League - Cursor Buildathon Submission</title>
<style>{CSS}</style></head><body>{body}
<p class="footer">Cyber League · Hackers League · Cursor × TechTalk360 · Confidential</p>
</body></html>"""
    HTML_PATH.write_text(html, encoding="utf-8")

    for cmd in (
        ["libreoffice", "--headless", "--convert-to", "pdf", "--outdir", str(OUT_DIR), str(HTML_PATH)],
        ["soffice", "--headless", "--convert-to", "pdf", "--outdir", str(OUT_DIR), str(HTML_PATH)],
    ):
        try:
            subprocess.run(cmd, check=True, capture_output=True, timeout=120)
            break
        except (FileNotFoundError, subprocess.CalledProcessError):
            continue
    else:
        print("LibreOffice not available; HTML written only:", HTML_PATH, file=sys.stderr)
        return 1

    if OUT_PDF.is_file():
        print(f"Wrote {OUT_PDF}")
        return 0
    print(f"Expected PDF not found at {OUT_PDF}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
