#!/usr/bin/env py -3.12
"""Step 2 prediction harness — predict held-out Q correctness from feature snapshots.

Rubric gap (§7 / Step 2): can we predict whether a student will answer a frozen
held_out question correctly from topic mastery, item difficulty, timing, and
outline coverage flags?

This script runs a **SYNTHETIC DEMONSTRATION ONLY**:
  * attempts are deterministic mock rows (or loaded from gen_synthetic_heldout output);
  * mastery / timing / coverage are mock snapshots derived from question metadata;
  * a transparent logistic model (fixed weights, documented below) produces p(correct).

Outputs calibration metrics (Brier, log-loss, accuracy @ 0.5 + Wilson 95% CI) and
writes ``docs/artifacts/step2-prediction-SYNTHETIC.summary.json``.

NO AI, no network, no API keys. Does NOT touch Memory or Readiness scores.

Usage
-----
  py -3.12 scripts/eval_step2_prediction.py
  py -3.12 scripts/eval_step2_prediction.py --attempts build/heldout-SYNTHETIC_testerB.json
  make eval-step2-synthetic
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BANK = ROOT / "data" / "questions.json"
DEFAULT_OUT = ROOT / "docs" / "artifacts" / "step2-prediction-SYNTHETIC.summary.json"
HELD_OUT_SPLIT = "held_out"

# Transparent logistic weights (assumptions — not fitted on real data).
LOGIT_WEIGHTS = {
    "intercept": -0.35,
    "topic_mastery": 2.4,
    "difficulty": -1.5,
    "timing_fast": -0.45,
    "coverage": 0.55,
}

DEMAND_DIFFICULTY = {
    "recall": 0.25,
    "application": 0.55,
    "synthesis": 0.80,
    "passage": 0.65,
}

try:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
except Exception:
    pass


def _unit(seed: str) -> float:
    h = hashlib.md5(seed.encode("utf-8")).hexdigest()
    return int(h[:8], 16) / 0xFFFFFFFF


def sigmoid(x: float) -> float:
    if x >= 0:
        z = math.exp(-x)
        return 1.0 / (1.0 + z)
    z = math.exp(x)
    return z / (1.0 + z)


def wilson_ci(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n <= 0:
        return (0.0, 1.0)
    p = k / n
    denom = 1.0 + z * z / n
    centre = p + z * z / (2 * n)
    margin = z * math.sqrt((p * (1 - p) + z * z / (4 * n)) / n)
    return ((centre - margin) / denom, (centre + margin) / denom)


def brier_score(preds: list[float], labels: list[int]) -> float:
    if not preds:
        return float("nan")
    return sum((p - y) ** 2 for p, y in zip(preds, labels)) / len(preds)


def log_loss(preds: list[float], labels: list[int], eps: float = 1e-12) -> float:
    if not preds:
        return float("nan")
    total = 0.0
    for p, y in zip(preds, labels):
        p = min(max(p, eps), 1.0 - eps)
        total += -(y * math.log(p) + (1 - y) * math.log(1 - p))
    return total / len(preds)


def load_bank(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("question bank must be a JSON array")
    return data


def held_out(bank: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [q for q in bank if q.get("split") == HELD_OUT_SPLIT]


@dataclass
class AttemptRow:
    question_id: str
    topic_id: str
    section: str
    correct: int
    time_seconds: float


@dataclass
class FeatureRow:
    question_id: str
    topic_mastery: float
    difficulty: float
    timing_fast: float
    coverage: float
    p_pred: float
    y: int


def mock_topic_mastery(topic_id: str, seed: int) -> float:
    base = _unit(f"mastery:{topic_id}:{seed}")
    return round(0.35 + 0.50 * base, 4)


def mock_timing_fast(question_id: str, seed: int) -> float:
    """Normalized fast-vs-slow proxy in [0,1]; higher = faster (worse transfer)."""
    base = _unit(f"timing:{question_id}:{seed}")
    return round(0.15 + 0.70 * base, 4)


def mock_coverage(topic_id: str, covered_topics: set[str]) -> float:
    return 1.0 if topic_id in covered_topics else 0.0


def difficulty_proxy(q: dict[str, Any]) -> float:
    demand = str(q.get("cognitive_demand") or "application").lower()
    return DEMAND_DIFFICULTY.get(demand, 0.55)


def predict_logistic(
    mastery: float, difficulty: float, timing_fast: float, coverage: float
) -> float:
    w = LOGIT_WEIGHTS
    z = (
        w["intercept"]
        + w["topic_mastery"] * mastery
        + w["difficulty"] * difficulty
        + w["timing_fast"] * timing_fast
        + w["coverage"] * coverage
    )
    return sigmoid(z)


def attempts_from_responses(
    raw: Any, bank_by_id: dict[str, dict[str, Any]], seed: int
) -> list[AttemptRow]:
    """Coerce a score_heldout-style responses file into graded attempt rows."""
    from score_heldout import coerce_responses, normalize_answer, correct_letter

    responses = coerce_responses(raw)
    rows: list[AttemptRow] = []
    for qid, ans in responses.items():
        q = bank_by_id.get(qid)
        if not q:
            continue
        try:
            picked = normalize_answer(ans, q)
        except ValueError:
            continue
        if picked is None:
            continue
        t = 25.0 + 55.0 * _unit(f"time:{qid}:{seed}")
        rows.append(
            AttemptRow(
                question_id=qid,
                topic_id=str(q.get("topic_id")),
                section=str(q.get("section")),
                correct=1 if picked == correct_letter(q) else 0,
                time_seconds=t,
            )
        )
    return rows


def synth_attempts(
    questions: list[dict[str, Any]], seed: int, covered_topics: set[str]
) -> list[AttemptRow]:
    """Deterministic synthetic attempts when no responses file is supplied."""
    rows: list[AttemptRow] = []
    for q in questions:
        qid = q["id"]
        mastery = mock_topic_mastery(str(q.get("topic_id")), seed)
        diff = difficulty_proxy(q)
        timing = mock_timing_fast(qid, seed)
        cov = mock_coverage(str(q.get("topic_id")), covered_topics)
        p = predict_logistic(mastery, diff, timing, cov)
        u = _unit(f"label:{qid}:{seed}")
        rows.append(
            AttemptRow(
                question_id=qid,
                topic_id=str(q.get("topic_id")),
                section=str(q.get("section")),
                correct=1 if u < p else 0,
                time_seconds=25.0 + 55.0 * timing,
            )
        )
    return rows


def build_features(
    attempts: list[AttemptRow],
    bank_by_id: dict[str, dict[str, Any]],
    seed: int,
    covered_topics: set[str],
) -> list[FeatureRow]:
    out: list[FeatureRow] = []
    for a in attempts:
        q = bank_by_id[a.question_id]
        mastery = mock_topic_mastery(a.topic_id, seed)
        diff = difficulty_proxy(q)
        timing = mock_timing_fast(a.question_id, seed)
        cov = mock_coverage(a.topic_id, covered_topics)
        p = predict_logistic(mastery, diff, timing, cov)
        out.append(
            FeatureRow(
                question_id=a.question_id,
                topic_mastery=mastery,
                difficulty=diff,
                timing_fast=timing,
                coverage=cov,
                p_pred=p,
                y=a.correct,
            )
        )
    return out


def accuracy_at_threshold(rows: list[FeatureRow], threshold: float = 0.5) -> tuple[int, int, float]:
    k = sum(1 for r in rows if (r.p_pred >= threshold) == bool(r.y))
    n = len(rows)
    return k, n, (k / n if n else float("nan"))


def report(rows: list[FeatureRow], source: str) -> None:
    preds = [r.p_pred for r in rows]
    labels = [r.y for r in rows]
    brier = brier_score(preds, labels)
    ll = log_loss(preds, labels)
    k_acc, n_acc, acc = accuracy_at_threshold(rows)
    lo, hi = wilson_ci(k_acc, n_acc)

    print("=" * 74)
    print(f"STEP 2 PREDICTION CALIBRATION   [{source}]")
    print("=" * 74)
    print(f"n_attempts           : {len(rows)}")
    print(f"observed accuracy    : {sum(labels) / len(labels):.3f}")
    print(f"mean predicted p     : {sum(preds) / len(preds):.3f}")
    print(f"Brier score          : {brier:.4f}   (lower is better)")
    print(f"log-loss             : {ll:.4f}   (lower is better)")
    print(f"accuracy @ p>=0.5    : {acc:.3f}  ({k_acc}/{n_acc})")
    print(f"Wilson 95% CI        : [{lo:.3f}, {hi:.3f}]")
    print()
    print("Features (mock snapshots): topic_mastery, difficulty_proxy,")
    print("  timing_fast, coverage_flag — see summary JSON for weights.")
    if len(rows) < 30:
        print(f"[HONESTY] n={len(rows)} (< 30): indicative only.")


def main() -> int:
    ap = argparse.ArgumentParser(description="Step 2 held-out prediction harness (synthetic)")
    ap.add_argument("--bank", type=Path, default=DEFAULT_BANK)
    ap.add_argument("--attempts", type=Path, help="optional responses JSON (held_out only)")
    ap.add_argument("--seed", type=int, default=20260705)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    bank = load_bank(args.bank)
    questions = held_out(bank)
    if not questions:
        print("ERROR: no held_out questions in bank.", file=sys.stderr)
        return 2
    bank_by_id = {q["id"]: q for q in bank}

    # Mock coverage: ~70% of topics "seen" (deterministic from seed).
    topics = sorted({str(q.get("topic_id")) for q in questions})
    covered = {t for t in topics if _unit(f"cov:{t}:{args.seed}") < 0.70}

    if args.attempts:
        raw = json.loads(args.attempts.read_text(encoding="utf-8"))
        attempts = attempts_from_responses(raw, bank_by_id, args.seed)
        source = f"synthetic attempts file: {args.attempts.name}"
        mode_note = "labels from supplied SYNTHETIC responses; features are mock snapshots"
    else:
        attempts = synth_attempts(questions, args.seed, covered)
        source = "synthetic demo — deterministic mock attempts + mock feature snapshots"
        mode_note = "attempts and feature snapshots are fully synthetic (seeded)"

    if not attempts:
        print("ERROR: no gradeable attempts.", file=sys.stderr)
        return 2

    rows = build_features(attempts, bank_by_id, args.seed, covered)
    report(rows, source)

    preds = [r.p_pred for r in rows]
    labels = [r.y for r in rows]
    k_acc, n_acc, acc = accuracy_at_threshold(rows)
    lo, hi = wilson_ci(k_acc, n_acc)

    summary = {
        "artifact": "step2_heldout_prediction",
        "mode": "synthetic",
        "is_real_data": False,
        "warning": "PIPELINE DEMONSTRATION ONLY — NOT a validated prediction model.",
        "eval_split": HELD_OUT_SPLIT,
        "seed": args.seed,
        "n_attempts": len(rows),
        "n_topics": len(topics),
        "n_topics_covered_mock": len(covered),
        "feature_definitions": {
            "topic_mastery": "mock FSRS-like [0.35,0.85] from topic_id + seed (not live mastery proto)",
            "difficulty": "cognitive_demand proxy (recall/application/synthesis/passage)",
            "timing_fast": "mock normalized speed [0.15,0.85] from question_id + seed",
            "coverage": "1 if topic in mock covered set (~70% of topics), else 0",
        },
        "model": {
            "type": "logistic (fixed transparent weights — not ML-trained)",
            "weights": LOGIT_WEIGHTS,
        },
        "metrics": {
            "brier": brier_score(preds, labels),
            "log_loss": log_loss(preds, labels),
            "mean_predicted_p": sum(preds) / len(preds),
            "observed_accuracy": sum(labels) / len(labels),
            "accuracy_at_threshold_0.5": acc,
            "accuracy_at_threshold_n": n_acc,
            "accuracy_at_threshold_k": k_acc,
            "wilson95_ci": [lo, hi],
        },
        "missing_data_note": (
            f"{mode_note}. No real held-out attempts paired with live mastery "
            "snapshots exist yet."
        ),
        "next_action": (
            "Replace with real held-out attempts + mastery snapshots exported "
            "at attempt time; rerun: py -3.12 scripts/eval_step2_prediction.py "
            "--attempts build/heldout-answers_<who>.json"
        ),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"\nsummary JSON: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
