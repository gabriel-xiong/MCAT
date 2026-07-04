#!/usr/bin/env py -3.12
"""Eval + baseline + attribution harness for the AI post-answer explainer.

Runs BEFORE any student sees an explanation. It:
  1. Generates a per-choice explanation for EVERY wrong-answer path (every
     distractor of every held_out question) using the offline AI provider.
  2. Scores three things against ground truth (answer key + choice_diagnosis):
       - accuracy            : names the right choice AND is source-grounded AND
                               does not contradict the key.
       - wrong_answer_rate   : names a WRONG correct choice / would reinforce the
                               student's wrong pick.
       - choice_specificity  : correctly names the error mode for the CHOSEN
                               distractor (checkable vs choice_diagnosis) AND the
                               feedback varies across a question's distractors.
                               This is the headline differentiation metric.
  3. Enforces a PRE-REGISTERED cutoff (constants below, set before any results).
     A per-item safety gate blocks any explanation that is ungrounded or names
     the wrong choice and replaces it with the static explanation (AI-off). If
     the aggregate fails the cutoff, the whole AI path is disabled (fall back to
     static) — the app still scores with AI off.
  4. Compares AI vs two simpler baselines (static explanation; TF-IDF retrieval
     from source) and prints a seeded side-by-side.
  5. Runs a leakage check (reuses scripts/eval_leakage.py) so the eval/gold sets
     do not leak across dev/held_out.

All numbers use the deterministic OFFLINE provider (no network). Labelled as such.

Run:  py -3.12 scripts/ai_eval_explanations.py
"""

from __future__ import annotations

import json
import math
import random
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

try:  # UTF-8 for chemistry unicode on Windows consoles
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

from ai_explain import (  # noqa: E402
    LETTERS,
    Explanation,
    OfflineDeterministicProvider,
    diagnose_choice,
    live_provider_from_env,
    load_backing_concepts,
    load_questions,
    load_topic_names,
    safety_block,
    static_fallback_explanation,
)

# =========================================================================== #
# PRE-REGISTERED CUTOFF — set BEFORE looking at any results (honesty rule).
# The AI path is only allowed to serve students if it clears ALL of these on the
# held_out split. Otherwise the app falls back to the static explanation.
# =========================================================================== #
CUTOFF = {
    "min_accuracy": 0.90,          # must correctly identify the right choice
    "max_wrong_answer_rate": 0.05,  # must not misinform about the answer
    "min_grounding_rate": 1.00,     # EVERY output must cite a named source
    "min_choice_specificity": 0.80,  # must actually be per-choice differentiated
}
SEED = 20260702  # deterministic side-by-side sampling

STOPWORDS = {
    "the", "a", "an", "of", "to", "in", "is", "are", "and", "or", "for", "on",
    "at", "by", "it", "its", "as", "be", "this", "that", "with", "from", "into",
    "than", "then", "which", "what", "when", "not", "no", "so", "if", "will",
    "can", "does", "do", "has", "have", "one", "two", "you", "your",
}


# --------------------------------------------------------------------------- #
# Text utilities
# --------------------------------------------------------------------------- #
def normalize(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return " ".join(text.split())


def tokens(text: str) -> list[str]:
    return [t for t in normalize(text).split() if t and t not in STOPWORDS]


def token_set(text: str) -> set[str]:
    return set(tokens(text))


def overlap_ratio(needle: str, haystack: str) -> float:
    """Fraction of needle content-tokens present in haystack."""
    n = token_set(needle)
    if not n:
        return 0.0
    h = token_set(haystack)
    return len(n & h) / len(n)


# --------------------------------------------------------------------------- #
# Baselines (the "simpler methods" the AI must beat)
# --------------------------------------------------------------------------- #
def static_explanation_text(q: dict) -> str:
    """Baseline 1 + AI-OFF fallback: the static per-question correct-answer
    rationale. Owned by a sibling worker as q['explanation']; if not present yet,
    synthesize a correct-answer statement so the app still scores with AI off.
    Note: this is CHOICE-AGNOSTIC by construction — same text no matter which
    distractor the student picked.
    """
    ci = LETTERS.index(q["correct"])
    correct = f"{q['correct']} ({q['choices'][ci]})"
    expl = q.get("explanation")
    if expl:
        return str(expl)
    return (
        f"The correct answer is {correct}. See the cited source for the "
        f"full rationale."
    )


class TfidfSourceRetriever:
    """Baseline 2: keyword/vector search over the source-derived concept corpus.

    Corpus = backing memory concepts (from build_flashcards, i.e. distilled from
    the named sources). Query = stem + the chosen choice. Returns the top-1
    concept by TF-IDF cosine similarity. This is a legit 'simpler method': it can
    surface a relevant fact, but it cannot diagnose the SPECIFIC chosen distractor
    or name its misconception/trap.
    """

    def __init__(self, backing: dict[str, list[str]]):
        # Deduplicate concepts into a corpus.
        corpus = sorted({c for concepts in backing.values() for c in concepts})
        self.docs = corpus
        self.doc_tokens = [tokens(d) for d in corpus]
        df: dict[str, int] = {}
        for toks in self.doc_tokens:
            for t in set(toks):
                df[t] = df.get(t, 0) + 1
        n = max(1, len(corpus))
        self.idf = {t: math.log(n / (1 + c)) + 1.0 for t, c in df.items()}
        self.doc_vecs = [self._vec(toks) for toks in self.doc_tokens]

    def _vec(self, toks: list[str]) -> dict[str, float]:
        tf: dict[str, float] = {}
        for t in toks:
            tf[t] = tf.get(t, 0.0) + 1.0
        return {t: c * self.idf.get(t, 1.0) for t, c in tf.items()}

    @staticmethod
    def _cos(a: dict[str, float], b: dict[str, float]) -> float:
        if not a or not b:
            return 0.0
        common = set(a) & set(b)
        num = sum(a[t] * b[t] for t in common)
        na = math.sqrt(sum(v * v for v in a.values()))
        nb = math.sqrt(sum(v * v for v in b.values()))
        return num / (na * nb) if na and nb else 0.0

    def retrieve(self, query: str) -> str:
        if not self.docs:
            return ""
        qv = self._vec(tokens(query))
        best_i, best_s = 0, -1.0
        for i, dv in enumerate(self.doc_vecs):
            s = self._cos(qv, dv)
            if s > best_s:
                best_i, best_s = i, s
        return self.docs[best_i]


# --------------------------------------------------------------------------- #
# Scoring
# --------------------------------------------------------------------------- #
def names_error_mode(expl: Explanation, q: dict, chosen_index: int) -> bool:
    """Does the feedback correctly name the error mode for THIS chosen distractor,
    checked against choice_diagnosis (the human-authored ground truth)?"""
    mode, entry = diagnose_choice(q, chosen_index)
    text = normalize(expl.why_wrong + " " + expl.next_action)
    if mode == "content_gap":
        misc = entry.get("misconception", "") if entry else ""
        # The feedback must actually reproduce the specific misconception.
        return overlap_ratio(misc, expl.why_wrong) >= 0.6
    if mode.startswith("trap:"):
        trap = mode.split(":", 1)[1]
        return trap in text
    if mode == "near_miss":
        return "near miss" in text or "no single" in text
    if mode == "passage_mapping":
        # Choice-aware passage feedback: must reference the passage AND be tied to
        # the specific chosen choice text.
        chose_txt = q["choices"][chosen_index]
        return "passage" in text and overlap_ratio(chose_txt, expl.why_wrong) >= 0.3
    return False


def identifies_correct(asserted_letter: str, q: dict) -> bool:
    return asserted_letter == q["correct"]


def build_pairs(held: list[dict]) -> list[tuple[dict, int]]:
    """Every (question, wrong-choice-index) path a student could take."""
    pairs = []
    for q in held:
        ci = LETTERS.index(q["correct"])
        for idx in range(len(q["choices"])):
            if idx != ci:
                pairs.append((q, idx))
    return pairs


# --------------------------------------------------------------------------- #
# Safety gate + cutoff enforcement
# --------------------------------------------------------------------------- #
# `safety_block` is the canonical gate, imported from ai_explain so the serving
# path and this eval enforce identical rules (ungrounded / wrong-choice -> block).


def gate_self_test(provider: OfflineDeterministicProvider, q: dict) -> bool:
    """Prove the gate is real: corrupt an output and confirm it gets blocked."""
    from dataclasses import replace

    ok = provider.explain(q, (LETTERS.index(q["correct"]) + 1) % 4)
    if safety_block(ok, q):
        return False  # a clean output should NOT be blocked
    bad = replace(ok, asserted_correct_letter="Z")  # wrong choice -> block
    ungrounded = replace(ok, source_name="")  # no source -> block
    return safety_block(bad, q) and safety_block(ungrounded, q)


# --------------------------------------------------------------------------- #
# Metric computation for a provider
# --------------------------------------------------------------------------- #
def eval_ai(provider, pairs, questions_by_id):
    """Score the (offline OR live) provider through the SAFETY GATE.

    Every path runs the provider, then the gate. If the provider errors (live
    model / network / bad JSON) or the gate blocks the output (ungrounded or
    wrong choice), the SERVED explanation is the static fallback — exactly what
    the student would see. Metrics are computed on what is served, so a live
    model can never push numbers below the static floor, and the numbers are the
    HONEST measured behavior of the provider (not by construction).
    """
    per_q_texts: dict[str, list[str]] = {}
    records = []
    blocked = errored = 0
    for q, idx in pairs:
        expl = None
        try:
            expl = provider.explain(q, idx)
        except Exception:
            errored += 1
        was_blocked = expl is None or safety_block(expl, q)
        if was_blocked:
            blocked += 1
            served = static_fallback_explanation(q, idx)  # gate -> static
        else:
            served = expl
        per_q_texts.setdefault(q["id"], []).append(served.why_wrong)
        records.append((q, idx, served))

    def q_varies(qid: str) -> bool:
        texts = per_q_texts[qid]
        return len(set(texts)) == len(texts)

    n = len(records)
    acc = wrong = grounded = spec = 0
    for q, idx, expl in records:
        if expl.is_grounded:
            grounded += 1
        if identifies_correct(expl.asserted_correct_letter, q):
            acc += 1
        else:
            wrong += 1
        if names_error_mode(expl, q, idx) and q_varies(q["id"]):
            spec += 1
    return {
        "n": n,
        "accuracy": acc / n,
        "wrong_answer_rate": wrong / n,
        "grounding_rate": grounded / n,
        "choice_specificity": spec / n,
        "blocked": blocked,
        "errored": errored,
        "variation_rate": sum(q_varies(qid) for qid in per_q_texts)
        / len(per_q_texts),
    }


def eval_static(pairs):
    per_q_texts: dict[str, list[str]] = {}
    records = []
    for q, idx in pairs:
        text = static_explanation_text(q)
        per_q_texts.setdefault(q["id"], []).append(text)
        records.append((q, idx, text))

    def q_varies(qid: str) -> bool:
        texts = per_q_texts[qid]
        return len(set(texts)) == len(texts)

    n = len(records)
    acc = wrong = grounded = spec = 0
    for q, idx, text in records:
        grounded += 1  # we always attach the question's named source
        # Static states the correct answer -> identifies correct, never wrong.
        acc += 1
        # Choice-specificity: static cannot name the chosen distractor's error
        # mode and never varies across choices -> structurally ~0.
        mode, entry = diagnose_choice(q, idx)
        named = False
        if mode == "content_gap" and entry:
            named = overlap_ratio(entry.get("misconception", ""), text) >= 0.6
        if named and q_varies(q["id"]):
            spec += 1
    return {
        "n": n,
        "accuracy": acc / n,
        "wrong_answer_rate": wrong / n,
        "grounding_rate": grounded / n,
        "choice_specificity": spec / n,
        "blocked": 0,
        "variation_rate": sum(q_varies(qid) for qid in per_q_texts)
        / len(per_q_texts),
    }


def eval_tfidf(retriever, pairs):
    per_q_texts: dict[str, list[str]] = {}
    records = []
    for q, idx in pairs:
        query = q["stem"].split("QUESTION")[-1] + " " + q["choices"][idx]
        text = retriever.retrieve(query)
        per_q_texts.setdefault(q["id"], []).append(text)
        records.append((q, idx, text))

    def q_varies(qid: str) -> bool:
        texts = per_q_texts[qid]
        return len(set(texts)) == len(texts)

    n = len(records)
    acc = wrong = grounded = spec = 0
    for q, idx, text in records:
        grounded += 1  # retrieved from source corpus (attributable to source)
        ci = LETTERS.index(q["correct"])
        correct_txt = q["choices"][ci]
        chosen_txt = q["choices"][idx]
        ov_correct = overlap_ratio(correct_txt, text)
        ov_chosen = overlap_ratio(chosen_txt, text)
        # "Identifies correct" only if retrieved text aligns with the correct
        # choice more than the chosen distractor.
        if ov_correct > ov_chosen and ov_correct > 0:
            acc += 1
        elif ov_chosen > ov_correct and ov_chosen > 0:
            wrong += 1  # would reinforce the student's wrong pick
        # Never names the error mode (no misconception/trap vocabulary).
        mode, entry = diagnose_choice(q, idx)
        named = False
        if mode == "content_gap" and entry:
            named = overlap_ratio(entry.get("misconception", ""), text) >= 0.6
        if named and q_varies(q["id"]):
            spec += 1
    return {
        "n": n,
        "accuracy": acc / n,
        "wrong_answer_rate": wrong / n,
        "grounding_rate": grounded / n,
        "choice_specificity": spec / n,
        "blocked": 0,
        "variation_rate": sum(q_varies(qid) for qid in per_q_texts)
        / len(per_q_texts),
    }


# --------------------------------------------------------------------------- #
# Goldset validation (dev split) + leakage check
# --------------------------------------------------------------------------- #
def validate_goldset(provider, questions_by_id) -> tuple[int, int, list[str]]:
    path = DATA / "ai-explainer-goldset.json"
    if not path.exists():
        return 0, 0, ["(no goldset file)"]
    gold = json.loads(path.read_text(encoding="utf-8"))["items"]
    passed = 0
    fails: list[str] = []
    for item in gold:
        q = questions_by_id.get(item["qid"])
        if q is None:
            fails.append(f"{item['qid']}: not found")
            continue
        idx = LETTERS.index(item["chosen_letter"])
        expl = provider.explain(q, idx)
        mode_ok = expl.error_mode == item["expected_error_mode"]
        mention_ok = item["must_mention"].lower() in normalize(
            expl.why_wrong + " " + expl.next_action
        )
        if mode_ok and mention_ok:
            passed += 1
        else:
            fails.append(
                f"{item['qid']}/{item['chosen_letter']}: "
                f"mode={expl.error_mode} (want {item['expected_error_mode']}), "
                f"mention={mention_ok}"
            )
    return passed, len(gold), fails


def source_traceability(held: list[dict]) -> dict:
    """Coverage of the spec claim "every AI output traces back to a named source".

    Every offline/live explanation attaches the question's own ``source_name`` /
    ``source_url`` / ``source_location`` (see ai_explain.Explanation), and the
    safety gate BLOCKS any output whose ``source_name`` is empty. So the held_out
    bank's source coverage is exactly the coverage of the served explanations.
    Reports, over the held_out questions:
      * has_source_name     — a NAMED source is present (the hard grounding rule)
      * has_source_url      — a resolvable URL is present (nice-to-have)
      * has_source_location — a page/section locator is present
      * fully_grounded      — source_name AND (source_url OR source_location)
    """
    n = len(held)
    has_name = sum(1 for q in held if (q.get("source_name") or "").strip())
    has_url = sum(1 for q in held if (q.get("source_url") or "").strip())
    has_loc = sum(1 for q in held if (q.get("source_location") or "").strip())
    fully = sum(
        1
        for q in held
        if (q.get("source_name") or "").strip()
        and ((q.get("source_url") or "").strip() or (q.get("source_location") or "").strip())
    )
    missing_name = [q["id"] for q in held if not (q.get("source_name") or "").strip()]
    missing_url = [q["id"] for q in held if not (q.get("source_url") or "").strip()]
    return {
        "n_held_out": n,
        "has_source_name": has_name,
        "has_source_url": has_url,
        "has_source_location": has_loc,
        "fully_grounded": fully,
        "source_name_rate": (has_name / n) if n else 0.0,
        "source_url_rate": (has_url / n) if n else 0.0,
        "source_location_rate": (has_loc / n) if n else 0.0,
        "fully_grounded_rate": (fully / n) if n else 0.0,
        "missing_source_name_ids": missing_name,
        "missing_source_url_ids": missing_url,
    }


def leakage_check(questions) -> tuple[bool, list[str]]:
    """Reuse the project's stem-dup logic + confirm goldset (dev) does not leak
    into held_out (by id or by near-duplicate stem)."""
    import eval_leakage  # reuse normalize + convention

    dev = [q for q in questions if q.get("split") == "dev"]
    held = [q for q in questions if q.get("split") == "held_out"]
    held_ids = {q["id"] for q in held}
    held_norm = {q["id"]: eval_leakage.normalize(q["stem"]) for q in held}

    issues: list[str] = []
    # 1) project-wide dev vs held_out stem leakage
    for q in dev:
        dn = eval_leakage.normalize(q["stem"])
        for hid, hn in held_norm.items():
            if dn and hn and (dn == hn or dn in hn or hn in dn):
                issues.append(f"dev {q['id']} ~ held_out {hid}")

    # 2) goldset must be dev-only and must not duplicate held_out
    gpath = DATA / "ai-explainer-goldset.json"
    if gpath.exists():
        gold = json.loads(gpath.read_text(encoding="utf-8"))["items"]
        qby = {q["id"]: q for q in questions}
        for item in gold:
            qid = item["qid"]
            if qid in held_ids:
                issues.append(f"goldset item {qid} is in held_out (LEAK)")
            q = qby.get(qid)
            if q and q.get("split") != "dev":
                issues.append(f"goldset item {qid} split={q.get('split')} (not dev)")
            if q:
                gn = eval_leakage.normalize(q["stem"])
                for hid, hn in held_norm.items():
                    if gn and hn and (gn == hn or gn in hn or hn in gn):
                        issues.append(f"goldset {qid} ~ held_out {hid}")
    return (len(issues) == 0), issues


# --------------------------------------------------------------------------- #
# Reporting
# --------------------------------------------------------------------------- #
def fmt_row(label: str, m: dict) -> str:
    return (
        f"  {label:<26} acc={m['accuracy']:.3f}  "
        f"wrong={m['wrong_answer_rate']:.3f}  "
        f"grounded={m['grounding_rate']:.3f}  "
        f"choice_spec={m['choice_specificity']:.3f}  "
        f"varies={m['variation_rate']:.3f}"
    )


def check_cutoff(m: dict) -> tuple[bool, list[str]]:
    reasons = []
    if m["accuracy"] < CUTOFF["min_accuracy"]:
        reasons.append(f"accuracy {m['accuracy']:.3f} < {CUTOFF['min_accuracy']}")
    if m["wrong_answer_rate"] > CUTOFF["max_wrong_answer_rate"]:
        reasons.append(
            f"wrong_answer_rate {m['wrong_answer_rate']:.3f} > "
            f"{CUTOFF['max_wrong_answer_rate']}"
        )
    if m["grounding_rate"] < CUTOFF["min_grounding_rate"]:
        reasons.append(
            f"grounding_rate {m['grounding_rate']:.3f} < "
            f"{CUTOFF['min_grounding_rate']}"
        )
    if m["choice_specificity"] < CUTOFF["min_choice_specificity"]:
        reasons.append(
            f"choice_specificity {m['choice_specificity']:.3f} < "
            f"{CUTOFF['min_choice_specificity']}"
        )
    return (len(reasons) == 0), reasons


def side_by_side(provider, retriever, held, n=4):
    rng = random.Random(SEED)
    sample = rng.sample(held, min(n, len(held)))
    print("\n=== Seeded side-by-side (seed="
          f"{SEED}) — AI vs baselines on one chosen distractor each ===")
    for q in sample:
        ci = LETTERS.index(q["correct"])
        # pick the first wrong choice deterministically
        idx = next(i for i in range(len(q["choices"])) if i != ci)
        ai = provider.explain(q, idx)
        stem_tail = q["stem"].splitlines()[-1][:90]
        print(f"\nQ {q['id']} ({q['topic_id']}) — student chose {LETTERS[idx]}")
        print(f"  stem: {stem_tail}")
        print(f"  [AI]     {ai.error_mode}: {ai.why_wrong}")
        print(f"           -> {ai.next_action}")
        print(f"  [static] {static_explanation_text(q)}")
        query = q["stem"].split("QUESTION")[-1] + " " + q["choices"][idx]
        print(f"  [tfidf]  {retriever.retrieve(query)}")


def _metrics_row(method: str, m: dict) -> dict:
    """Flatten a method's metrics into a JSON/CSV-friendly row."""
    return {
        "method": method,
        "n_paths": m["n"],
        "accuracy": round(m["accuracy"], 4),
        "wrong_answer_rate": round(m["wrong_answer_rate"], 4),
        "grounding_rate": round(m["grounding_rate"], 4),
        "choice_specificity": round(m["choice_specificity"], 4),
        "variation_rate": round(m["variation_rate"], 4),
        "blocked_to_static": m.get("blocked", 0),
        "provider_errors": m.get("errored", 0),
    }


def write_artifacts(
    out_stem: Path,
    *,
    provider_label: str,
    src: str,
    n_held_out: int,
    n_paths: int,
    cutoff: dict,
    cutoff_passed: bool,
    cutoff_reasons: list[str],
    gate_pass: bool,
    ai_m: dict,
    static_m: dict,
    tfidf_m: dict,
    gap: float,
    trace: dict,
    leakage_ok: bool,
    leakage_issues: list[str],
    goldset_passed: int,
    goldset_total: int,
) -> tuple[Path, Path]:
    """Emit a machine-readable ``.summary.json`` + ``.baselines.csv`` under
    ``docs/artifacts/`` (mirrors eval_memory.py / eval_study_feature.py). Returns
    the two written paths. This is the reproducible evidence artifact — every
    number in docs/AI-FEATURE.md §5 comes from here."""
    import csv
    import datetime as _dt

    out_stem.parent.mkdir(parents=True, exist_ok=True)
    rows = [
        _metrics_row("ai", ai_m),
        _metrics_row("static", static_m),
        _metrics_row("tfidf", tfidf_m),
    ]
    summary = {
        "eval": "ai_post_answer_explainer",
        "generated_utc": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
        "provider_under_test": provider_label,
        "provider_mode": src,  # "offline" | "live"
        "numbers_are": (
            "offline_deterministic_by_construction" if src == "offline" else "live_measured"
        ),
        "eval_split": "held_out",
        "n_held_out_questions": n_held_out,
        "n_wrong_answer_paths": n_paths,
        "pre_registered_cutoff": cutoff,
        "cutoff_decision": {
            "passed": cutoff_passed,
            "reasons_if_failed": cutoff_reasons,
            "ai_path": "ENABLED" if cutoff_passed else "DISABLED (falls back to static)",
        },
        "safety_gate_self_test": "PASS" if gate_pass else "FAIL",
        "methods": {
            "ai": _metrics_row("ai", ai_m),
            "static": _metrics_row("static", static_m),
            "tfidf": _metrics_row("tfidf", tfidf_m),
        },
        "headline_differentiation_gap_ai_minus_best_baseline": round(gap, 4),
        "source_traceability": trace,
        "leakage_check": {"ok": leakage_ok, "issues": leakage_issues},
        "goldset_validation": {"passed": goldset_passed, "total": goldset_total},
        "reproduce": "py -3.12 scripts/ai_eval_explanations.py",
    }
    json_path = out_stem.with_suffix(".summary.json")
    json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    csv_path = out_stem.with_suffix(".baselines.csv")
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    return json_path, csv_path


def main(argv: list[str] | None = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(
        description="AI post-answer explainer eval / baseline / attribution."
    )
    ap.add_argument(
        "--provider",
        choices=["offline", "live"],
        default="offline",
        help="offline = deterministic, reproducible, no network (default). "
        "live = env-configured LLM (MCAT_LLM_PROVIDER=...); numbers are real, "
        "gated, and fall back to static on any failure.",
    )
    ap.add_argument(
        "--out",
        type=Path,
        default=ROOT / "docs" / "artifacts" / "ai-explainer-eval",
        help="artifact path STEM (default docs/artifacts/ai-explainer-eval); "
        "writes <stem>.summary.json + <stem>.baselines.csv.",
    )
    ap.add_argument(
        "--no-write",
        action="store_true",
        help="do not write the machine-readable artifacts (console only).",
    )
    args = ap.parse_args(argv)

    questions = load_questions()
    questions_by_id = {q["id"]: q for q in questions}
    held = [q for q in questions if q.get("split") == "held_out"]
    topic_names = load_topic_names()
    backing = load_backing_concepts()
    offline_provider = OfflineDeterministicProvider(
        topic_names=topic_names, backing=backing
    )
    retriever = TfidfSourceRetriever(backing)

    provider = offline_provider
    provider_label = "offline_deterministic (NO network, reproducible)"
    if args.provider == "live":
        live = live_provider_from_env()
        if live is None:
            print(
                "ERROR: --provider live requires MCAT_LLM_PROVIDER (openai|"
                "anthropic) + a key in the environment. AI is OFF; nothing to "
                "evaluate live. Run without --provider live for the offline eval."
            )
            return 2
        provider = live
        provider_label = f"LIVE {live.model_label} (network; real numbers)"

    has_expl = sum(1 for q in questions if q.get("explanation"))

    print("=" * 72)
    print("AI POST-ANSWER EXPLAINER — EVAL / BASELINE / ATTRIBUTION HARNESS")
    print("=" * 72)
    print(f"Provider under test : {provider_label}")
    print(f"Held-out questions  : {len(held)}  (eval split = project 'held_out')")
    print(f"Static explanation  : {'present' if has_expl else 'NOT YET PRESENT'} "
          f"in questions.json (sibling worker owns q['explanation'])")
    print("\nPRE-REGISTERED CUTOFF (declared before results):")
    for k, v in CUTOFF.items():
        print(f"  {k} = {v}")

    pairs = build_pairs(held)
    print(f"\nEvaluated wrong-answer paths (held_out distractors): {len(pairs)}")

    # gate self-test (always exercised on the deterministic provider — it tests
    # the GATE logic, not the model, and must never make a network call).
    gpass = gate_self_test(offline_provider, held[0])
    print(f"Safety-gate self-test (blocks wrong-choice + ungrounded): "
          f"{'PASS' if gpass else 'FAIL'}")

    ai_m = eval_ai(provider, pairs, questions_by_id)
    static_m = eval_static(pairs)
    tfidf_m = eval_tfidf(retriever, pairs)

    src = "live" if args.provider == "live" else "offline"
    ai_label = f"AI ({src} explainer)"
    print(f"\n--- RESULTS on held_out (all metrics, {src}) ---")
    print(fmt_row(ai_label, ai_m))
    print(fmt_row("baseline: static expl.", static_m))
    print(fmt_row("baseline: TF-IDF source", tfidf_m))
    print(f"\n  AI outputs blocked by safety gate -> static: {ai_m['blocked']}"
          f"  (provider errors -> static: {ai_m.get('errored', 0)})")

    passed, reasons = check_cutoff(ai_m)
    print(f"\nCUTOFF DECISION: {'PASS — AI path ENABLED' if passed else 'FAIL'}")
    if not passed:
        print("  AI path DISABLED; app falls back to static explanation. Reasons:")
        for r in reasons:
            print(f"   - {r}")

    # Headline differentiation gap
    gap = ai_m["choice_specificity"] - max(
        static_m["choice_specificity"], tfidf_m["choice_specificity"]
    )
    print("\n--- HEADLINE: AI beats baseline on per-choice differentiation ---")
    print(f"  choice_specificity  AI={ai_m['choice_specificity']:.3f}  "
          f"static={static_m['choice_specificity']:.3f}  "
          f"tfidf={tfidf_m['choice_specificity']:.3f}")
    print(f"  differentiation gap (AI - best baseline) = {gap:+.3f}")
    print(f"  wrong-answer rate    AI={ai_m['wrong_answer_rate']:.3f}  "
          f"static={static_m['wrong_answer_rate']:.3f}  "
          f"tfidf={tfidf_m['wrong_answer_rate']:.3f}")

    # Goldset (dev) validation — always on the deterministic provider: it checks
    # exact error-mode + required-mention against hand labels and must not depend
    # on (or spend) live calls.
    passed_g, total_g, fails = validate_goldset(offline_provider, questions_by_id)
    print(f"\n--- Goldset validation (dev split, hand-labeled) ---")
    print(f"  {passed_g}/{total_g} gold items matched expected error mode + mention")
    for f in fails:
        print(f"   - {f}")

    # Source traceability — "every AI output traces back to a named source".
    trace = source_traceability(held)
    print("\n--- Source traceability (held_out; every AI output cites a named source) ---")
    print(f"  source_name present   : {trace['has_source_name']}/{trace['n_held_out']} "
          f"({trace['source_name_rate']:.1%})  <- hard grounding rule (gate blocks empties)")
    print(f"  source_location present: {trace['has_source_location']}/{trace['n_held_out']} "
          f"({trace['source_location_rate']:.1%})")
    print(f"  source_url present     : {trace['has_source_url']}/{trace['n_held_out']} "
          f"({trace['source_url_rate']:.1%})")
    print(f"  fully grounded (name + url/loc): {trace['fully_grounded']}/{trace['n_held_out']} "
          f"({trace['fully_grounded_rate']:.1%})")
    if trace["missing_source_url_ids"]:
        preview = ", ".join(trace["missing_source_url_ids"][:8])
        more = "" if len(trace["missing_source_url_ids"]) <= 8 else \
            f" (+{len(trace['missing_source_url_ids']) - 8} more)"
        print(f"  (no source_url, but named+located): {preview}{more}")

    # Leakage
    ok, issues = leakage_check(questions)
    print(f"\n--- Leakage check (dev vs held_out; goldset must be dev-only) ---")
    print(f"  {'OK — no leakage' if ok else 'FAILED'}")
    for i in issues:
        print(f"   - {i}")

    # Machine-readable artifact (docs/artifacts/) — the reproducible evidence.
    if not args.no_write:
        json_path, csv_path = write_artifacts(
            args.out,
            provider_label=provider_label,
            src=src,
            n_held_out=len(held),
            n_paths=len(pairs),
            cutoff=CUTOFF,
            cutoff_passed=passed,
            cutoff_reasons=reasons,
            gate_pass=gpass,
            ai_m=ai_m,
            static_m=static_m,
            tfidf_m=tfidf_m,
            gap=gap,
            trace=trace,
            leakage_ok=ok,
            leakage_issues=issues,
            goldset_passed=passed_g,
            goldset_total=total_g,
        )
        print(f"\n--- Artifacts written ---")
        print(f"  {json_path.relative_to(ROOT)}")
        print(f"  {csv_path.relative_to(ROOT)}")

    # Side-by-side uses the deterministic provider so the illustrative sample is
    # stable and network-free even when the headline metrics are from --live.
    side_by_side(offline_provider, retriever, held)

    print("\n" + "=" * 72)
    final_ok = passed and ok and gap > 0 and gpass and (
        passed_g == total_g if total_g else True
    )
    print(f"OVERALL: {'PASS' if final_ok else 'REVIEW NEEDED'} "
          f"(AI cutoff + no leakage + beats baseline + gate + goldset)")
    print("=" * 72)
    return 0 if final_ok else 1


if __name__ == "__main__":
    sys.exit(main())
