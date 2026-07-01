#!/usr/bin/env py -3.12
"""Scan dev vs held_out questions for duplicate/near-duplicate stems."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


def normalize(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return " ".join(text.split())


def main() -> int:
    path = DATA / "questions.json"
    if not path.exists():
        print("No questions.json — nothing to scan")
        return 0

    questions = json.loads(path.read_text(encoding="utf-8"))
    dev = [q for q in questions if q.get("split") == "dev"]
    held = [q for q in questions if q.get("split") == "held_out"]

    print(f"dev: {len(dev)}  held_out: {len(held)}")

    leaks: list[str] = []
    held_norm = {q["id"]: normalize(q["stem"]) for q in held}

    for q in dev:
        dn = normalize(q["stem"])
        for hid, hn in held_norm.items():
            if not dn or not hn:
                continue
            if dn == hn or dn in hn or hn in dn:
                leaks.append(f"LEAK: dev {q['id']} ~ held_out {hid}")

    if leaks:
        print("Leakage check FAILED:")
        for line in leaks:
            print(f"  - {line}")
        return 1

    print("Leakage check OK (exact/substring stem match)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
