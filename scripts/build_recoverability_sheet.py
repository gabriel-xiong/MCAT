#!/usr/bin/env py -3.12
"""Build a BLIND tag-recoverability instrument for a human pilot (NEW file).

Emits three files under data/:
  * tag-recoverability-sheet.json   -> given to the human. Question stem, choices,
                                       correct letter, and the CHOSEN distractor.
                                       TAGS ARE WITHHELD.
  * tag-recoverability-key.json     -> hidden answer key (gold map + misconception
                                       + heuristic distinctiveness). Do NOT show
                                       the human.
  * tag-recoverability-human.TEMPLATE.json -> blank template the human fills in.

The human's task: from ONLY the stem + choices + which distractor was chosen,
independently label the error mode of the chosen distractor:
  label = one of {content_gap, trap, null}
  trap_enum (only if label==trap) = inverse|unit|scaling|negation|transpose|partial
  misconception (only if label==content_gap) = free-text: the SPECIFIC wrong belief.

Then scripts/score_tag_agreement.py compares the filled human file to the key.

Sample: stratified across the eval trio (cp_acids_bases, bb_enzymes, cp_kinetics)
spanning trap + content_gap (distinctive/borderline/generic) + null. Seeded.
"""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from analyze_tags import classify, distinctiveness  # noqa: E402

LETTERS = "ABCD"
TRIO = ["cp_acids_bases", "bb_enzymes", "cp_kinetics"]
SEED = 20260702

# Stratified target counts (across the whole trio).
TARGETS = {
    "trap": 12,          # take all available trap distractors in the trio
    "null": 8,
    "cg_distinctive": 10,
    "cg_borderline": 6,
    "cg_generic": 4,
}


def coarse_map(cls: str) -> str:
    if cls.startswith("trap:"):
        return "trap"
    return cls  # 'content_gap' or 'null'


def build_cases(qs):
    cases = []
    for q in qs:
        if q.get("topic_id") not in TRIO:
            continue
        cd = q.get("choice_diagnosis") or []
        ci = LETTERS.index(q["correct"])
        for i, ctext in enumerate(q["choices"]):
            if i == ci:
                continue
            entry = cd[i] if i < len(cd) else None
            cls = classify(entry)
            cmap = coarse_map(cls)
            if cmap == "content_gap":
                strat = "cg_" + distinctiveness(entry.get("misconception", ""), ctext)
            elif cmap == "trap":
                strat = "trap"
            else:
                strat = "null"
            cases.append(
                {
                    "qid": q["id"],
                    "topic_id": q["topic_id"],
                    "section": q.get("section", ""),
                    "stem": q["stem"],
                    "choices": q["choices"],
                    "correct_letter": q["correct"],
                    "chosen_letter": LETTERS[i],
                    "chosen_text": ctext,
                    "_gold_map": cmap,
                    "_gold_trap": cls.split(":", 1)[1] if cls.startswith("trap:") else "",
                    "_gold_misconception": entry.get("misconception", "") if entry else "",
                    "_distinctiveness": strat.replace("cg_", "") if cmap == "content_gap" else "",
                    "_strat": strat,
                }
            )
    return cases


def stratified_sample(cases):
    rng = random.Random(SEED)
    buckets = {}
    for c in cases:
        buckets.setdefault(c["_strat"], []).append(c)
    picked = []
    for strat, target in TARGETS.items():
        pool = buckets.get(strat, [])
        rng.shuffle(pool)
        picked.extend(pool[:target])
    # Stable ordering by qid+chosen for a clean sheet, but shuffle so the human
    # cannot infer the stratum from ordering.
    rng.shuffle(picked)
    return picked


def main():
    qs = json.loads((DATA / "questions.json").read_text(encoding="utf-8"))
    cases = build_cases(qs)
    picked = stratified_sample(cases)

    sheet_items, key_items, tmpl_items = [], [], []
    for n, c in enumerate(picked, 1):
        cid = f"C{n:02d}"
        sheet_items.append(
            {
                "case_id": cid,
                "qid": c["qid"],
                "topic_id": c["topic_id"],
                "section": c["section"],
                "stem": c["stem"],
                "choices": {LETTERS[i]: t for i, t in enumerate(c["choices"])},
                "correct_letter": c["correct_letter"],
                "chosen_letter": c["chosen_letter"],
                "chosen_text": c["chosen_text"],
            }
        )
        key_items.append(
            {
                "case_id": cid,
                "qid": c["qid"],
                "chosen_letter": c["chosen_letter"],
                "gold_map": c["_gold_map"],
                "gold_trap": c["_gold_trap"],
                "gold_misconception": c["_gold_misconception"],
                "heuristic_distinctiveness": c["_distinctiveness"],
            }
        )
        tmpl_items.append(
            {
                "case_id": cid,
                "label": "",           # content_gap | trap | null
                "trap_enum": "",       # inverse|unit|scaling|negation|transpose|partial
                "misconception": "",   # free-text if label==content_gap
            }
        )

    sheet = {
        "instructions": (
            "For each case you see a question, its choices, the CORRECT answer, "
            "and the ONE distractor a student chose. Without any answer key, decide "
            "WHY that specific wrong choice is attractive and label its error mode. "
            "label = 'content_gap' (a specific misconception), 'trap' (an execution "
            "slip: inverse/unit/scaling/negation/transpose/partial), or 'null' (a "
            "generic near-miss with no single identifiable error). If 'content_gap', "
            "write the SPECIFIC wrong belief in one clause. Fill "
            "tag-recoverability-human.json (copy the TEMPLATE)."
        ),
        "allowed_labels": ["content_gap", "trap", "null"],
        "allowed_trap_enums": [
            "inverse", "unit", "scaling", "negation", "transpose", "partial",
        ],
        "n_cases": len(sheet_items),
        "items": sheet_items,
    }
    key = {"n_cases": len(key_items), "items": key_items}
    tmpl = {
        "note": "Copy to tag-recoverability-human.json and fill each item.",
        "items": tmpl_items,
    }

    (DATA / "tag-recoverability-sheet.json").write_text(
        json.dumps(sheet, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (DATA / "tag-recoverability-key.json").write_text(
        json.dumps(key, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (DATA / "tag-recoverability-human.TEMPLATE.json").write_text(
        json.dumps(tmpl, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    from collections import Counter

    strat_counts = Counter(c["_strat"] for c in picked)
    print(f"Built {len(picked)} cases -> data/tag-recoverability-sheet.json")
    print("Stratum counts:", dict(strat_counts))
    print("Key -> data/tag-recoverability-key.json")
    print("Template -> data/tag-recoverability-human.TEMPLATE.json")


if __name__ == "__main__":
    main()
