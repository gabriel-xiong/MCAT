#!/usr/bin/env py -3.12
"""Generate LIVE OpenAI follow-up answers for the QA gold set (for HUMAN review).

For each selected gold item (all items by default, or a subset via ``--ids``),
this calls the same live model path that ``ai_qa.serve_followup`` uses
(``answer_followup`` + the env-configured OpenAI caller) and records the VERBATIM
answer so a human can hand-review it. Unselected items keep their cached answer.

Why call ``answer_followup`` instead of ``serve_followup`` directly:
``serve_followup`` swallows its result to ``None`` on (a) any exception or
(b) an ungrounded answer. For hand review we must keep the verbatim text even
when the grounding flag is "no", so we call ``answer_followup`` (exactly what
``serve_followup`` wraps) and reconstruct what ``serve_followup`` WOULD have
returned via the ``served`` field. Behaviour is otherwise identical.

Safety:
  * The API key is never printed or written anywhere.
  * If the FIRST call fails with an auth error (401 / invalid key), STOP
    immediately without burning the remaining calls.
  * On a non-auth exception, retry once; if it still fails, record BLOCKED/None
    with the reason (this surfaces the bare-except-None issue in serve_followup).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import ai_explain as ax  # noqa: E402
import ai_qa  # noqa: E402
from mcat_env import ensure_mcat_env_loaded  # noqa: E402

LETTERS = ax.LETTERS
GOLDSET = ROOT / "data" / "qa-goldset.json"
OUT = ROOT / "data" / "qa-goldset-live-answers.json"

AUTH_MARKERS = ("401", "invalid_api_key", "authentication", "unauthorized", "invalid api key")


def _is_auth_error(exc: Exception) -> bool:
    msg = f"{type(exc).__name__} {exc}".lower()
    return any(m in msg for m in AUTH_MARKERS)


def parse_ids(spec: str | None, all_ids: list[str]) -> set[str]:
    """Expand an --ids spec into a set of gold ids.

    Accepts comma-separated ids and/or inclusive ranges, e.g.
    ``g031-g060,g007``. When *spec* is falsy, ALL ids are selected (the
    historical default: regenerate the whole file).
    """
    if not spec:
        return set(all_ids)
    out: set[str] = set()
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            lo_s, hi_s = part.split("-", 1)
            lo, hi = int(lo_s.strip()[1:]), int(hi_s.strip()[1:])
            for n in range(lo, hi + 1):
                out.add(f"g{n:03d}")
        else:
            out.add(part)
    return out


def _chosen_index(item: dict, q: dict) -> int:
    """Index to frame the item with. Null (differentiation) items have no chosen
    distractor, so use the first non-correct choice to keep the missed-question
    framing sensible without falsely marking the correct choice as chosen."""
    idx = item.get("chosen_distractor_index")
    if idx is not None:
        return int(idx)
    correct = LETTERS.index(q["correct"])
    for i in range(len(q["choices"])):
        if i != correct:
            return i
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Generate live OpenAI follow-up answers for the QA gold set."
    )
    ap.add_argument(
        "--ids",
        default=None,
        metavar="SPEC",
        help="Only (re)generate these ids; comma-separated ids and/or inclusive "
        "ranges, e.g. 'g031-g060'. Unselected items keep their cached answer from "
        "the existing output file. Default: regenerate every item.",
    )
    args = ap.parse_args(argv)

    ensure_mcat_env_loaded()
    caller, label = ai_qa.live_followup_caller_from_env()
    if caller is None:
        print("AI OFF (MCAT_LLM_PROVIDER not set). Nothing to do.")
        return 1

    gold = json.loads(GOLDSET.read_text(encoding="utf-8"))
    questions = {q["id"]: q for q in ax.load_questions()}
    items = gold["items"]

    selected = parse_ids(args.ids, [it["id"] for it in items])
    cached = {}
    if OUT.is_file():
        try:
            cached = {r["id"]: r for r in json.loads(OUT.read_text(encoding="utf-8"))}
        except Exception:
            cached = {}
    n_reused = 0

    results = []
    first_call = True
    for item in items:
        gid = item["id"]
        qid = item["question_id"]

        # Preserve cached answers for items outside the selected set (e.g. keep
        # g001-g030 untouched while regenerating only g031-g060).
        if gid not in selected and gid in cached:
            results.append(cached[gid])
            n_reused += 1
            continue

        q = questions.get(qid)
        if q is None:
            results.append(_blocked(item, f"question_id {qid} not found in questions.json"))
            print(f"{gid}: BLOCKED (missing question {qid})")
            continue

        idx = _chosen_index(item, q)
        fq = item["followup_question"]

        ans_text = None
        grounded = None
        reason = None
        for attempt in (1, 2):
            try:
                ans = ai_qa.answer_followup(q, idx, fq, caller, provider_label=label)
                ans_text = ans.answer
                grounded = ans.is_grounded
                first_call = False
                break
            except Exception as exc:  # mirror serve_followup's broad catch, but keep the reason
                if first_call and _is_auth_error(exc):
                    print("AUTH ERROR on first call — stopping. Auth is still broken.")
                    print(f"  reason: {type(exc).__name__}: {exc}")
                    return 2
                first_call = False
                reason = f"{type(exc).__name__}: {exc}"
                if attempt == 2:
                    print(f"{gid}: BLOCKED/None after retry — {reason}")

        if ans_text is None:
            results.append(_blocked(item, reason or "serve_followup returned None"))
            continue

        served = bool(grounded)  # what serve_followup would have returned (non-None)
        results.append(
            {
                "id": gid,
                "topic_id": item.get("topic_id"),
                "bucket": item["bucket"],
                "question_id": qid,
                "chosen_index_used": idx,
                "followup_question": fq,
                "ai_answer": ans_text,
                "grounded": grounded,
                "served_by_serve_followup": served,
                "provider": label,
                "fact_atoms": item["fact_atoms"],
                "must_not_say": item["must_not_say"],
            }
        )
        flag = "grounded" if grounded else "UNGROUNDED"
        print(f"{gid}: ok ({flag}) [{len(ans_text)} chars]")

    OUT.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    n_ok = sum(1 for r in results if r.get("ai_answer"))
    n_blocked = len(results) - n_ok
    print(f"\nWrote {len(results)} records to {OUT.relative_to(ROOT)} "
          f"({n_ok} answered, {n_blocked} blocked, {n_reused} reused from cache). "
          f"provider={label}")
    return 0


def _blocked(item: dict, reason: str) -> dict:
    return {
        "id": item["id"],
        "topic_id": item.get("topic_id"),
        "bucket": item["bucket"],
        "question_id": item["question_id"],
        "followup_question": item["followup_question"],
        "ai_answer": None,
        "grounded": None,
        "served_by_serve_followup": False,
        "blocked_reason": reason,
        "fact_atoms": item["fact_atoms"],
        "must_not_say": item["must_not_say"],
    }


if __name__ == "__main__":
    raise SystemExit(main())
