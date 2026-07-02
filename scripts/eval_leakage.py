#!/usr/bin/env py -3.12
"""Scan for question leakage.

Two checks:
  1. dev vs held_out stems in questions.json (exact / substring match).
  2. the application-practice remediation pool
     (data/application-practice.json) vs EVERY questions.json stem — both dev and
     held_out. "Practice" that re-shows a held_out eval item is leakage (zeroes
     the score); one that re-shows a dev/performance item the student already saw
     is not real practice. This pass uses exact/substring PLUS a token-overlap
     (Jaccard) near-duplicate threshold to catch reworded near-dupes.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

# Jaccard token-overlap at or above this ratio flags a near-duplicate stem.
NEAR_DUP_JACCARD = 0.60

# A §7d paraphrase pair must be genuinely REWORDED, not a near-identical clone:
# the two stems of a pair are flagged if they are exact/substring matches or
# their token overlap is at or above this ratio.
PARAPHRASE_MAX_JACCARD = 0.70


def normalize(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return " ".join(text.split())


def tokens(text: str) -> set[str]:
    return set(normalize(text).split())


def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def check_dev_vs_held(questions: list[dict]) -> list[str]:
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
    return leaks


def check_pool_vs_questions(questions: list[dict]) -> list[str]:
    """Flag any application-practice item that duplicates or closely paraphrases
    a stem served in questions.json (dev OR held_out)."""
    pool_path = DATA / "application-practice.json"
    if not pool_path.exists():
        print("No application-practice.json — skipping pool leakage check")
        return []

    pool = json.loads(pool_path.read_text(encoding="utf-8"))
    print(f"application-practice pool: {len(pool)} items vs {len(questions)} bank items")

    bank = [
        (q["id"], q.get("split", "?"), normalize(q["stem"]), tokens(q["stem"]))
        for q in questions
    ]
    leaks: list[str] = []
    for p in pool:
        pn = normalize(p["stem"])
        pt = tokens(p["stem"])
        for bid, bsplit, bn, bt in bank:
            if not pn or not bn:
                continue
            if pn == bn or pn in bn or bn in pn:
                leaks.append(
                    f"LEAK: pool {p['id']} ~ {bsplit} {bid} (exact/substring)"
                )
                continue
            sim = jaccard(pt, bt)
            if sim >= NEAR_DUP_JACCARD:
                leaks.append(
                    f"NEAR-DUP: pool {p['id']} ~ {bsplit} {bid} "
                    f"(jaccard={sim:.2f})"
                )
    return leaks


def check_paraphrase_pairs(questions: list[dict]) -> list[str]:
    """Confirm each §7d paraphrase pair is genuinely reworded: the two linked
    stems must not be exact/substring duplicates and must fall below the
    near-identical token-overlap threshold. (This is the opposite intent from
    the split-leakage checks: here we prove the pair is DIFFERENT enough.)"""
    manifest = DATA / "paraphrase-test.json"
    if not manifest.exists():
        print("No paraphrase-test.json — skipping paraphrase-pair check")
        return []

    doc = json.loads(manifest.read_text(encoding="utf-8"))
    rows = doc.get("concepts") if isinstance(doc, dict) else doc
    by_id = {q["id"]: q for q in questions}

    leaks: list[str] = []
    max_j = 0.0
    checked = 0
    for row in rows:
        a, b = row["question_ids"]
        qa, qb = by_id.get(a), by_id.get(b)
        if not qa or not qb:
            leaks.append(f"MISSING: pair {row['concept']} references unknown id")
            continue
        na, nb = normalize(qa["stem"]), normalize(qb["stem"])
        if na == nb or na in nb or nb in na:
            leaks.append(
                f"CLONE: {row['concept']} {a}~{b} stems are exact/substring "
                "duplicates (not a paraphrase)"
            )
            continue
        sim = jaccard(tokens(qa["stem"]), tokens(qb["stem"]))
        max_j = max(max_j, sim)
        checked += 1
        if sim >= PARAPHRASE_MAX_JACCARD:
            leaks.append(
                f"NEAR-IDENTICAL: {row['concept']} {a}~{b} "
                f"(jaccard={sim:.2f} ≥ {PARAPHRASE_MAX_JACCARD}) — reword"
            )
    print(
        f"paraphrase pairs: {checked} checked, max stem jaccard={max_j:.2f} "
        f"(threshold {PARAPHRASE_MAX_JACCARD})"
    )
    return leaks


def main() -> int:
    path = DATA / "questions.json"
    if not path.exists():
        print("No questions.json — nothing to scan")
        return 0

    questions = json.loads(path.read_text(encoding="utf-8"))

    leaks = check_dev_vs_held(questions)
    leaks.extend(check_pool_vs_questions(questions))
    leaks.extend(check_paraphrase_pairs(questions))

    if leaks:
        print("Leakage check FAILED:")
        for line in leaks:
            print(f"  - {line}")
        return 1

    print(
        "Leakage check OK (dev/held_out exact/substring; "
        f"pool exact/substring + jaccard<{NEAR_DUP_JACCARD})"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
