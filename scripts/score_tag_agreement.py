#!/usr/bin/env py -3.12
"""Score a human's blind tag labels against the hidden key (NEW file).

Compares data/tag-recoverability-human.json (filled by a human, same shape as
the TEMPLATE) to data/tag-recoverability-key.json produced by
build_recoverability_sheet.py.

Reports:
  * Coarse category agreement (content_gap / trap / null) + Cohen's kappa.
  * Fine agreement (trap enum must also match on trap cases).
  * For content_gap gold cases the human also called content_gap: whether the
    human's free-text misconception RECOVERS the stored one at the eval's own
    bar (token overlap >= 0.6, matching ai_eval_explanations.names_error_mode).
  * All breakdowns split by heuristic distinctiveness (distinctive/borderline/
    generic) so weak tags can be identified.

Usage:
  py -3.12 scripts/score_tag_agreement.py [human.json]
Defaults to data/tag-recoverability-human.json.
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

STOP = {
    "the", "a", "an", "of", "to", "in", "is", "are", "and", "or", "for", "on",
    "at", "by", "it", "its", "as", "be", "this", "that", "with", "from", "into",
    "than", "then", "which", "what", "when", "not", "no", "so", "if", "will",
    "can", "does", "do", "has", "have", "one", "two", "you", "your",
}
OVERLAP_BAR = 0.6  # matches ai_eval_explanations.names_error_mode content_gap bar


def toks(text: str):
    out, cur = [], ""
    for ch in text.lower():
        if ch.isalnum():
            cur += ch
        else:
            if cur:
                out.append(cur)
            cur = ""
    if cur:
        out.append(cur)
    return [t for t in out if t and t not in STOP]


def overlap_ratio(needle: str, haystack: str) -> float:
    n = set(toks(needle))
    if not n:
        return 0.0
    h = set(toks(haystack))
    return len(n & h) / len(n)


def cohen_kappa(pairs: list[tuple[str, str]]) -> float:
    """Cohen's kappa for a list of (gold, pred) categorical labels."""
    if not pairs:
        return float("nan")
    labels = sorted({x for p in pairs for x in p})
    n = len(pairs)
    po = sum(1 for g, p in pairs if g == p) / n
    g_count = Counter(g for g, _ in pairs)
    p_count = Counter(p for _, p in pairs)
    pe = sum((g_count[l] / n) * (p_count[l] / n) for l in labels)
    if pe == 1.0:
        return 1.0
    return (po - pe) / (1 - pe)


def main(argv):
    human_path = Path(argv[1]) if len(argv) > 1 else DATA / "tag-recoverability-human.json"
    key = json.loads((DATA / "tag-recoverability-key.json").read_text(encoding="utf-8"))
    if not human_path.exists():
        print(f"ERROR: {human_path} not found. Copy the TEMPLATE, fill it, retry.")
        return 2
    human = json.loads(human_path.read_text(encoding="utf-8"))

    key_by = {k["case_id"]: k for k in key["items"]}
    hum_by = {h["case_id"]: h for h in human["items"]}
    missing = [c for c in key_by if c not in hum_by or not hum_by[c].get("label")]
    if missing:
        print(f"WARNING: {len(missing)} cases unlabeled/missing: {missing}")

    coarse_pairs = []            # (gold_map, human_label)
    fine_correct = fine_total = 0
    cg_recovered = cg_total = 0  # content_gap misconception recovery @0.6
    by_dist = defaultdict(lambda: {"n": 0, "coarse_ok": 0})
    by_goldmap = defaultdict(lambda: {"n": 0, "coarse_ok": 0})
    trap_pairs = []              # (gold_trap, human_trap) on gold trap cases

    rows = []
    for cid, k in key_by.items():
        h = hum_by.get(cid, {})
        hlabel = (h.get("label") or "").strip().lower()
        gmap = k["gold_map"]
        dist = k.get("heuristic_distinctiveness") or "-"
        coarse_ok = int(hlabel == gmap)
        coarse_pairs.append((gmap, hlabel or "MISSING"))
        by_goldmap[gmap]["n"] += 1
        by_goldmap[gmap]["coarse_ok"] += coarse_ok
        if gmap == "content_gap":
            by_dist[dist]["n"] += 1
            by_dist[dist]["coarse_ok"] += coarse_ok

        fine_total += 1
        if gmap == "trap":
            htrap = (h.get("trap_enum") or "").strip().lower()
            trap_pairs.append((k["gold_trap"], htrap or "MISSING"))
            fine_correct += int(hlabel == "trap" and htrap == k["gold_trap"])
        else:
            fine_correct += coarse_ok

        recov = None
        if gmap == "content_gap":
            cg_total += 1
            if hlabel == "content_gap":
                ov = overlap_ratio(k["gold_misconception"], h.get("misconception", ""))
                recov = ov >= OVERLAP_BAR
                cg_recovered += int(recov)
        rows.append((cid, k["qid"], gmap, dist, hlabel, coarse_ok, recov))

    n = len(coarse_pairs)
    coarse_acc = sum(1 for g, p in coarse_pairs if g == p) / n if n else 0
    kappa = cohen_kappa(coarse_pairs)

    print("=" * 74)
    print("TAG RECOVERABILITY — human blind labels vs hidden key")
    print("=" * 74)
    print(f"Cases scored: {n}   (human file: {human_path.name})")
    print(f"\nCoarse (content_gap/trap/null) agreement: {coarse_acc:.3f}")
    print(f"Cohen's kappa (coarse): {kappa:.3f}")
    print(f"Fine agreement (trap enum must match): {fine_correct}/{fine_total} "
          f"= {fine_correct / fine_total:.3f}")

    print("\nAgreement by GOLD map:")
    for gmap, d in sorted(by_goldmap.items()):
        acc = d["coarse_ok"] / d["n"] if d["n"] else 0
        print(f"  {gmap:<12} n={d['n']:>2}  coarse_agree={acc:.3f}")

    print("\ncontent_gap agreement by heuristic distinctiveness:")
    for dist in ("distinctive", "borderline", "generic"):
        d = by_dist.get(dist)
        if not d or not d["n"]:
            continue
        acc = d["coarse_ok"] / d["n"]
        print(f"  {dist:<12} n={d['n']:>2}  coarse_agree={acc:.3f}")

    print(f"\ncontent_gap MISCONCEPTION recovery @overlap>={OVERLAP_BAR} "
          f"(eval's bar): {cg_recovered}/{cg_total} = "
          f"{(cg_recovered / cg_total if cg_total else 0):.3f}")

    if trap_pairs:
        tk = cohen_kappa(trap_pairs)
        tacc = sum(1 for g, p in trap_pairs if g == p) / len(trap_pairs)
        print(f"\ntrap-enum exact agreement (on gold trap cases): {tacc:.3f}  "
              f"(kappa={tk:.3f}, n={len(trap_pairs)})")

    print("\nPer-case:")
    print(f"  {'case':<5}{'qid':<12}{'gold':<12}{'dist':<12}{'human':<12}{'ok':<3}{'recov'}")
    for cid, qid, gmap, dist, hlabel, ok, recov in rows:
        rv = "" if recov is None else ("Y" if recov else "n")
        print(f"  {cid:<5}{qid:<12}{gmap:<12}{dist:<12}{hlabel or '-':<12}"
              f"{('Y' if ok else 'n'):<3}{rv}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
