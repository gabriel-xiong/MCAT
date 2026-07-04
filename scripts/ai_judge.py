#!/usr/bin/env py -3.12
"""Cross-model LLM-as-judge for the AI follow-up Q&A gold set.

The follow-up feature under test generates answers with **OpenAI**
(``MCAT_LLM_PROVIDER``). To grade those answers without circularity, the judge
here MUST be a *different model family* — by default **Anthropic Claude**
(``MCAT_JUDGE_PROVIDER`` / ``MCAT_JUDGE_MODEL``). The judge scores each answer
against the human-validated ``fact_atoms`` (the rubric) plus the ``must_not_say``
list, returning per-atom coverage, per-phrase violations, an overall
``coverage_fraction`` for partial credit, and free-text notes.

Why cross-model (circularity):
  * If the same family both answered and judged, they would share blind spots and
    phrasing biases, inflating measured accuracy.
  * The rubric (``fact_atoms``) is human-validated, and the judge is a *third*
    party from a different family than the generator. The judge cannot silently
    rewrite the rubric — it only maps an answer onto fixed, validated atoms.

Seam / offline path:
  * ``judge_answer`` takes an injected ``call_model(prompt) -> str`` (same seam as
    ``ai_explain``), so it is fully testable with a mock and no network.
  * ``offline_judge_result`` produces a judge-shaped result from local token
    heuristics (no LLM), routed through the real ``parse_judge_result`` so the
    parsing/aggregation plumbing is exercised offline.
"""

from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import ai_explain as ax  # noqa: E402  (reuse provider callers + lazy SDK imports)

# Judge defaults: a DIFFERENT family than the OpenAI answer generator.
DEFAULT_JUDGE_PROVIDER = "anthropic"
DEFAULT_JUDGE_MODELS = {
    "anthropic": "claude-3-5-sonnet-latest",
    "openai": "gpt-4o-mini",
}

JUDGE_SYSTEM_PROMPT = (
    "You are a strict but fair grader for an MCAT tutoring answer. You are given "
    "a student's follow-up question, an AI tutor's ANSWER, a numbered list of "
    "validated FACT_ATOMS (the rubric of facts a correct answer should convey), "
    "and a MUST_NOT_SAY list (claims that are wrong).\n"
    "Grade the ANSWER against the rubric with these rules:\n"
    "  * An atom is COVERED if the answer conveys that fact, in ANY paraphrase or "
    "equivalent wording (numbers, symbols, or restated concepts all count). The "
    "answer need not quote the atom.\n"
    "  * A must_not_say phrase is VIOLATED only if the answer actually ASSERTS "
    "that wrong claim. If the answer NEGATES or refutes it (e.g. says it is NOT "
    "true, or states the opposite/correct version), that is NOT a violation — it "
    "is correct behavior.\n"
    "  * Do not reward fluent but off-topic text; judge only against the atoms.\n"
    "Return ONLY a compact JSON object with EXACTLY these keys:\n"
    '  "atoms_covered"          : array of booleans, one per fact atom, in order.\n'
    '  "must_not_say_violated"  : array of booleans, one per must_not_say phrase, '
    "in order (empty array if none).\n"
    '  "coverage_fraction"      : number in [0,1] = fraction of atoms covered.\n'
    '  "notes"                  : one short sentence explaining the grade.\n'
    "No markdown, no commentary outside the JSON."
)


@dataclass
class JudgeResult:
    """A judge's grade of one answer against one item's atoms/must_not_say."""

    atoms_covered: list[bool] = field(default_factory=list)
    must_not_say_violated: list[bool] = field(default_factory=list)
    coverage_fraction: float = 0.0
    notes: str = ""
    judge_label: str = ""

    @property
    def any_violation(self) -> bool:
        return any(self.must_not_say_violated)


def build_judge_prompt(
    followup_question: str,
    answer: str,
    fact_atoms: list[str],
    must_not_say: list[str],
) -> str:
    atoms_block = "\n".join(f"  [{i}] {a}" for i, a in enumerate(fact_atoms)) or "  (none)"
    mns_block = (
        "\n".join(f"  [{i}] {p}" for i, p in enumerate(must_not_say)) or "  (none)"
    )
    return (
        f"FOLLOWUP_QUESTION: {followup_question.strip()}\n\n"
        f"ANSWER:\n{(answer or '').strip()}\n\n"
        f"FACT_ATOMS ({len(fact_atoms)}):\n{atoms_block}\n\n"
        f"MUST_NOT_SAY ({len(must_not_say)}):\n{mns_block}\n\n"
        f"Grade the ANSWER. Return atoms_covered with exactly {len(fact_atoms)} "
        f"booleans and must_not_say_violated with exactly {len(must_not_say)} "
        "booleans, in order, plus coverage_fraction and notes."
    )


def _extract_json(raw: str) -> dict:
    text = (raw or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
        text = re.sub(r"\s*```$", "", text).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            return json.loads(m.group(0))
        raise


def _coerce_bools(value, n: int) -> list[bool]:
    """Coerce the model's list to exactly n booleans (pad False / truncate)."""
    out: list[bool] = []
    if isinstance(value, list):
        for v in value:
            if isinstance(v, bool):
                out.append(v)
            elif isinstance(v, (int, float)):
                out.append(bool(v))
            elif isinstance(v, str):
                out.append(v.strip().lower() in ("true", "yes", "1", "covered", "y"))
            else:
                out.append(False)
    out = out[:n]
    out += [False] * (n - len(out))
    return out


def parse_judge_result(
    raw: str,
    n_atoms: int,
    n_must_not: int,
    *,
    judge_label: str = "",
) -> JudgeResult:
    """Map the judge model's JSON into a JudgeResult, robust to sloppy output."""
    data = _extract_json(raw)
    atoms_covered = _coerce_bools(data.get("atoms_covered"), n_atoms)
    violated = _coerce_bools(data.get("must_not_say_violated"), n_must_not)

    cov = data.get("coverage_fraction")
    try:
        cov_f = float(cov)
    except (TypeError, ValueError):
        cov_f = (sum(atoms_covered) / n_atoms) if n_atoms else 0.0
    cov_f = max(0.0, min(1.0, cov_f))

    notes = str(data.get("notes", "")).strip()
    return JudgeResult(
        atoms_covered=atoms_covered,
        must_not_say_violated=violated,
        coverage_fraction=cov_f,
        notes=notes,
        judge_label=judge_label,
    )


def judge_answer(
    followup_question: str,
    answer: str,
    fact_atoms: list[str],
    must_not_say: list[str],
    call_model,
    *,
    judge_label: str = "",
) -> JudgeResult:
    """Judge ONE answer with an injected ``call_model(prompt) -> str`` callable."""
    prompt = build_judge_prompt(followup_question, answer, fact_atoms, must_not_say)
    raw = call_model(prompt)
    return parse_judge_result(
        raw, len(fact_atoms), len(must_not_say), judge_label=judge_label
    )


def offline_judge_result(
    followup_question: str,
    answer: str,
    fact_atoms: list[str],
    must_not_say: list[str],
    atom_scorer,
    must_not_scorer,
    *,
    judge_label: str = "offline-mock",
) -> JudgeResult:
    """Deterministic, network-free judge stand-in for testing the plumbing.

    Uses the caller's token heuristics (``atom_scorer`` / ``must_not_scorer``) to
    fabricate judge-shaped JSON, then runs it through the REAL
    ``parse_judge_result`` so the parse + aggregation path is exercised offline.
    This is NOT a substitute for a live cross-model judge; it only verifies wiring.
    """
    atoms_covered = [bool(atom_scorer(a, answer)) for a in fact_atoms]
    violated = [bool(must_not_scorer(p, answer)) for p in must_not_say]
    cov = (sum(atoms_covered) / len(atoms_covered)) if atoms_covered else 0.0
    payload = {
        "atoms_covered": atoms_covered,
        "must_not_say_violated": violated,
        "coverage_fraction": cov,
        "notes": "offline-mock judge (local token heuristic; no LLM was called)",
    }
    return parse_judge_result(
        json.dumps(payload),
        len(fact_atoms),
        len(must_not_say),
        judge_label=judge_label,
    )


def _resolve_judge_key(env: dict, provider: str) -> str:
    """Read the judge key from env ONLY. Never logged or defaulted.

    Prefers a judge-specific ``MCAT_JUDGE_API_KEY`` so the judge key stays
    distinct from the answer generator's key, then falls back to the provider's
    standard variable.
    """
    dedicated = env.get("MCAT_JUDGE_API_KEY")
    if dedicated:
        return dedicated
    var = "OPENAI_API_KEY" if provider == "openai" else "ANTHROPIC_API_KEY"
    return env.get(var, "")


def build_judge_caller_from_env(
    env: dict | None = None,
    *,
    answer_provider: str = "",
):
    """Build a judge ``call_model`` callable, enforcing CROSS-MODEL grading.

    Env contract:
      MCAT_JUDGE_PROVIDER : "anthropic" | "openai"  (default: anthropic)
      MCAT_JUDGE_MODEL    : judge model id (default: claude-3-5-sonnet-latest)
      key                 : MCAT_JUDGE_API_KEY, else ANTHROPIC_API_KEY /
                            OPENAI_API_KEY (read from env ONLY).

    ``answer_provider`` is the family that GENERATED the answers (e.g. "openai"
    for a live run). If the judge family equals it, the judge is REFUSED to avoid
    circularity.

    Returns ``(callable_or_None, label, note)``. On refusal / missing key the
    callable is None and ``note`` explains why (so the caller can fall back to the
    token-overlap scorer). SDKs are imported lazily inside the callable.
    """
    if env is None:
        try:
            from mcat_env import ensure_mcat_env_loaded

            ensure_mcat_env_loaded()
        except Exception:
            pass
        env = os.environ

    provider = (env.get("MCAT_JUDGE_PROVIDER") or DEFAULT_JUDGE_PROVIDER).strip().lower()
    if provider not in ("openai", "anthropic"):
        return None, "", (
            f"unknown MCAT_JUDGE_PROVIDER={provider!r} (expected anthropic|openai)."
        )

    answer_provider = (answer_provider or "").strip().lower()
    if answer_provider and provider == answer_provider:
        return None, "", (
            f"judge provider {provider!r} is the SAME family as the answer "
            "generator — refusing to judge (would be circular). Set "
            "MCAT_JUDGE_PROVIDER to a different family (e.g. anthropic)."
        )

    model = (env.get("MCAT_JUDGE_MODEL") or "").strip() or DEFAULT_JUDGE_MODELS[provider]
    key = _resolve_judge_key(env, provider)
    if not key:
        var = "OPENAI_API_KEY" if provider == "openai" else "ANTHROPIC_API_KEY"
        return None, "", (
            f"no judge API key for provider={provider}. Set MCAT_JUDGE_API_KEY or "
            f"{var} in the environment (never commit it)."
        )

    if provider == "openai":
        caller = ax._make_openai_caller(model, key, system_prompt=JUDGE_SYSTEM_PROMPT)
    else:
        caller = ax._make_anthropic_caller(model, key, system_prompt=JUDGE_SYSTEM_PROMPT)
    return caller, f"{provider}:{model}", ""
