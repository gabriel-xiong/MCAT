#!/usr/bin/env py -3.12
"""§7d paraphrase-gap scorer.

Proves the app measures PERFORMANCE (transfer) and not just MEMORY, by
comparing, for each anchor flashcard concept in data/paraphrase-test.json:

  * card_recall_rate    — how reliably the student recalls the flashcard, and
  * question_accuracy   — mean accuracy on the TWO reworded exam-style
                          questions linked to that concept.

    paraphrase_gap = card_recall_rate - question_accuracy      (per concept)

A gap near 0 with high recall means the "performance" score is essentially
parroting memory. A large positive gap means the student recalls the fact but
cannot apply it in new words — exactly the honest signal we want to surface.
The report aggregates the gap overall and per topic.

NO AI, no network, deterministic. Runtime never calls this — it is an eval.

------------------------------------------------------------------- input data
Two inputs, both plain JSON (see docs/PARAPHRASE-TEST.md "Real-data path"):

  --recall PATH   Memory recall per concept. Either
                    {"<concept>": 0.83, ...}                    (rate in [0,1])
                  or a list of raw events aggregated by this script:
                    [{"concept": "vmax_saturation", "recalled": true}, ...]
                  Keys may be the manifest `concept` slug or its `card_ref`.

  --attempts PATH Performance attempts export. Either
                    {"q_ho_075": 0.5, ...}                      (accuracy in [0,1])
                  or a list of raw attempts aggregated by this script:
                    [{"question_id": "q_ho_075", "correct": false}, ...]

With NO --recall/--attempts the script runs a built-in, deterministic SYNTHETIC
demo derived from the manifest, so `make eval-performance` always prints a
reproducible sample gap report even before any real user data exists.

Run:
  py -3.12 scripts/eval_paraphrase.py                      # synthetic demo
  py -3.12 scripts/eval_paraphrase.py --recall r.json --attempts a.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
MANIFEST = DATA / "paraphrase-test.json"

# Report uses § and — ; force UTF-8 so it renders on a Windows cp1252 console.
try:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
except Exception:
    pass


def load_manifest(path: Path) -> list[dict]:
    doc = json.loads(path.read_text(encoding="utf-8"))
    return doc["concepts"] if isinstance(doc, dict) else doc


def _unit(seed: str) -> float:
    """Deterministic float in [0,1) from a string (stable across runs/OSes)."""
    h = hashlib.md5(seed.encode("utf-8")).hexdigest()
    return int(h[:8], 16) / 0xFFFFFFFF


def synth_signals(concepts: list[dict]) -> tuple[dict[str, float], dict[str, float]]:
    """Build a deterministic synthetic recall map + attempts map from the
    manifest. Engineered so recall tends to exceed reworded-question accuracy
    (a realistic, honestly-positive paraphrase gap that is larger on the freshly
    authored held_out probes than on the reused stems)."""
    recall: dict[str, float] = {}
    attempts: dict[str, float] = {}
    for row in concepts:
        c = row["concept"]
        base = _unit(c)
        # High, believable flashcard recall: 0.72–0.98.
        r = round(0.72 + 0.26 * base, 3)
        recall[c] = r
        authored = set(row.get("new_question_ids", []))
        for qid in row["question_ids"]:
            d = _unit(qid)
            # Reworded/authored probes transfer worse (bigger gap) than reused.
            drop = (0.12 + 0.22 * d) if qid in authored else (0.04 + 0.10 * d)
            attempts[qid] = round(max(0.0, min(1.0, r - drop)), 3)
    return recall, attempts


def coerce_recall(raw: object) -> dict[str, float]:
    if isinstance(raw, dict):
        return {str(k): float(v) for k, v in raw.items()}
    # list of {concept|card_ref, recalled: bool}
    agg: dict[str, list[bool]] = {}
    for ev in raw:  # type: ignore[union-attr]
        key = str(ev.get("concept") or ev.get("card_ref"))
        agg.setdefault(key, []).append(bool(ev.get("recalled")))
    return {k: (sum(v) / len(v)) for k, v in agg.items() if v}


def coerce_attempts(raw: object) -> dict[str, float]:
    if isinstance(raw, dict):
        return {str(k): float(v) for k, v in raw.items()}
    agg: dict[str, list[bool]] = {}
    for at in raw:  # type: ignore[union-attr]
        qid = str(at.get("question_id") or at.get("id"))
        agg.setdefault(qid, []).append(bool(at.get("correct")))
    return {k: (sum(v) / len(v)) for k, v in agg.items() if v}


def recall_for(row: dict, recall: dict[str, float]) -> float | None:
    for key in (row["concept"], row.get("card_ref")):
        if key in recall:
            return recall[key]
    return None


def score(concepts: list[dict], recall: dict[str, float],
          attempts: dict[str, float]) -> dict:
    rows = []
    for row in concepts:
        rr = recall_for(row, recall)
        accs = [attempts[q] for q in row["question_ids"] if q in attempts]
        if rr is None or not accs:
            rows.append({**row, "_recall": rr, "_qacc": None, "_gap": None,
                         "_ndata": len(accs)})
            continue
        qacc = sum(accs) / len(accs)
        rows.append({**row, "_recall": rr, "_qacc": qacc,
                     "_gap": rr - qacc, "_ndata": len(accs)})
    return {"rows": rows}


def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else float("nan")


def report(result: dict, source: str) -> None:
    rows = result["rows"]
    scored = [r for r in rows if r["_gap"] is not None]
    skipped = [r for r in rows if r["_gap"] is None]

    print("=" * 74)
    print(f"§7d PARAPHRASE-GAP REPORT   [{source}]")
    print("=" * 74)
    print(f"concepts in manifest: {len(rows)}   scored: {len(scored)}   "
          f"skipped (missing data): {len(skipped)}")
    print()
    print("per-concept  (recall - question_accuracy = gap)")
    print(f"  {'concept':34} {'recall':>7} {'q_acc':>7} {'gap':>7}  pair")
    print("  " + "-" * 70)
    for r in sorted(scored, key=lambda x: (x["topic_id"], x["concept"])):
        print(f"  {r['concept'][:34]:34} {r['_recall']:7.2f} "
              f"{r['_qacc']:7.2f} {r['_gap']:+7.2f}  {r['pair_type']}")
    print()

    print("per-topic")
    print(f"  {'topic':18} {'n':>3} {'recall':>7} {'q_acc':>7} {'gap':>7}")
    print("  " + "-" * 46)
    topics = sorted({r["topic_id"] for r in scored})
    for t in topics:
        trs = [r for r in scored if r["topic_id"] == t]
        print(f"  {t:18} {len(trs):3d} {_mean([r['_recall'] for r in trs]):7.2f} "
              f"{_mean([r['_qacc'] for r in trs]):7.2f} "
              f"{_mean([r['_gap'] for r in trs]):+7.2f}")
    print()

    g = _mean([r["_gap"] for r in scored])
    mr = _mean([r["_recall"] for r in scored])
    mq = _mean([r["_qacc"] for r in scored])
    print("AGGREGATE")
    print(f"  mean card recall      : {mr:5.2f}")
    print(f"  mean question accuracy: {mq:5.2f}")
    print(f"  PARAPHRASE GAP        : {g:+5.2f}   "
          f"(recall {mr:.2f} - accuracy {mq:.2f})")
    print()
    if scored:
        if g >= 0.15:
            verdict = ("LARGE gap: recall outstrips transfer — the performance "
                       "score is NOT just parroting memory.")
        elif g >= 0.05:
            verdict = ("MODERATE gap: some transfer loss between memorized cards "
                       "and reworded questions.")
        else:
            verdict = ("SMALL gap: question accuracy tracks recall closely — "
                       "warn that performance may be echoing memory.")
        print(f"  verdict: {verdict}")
    if skipped:
        ids = ", ".join(r["concept"] for r in skipped)
        print(f"  note: {len(skipped)} concept(s) lacked recall/attempt data: {ids}")


def main() -> int:
    ap = argparse.ArgumentParser(description="§7d paraphrase-gap scorer")
    ap.add_argument("--manifest", type=Path, default=MANIFEST)
    ap.add_argument("--recall", type=Path, help="memory recall JSON")
    ap.add_argument("--attempts", type=Path, help="performance attempts JSON")
    args = ap.parse_args()

    concepts = load_manifest(args.manifest)

    if args.recall and args.attempts:
        recall = coerce_recall(json.loads(args.recall.read_text(encoding="utf-8")))
        attempts = coerce_attempts(
            json.loads(args.attempts.read_text(encoding="utf-8")))
        source = f"real data: {args.recall.name} + {args.attempts.name}"
    elif args.recall or args.attempts:
        print("ERROR: provide BOTH --recall and --attempts, or neither "
              "(for the synthetic demo).", file=sys.stderr)
        return 2
    else:
        recall, attempts = synth_signals(concepts)
        source = "synthetic demo — deterministic, no real user data yet"

    result = score(concepts, recall, attempts)
    report(result, source)
    return 0


if __name__ == "__main__":
    sys.exit(main())
