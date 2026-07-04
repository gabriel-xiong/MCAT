#!/usr/bin/env py -3.12
"""AI follow-up Q&A after a missed performance question (opt-in, live LLM).

Students ask open-ended questions ("Why isn't the answer 12.0?") with full item
context. Uses the same env-driven provider seam as ``ai_explain``; no network
unless the caller passes a live ``call_model``.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:  # pragma: no cover
    pass

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import ai_explain as ax  # noqa: E402
from mcat_env import ensure_mcat_env_loaded  # noqa: E402

LETTERS = ax.LETTERS

QA_SYSTEM_PROMPT = (
    "You are an MCAT tutor answering a student's follow-up question after they "
    "missed a multiple-choice item. Use ONLY the supplied question context, "
    "explanation, choice diagnosis, and named SOURCE — do not invent facts or "
    "change the correct answer.\n"
    "Return ONLY a compact JSON object with these string keys:\n"
    '  "answer"       : a concise reply (2–5 sentences) to the follow-up.\n'
    '  "grounded"     : "yes" if every claim is traceable to the context/source.\n'
    "No markdown, no commentary outside the JSON."
)

# Directional-reasoning guardrail (general, no item-specific facts). Addresses the
# model's main observed failure: keeping the right framework but FLIPPING the
# direction of a cause->effect or a role assignment (e.g. which species handles
# added acid vs. added base; which of two options is larger / more temperature-
# sensitive; whether a quantity rises or falls). Injected into every follow-up
# prompt so it generalizes rather than patching specific items.
DIRECTIONAL_GUARDRAIL = (
    "DIRECTION CHECK — before you answer, verify the direction of every "
    "cause->effect link and every role assignment you state: which species/agent "
    "does which job (e.g. which one neutralizes added acid vs. added base), which "
    "quantity increases vs. decreases, and which of two options is larger, "
    "stronger, or more sensitive. For a counterfactual ('what if X changed') "
    "question, state which way the change goes and re-derive that direction from "
    "the underlying relationship before committing to it. If the question asks for "
    "a CONTRAST between two things, answer BOTH sides explicitly. Never assert a "
    "claim that reverses the true relationship."
)


@dataclass
class FollowUpAnswer:
    qid: str
    followup_question: str
    answer: str
    is_grounded: bool
    provider: str
    source_name: str

    def render(self) -> str:
        tag = "grounded" if self.is_grounded else "ungrounded"
        src = f" ({self.source_name})" if self.source_name else ""
        return f"[{tag}{src}] {self.answer}"


def build_followup_prompt(q: dict, chosen_index: int, followup_question: str) -> str:
    cd = q.get("choice_diagnosis")
    diag = cd[chosen_index] if cd and chosen_index < len(cd) else None
    cf = q.get("choice_feedback")
    chosen_fb = ""
    if isinstance(cf, list) and 0 <= chosen_index < len(cf):
        chosen_fb = (cf[chosen_index] or "").strip()
    return (
        f"STEM: {q['stem']}\n"
        f"CHOICES: {q['choices']}\n"
        f"CORRECT: {q['correct']}\n"
        f"STUDENT_CHOSE: {LETTERS[chosen_index]} "
        f"(\"{q['choices'][chosen_index]}\")\n"
        f"CHOICE_DIAGNOSIS_FOR_CHOSEN: {json.dumps(diag)}\n"
        f"PER_CHOICE_FEEDBACK_FOR_CHOSEN: {chosen_fb}\n"
        f"STATIC_EXPLANATION: {q.get('explanation', '')}\n"
        f"SECTION: {q.get('section')}\n"
        f"SOURCE: {q.get('source_name')} — {q.get('source_location')}\n"
        f"FOLLOWUP_QUESTION: {followup_question.strip()}\n"
        f"{DIRECTIONAL_GUARDRAIL}\n"
        "Answer the follow-up for THIS student and chosen distractor."
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


def parse_followup(raw: str, q: dict, followup_question: str, provider: str) -> FollowUpAnswer:
    data = _extract_json(raw)
    answer = str(data.get("answer", "")).strip()
    if not answer:
        raise ax.ProviderUnavailable("LLM follow-up missing answer field.")
    grounded_raw = str(data.get("grounded", "")).strip().lower()
    is_grounded = grounded_raw in ("yes", "true", "1") and bool(q.get("source_name"))
    return FollowUpAnswer(
        qid=q["id"],
        followup_question=followup_question.strip(),
        answer=answer,
        is_grounded=is_grounded,
        provider=provider,
        source_name=q.get("source_name", ""),
    )


def answer_followup(
    q: dict,
    chosen_index: int,
    followup_question: str,
    call_model,
    *,
    provider_label: str = "llm",
) -> FollowUpAnswer:
    """Call a live model for one follow-up. Raises ProviderUnavailable on failure."""
    if not (followup_question or "").strip():
        raise ax.ProviderUnavailable("Follow-up question is empty.")
    prompt = build_followup_prompt(q, chosen_index, followup_question)
    raw = call_model(prompt)
    return parse_followup(raw, q, followup_question, provider_label)


def live_followup_caller_from_env(env: dict | None = None, *, timeout: float | None = None):
    """Return (callable, label) for follow-up Q&A, or (None, '') when AI is OFF.

    The live caller carries the same client-side timeout ceiling as the
    explainer (``ai_explain.LLM_TIMEOUT_SECONDS`` / ``MCAT_LLM_TIMEOUT``), so a
    slow/hung follow-up call returns promptly instead of blocking indefinitely.
    """
    ensure_mcat_env_loaded()
    return ax.build_live_call_model_from_env(
        env, system_prompt=QA_SYSTEM_PROMPT, timeout=timeout
    )


@dataclass
class FollowUpResult:
    """Outcome of a follow-up attempt, so callers can DISTINGUISH why no answer
    was produced instead of collapsing every path to a bare ``None``.

    status:
      "answered" — a grounded answer is available in ``.answer``.
      "off"      — no live provider configured (AI OFF) / provider unusable.
      "blocked"  — the model answered but it wasn't source-grounded, so it was
                   legitimately declined (grounding guarantee preserved).
      "error"    — the provider/model call or the parse failed.
    """

    status: str
    answer: FollowUpAnswer | None = None
    detail: str = ""


def serve_followup_result(
    q: dict,
    chosen_index: int,
    followup_question: str,
    call_model=None,
    *,
    provider_label: str = "",
) -> FollowUpResult:
    """Serve a follow-up and REPORT why when it doesn't answer.

    Mirrors the explainer serving path: when no ``call_model`` is injected it
    resolves the live provider from env (same seam as ``ai_explain``). Grounding
    and opt-in behavior are unchanged — an ungrounded answer is still dropped,
    now surfaced as ``status="blocked"`` rather than a silent ``None``.
    """
    if call_model is None:
        try:
            call_model, provider_label = live_followup_caller_from_env()
        except ax.ProviderUnavailable as exc:
            # Provider named but no usable key → treat as AI OFF for the user.
            return FollowUpResult("off", detail=str(exc))
        except Exception as exc:  # e.g. unknown provider name (misconfig)
            return FollowUpResult("error", detail=str(exc))
        if call_model is None:
            return FollowUpResult("off")
    try:
        ans = answer_followup(
            q,
            chosen_index,
            followup_question,
            call_model,
            provider_label=provider_label or "llm",
        )
    except Exception as exc:
        return FollowUpResult("error", detail=str(exc))
    if not ans.is_grounded:
        return FollowUpResult("blocked", answer=ans)
    return FollowUpResult("answered", answer=ans)


def serve_followup(
    q: dict,
    chosen_index: int,
    followup_question: str,
    call_model=None,
    *,
    provider_label: str = "",
) -> FollowUpAnswer | None:
    """Best-effort follow-up answer; None when AI is OFF, blocked, or on error.

    Thin back-compat wrapper over ``serve_followup_result`` (which reports the
    specific reason). Existing callers that only need the answer keep working.
    """
    result = serve_followup_result(
        q, chosen_index, followup_question, call_model, provider_label=provider_label
    )
    return result.answer if result.status == "answered" else None


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="AI follow-up Q&A (live, opt-in).")
    ap.add_argument("--qid", required=True)
    ap.add_argument("--chose", required=True, help="chosen letter A-D")
    ap.add_argument("--question", required=True, help="follow-up question text")
    args = ap.parse_args(argv)

    ensure_mcat_env_loaded()
    questions = ax.load_questions()
    q = next((x for x in questions if x["id"] == args.qid), None)
    if q is None:
        raise SystemExit(f"question id not found: {args.qid}")
    idx = LETTERS.index(args.chose.strip().upper())

    caller, label = live_followup_caller_from_env()
    if caller is None:
        print("AI OFF (MCAT_LLM_PROVIDER not set).")
        return 1
    ans = serve_followup(q, idx, args.question, caller, provider_label=label)
    if ans is None:
        print("Follow-up blocked or failed — review the static explanation.")
        return 1
    print(ans.render())
    return 0


if __name__ == "__main__":
    sys.exit(main())
