#!/usr/bin/env python3
"""Apply all n8n workflow patches: forms, scan cmd, report, parse, AI, pre-scan path."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent


def main() -> None:
    order = [
        "patch_scan_config_form.py",
        "patch_report_node.py",
        "patch_parse_scan.py",
        "patch_ai_workflow.py",
        "patch_portal_webhook.py",
    ]
    for name in order:
        path = SCRIPTS / name
        print(f"\n=== {name} ===")
        subprocess.run([sys.executable, str(path)], check=True)
    print("\nAll workflow patches applied. Refresh n8n in the browser.")


if __name__ == "__main__":
    main()
