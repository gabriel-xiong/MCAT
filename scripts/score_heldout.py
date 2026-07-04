#!/usr/bin/env py -3.12
"""Score a friend's answers to the FROZEN held_out question bank (Sunday eval).

Question answered
-----------------
What is the app's **real held-out performance accuracy**? A volunteer answers the
questions whose ``split == "held_out"`` in ``data/questions.json`` (never shown in
a dev performance session), we collect their picks, and this script grades them
against the bank's ``correct`` key. Output is honest accuracy + a Wilson 95% CI,
broken down by section and topic.

This is READ-ONLY against the bank: it never mutates ``questions.json`` or any
shared module. It only reads the bank + a responses file and prints/writes a
report.

Responses file (``--responses``) — any of these shapes is accepted
------------------------------------------------------------------
  * dict  :  {"q_ho_001": "A", "q_ho_002": "C", ...}
  * list  :  [{"question_id": "q_ho_001", "answer": "A"}, ...]
             (key may be ``question_id`` or ``id``; value key may be
              ``answer`` / ``choice`` / ``selected`` / ``response``)

Each answer value may be:
  * a letter  "A".."Z"      (case-insensitive; the normal MCAT form)
  * the exact choice text   (matched against the question's ``choices``)
  * an integer index        (0-based into ``choices``)

Blank / null / "" answers are treated as UNANSWERED (skipped, reported).

Usage
-----
  # 1. make a blank answer sheet for the volunteer to fill in:
  py -3.12 scripts/score_heldout.py --make-template build/heldout-answers.TEMPLATE.json

  # 2. score their returned answers:
  py -3.12 scripts/score_heldout.py --responses build/heldout-answers_friend.json

  # 3. (optional) emit a paraphrase-gap attempts file for eval_paraphrase.py:
  py -3.12 scripts/score_heldout.py --responses R.json --emit-attempts build/attempts.json

  # prove the pipeline with deterministic synthetic answers (no real data):
  py -3.12 scripts/score_heldout.py --demo

Exit 0 on success; 2 on bad input.
"""
from __future__ import annotations

import argparse
import json
import math
import random
import string
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BANK = ROOT / "data" / "questions.json"
HELD_OUT_SPLIT = "held_out"

# Report uses — and § ; force UTF-8 so it renders on a Windows cp1252 console.
try:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
except Exception:
    pass


def load_bank(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("question bank must be a JSON array")
    return data


def held_out(bank: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [q for q in bank if q.get("split") == HELD_OUT_SPLIT]


def correct_letter(q: dict[str, Any]) -> str:
    """The bank stores ``correct`` as a letter (A, B, C, ...)."""
    return str(q["correct"]).strip().upper()


def letter_to_index(letter: str) -> int:
    return string.ascii_uppercase.index(letter)


def normalize_answer(raw: Any, q: dict[str, Any]) -> str | None:
    """Coerce a volunteer's answer into a canonical letter, or None if blank.

    Raises ValueError if the answer is non-blank but cannot be matched."""
    if raw is None:
        return None
    choices = q.get("choices") or []
    n = len(choices)

    # integer index (0-based)
    if isinstance(raw, bool):  # guard: bool is an int subclass
        raise ValueError(f"boolean answer {raw!r} is not valid")
    if isinstance(raw, int):
        if 0 <= raw < n:
            return string.ascii_uppercase[raw]
        raise ValueError(f"index {raw} out of range for {n} choices")

    s = str(raw).strip()
    if s == "":
        return None

    # single letter
    if len(s) == 1 and s.upper() in string.ascii_uppercase:
        idx = letter_to_index(s.upper())
        if idx < n:
            return s.upper()
        raise ValueError(f"letter {s!r} out of range for {n} choices")

    # exact choice text
    for i, choice in enumerate(choices):
        if str(choice).strip() == s:
            return string.ascii_uppercase[i]

    raise ValueError(f"answer {raw!r} not a letter/index/choice-text match")


def coerce_responses(raw: Any) -> dict[str, Any]:
    """Return {question_id: answer_value} from a dict or list responses file."""
    if isinstance(raw, dict):
        return {str(k): v for k, v in raw.items()}
    if isinstance(raw, list):
        out: dict[str, Any] = {}
        for row in raw:
            if not isinstance(row, dict):
                raise ValueError("each response list item must be an object")
            qid = row.get("question_id") or row.get("id")
            if qid is None:
                raise ValueError("response item missing 'question_id'/'id'")
            for key in ("answer", "choice", "selected", "response"):
                if key in row:
                    out[str(qid)] = row[key]
                    break
            else:
                raise ValueError(
                    f"response for {qid} missing answer key "
                    "(answer/choice/selected/response)")
        return out
    raise ValueError("responses must be a JSON object or array")


def wilson_ci(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score 95% interval for a binomial proportion (honest small-n CI)."""
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = (z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / denom
    return (max(0.0, center - half), min(1.0, center + half))


def make_template(path: Path, questions: list[dict[str, Any]]) -> None:
    """Write a blank answer sheet: one entry per held_out question, answer "".

    Deliberately does NOT include the correct answer or explanation, so it is
    safe to hand to a volunteer without leaking the key."""
    rows = [{"question_id": q["id"], "answer": "",
             "topic_id": q.get("topic_id"), "section": q.get("section")}
            for q in questions]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rows, indent=2), encoding="utf-8")


def synth_responses(questions: list[dict[str, Any]], seed: int) -> dict[str, str]:
    """Deterministic synthetic answers: ~70% correct, else a random wrong letter.

    Used only by --demo to prove the scorer end-to-end without real data."""
    rng = random.Random(seed)
    out: dict[str, str] = {}
    for q in questions:
        n = len(q.get("choices") or [])
        cl = correct_letter(q)
        if rng.random() < 0.70:
            out[q["id"]] = cl
        else:
            others = [string.ascii_uppercase[i] for i in range(n)
                      if string.ascii_uppercase[i] != cl]
            out[q["id"]] = rng.choice(others) if others else cl
    return out


def score(questions: list[dict[str, Any]], responses: dict[str, Any]) -> dict[str, Any]:
    by_id = {q["id"]: q for q in questions}
    graded: list[dict[str, Any]] = []
    unanswered: list[str] = []
    bad: list[str] = []
    unknown_ids = [qid for qid in responses if qid not in by_id]

    for q in questions:
        qid = q["id"]
        if qid not in responses:
            unanswered.append(qid)
            continue
        try:
            picked = normalize_answer(responses[qid], q)
        except ValueError as exc:
            bad.append(f"{qid}: {exc}")
            continue
        if picked is None:
            unanswered.append(qid)
            continue
        graded.append({
            "id": qid,
            "topic_id": q.get("topic_id"),
            "section": q.get("section"),
            "picked": picked,
            "correct": correct_letter(q),
            "is_correct": picked == correct_letter(q),
        })

    return {
        "graded": graded,
        "unanswered": unanswered,
        "bad": bad,
        "unknown_ids": unknown_ids,
        "n_total": len(questions),
    }


def _group_acc(graded: list[dict[str, Any]], key: str) -> list[tuple[str, int, int]]:
    agg: dict[str, list[int]] = defaultdict(list)
    for g in graded:
        agg[str(g.get(key))].append(1 if g["is_correct"] else 0)
    rows = [(k, sum(v), len(v)) for k, v in agg.items()]
    return sorted(rows, key=lambda r: r[0])


def report(res: dict[str, Any], source: str) -> None:
    graded = res["graded"]
    n = len(graded)
    k = sum(1 for g in graded if g["is_correct"])

    print("=" * 70)
    print(f"HELD-OUT PERFORMANCE ACCURACY   [{source}]")
    print("=" * 70)
    print(f"held_out questions in bank : {res['n_total']}")
    print(f"answered (graded)          : {n}")
    print(f"unanswered / blank         : {len(res['unanswered'])}")
    if res["bad"]:
        print(f"unparseable answers        : {len(res['bad'])}")
    if res["unknown_ids"]:
        print(f"responses for unknown ids  : {len(res['unknown_ids'])}")
    print()

    if n == 0:
        print("No gradeable answers — cannot report accuracy.")
        return

    acc = k / n
    lo, hi = wilson_ci(k, n)
    print(f"OVERALL ACCURACY : {acc:.3f}  ({k}/{n})")
    print(f"Wilson 95% CI    : [{lo:.3f}, {hi:.3f}]")
    print()

    print("by section")
    print(f"  {'section':10} {'n':>4} {'correct':>8} {'acc':>7}")
    print("  " + "-" * 34)
    for name, kk, nn in _group_acc(graded, "section"):
        print(f"  {name:10} {nn:4d} {kk:8d} {kk / nn:7.3f}")
    print()

    print("by topic")
    print(f"  {'topic_id':22} {'n':>4} {'correct':>8} {'acc':>7}")
    print("  " + "-" * 46)
    for name, kk, nn in _group_acc(graded, "topic_id"):
        print(f"  {name:22} {nn:4d} {kk:8d} {kk / nn:7.3f}")
    print()

    if n < 30:
        print(f"[HONESTY] Only {n} graded held-out answers (< 30). Treat this "
              "accuracy as indicative only; the CI above is wide on purpose.")
    if res["bad"]:
        print("\nUnparseable answers (fix and re-run):")
        for b in res["bad"]:
            print(f"  - {b}")
    if res["unknown_ids"]:
        preview = ", ".join(res["unknown_ids"][:8])
        more = "" if len(res["unknown_ids"]) <= 8 else f" (+{len(res['unknown_ids']) - 8} more)"
        print(f"\nResponses referencing ids not in the held_out split: {preview}{more}")


def emit_attempts(res: dict[str, Any], path: Path) -> None:
    """Write [{question_id, correct: bool}, ...] for scripts/eval_paraphrase.py."""
    rows = [{"question_id": g["id"], "correct": bool(g["is_correct"])}
            for g in res["graded"]]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    print(f"\nwrote {len(rows)} attempts -> {path}  (feed to eval_paraphrase.py --attempts)")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="score_heldout.py",
        description="Score a volunteer's answers to the frozen held_out question bank.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Examples:\n"
               "  py -3.12 scripts/score_heldout.py --make-template build/heldout.TEMPLATE.json\n"
               "  py -3.12 scripts/score_heldout.py --responses build/heldout_friend.json\n"
               "  py -3.12 scripts/score_heldout.py --demo\n",
    )
    ap.add_argument("--bank", type=Path, default=DEFAULT_BANK,
                    help=f"question bank JSON (default {DEFAULT_BANK.relative_to(ROOT)})")
    ap.add_argument("--responses", type=Path,
                    help="volunteer answers JSON (dict or list; see module docstring)")
    ap.add_argument("--make-template", type=Path, metavar="PATH",
                    help="write a blank answer sheet (no key leaked) and exit")
    ap.add_argument("--emit-attempts", type=Path, metavar="PATH",
                    help="also write a paraphrase-gap attempts file for eval_paraphrase.py")
    ap.add_argument("--demo", action="store_true",
                    help="score deterministic SYNTHETIC answers (proves the pipeline, no real data)")
    args = ap.parse_args(argv)

    if not args.bank.is_file():
        print(f"bank not found: {args.bank}", file=sys.stderr)
        return 2

    bank = load_bank(args.bank)
    questions = held_out(bank)
    if not questions:
        print(f"no questions with split=={HELD_OUT_SPLIT!r} in {args.bank}", file=sys.stderr)
        return 2

    if args.make_template:
        make_template(args.make_template, questions)
        print(f"wrote blank answer sheet ({len(questions)} held_out questions, "
              f"NO answer key) -> {args.make_template}")
        return 0

    if args.demo:
        responses: dict[str, Any] = synth_responses(questions, seed=20260705)
        source = "SYNTHETIC demo — deterministic, NOT real volunteer data"
    elif args.responses:
        if not args.responses.is_file():
            print(f"responses not found: {args.responses}", file=sys.stderr)
            return 2
        responses = coerce_responses(json.loads(args.responses.read_text(encoding="utf-8")))
        source = f"real data: {args.responses.name}"
    else:
        ap.error("provide --responses PATH, or --make-template PATH, or --demo")

    res = score(questions, responses)
    report(res, source)
    if args.emit_attempts:
        emit_attempts(res, args.emit_attempts)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
