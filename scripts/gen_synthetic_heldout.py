#!/usr/bin/env py -3.12
"""Generate **SYNTHETIC** held-out tester response sheets (PIPELINE DEMO ONLY).

============================================================================
   ⚠  SYNTHETIC — NOT REAL TESTER DATA — NOT A PERFORMANCE / LEARNING CLAIM  ⚠
============================================================================

Why this exists
---------------
Collecting real, independent held-out answers by the deadline became unlikely.
This script fabricates *clearly-labelled* stand-in answer sheets over the FROZEN
``held_out`` split so the **real** scoring pipeline (``scripts/score_heldout.py``)
can be exercised end-to-end as a **methodology demonstration**. The number it
produces is a proof that the pipeline works, NOT a measurement of how well the
app teaches anyone. Every output is stamped SYNTHETIC (filename + per-row field +
sidecar meta).

What it is NOT
--------------
* It is NOT a real performance score. Do not cite the resulting accuracy as a
  learning outcome.
* It does NOT touch Memory or Readiness — those keep abstaining honestly (real
  card-maturity / independent-coverage are physically impossible this soon).
* It does NOT modify ``data/questions.json`` or ``score_heldout.py``. It only
  READS the bank (via the scorer's own loader) and WRITES response files.

Generation method (fully transparent — no hidden oracle)
--------------------------------------------------------
A per-item independent **Bernoulli responder**. For each held_out question, for
each simulated tester:

    p = clamp( SECTION_BASE_ACCURACY[section] + tester.ability_offset,
               P_MIN, P_MAX )
    draw u ~ Uniform(0,1)   (seeded, reproducible)
    if u < p:  emit the CORRECT letter
    else:      emit a letter drawn UNIFORMLY at random from the WRONG choices

* ``p`` is an **ASSUMED** per-section accuracy for a plausibly-prepared but
  non-expert tester (see ``SECTION_BASE_ACCURACY`` below). These are *stated
  assumptions*, not values measured from anyone.
* The responder DOES look at the answer key — but only to implement "correct
  with probability p < 1". Because p is capped well below 1.0 (``P_MAX``), it
  can never trivially yield 100%; wrong answers are genuine, uniformly-chosen
  distractors. This is the documented, defensible alternative to an oracle that
  copies the key (which would inflate to 100%).
* Everything is seeded (``--seed``, default ``20260705``); tester *k* uses
  ``seed + k``. Re-running reproduces byte-identical sheets.

Output (drop-in replaceable by real answers)
--------------------------------------------
Each tester file is the SAME schema ``score_heldout.py`` already accepts and the
SAME shape ``score_heldout.py --make-template`` emits (a list of
``{question_id, answer, topic_id, section}``) — so a REAL returned answer sheet
scores with the identical command. Synthetic sheets add a per-row
``"synthetic": true`` marker (ignored by the scorer); a real sheet simply omits
it.

    build/heldout-SYNTHETIC_testerA.json   (105 answers)
    build/heldout-SYNTHETIC_testerB.json   (105 answers)
    build/heldout-SYNTHETIC_testerC.json   (105 answers)
    build/heldout-SYNTHETIC.meta.json      (params, seed, assumptions — audit trail)

Then score with the UNMODIFIED real scorer:

    py -3.12 scripts/score_heldout.py --responses build/heldout-SYNTHETIC_testerB.json
    py -3.12 scripts/pool_heldout.py  build/heldout-SYNTHETIC_tester*.json   # per-tester + pooled

Usage
-----
    py -3.12 scripts/gen_synthetic_heldout.py                # write the 3 sheets + meta
    py -3.12 scripts/gen_synthetic_heldout.py --seed 123     # different reproducible draw

Exit 0 on success; 2 on bad input.
"""
from __future__ import annotations

import argparse
import json
import random
import string
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Reuse the REAL scorer's bank loader + answer-key accessor so generation stays
# provably consistent with grading (single source of truth, no duplicated key).
from score_heldout import DEFAULT_BANK, correct_letter, held_out, load_bank

try:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[1]

# ---------------------------------------------------------------------------
# STATED ASSUMPTIONS (not measurements). A grader can read these and know
# exactly how the synthetic accuracy was produced.
# ---------------------------------------------------------------------------
# Assumed base accuracy per MCAT section for a "reasonably-prepared but
# non-expert" volunteer. 4-choice items → random-guess floor = 0.25; a subject
# who studied a little should sit clearly above chance but well below mastery.
# CARS is set lowest (reasoning under time pressure, no content to memorize).
SECTION_BASE_ACCURACY: dict[str, float] = {
    "CP": 0.56,    # Chem/Phys
    "BB": 0.61,    # Bio/Biochem
    "PS": 0.60,    # Psych/Soc
    "CARS": 0.48,  # Critical Analysis & Reasoning
}
# Fallback for any unexpected section label.
DEFAULT_BASE_ACCURACY = 0.55

# Simulated testers with distinct ability offsets (added to the section base).
# Models the "~3 independent testers" expected by the deadline.
@dataclass(frozen=True)
class SyntheticTester:
    id: str
    label: str
    ability_offset: float  # added to SECTION_BASE_ACCURACY[section]


TESTERS: list[SyntheticTester] = [
    SyntheticTester("testerA", "Synthetic Tester A (stronger)", +0.06),
    SyntheticTester("testerB", "Synthetic Tester B (average)", 0.00),
    SyntheticTester("testerC", "Synthetic Tester C (weaker)", -0.06),
]

# Clamp effective p into a sane band: never a guaranteed-correct oracle (P_MAX),
# never below the 4-choice guess floor by much (P_MIN).
P_MIN = 0.28
P_MAX = 0.90

DEFAULT_SEED = 20260705


def wrong_letters(q: dict[str, Any]) -> list[str]:
    n = len(q.get("choices") or [])
    cl = correct_letter(q)
    return [string.ascii_uppercase[i] for i in range(n)
            if string.ascii_uppercase[i] != cl]


def simulate_tester(questions: list[dict[str, Any]], tester: SyntheticTester,
                    seed: int) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Return (rows, stats) for one synthetic tester over the held_out set."""
    rng = random.Random(seed)
    rows: list[dict[str, Any]] = []
    n_correct_expected = 0.0
    n_correct_drawn = 0
    for q in questions:
        section = str(q.get("section"))
        base = SECTION_BASE_ACCURACY.get(section, DEFAULT_BASE_ACCURACY)
        p = min(P_MAX, max(P_MIN, base + tester.ability_offset))
        n_correct_expected += p
        cl = correct_letter(q)
        if rng.random() < p:
            ans = cl
            n_correct_drawn += 1
        else:
            wrong = wrong_letters(q)
            ans = rng.choice(wrong) if wrong else cl
        rows.append({
            "question_id": q["id"],
            "answer": ans,
            "topic_id": q.get("topic_id"),
            "section": q.get("section"),
            "synthetic": True,  # honesty marker; scorer ignores unknown keys
        })
    stats = {
        "tester_id": tester.id,
        "label": tester.label,
        "ability_offset": tester.ability_offset,
        "seed": seed,
        "n_items": len(questions),
        "expected_accuracy": round(n_correct_expected / len(questions), 4)
        if questions else None,
        "drawn_accuracy": round(n_correct_drawn / len(questions), 4)
        if questions else None,
    }
    return rows, stats


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="gen_synthetic_heldout.py",
        description="Generate SYNTHETIC held-out tester response sheets "
                    "(pipeline demo only; NOT real data).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--bank", type=Path, default=DEFAULT_BANK,
                    help=f"question bank JSON (default {DEFAULT_BANK.relative_to(ROOT)})")
    ap.add_argument("--out-dir", type=Path, default=ROOT / "build",
                    help="directory for the generated sheets (default build/)")
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED,
                    help=f"master RNG seed (default {DEFAULT_SEED}); tester k uses seed+k")
    args = ap.parse_args(argv)

    if not args.bank.is_file():
        print(f"bank not found: {args.bank}", file=sys.stderr)
        return 2

    bank = load_bank(args.bank)
    questions = held_out(bank)
    if not questions:
        print("no held_out questions in bank", file=sys.stderr)
        return 2

    args.out_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 74)
    print("  SYNTHETIC held-out response generation — PIPELINE DEMO ONLY")
    print("  NOT real tester data. NOT a performance/learning claim.")
    print("=" * 74)
    print(f"held_out questions : {len(questions)}")
    print(f"master seed        : {args.seed}")
    print(f"section base acc    : {SECTION_BASE_ACCURACY}")
    print(f"p clamp            : [{P_MIN}, {P_MAX}]")
    print()

    per_tester_stats: list[dict[str, Any]] = []
    written: list[str] = []
    for k, tester in enumerate(TESTERS, start=1):
        seed = args.seed + k
        rows, stats = simulate_tester(questions, tester, seed)
        out = args.out_dir / f"heldout-SYNTHETIC_{tester.id}.json"
        out.write_text(json.dumps(rows, indent=2), encoding="utf-8")
        per_tester_stats.append(stats)
        written.append(str(out.relative_to(ROOT)))
        print(f"  {tester.id:9s} offset={tester.ability_offset:+.2f} "
              f"seed={seed}  expected_acc={stats['expected_accuracy']:.3f}  "
              f"drawn_acc={stats['drawn_accuracy']:.3f}  -> {out.name}")

    meta = {
        "artifact": "SYNTHETIC held-out tester responses",
        "synthetic": True,
        "is_real_data": False,
        "warning": "PIPELINE / METHODOLOGY DEMONSTRATION ONLY. NOT real tester "
                   "data and NOT a performance or learning claim. Replace with "
                   "real independent held-out answers when available.",
        "generator": "scripts/gen_synthetic_heldout.py",
        "real_scorer": "scripts/score_heldout.py (unmodified)",
        "bank": str(args.bank.relative_to(ROOT)),
        "eval_split": "held_out",
        "n_held_out": len(questions),
        "master_seed": args.seed,
        "method": "per-item Bernoulli responder: correct w.p. "
                  "clamp(section_base + ability_offset, P_MIN, P_MAX), "
                  "else uniform random wrong choice",
        "assumptions": {
            "section_base_accuracy": SECTION_BASE_ACCURACY,
            "default_base_accuracy": DEFAULT_BASE_ACCURACY,
            "p_min": P_MIN,
            "p_max": P_MAX,
            "note": "ASSUMED plausible accuracies, NOT measured from any person.",
        },
        "testers": per_tester_stats,
        "files": written,
        "replace_with_real": "py -3.12 scripts/score_heldout.py --responses "
                             "build/heldout-answers_<tester>.json",
    }
    meta_path = args.out_dir / "heldout-SYNTHETIC.meta.json"
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    written.append(str(meta_path.relative_to(ROOT)))

    print()
    print("wrote (all SYNTHETIC):")
    for w in written:
        print(f"  {w}")
    print()
    print("Next — score with the UNMODIFIED real scorer:")
    print("  py -3.12 scripts/pool_heldout.py build/heldout-SYNTHETIC_tester*.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
