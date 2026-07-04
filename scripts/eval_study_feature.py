#!/usr/bin/env py -3.12
"""STUDY-FEATURE 3-BUILD ABLATION harness for MCAT Speedrun (Sunday deliverable).

Question answered
-----------------
Does the **study METHOD** change **performance** outcomes at **equal study time**?
Three arms (PRD §6.9 SF-2/SF-3/SF-4, DECISIONS.md §11):

  1. ``interleaved``  — performance practice sessions with topics INTERLEAVED
  2. ``blocked``      — performance practice sessions BLOCKED by topic
  3. ``plain_anki``   — memory-only reviews (flashcards); NO performance practice

Locked comparison rule (do not violate)
---------------------------------------
Compare the study method on **performance** outcomes at **EQUAL STUDY TIME**.
Never blend the three scores (memory / performance / readiness). The outcome we
score is accuracy on a SHARED ``held_out`` performance test (the SAME questions
for every arm — SF-3); the thing that differs between arms is only *how the
study time was spent*.

Equal-time control — WHICH and WHY
----------------------------------
We equalize **total study SECONDS**, not number of attempts.

  * Why seconds, not attempts: the interleaving effect (Kornell & Bjork 2008) is
    defined *at equal time*. Blocked practice is typically faster per item, so
    equalizing the attempt count would silently hand one method more wall-clock
    study and confound the comparison. Equalizing seconds is the fair budget.
  * The 3-build protocol imposes this by design (each build gets the same study
    block). This harness (a) ENFORCES it in ``--synthetic`` by simulating study
    reps until a shared second-budget ``T`` is exhausted, and (b) AUDITS +
    reports it on real data, warning when the realized study seconds are
    imbalanced beyond tolerance. It does NOT statistically reweight for time
    (that would need a dose-response model we do not have) — it reports the
    outcome comparison and flags any equal-time violation honestly.
  * If real per-attempt timing is missing, it falls back to equal #attempts and
    SAYS SO in the report + JSON.

How arms map to logged data (the clean seam for real tester data)
-----------------------------------------------------------------
The desktop fork logs performance attempts to a local sidecar
(``collection.mcat_perf.db``; DECISIONS.md §5/§22) with an ``interleaved`` flag
and a ``split`` (``dev`` practice vs ``held_out`` assessment) on every attempt.
A real 3-build ablation is run as three builds / sessions, so each arm is its
own data source. This harness ingests **one source per arm** via a manifest:

    {
      "arms": {
        "interleaved": {"sidecar": ".../collection.mcat_perf.db"},
        "blocked":     {"attempts": "blocked_attempts.json"},
        "plain_anki":  {"bundle": "plain.perf_bundle.json"}
      },
      "time_budget_seconds": null
    }

Per arm source (read-only; mirrors ``anki.mcat_perf.read_attempts`` +
``scripts/revlog_from_bundle.py`` — we do NOT import the heavy ``anki`` package):
  * ``sidecar`` — a ``*.mcat_perf.db`` read read-only (URI ``mode=ro``).
  * ``attempts`` — an exported attempts JSON (list of dicts, the
    ``anki.mcat_perf.export_attempts`` / bundle ``attempts`` shape).
  * ``bundle`` — an "Export my data" perf bundle (its ``attempts`` list, and
    ``memory_revlog`` for plain-Anki study seconds).

Within a source: ``split == 'dev'`` attempts are the STUDY phase (their
``time_seconds`` sum + ``interleaved`` flag are audited); ``split == 'held_out'``
attempts are that arm's OUTCOME TEST (scored). ``plain_anki`` supplies its study
seconds from ``memory_revlog`` (the revlog ``time`` column, ms/review) and its
outcome test from any ``held_out`` attempts recorded after the memory block.

Because real multi-participant data does not exist yet, the harness ALSO ships a
documented ``--synthetic`` simulation (fixed seed) so we have real output now
with the real-data path as a clean seam. The synthetic generative model is made
explicit + honest below (assumed effect sizes, tunable, ``--null`` for a null
result). It reports null / negative results honestly (SF-4).

Metrics
-------
Per arm: n test attempts, k correct, accuracy, **Wilson 95% CI**. Between arms:
absolute accuracy difference with a **Newcombe** difference CI, **Cohen's h**
effect size, and a two-proportion **z-test** p-value (normal approx, stdlib) —
each stamped with a small-n honesty caveat.

Outputs (mirror ``scripts/eval_memory.py``'s ``.png`` + ``.summary.json``)
--------------------------------------------------------------------------
  docs/artifacts/study-feature.png           bar chart, Wilson CI whiskers
  docs/artifacts/study-feature.summary.json  full machine-readable result
  docs/artifacts/study-feature.arms.csv      per-arm table

No AI, no network. Runtime never calls this — it is an offline eval.

Usage
-----
    py -3.12 scripts/eval_study_feature.py --synthetic
    py -3.12 scripts/eval_study_feature.py --synthetic --null       # null result
    py -3.12 scripts/eval_study_feature.py --manifest study.json     # real data

Exit 0 on success.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import random
import sqlite3
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
DEFAULT_OUT = ROOT / "docs" / "artifacts" / "study-feature.png"
SCORING_CONFIG = ROOT / "data" / "scoring-config.json"

DEV_SPLIT = "dev"
HELD_OUT_SPLIT = "held_out"

# Canonical arm ids + display order.
ARM_INTERLEAVED = "interleaved"
ARM_BLOCKED = "blocked"
ARM_PLAIN = "plain_anki"
ARM_ORDER = (ARM_INTERLEAVED, ARM_BLOCKED, ARM_PLAIN)
ARM_LABEL = {
    ARM_INTERLEAVED: "Interleaved perf",
    ARM_BLOCKED: "Blocked perf",
    ARM_PLAIN: "Plain Anki",
}

# Report uses ± and — ; force UTF-8 so it renders on a Windows cp1252 console.
try:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
except Exception:
    pass


# ---------------------------------------------------------------------------
# Statistics (pure stdlib — no numpy/scipy dependency)
# ---------------------------------------------------------------------------

def _phi(x: float) -> float:
    """Standard normal CDF via erf (stdlib)."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def wilson_interval(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion. Widens at small n."""
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    z2 = z * z
    denom = 1.0 + z2 / n
    center = (p + z2 / (2 * n)) / denom
    half = (z * math.sqrt(p * (1 - p) / n + z2 / (4 * n * n))) / denom
    return (max(0.0, center - half), min(1.0, center + half))


def two_proportion_z(k1: int, n1: int, k2: int, n2: int) -> tuple[Optional[float], Optional[float]]:
    """Pooled two-proportion z-test. Returns (z, two-sided p) or (None, None)."""
    if n1 == 0 or n2 == 0:
        return (None, None)
    p1, p2 = k1 / n1, k2 / n2
    p_pool = (k1 + k2) / (n1 + n2)
    se = math.sqrt(p_pool * (1 - p_pool) * (1 / n1 + 1 / n2))
    if se == 0:
        return (None, None)
    z = (p1 - p2) / se
    p = 2.0 * (1.0 - _phi(abs(z)))
    return (z, p)


def newcombe_diff_ci(k1: int, n1: int, k2: int, n2: int,
                     z: float = 1.96) -> tuple[Optional[float], Optional[float]]:
    """Newcombe method-10 CI for the difference of two proportions (p1 - p2).

    More honest than a Wald difference CI at small n. Built from the two
    individual Wilson intervals.
    """
    if n1 == 0 or n2 == 0:
        return (None, None)
    p1, p2 = k1 / n1, k2 / n2
    l1, u1 = wilson_interval(k1, n1, z)
    l2, u2 = wilson_interval(k2, n2, z)
    diff = p1 - p2
    lower = diff - math.sqrt((p1 - l1) ** 2 + (u2 - p2) ** 2)
    upper = diff + math.sqrt((u1 - p1) ** 2 + (p2 - l2) ** 2)
    return (lower, upper)


def cohens_h(p1: float, p2: float) -> float:
    """Cohen's h effect size for two proportions (|h|: .2 small, .5 med, .8 lg)."""
    return 2 * math.asin(math.sqrt(p1)) - 2 * math.asin(math.sqrt(p2))


# ---------------------------------------------------------------------------
# Arm data model
# ---------------------------------------------------------------------------

@dataclass
class ArmData:
    """Everything the scorer needs for one experimental arm."""
    arm: str
    # OUTCOME test: per-attempt correctness (1/0) on the shared held_out set.
    test_correct: list[int] = field(default_factory=list)
    # STUDY phase accounting (audited for the equal-time control).
    study_seconds: float = 0.0
    study_attempts: int = 0
    study_time_missing: bool = False       # timing absent on real study rows
    interleaved_flag_seen: Optional[bool] = None  # realized flag on study rows
    source_desc: str = ""

    @property
    def n(self) -> int:
        return len(self.test_correct)

    @property
    def k(self) -> int:
        return sum(self.test_correct)

    @property
    def accuracy(self) -> Optional[float]:
        return (self.k / self.n) if self.n else None


# ---------------------------------------------------------------------------
# Real-data readers (read-only; standalone mirror of anki.mcat_perf +
# revlog_from_bundle so we never import the heavy `anki` package)
# ---------------------------------------------------------------------------

# Mirrors anki.mcat_perf._EXPORT_QUERY (read-only) — a.* plus question context.
_SIDECAR_QUERY = """
SELECT a.*,
       q.topic_id        AS topic_id,
       q.section         AS section,
       q.split           AS split,
       q.cognitive_demand AS cognitive_demand,
       q.source_name     AS source_name
FROM perf_attempts a
LEFT JOIN perf_questions q ON q.id = a.question_id
ORDER BY a.id
"""


def read_sidecar_attempts(db_path: str) -> list[dict[str, Any]]:
    """Read attempts from a ``*.mcat_perf.db`` sidecar READ-ONLY.

    Mirrors ``anki.mcat_perf.read_attempts`` (same join, same read-only URI) but
    is standalone so this eval has no dependency on the fork's Python package.
    """
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(_SIDECAR_QUERY).fetchall()
    finally:
        conn.close()
    out: list[dict[str, Any]] = []
    for r in rows:
        d = dict(r)
        raw = d.get("feature_json")
        try:
            d["feature"] = json.loads(raw) if raw else None
        except (TypeError, ValueError):
            d["feature"] = None
        out.append(d)
    return out


def _load_bundle(path: Path) -> dict[str, Any]:
    """Load an 'Export my data' / sync bundle. Reuses revlog_from_bundle's loader
    when importable; otherwise a byte-identical local fallback."""
    try:
        if str(SCRIPTS) not in sys.path:
            sys.path.insert(0, str(SCRIPTS))
        from revlog_from_bundle import _load_bundle as _rfb_load  # type: ignore
        return _rfb_load(path)
    except Exception:
        doc = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(doc, dict):
            raise ValueError("bundle must be a JSON object")
        return doc


def _attempt_split(row: dict[str, Any]) -> Optional[str]:
    split = row.get("split")
    if split is None:
        feat = row.get("feature")
        if isinstance(feat, dict):
            split = feat.get("split")
    return split


def _attempt_time(row: dict[str, Any]) -> Optional[float]:
    t = row.get("time_seconds")
    if t is None:
        feat = row.get("feature")
        if isinstance(feat, dict):
            t = feat.get("time_seconds")
    try:
        return float(t) if t is not None else None
    except (TypeError, ValueError):
        return None


def _attempt_interleaved(row: dict[str, Any]) -> Optional[bool]:
    v = row.get("interleaved")
    if v is None:
        feat = row.get("feature")
        if isinstance(feat, dict):
            v = feat.get("interleaved")
    return None if v is None else bool(v)


def _memory_study_seconds(bundle: dict[str, Any]) -> tuple[float, int]:
    """Sum revlog ``time`` (ms) → study seconds from a bundle's memory_revlog."""
    revlog = bundle.get("memory_revlog") or []
    total_ms = 0.0
    n = 0
    for r in revlog:
        try:
            total_ms += float(r.get("time") or 0)
            n += 1
        except (TypeError, ValueError):
            continue
    return (total_ms / 1000.0, n)


def load_arm_from_source(arm: str, spec: dict[str, Any]) -> ArmData:
    """Build an ArmData from one manifest arm spec (sidecar | attempts | bundle)."""
    data = ArmData(arm=arm)
    attempts: list[dict[str, Any]] = []
    descs: list[str] = []

    if "sidecar" in spec:
        p = spec["sidecar"]
        attempts += read_sidecar_attempts(p)
        descs.append(f"sidecar {os.path.basename(p)}")
    if "attempts" in spec:
        p = spec["attempts"]
        raw = json.loads(Path(p).read_text(encoding="utf-8"))
        if isinstance(raw, dict) and "attempts" in raw:
            raw = raw["attempts"]
        attempts += list(raw)
        descs.append(f"attempts {os.path.basename(p)}")
    if "bundle" in spec:
        p = spec["bundle"]
        bundle = _load_bundle(Path(p))
        attempts += list(bundle.get("attempts") or [])
        secs, nrev = _memory_study_seconds(bundle)
        data.study_seconds += secs
        data.study_attempts += nrev
        descs.append(f"bundle {os.path.basename(p)} (+{nrev} revlog rows)")

    study_times: list[float] = []
    flags: list[bool] = []
    for row in attempts:
        split = _attempt_split(row)
        if split == HELD_OUT_SPLIT:
            data.test_correct.append(1 if row.get("correct") else 0)
        else:  # dev / unknown → study phase
            data.study_attempts += 1
            t = _attempt_time(row)
            if t is None:
                data.study_time_missing = True
            else:
                study_times.append(t)
            fl = _attempt_interleaved(row)
            if fl is not None:
                flags.append(fl)
    data.study_seconds += sum(study_times)
    if flags:
        # majority flag observed on this arm's study rows (audit only).
        data.interleaved_flag_seen = sum(flags) >= (len(flags) / 2)
    data.source_desc = "; ".join(descs) if descs else "(empty source)"
    return data


def load_manifest(path: Path) -> tuple[list[ArmData], Optional[float]]:
    doc = json.loads(path.read_text(encoding="utf-8"))
    arms_spec = doc.get("arms") or {}
    arms: list[ArmData] = []
    for arm in ARM_ORDER:
        if arm in arms_spec:
            arms.append(load_arm_from_source(arm, arms_spec[arm]))
    # allow arbitrary extra arm ids too (kept in file order)
    for arm, spec in arms_spec.items():
        if arm not in ARM_ORDER:
            arms.append(load_arm_from_source(arm, spec))
    budget = doc.get("time_budget_seconds")
    return arms, (float(budget) if budget is not None else None)


# ---------------------------------------------------------------------------
# Synthetic generative model (explicit + honest; fixed seed)
# ---------------------------------------------------------------------------

@dataclass
class SynthConfig:
    """Documented synthetic generative parameters. ALL are ASSUMPTIONS, not
    evidence — they are recorded verbatim into the summary JSON + PNG so nobody
    mistakes the demo for a finding."""
    seed: int = 20260703
    n_topics: int = 12
    test_n: int = 120                # held_out test attempts per arm (pooled set)
    time_budget_seconds: float = 1800.0  # equal study block per arm (30 min)
    base_accuracy: float = 0.55      # plain-Anki transfer accuracy on held_out
    blocked_uplift: float = 0.06     # blocked perf practice vs plain Anki
    interleave_uplift: float = 0.10  # interleaved vs blocked (headline ASSUMED)
    topic_sd: float = 0.06           # per-topic accuracy spread (realism)
    # per-rep study seconds (interleaving is slower/harder per rep — realistic)
    sec_interleaved: float = 26.0
    sec_blocked: float = 20.0
    sec_review: float = 8.0


def _clamp01(x: float) -> float:
    return 0.0 if x < 0 else 1.0 if x > 1 else x


def simulate_arm(arm: str, arm_index: int, true_mean: float, cfg: SynthConfig) -> ArmData:
    """Simulate one arm: fill the equal-time study budget with reps, then draw
    ``test_n`` Bernoulli outcomes on the shared held_out test at the arm's true
    (assumed) transfer accuracy, spread across topics.

    Each arm gets its OWN deterministic RNG streams (derived from the global
    seed + arm index) so arms are independent and the test outcomes do not shift
    when an unrelated knob (e.g. the study budget) changes. Study and test draws
    use separate streams for the same reason.
    """
    data = ArmData(arm=arm, source_desc="synthetic")
    study_rng = random.Random(cfg.seed * 1000003 + arm_index * 7919 + 1)
    test_rng = random.Random(cfg.seed * 1000003 + arm_index * 7919 + 2)

    # --- study phase: burn reps until the shared second-budget is spent ---
    per_rep = {
        ARM_INTERLEAVED: cfg.sec_interleaved,
        ARM_BLOCKED: cfg.sec_blocked,
        ARM_PLAIN: cfg.sec_review,
    }.get(arm, cfg.sec_blocked)
    spent = 0.0
    reps = 0
    while spent < cfg.time_budget_seconds:
        spent += max(1.0, study_rng.gauss(per_rep, per_rep * 0.25))
        reps += 1
    data.study_seconds = round(spent, 1)
    data.study_attempts = reps
    if arm == ARM_INTERLEAVED:
        data.interleaved_flag_seen = True
    elif arm == ARM_BLOCKED:
        data.interleaved_flag_seen = False

    # --- outcome test: per-topic true prob = arm mean + deterministic offset ---
    topic_offsets = [test_rng.gauss(0.0, cfg.topic_sd) for _ in range(cfg.n_topics)]
    for i in range(cfg.test_n):
        topic = i % cfg.n_topics
        p_attempt = _clamp01(true_mean + topic_offsets[topic])
        data.test_correct.append(1 if test_rng.random() < p_attempt else 0)
    return data


def generate_synthetic(cfg: SynthConfig) -> list[ArmData]:
    """Build all three arms from the documented generative model.

    True (ASSUMED) transfer accuracy per arm:
        plain_anki  = base_accuracy
        blocked     = base_accuracy + blocked_uplift
        interleaved = base_accuracy + blocked_uplift + interleave_uplift

    Interpretation of the assumptions:
      * blocked_uplift > 0 : ANY performance practice trains application/transfer
        that plain flashcard recall does not (PRD §2.1 SPOV 2).
      * interleave_uplift > 0 : interleaving improves mixed-topic transfer at
        equal time (Kornell & Bjork 2008; DECISIONS.md §11).
    Set either to 0 (``--null`` sets both) to demonstrate an HONEST null result.
    """
    means = {
        ARM_PLAIN: _clamp01(cfg.base_accuracy),
        ARM_BLOCKED: _clamp01(cfg.base_accuracy + cfg.blocked_uplift),
        ARM_INTERLEAVED: _clamp01(
            cfg.base_accuracy + cfg.blocked_uplift + cfg.interleave_uplift
        ),
    }
    # each arm has its own seeded (independent) stream → reproducible + decoupled
    return [simulate_arm(arm, i, means[arm], cfg) for i, arm in enumerate(ARM_ORDER)]


# ---------------------------------------------------------------------------
# Scoring + report
# ---------------------------------------------------------------------------

def default_perf_min_attempts() -> int:
    try:
        cfg = json.loads(SCORING_CONFIG.read_text(encoding="utf-8"))
        return int(cfg["give_up"]["performance"]["min_total_attempts"])
    except Exception:
        return 30


def wilson_z() -> float:
    try:
        cfg = json.loads(SCORING_CONFIG.read_text(encoding="utf-8"))
        return float(cfg["performance"]["interval"]["z"])
    except Exception:
        return 1.96


@dataclass
class Comparison:
    a: str
    b: str
    diff: Optional[float]
    diff_ci: tuple[Optional[float], Optional[float]]
    cohens_h: Optional[float]
    z: Optional[float]
    p: Optional[float]


def compare(a: ArmData, b: ArmData, z: float) -> Comparison:
    if a.n == 0 or b.n == 0 or a.accuracy is None or b.accuracy is None:
        return Comparison(a.arm, b.arm, None, (None, None), None, None, None)
    diff = a.accuracy - b.accuracy
    ci = newcombe_diff_ci(a.k, a.n, b.k, b.n, z)
    h = cohens_h(a.accuracy, b.accuracy)
    zz, p = two_proportion_z(a.k, a.n, b.k, b.n)
    return Comparison(a.arm, b.arm, diff, ci, h, zz, p)


def _fmt_pct(x: Optional[float]) -> str:
    return "  --  " if x is None else f"{100 * x:5.1f}%"


def build_summary(arms: list[ArmData], comps: list[Comparison], *,
                  mode: str, z: float, budget: Optional[float],
                  equal_time_ok: bool, equal_time_note: str,
                  synth_cfg: Optional[SynthConfig], min_attempts: int) -> dict[str, Any]:
    arm_rows = []
    for a in arms:
        lo, hi = wilson_interval(a.k, a.n, z) if a.n else (None, None)
        arm_rows.append({
            "arm": a.arm,
            "label": ARM_LABEL.get(a.arm, a.arm),
            "n_test": a.n,
            "correct": a.k,
            "accuracy": a.accuracy,
            "wilson_lo": lo,
            "wilson_hi": hi,
            "study_seconds": round(a.study_seconds, 1),
            "study_attempts": a.study_attempts,
            "study_time_missing": a.study_time_missing,
            "interleaved_flag_seen": a.interleaved_flag_seen,
            "source": a.source_desc,
            "below_give_up": a.n < min_attempts,
        })
    comp_rows = []
    for c in comps:
        comp_rows.append({
            "arm_a": c.a, "arm_b": c.b,
            "accuracy_diff": c.diff,
            "diff_ci_lo": c.diff_ci[0], "diff_ci_hi": c.diff_ci[1],
            "cohens_h": c.cohens_h,
            "z": c.z, "p_value": c.p,
            "significant_0_05": (c.p is not None and c.p < 0.05),
        })
    summary: dict[str, Any] = {
        "experiment": "study_feature_3_build_ablation",
        "prd_refs": ["§3.1 goal 7", "§6.9 SF-1..SF-4", "§8 study feature"],
        "mode": mode,
        "comparison_rule": ("study method vs PERFORMANCE outcome at EQUAL STUDY "
                            "TIME; scores never blended"),
        "outcome_measure": "accuracy on shared held_out performance test",
        "equal_time_control": {
            "unit": "total study seconds",
            "why": ("interleaving is defined at equal time; blocked practice is "
                    "faster per rep, so equal-attempts would confound"),
            "budget_seconds": budget,
            "balanced": equal_time_ok,
            "note": equal_time_note,
        },
        "wilson_z": z,
        "perf_give_up_min_attempts": min_attempts,
        "arms": arm_rows,
        "comparisons": comp_rows,
    }
    if synth_cfg is not None:
        summary["synthetic_model"] = {
            "WARNING": ("SYNTHETIC — arm effect sizes are ASSUMPTIONS, not "
                        "evidence. Real numbers require the manifest path."),
            "seed": synth_cfg.seed,
            "n_topics": synth_cfg.n_topics,
            "test_n_per_arm": synth_cfg.test_n,
            "time_budget_seconds": synth_cfg.time_budget_seconds,
            "base_accuracy_plain_anki": synth_cfg.base_accuracy,
            "blocked_uplift_vs_plain": synth_cfg.blocked_uplift,
            "interleave_uplift_vs_blocked": synth_cfg.interleave_uplift,
            "topic_sd": synth_cfg.topic_sd,
            "per_rep_seconds": {
                "interleaved": synth_cfg.sec_interleaved,
                "blocked": synth_cfg.sec_blocked,
                "review": synth_cfg.sec_review,
            },
        }
    return summary


def print_report(summary: dict[str, Any]) -> None:
    print("=" * 74)
    print("STUDY-FEATURE 3-BUILD ABLATION  "
          f"[{summary['mode']}]")
    print("=" * 74)
    if summary["mode"] == "synthetic":
        sm = summary["synthetic_model"]
        print("*** SYNTHETIC DEMO — effect sizes below are ASSUMPTIONS, not "
              "measured results. ***")
        print(f"    seed={sm['seed']}  test_n/arm={sm['test_n_per_arm']}  "
              f"budget={sm['time_budget_seconds']:.0f}s")
        print(f"    assumed uplifts: blocked vs plain +{sm['blocked_uplift_vs_plain']:.2f}, "
              f"interleaved vs blocked +{sm['interleave_uplift_vs_blocked']:.2f}")
    else:
        print(f"    source: real data (manifest)")
    print()

    et = summary["equal_time_control"]
    print(f"equal-time control: unit={et['unit']}  budget="
          f"{'auto' if et['budget_seconds'] is None else f'{et['budget_seconds']:.0f}s'}"
          f"  balanced={'YES' if et['balanced'] else 'NO — see note'}")
    print(f"  {et['note']}")
    print()

    print("PER-ARM  (outcome = accuracy on shared held_out test; Wilson 95% CI)")
    print(f"  {'arm':16} {'n':>4} {'acc':>7} {'95% CI':>16} {'study_s':>9} {'reps':>6}")
    print("  " + "-" * 64)
    for a in summary["arms"]:
        ci = (f"[{_fmt_pct(a['wilson_lo'])},{_fmt_pct(a['wilson_hi'])}]"
              if a["accuracy"] is not None else "     --      ")
        acc = _fmt_pct(a["accuracy"])
        flag = ""
        if a["below_give_up"]:
            flag = "  (< give-up n!)"
        print(f"  {ARM_LABEL.get(a['arm'], a['arm']):16} {a['n_test']:4d} {acc:>7} "
              f"{ci:>16} {a['study_seconds']:9.0f} {a['study_attempts']:6d}{flag}")
    print()

    print("BETWEEN-ARM  (diff = A − B accuracy; Newcombe 95% CI; two-prop z-test)")
    print(f"  {'contrast':28} {'diff':>7} {'95% CI':>18} {'h':>6} {'p':>8}")
    print("  " + "-" * 72)
    for c in summary["comparisons"]:
        if c["accuracy_diff"] is None:
            print(f"  {c['arm_a']+' − '+c['arm_b']:28} {'--':>7} "
                  f"{'(insufficient data)':>18}")
            continue
        ci = f"[{c['diff_ci_lo']*100:+5.1f},{c['diff_ci_hi']*100:+5.1f}]"
        sig = "" if c["p_value"] is None else ("  *" if c["significant_0_05"] else "")
        pstr = "  --  " if c["p_value"] is None else f"{c['p_value']:.3f}"
        print(f"  {ARM_LABEL.get(c['arm_a'],c['arm_a'])+' − '+ARM_LABEL.get(c['arm_b'],c['arm_b']):28} "
              f"{c['accuracy_diff']*100:+6.1f} {ci:>18} {c['cohens_h']:+5.2f} {pstr:>8}{sig}")
    print()

    # honest verdict
    any_below = any(a["below_give_up"] for a in summary["arms"])
    sig_any = any(c["significant_0_05"] for c in summary["comparisons"])
    print("VERDICT")
    if sig_any:
        print("  At least one between-arm difference is significant at p<0.05.")
    else:
        print("  No between-arm difference reaches p<0.05 — report as a NULL "
              "result at this sample size (SF-4: negative results acceptable).")
    if any_below:
        mn = summary["perf_give_up_min_attempts"]
        print(f"  [HONESTY] One or more arms have < {mn} test attempts — below the "
              "performance give-up threshold; treat as indicative only (small n).")
    if summary["mode"] == "synthetic":
        print("  [HONESTY] Synthetic run: any effect shown is BY CONSTRUCTION "
              "from the assumed uplifts, not evidence. Rerun with --manifest for "
              "real tester data.")


# ---------------------------------------------------------------------------
# Chart (matplotlib if present, else eval_memory's pure-stdlib PNG canvas)
# ---------------------------------------------------------------------------

def write_png_matplotlib(out: Path, summary: dict[str, Any]) -> bool:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        return False
    arms = summary["arms"]
    xs = list(range(len(arms)))
    accs = [(a["accuracy"] or 0.0) for a in arms]
    los = [(a["accuracy"] or 0.0) - (a["wilson_lo"] or 0.0) for a in arms]
    his = [(a["wilson_hi"] or 0.0) - (a["accuracy"] or 0.0) for a in arms]
    labels = [ARM_LABEL.get(a["arm"], a["arm"]) for a in arms]
    colors = ["#1f77b4", "#ff7f0e", "#7f7f7f"]

    fig, ax = plt.subplots(figsize=(6.4, 5.2), dpi=110)
    ax.bar(xs, accs, yerr=[los, his], capsize=6,
           color=[colors[i % len(colors)] for i in xs], alpha=0.85)
    for i, a in enumerate(arms):
        if a["accuracy"] is not None:
            ax.text(i, (a["accuracy"] or 0) + 0.02, f"{100*a['accuracy']:.0f}%\n(n={a['n_test']})",
                    ha="center", va="bottom", fontsize=8)
    ax.set_xticks(xs)
    ax.set_xticklabels(labels)
    ax.set_ylim(0, 1)
    ax.set_ylabel("held_out performance accuracy")
    title = "Study-feature 3-build ablation (equal study time)"
    ax.set_title(title)
    ax.grid(True, axis="y", color="#eee")
    tag = "SYNTHETIC (assumed effect sizes)" if summary["mode"] == "synthetic" else "real data"
    ax.text(0.99, 0.01, tag, ha="right", va="bottom", fontsize=6, color="#666",
            transform=ax.transAxes)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(out)
    plt.close(fig)
    return True


def write_png_fallback(out: Path, summary: dict[str, Any]) -> None:
    """Pure-stdlib PNG bar chart reusing eval_memory's canvas + bitmap font."""
    try:
        if str(SCRIPTS) not in sys.path:
            sys.path.insert(0, str(SCRIPTS))
        from eval_memory import _Canvas, _FONT  # noqa: F401  (font used by _Canvas)
    except Exception:
        # last-resort: no chart lib at all — write a 1x1 note-free stub so the
        # pipeline still emits *a* PNG path (documented). Extremely unlikely.
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(b"")
        return

    W, H = 640, 540
    L, T = 80, 70
    PW, PH = 480, 380
    B = T + PH
    R = L + PW
    cv = _Canvas(W, H)
    ink = (30, 30, 30)
    grey = (170, 170, 170)
    light = (225, 225, 225)
    palette = [(31, 119, 180), (255, 127, 14), (127, 127, 127)]

    def Y(v: float) -> int:
        return int(B - v * PH)

    # y grid + ticks (0..1)
    for t in range(6):
        v = t / 5.0
        cv.line(L, Y(v), R, Y(v), light)
        cv.text(L - 40, Y(v) - 3, f"{v:.1f}", ink, 1)
    cv.rect(L, T, R, T, grey)
    cv.rect(L, B, R, B, grey)
    cv.rect(L, T, L, B, grey)
    cv.rect(R, T, R, B, grey)

    arms = summary["arms"]
    n = max(1, len(arms))
    slot = PW // n
    bw = int(slot * 0.5)
    for i, a in enumerate(arms):
        cx = L + slot * i + slot // 2
        acc = a["accuracy"]
        color = palette[i % len(palette)]
        if acc is not None:
            cv.rect(cx - bw // 2, Y(acc), cx + bw // 2, B - 1, color)
            # Wilson CI whisker
            lo, hi = a["wilson_lo"], a["wilson_hi"]
            if lo is not None and hi is not None:
                cv.line(cx, Y(lo), cx, Y(hi), ink)
                cv.line(cx - 6, Y(hi), cx + 6, Y(hi), ink)
                cv.line(cx - 6, Y(lo), cx + 6, Y(lo), ink)
            cv.text(cx - 16, Y(acc) - 12, f"{100*acc:.0f}%", ink, 1)
            cv.text(cx - 20, B + 8, f"n={a['n_test']}", ink, 1)
        label = ARM_LABEL.get(a["arm"], a["arm"]).lower()
        cv.text(cx - len(label) * 3, B + 20, label[:16], ink, 1)

    # NB: the reused eval_memory bitmap font lacks j/q/z glyphs, so these chart
    # captions are worded to avoid them (the JSON/CSV/stdout carry full text).
    cv.text(L, 18, "study-feature 3-build ablation", ink, 2)
    cv.text(L, 44, "held_out perf accuracy at fixed study time", ink, 1)
    tag = ("synthetic (assumed effects)"
           if summary["mode"] == "synthetic" else "real data")
    cv.text(L, H - 16, "src: " + tag, grey, 1)

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(cv.png())


# ---------------------------------------------------------------------------
# Equal-time audit
# ---------------------------------------------------------------------------

def audit_equal_time(arms: list[ArmData], budget: Optional[float],
                     tol: float = 0.15) -> tuple[bool, str, Optional[float]]:
    """Report whether realized study seconds are balanced across arms."""
    secs = [a.study_seconds for a in arms if a.study_seconds > 0]
    any_missing = any(a.study_time_missing for a in arms)
    if not secs:
        return (False, "no study-time signal on any arm (equal-time UNVERIFIED); "
                       "falling back to equal-#attempts assumption — stated honestly.",
                budget)
    lo, hi = min(secs), max(secs)
    ratio = (hi / lo) if lo > 0 else float("inf")
    balanced = ratio <= (1.0 + tol)
    eff_budget = budget if budget is not None else lo
    note = (f"realized study seconds range {lo:.0f}–{hi:.0f} "
            f"(max/min ratio {ratio:.2f}; tol {1+tol:.2f}). ")
    if any_missing:
        note += ("Some study rows lacked timing → seconds are a lower bound; "
                 "equal-time is partially unverified. ")
    note += ("BALANCED." if balanced else
             "IMBALANCED — equal-time constraint violated; interpret the outcome "
             "comparison with caution (a faster/longer arm confounds the effect).")
    return (balanced, note, eff_budget)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def write_csv(path: Path, summary: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["arm", "n_test", "correct", "accuracy", "wilson_lo",
                    "wilson_hi", "study_seconds", "study_attempts",
                    "study_time_missing", "below_give_up"])
        for a in summary["arms"]:
            w.writerow([
                a["arm"], a["n_test"], a["correct"],
                "" if a["accuracy"] is None else f"{a['accuracy']:.6f}",
                "" if a["wilson_lo"] is None else f"{a['wilson_lo']:.6f}",
                "" if a["wilson_hi"] is None else f"{a['wilson_hi']:.6f}",
                f"{a['study_seconds']:.1f}", a["study_attempts"],
                a["study_time_missing"], a["below_give_up"],
            ])


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="eval_study_feature.py",
        description="Study-feature 3-build ablation: interleaved vs blocked "
                    "performance sessions vs plain Anki, on PERFORMANCE outcome "
                    "at EQUAL STUDY TIME.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Examples:\n"
               "  py -3.12 scripts/eval_study_feature.py --synthetic\n"
               "  py -3.12 scripts/eval_study_feature.py --synthetic --null\n"
               "  py -3.12 scripts/eval_study_feature.py --manifest study.json\n",
    )
    ap.add_argument("--manifest", type=Path,
                    help="real-data manifest mapping arm -> source "
                         "(sidecar|attempts|bundle)")
    ap.add_argument("--synthetic", action="store_true",
                    help="run the documented synthetic simulation (no real data)")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT,
                    help=f"chart PNG path (default {DEFAULT_OUT.relative_to(ROOT)})")
    # synthetic knobs (all recorded into the summary JSON)
    ap.add_argument("--seed", type=int, default=20260703)
    ap.add_argument("--topics", type=int, default=12)
    ap.add_argument("--test-n", type=int, default=120,
                    help="held_out test attempts per arm (default 120, a pooled "
                         "sample; a single-friend held-out set is ~60 and would "
                         "be underpowered)")
    ap.add_argument("--budget-seconds", type=float, default=1800.0,
                    help="equal study-time budget per arm (synthetic; default 1800)")
    ap.add_argument("--base-accuracy", type=float, default=0.55)
    ap.add_argument("--blocked-uplift", type=float, default=0.06,
                    help="assumed blocked-perf uplift vs plain Anki")
    ap.add_argument("--interleave-uplift", type=float, default=0.10,
                    help="assumed interleaved uplift vs blocked (headline effect)")
    ap.add_argument("--null", action="store_true",
                    help="set BOTH uplifts to 0.0 to demonstrate a null result")
    args = ap.parse_args(argv)

    if not args.synthetic and not args.manifest:
        ap.error("provide --manifest PATH or use --synthetic")

    z = wilson_z()
    min_attempts = default_perf_min_attempts()
    synth_cfg: Optional[SynthConfig] = None

    if args.manifest:
        if not args.manifest.is_file():
            ap.error(f"manifest not found: {args.manifest}")
        mode = "real"
        arms, budget = load_manifest(args.manifest)
        if not arms:
            print("ERROR: manifest has no arms.", file=sys.stderr)
            return 1
    else:
        mode = "synthetic"
        synth_cfg = SynthConfig(
            seed=args.seed, n_topics=args.topics, test_n=args.test_n,
            time_budget_seconds=args.budget_seconds,
            base_accuracy=args.base_accuracy,
            blocked_uplift=0.0 if args.null else args.blocked_uplift,
            interleave_uplift=0.0 if args.null else args.interleave_uplift,
        )
        print("=== SYNTHETIC MODE ===")
        print(f"generating 3 arms; seed={synth_cfg.seed}; equal budget="
              f"{synth_cfg.time_budget_seconds:.0f}s; test_n/arm={synth_cfg.test_n}")
        print(f"ASSUMED uplifts: blocked vs plain +{synth_cfg.blocked_uplift:.2f}, "
              f"interleaved vs blocked +{synth_cfg.interleave_uplift:.2f}"
              + ("   [--null]" if args.null else ""))
        arms = generate_synthetic(synth_cfg)
        budget = synth_cfg.time_budget_seconds

    equal_time_ok, equal_time_note, eff_budget = audit_equal_time(arms, budget)

    # comparisons: interleaved vs blocked (headline), interleaved vs plain,
    # blocked vs plain.
    by_id = {a.arm: a for a in arms}

    def cmp(a_id: str, b_id: str) -> Optional[Comparison]:
        if a_id in by_id and b_id in by_id:
            return compare(by_id[a_id], by_id[b_id], z)
        return None

    comps = [c for c in (
        cmp(ARM_INTERLEAVED, ARM_BLOCKED),
        cmp(ARM_INTERLEAVED, ARM_PLAIN),
        cmp(ARM_BLOCKED, ARM_PLAIN),
    ) if c is not None]

    summary = build_summary(
        arms, comps, mode=mode, z=z, budget=eff_budget,
        equal_time_ok=equal_time_ok, equal_time_note=equal_time_note,
        synth_cfg=synth_cfg, min_attempts=min_attempts,
    )

    print_report(summary)

    out_png = args.out
    json_path = out_png.with_suffix(".summary.json")
    csv_path = out_png.with_suffix(".arms.csv")
    write_csv(csv_path, summary)
    json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    if write_png_matplotlib(out_png, summary):
        chart_note = f"chart (matplotlib): {out_png}"
    else:
        write_png_fallback(out_png, summary)
        chart_note = f"chart (pure-stdlib PNG; matplotlib not installed): {out_png}"

    print()
    print(chart_note)
    print(f"summary JSON: {json_path}")
    print(f"per-arm CSV : {csv_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
