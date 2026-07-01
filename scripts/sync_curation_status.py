#!/usr/bin/env py -3.12
"""Recount questions.json into data/curation-status.json topic tallies."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


def main() -> None:
    status_path = DATA / "curation-status.json"
    questions_path = DATA / "questions.json"

    status = json.loads(status_path.read_text(encoding="utf-8"))
    questions = json.loads(questions_path.read_text(encoding="utf-8"))

    counts: dict[str, dict[str, int]] = defaultdict(lambda: {"dev": 0, "held_out": 0})
    for q in questions:
        tid = q["topic_id"]
        split = q["split"]
        counts[tid][split] += 1

    for tid, entry in status.get("topics", {}).items():
        entry["dev"] = counts[tid]["dev"]
        entry["held_out"] = counts[tid]["held_out"]

    status_path.write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")

    total_dev = sum(c["dev"] for c in counts.values())
    total_held = sum(c["held_out"] for c in counts.values())
    print(f"Updated curation-status.json — dev: {total_dev}, held_out: {total_held}")


if __name__ == "__main__":
    main()
