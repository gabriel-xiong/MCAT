#!/usr/bin/env py -3.12
"""Score + POOL several held-out answer sheets through the REAL scorer.

This is a thin multi-file wrapper around ``scripts/score_heldout.py``: it imports
that module's OWN ``score()`` grading and ``wilson_ci()`` confidence interval and
applies them, so the numbers are produced by the real scorer's code — this file
adds no independent grading logic. It reports each sheet individually AND the
pooled result across all sheets (per-section + per-topic + Wilson 95% CI +
coverage), plus honesty fields (n, coverage %, missing-data note, next action).

Split-agnostic on purpose
--------------------------
It does not care whether the input sheets are SYNTHETIC (from
``gen_synthetic_heldout.py``) or REAL (returned by volunteers). The SAME command
scores real answer sheets — that is how a real answer sheet "drops straight in"
and replaces the synthetic demo:

    # synthetic demo (pipeline proof):
    py -3.12 scripts/pool_heldout.py build/heldout-SYNTHETIC_tester*.json

    # real data (the actual deliverable, when it arrives — identical command):
    py -3.12 scripts/pool_heldout.py build/heldout-answers_*.json

If ANY input row carries ``"synthetic": true`` the report is loudly banner-tagged
SYNTHETIC so a pooled synthetic number can never be mistaken for a real one.

Usage
-----
    py -3.12 scripts/pool_heldout.py FILE [FILE ...] [--summary-json PATH]

Exit 0 on success; 2 on bad input.
"""
from __future__ import annotations

import argparse
import glob as globmod
import json
import sys
from pathlib import Path
from typing import Any

from score_heldout import (
    DEFAULT_BANK,
    _group_acc,
    coerce_responses,
    held_out,
    load_bank,
    score,
    wilson_ci,
)

try:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[1]

# Full shipped held_out instrument scope (for coverage denominators).
N_SECTIONS_TOTAL = 4  # CP, BB, PS, CARS


def expand_paths(patterns: list[str]) -> list[Path]:
    out: list[Path] = []
    for pat in patterns:
        if any(ch in pat for ch in "*?["):
            matched = sorted(globmod.glob(pat))
            if not matched:
                print(f"warning: no files match {pat!r}", file=sys.stderr)
            out.extend(Path(m) for m in matched)
        else:
            out.append(Path(pat))
    return out


def raw_rows_are_synthetic(raw: Any) -> bool:
    if isinstance(raw, list):
        return any(isinstance(r, dict) and r.get("synthetic") is True for r in raw)
    if isinstance(raw, dict):
        return bool(raw.get("synthetic")) or bool(raw.get("_synthetic"))
    return False


def acc_line(k: int, n: int) -> str:
    if n == 0:
        return "no gradeable answers"
    acc = k / n
    lo, hi = wilson_ci(k, n)
    return f"accuracy {acc:.3f} ({k}/{n})   Wilson 95% CI [{lo:.3f}, {hi:.3f}]"


def summarize(graded: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(graded)
    k = sum(1 for g in graded if g["is_correct"])
    lo, hi = wilson_ci(k, n) if n else (None, None)
    sections = _group_acc(graded, "section")
    topics = _group_acc(graded, "topic_id")
    return {
        "n_graded": n,
        "n_correct": k,
        "accuracy": round(k / n, 4) if n else None,
        "wilson95_ci": [round(lo, 4), round(hi, 4)] if n else None,
        "by_section": [{"section": s, "n": nn, "correct": kk,
                        "accuracy": round(kk / nn, 4)} for s, kk, nn in sections],
        "by_topic": [{"topic_id": t, "n": nn, "correct": kk,
                      "accuracy": round(kk / nn, 4)} for t, kk, nn in topics],
        "sections_covered": len(sections),
        "topics_covered": len(topics),
    }


def print_breakdown(graded: list[dict[str, Any]]) -> None:
    print("  by section")
    print(f"    {'section':10} {'n':>4} {'correct':>8} {'acc':>7}")
    print("    " + "-" * 32)
    for name, kk, nn in _group_acc(graded, "section"):
        print(f"    {name:10} {nn:4d} {kk:8d} {kk / nn:7.3f}")
    print("  by topic")
    print(f"    {'topic_id':22} {'n':>4} {'correct':>8} {'acc':>7}")
    print("    " + "-" * 44)
    for name, kk, nn in _group_acc(graded, "topic_id"):
        print(f"    {name:22} {nn:4d} {kk:8d} {kk / nn:7.3f}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="pool_heldout.py",
                                 description="Score + pool held-out answer sheets "
                                             "through the real scorer.")
    ap.add_argument("files", nargs="+", help="answer-sheet JSON files (globs OK)")
    ap.add_argument("--bank", type=Path, default=DEFAULT_BANK)
    ap.add_argument("--summary-json", type=Path,
                    help="also write a machine-readable pooled summary here")
    args = ap.parse_args(argv)

    if not args.bank.is_file():
        print(f"bank not found: {args.bank}", file=sys.stderr)
        return 2
    questions = held_out(load_bank(args.bank))
    if not questions:
        print("no held_out questions in bank", file=sys.stderr)
        return 2
    n_topics_total = len({q.get("topic_id") for q in questions})

    paths = expand_paths(args.files)
    paths = [p for p in paths if p.is_file()]
    if not paths:
        print("no input files found", file=sys.stderr)
        return 2

    per_file: list[dict[str, Any]] = []
    pooled_graded: list[dict[str, Any]] = []
    any_synthetic = False

    for p in paths:
        raw = json.loads(p.read_text(encoding="utf-8"))
        synthetic = raw_rows_are_synthetic(raw)
        any_synthetic = any_synthetic or synthetic
        responses = coerce_responses(raw)
        res = score(questions, responses)
        graded = res["graded"]
        pooled_graded.extend(graded)
        s = summarize(graded)
        s["file"] = str(p)
        s["synthetic"] = synthetic
        per_file.append(s)

    banner = ("SYNTHETIC — PIPELINE DEMO ONLY, NOT REAL DATA"
              if any_synthetic else "REAL held-out data")
    print("#" * 74)
    print(f"#  POOLED HELD-OUT PERFORMANCE   [{banner}]")
    print("#" * 74)
    if any_synthetic:
        print("#  WARNING: at least one sheet is SYNTHETIC. The pooled accuracy")
        print("#  below is a METHODOLOGY DEMONSTRATION, not a performance or")
        print("#  learning claim. Do not report it as a real score.")
        print("#" * 74)
    print()

    print(f"held_out questions in bank : {len(questions)}")
    print(f"sheets scored              : {len(paths)}")
    print()

    print("PER-SHEET (never merged — independent runs):")
    for s in per_file:
        tag = "  [SYNTHETIC]" if s["synthetic"] else ""
        print(f"  {Path(s['file']).name}{tag}")
        print(f"    {acc_line(s['n_correct'], s['n_graded'])}")
    print()

    n = len(pooled_graded)
    k = sum(1 for g in pooled_graded if g["is_correct"])
    print("POOLED (all sheets, union of independent attempts):")
    print(f"  {acc_line(k, n)}")
    print()
    print_breakdown(pooled_graded)
    print()

    sections_covered = len({g.get("section") for g in pooled_graded})
    topics_covered = len({g.get("topic_id") for g in pooled_graded})
    cov_items = n / (len(questions) * len(paths)) if paths else 0.0
    print("COVERAGE (honesty fields):")
    print(f"  answered attempts        : {n} of {len(questions) * len(paths)} "
          f"possible ({cov_items * 100:.1f}%)")
    print(f"  sections covered         : {sections_covered}/{N_SECTIONS_TOTAL}")
    print(f"  topics covered           : {topics_covered}/{n_topics_total}")
    strict_gate = "PASS (>=30)" if n >= 30 else "FAIL (<30)"
    print(f"  strict attempt gate (>=30): {strict_gate}")
    print()
    print("MISSING-DATA NOTE:")
    if any_synthetic:
        print("  These attempts are SYNTHETIC (documented Bernoulli responder,")
        print("  stated per-section accuracy + seed). No real independent tester")
        print("  has answered the frozen held_out set yet.")
    else:
        print("  Real independent held-out attempts.")
    print("SINGLE NEXT ACTION:")
    print("  Replace with real independent held-out answers (collection kit ready):")
    print("  py -3.12 scripts/pool_heldout.py build/heldout-answers_*.json")

    if args.summary_json:
        out = {
            "artifact": "pooled_heldout_performance",
            "synthetic": any_synthetic,
            "is_real_data": not any_synthetic,
            "warning": ("PIPELINE DEMONSTRATION ONLY — NOT a real performance/"
                        "learning claim." if any_synthetic else None),
            "real_scorer": "scripts/score_heldout.py (score + wilson_ci)",
            "eval_split": "held_out",
            "n_held_out_questions": len(questions),
            "sheets": [str(p) for p in paths],
            "per_sheet": per_file,
            "pooled": summarize(pooled_graded),
            "coverage": {
                "answered_attempts": n,
                "possible_attempts": len(questions) * len(paths),
                "attempt_coverage_pct": round(cov_items * 100, 1),
                "sections_covered": sections_covered,
                "sections_total": N_SECTIONS_TOTAL,
                "topics_covered": topics_covered,
                "topics_total": n_topics_total,
                "strict_attempt_gate_pass": n >= 30,
            },
            "missing_data_note": (
                "Attempts are SYNTHETIC (documented responder + seed); no real "
                "independent held_out run exists yet." if any_synthetic else
                "Real independent held_out attempts."),
            "single_next_action": (
                "Replace with real independent held-out answers: "
                "py -3.12 scripts/pool_heldout.py build/heldout-answers_*.json"),
        }
        args.summary_json.parent.mkdir(parents=True, exist_ok=True)
        args.summary_json.write_text(json.dumps(out, indent=2), encoding="utf-8")
        print(f"\nwrote pooled summary -> {args.summary_json}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
