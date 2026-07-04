#!/usr/bin/env py -3.12
"""Merge the fresh g031-g060 semantic judgments into the main semantic-judge file.

Keeps g001-g030 as-is, REPLACES the stale g031-g040 entries (their questions were
trimmed and AI answers regenerated), and ADDS g041-g060 -> 60 item entries total.
Updates _meta counts and honest_notes. Idempotent: re-running yields the same 60.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
BUILD = ROOT / "build"

MAIN = DATA / "qa-goldset-semantic-judge.json"
FRESH = BUILD / "qa-judgments-g031-g060.json"

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # pragma: no cover
    pass


def main() -> int:
    main_doc = json.loads(MAIN.read_text(encoding="utf-8"))
    fresh_doc = json.loads(FRESH.read_text(encoding="utf-8"))

    fresh_items = {it["id"]: it for it in fresh_doc["items"]}
    changed_ids = set(fresh_items)  # g031..g060

    # Keep only g001-g030 from the existing file, then append the fresh g031-g060.
    kept = [it for it in main_doc["items"] if it["id"] not in changed_ids]
    kept_ids = {it["id"] for it in kept}
    expected_keep = {f"g{n:03d}" for n in range(1, 31)}
    missing_keep = expected_keep - kept_ids
    if missing_keep:
        raise SystemExit(f"expected g001-g030 to remain but missing: {sorted(missing_keep)}")

    ordered = kept + [fresh_items[f"g{n:03d}"] for n in range(31, 61)]
    ordered.sort(key=lambda it: it["id"])

    if len(ordered) != 60:
        raise SystemExit(f"expected 60 items after merge, got {len(ordered)}")

    meta = main_doc["_meta"]
    meta["must_not_say"] = (
        "any_violation booleans per method. Under semantic judging, exactly ONE of the 180 "
        "answers asserts a forbidden claim: the AI on g060 (it claims a LOWER activation energy "
        "is more temperature-sensitive -- the reverse of the truth -- asserting the g060 "
        "must_not_say). That is the only genuine violation across all 60 items and both baselines "
        "(static 0/60, keyword 0/60; AI 1/60 = 1.7%). The token scorer's extra must_not_say flags "
        "(ai/keyword on g001-g030) remain negation/refutation false positives."
    )
    meta["rubric_source"] = (
        "data/qa-goldset.json fact_atoms + must_not_say (human-validated: g001-g030 on 2026-07-02; "
        "g031-g060 on 2026-07-03)."
    )
    meta["generator_under_test"] = (
        "openai:gpt-4o-mini (data/qa-goldset-live-answers.json, all 60 answers incl. the regenerated g031-g060)"
    )
    meta["coverage_scale"] = (
        "0..1 per method per item; each fact_atom scored covered(1)/not(0), coverage = mean over that "
        "item's atoms. n=60 (9 parity / 51 differentiation, of which g031-g060 are the 30 hard items)."
    )
    meta["scope"] = (
        "60 items (g001-g060). g001-g030 judged 2026-07-02/03; g031-g040 RE-judged 2026-07-03 after "
        "their questions were trimmed and AI answers regenerated; g041-g060 judged 2026-07-03 (new). "
        "Fresh worksheet: build/qa-judge-worksheet-g031-g060.json; fresh judgments: "
        "build/qa-judgments-g031-g060.json."
    )
    meta["date"] = "2026-07-03"
    meta["honest_notes"] = (
        "AI does NOT win everywhere. (1) PARITY bucket: the static per-choice feedback is purpose-built "
        "to answer 'why is X wrong?' and slightly beats the AI here (parity: AI 90.8% vs static 94.4%). "
        "The clearest single parity loss is g013 (AI 0.67 vs static 1.0: AI omits the induced-fit atom); "
        "g001 and g002 are ties at 0.75 where the AI drops one secondary atom. "
        "(2) HARD items with WEAK/ERRONEOUS AI answers (regenerated g031-g060): g060 is the worst -- the "
        "AI REVERSES the Arrhenius temperature-sensitivity relation and thereby ASSERTS the g060 "
        "must_not_say (claiming a lower Ea is more temperature-sensitive), so despite 'winning' on raw "
        "coverage (0.50 vs 0.25/0.25) it is effectively WORSE than both baselines because it states a "
        "disqualifying wrong claim. g032 has an AI factual error (it swaps the NH3/NH4+ neutralization "
        "roles), landing at 0.50. g036 (0.50) omits the competitive contrast the item wanted; g056 (0.50) "
        "omits the exo/endothermic and catalyst atoms. Several other hard items sit at 0.75 where the AI "
        "drops one atom (g033/g037/g042/g048/g049/g051/g052/g053/g057/g058/g059). "
        "(3) Where the AI's advantage IS decisive and structural: the differentiation bucket overall "
        "(AI 90.7% vs static 53.4% / keyword 40.3%) and especially the g031-g060 HARD cross-question / "
        "counterfactual / synthesis / transfer items (AI 84.2% vs static 20.8% / keyword 16.7%), which the "
        "static dump and keyword retrieval cannot answer because the needed facts are absent from the "
        "anchor question's own explanation."
    )

    main_doc["_meta"] = meta
    main_doc["items"] = ordered
    MAIN.write_text(json.dumps(main_doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    ai_mn = sum(1 for it in ordered if it["any_must_not"]["ai"])
    print(f"Wrote {MAIN.relative_to(ROOT)} with {len(ordered)} items.")
    print(f"  ids: {ordered[0]['id']} .. {ordered[-1]['id']}")
    print(f"  AI must_not_say violations: {ai_mn}/60")
    return 0


if __name__ == "__main__":
    sys.exit(main())
