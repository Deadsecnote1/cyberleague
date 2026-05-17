#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def main() -> int:
    payload = json.loads(sys.stdin.read())
    path = Path(payload["reportPath"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload["html"], encoding="utf-8")
    print(json.dumps({"ok": True, "reportPath": str(path.resolve())}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
