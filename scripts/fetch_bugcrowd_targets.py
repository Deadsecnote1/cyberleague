#!/usr/bin/env python3
"""Load bug bounty targets for n8n. Primary source: data/targets.csv."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CSV = ROOT / "data" / "targets.csv"
DOMAIN_RE = re.compile(
    r"^(?:\*\.|[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,}$",
    re.IGNORECASE,
)


def normalize_domain(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"^https?://", "", value)
    value = value.split("/")[0].split(":")[0]
    if value.startswith("www."):
        value = value[4:]
    return value


def load_csv(path: Path) -> list[dict]:
    if not path.exists():
        raise FileNotFoundError(f"Targets file not found: {path}")

    rows: list[dict] = []
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        required = {"program", "domain"}
        if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
            raise ValueError(
                f"CSV must include columns: program,domain (optional: notes,in_scope). Got: {reader.fieldnames}"
            )

        for line_no, row in enumerate(reader, start=2):
            domain_raw = (row.get("domain") or "").strip()
            if not domain_raw or domain_raw.startswith("#"):
                continue

            domain = normalize_domain(domain_raw)
            wildcard = domain_raw.strip().startswith("*.")
            if not wildcard and not DOMAIN_RE.match(domain):
                print(f"Skipping invalid domain on line {line_no}: {domain_raw}", file=sys.stderr)
                continue

            in_scope = (row.get("in_scope") or "yes").strip().lower()
            if in_scope not in {"yes", "true", "1", "y"}:
                continue

            rows.append(
                {
                    "program": (row.get("program") or "unknown").strip(),
                    "domain": domain,
                    "scope_raw": domain_raw,
                    "notes": (row.get("notes") or "").strip(),
                    "source": "targets.csv",
                }
            )

    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Load authorized bug bounty targets")
    parser.add_argument(
        "--csv",
        default=str(DEFAULT_CSV),
        help="Path to targets CSV (program,domain,notes,in_scope)",
    )
    args = parser.parse_args()

    try:
        targets = load_csv(Path(args.csv))
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"ok": False, "error": str(exc), "targets": []}))
        return 1

    print(
        json.dumps(
            {
                "ok": True,
                "count": len(targets),
                "csv": str(Path(args.csv).resolve()),
                "targets": targets,
                "note": (
                    "Using intentionally vulnerable demo targets from data/targets.csv. "
                    "Replace with Bugcrowd in-scope domains when ready."
                ),
            }
        )
    )
    return 0 if targets else 2


if __name__ == "__main__":
    raise SystemExit(main())
