#!/usr/bin/env py -3.12
"""Persist a cross-model judging worksheet for the CHANGED gold items (g031-g060).

The semantic judge (a Claude coding subagent) needs, per item, the three answer
sources side by side with the human-validated rubric. Keeping that only in the
model's context is what stalled prior attempts, so this dumps it to disk.

For each item in the id range (default g031-g060) it records:
  {id, bucket, followup_question, fact_atoms, must_not_say,
   ai_answer, static_answer, keyword_answer}

  * ai_answer     — saved live OpenAI answer (data/qa-goldset-live-answers.json)
  * static_answer — build_static_baseline (shipped explanation + choice_feedback)
  * keyword_answer— build_keyword_baseline (top-k retrieved sentences)

Run:
  py -3.12 scripts/build_qa_judge_worksheet.py
  py -3.12 scripts/build_qa_judge_worksheet.py --start 31 --end 60
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
SCRIPTS = ROOT / "scripts"
BUILD = ROOT / "build"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:  # pragma: no cover
    pass

from qa_baseline_compare import build_static_baseline, build_keyword_baseline  # noqa: E402
from ai_explain import load_questions  # noqa: E402

GOLDSET_PATH = DATA / "qa-goldset.json"
LIVE_ANSWERS_PATH = DATA / "qa-goldset-live-answers.json"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Dump cross-model judging worksheet.")
    ap.add_argument("--start", type=int, default=31, help="First gNNN id (inclusive).")
    ap.add_argument("--end", type=int, default=60, help="Last gNNN id (inclusive).")
    args = ap.parse_args(argv)

    want = {f"g{n:03d}" for n in range(args.start, args.end + 1)}

    gold = json.loads(GOLDSET_PATH.read_text(encoding="utf-8"))
    items_by_id = {x["id"]: x for x in gold.get("items", [])}
    questions_by_id = {q["id"]: q for q in load_questions()}
    live_raw = json.loads(LIVE_ANSWERS_PATH.read_text(encoding="utf-8"))
    ai_by_id = {row["id"]: row for row in live_raw}

    worksheet: list[dict] = []
    missing: list[str] = []
    for gid in sorted(want):
        item = items_by_id.get(gid)
        if item is None:
            missing.append(gid)
            continue
        qid = item["question_id"]
        q = questions_by_id.get(qid, {})
        followup = item.get("followup_question", "")
        chosen_index = item.get("chosen_distractor_index")
        ai_answer = (ai_by_id.get(gid) or {}).get("ai_answer", "")
        worksheet.append(
            {
                "id": gid,
                "question_id": qid,
                "bucket": item.get("bucket", ""),
                "followup_question": followup,
                "fact_atoms": item.get("fact_atoms") or [],
                "must_not_say": item.get("must_not_say") or [],
                "ai_answer": ai_answer,
                "static_answer": build_static_baseline(q, chosen_index),
                "keyword_answer": build_keyword_baseline(q, followup),
            }
        )

    BUILD.mkdir(exist_ok=True)
    out_path = BUILD / f"qa-judge-worksheet-g{args.start:03d}-g{args.end:03d}.json"
    out_path.write_text(json.dumps(worksheet, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Wrote {out_path.relative_to(ROOT)} with {len(worksheet)} entries.")
    if missing:
        print(f"WARNING: missing gold items: {', '.join(missing)}")
    empties = [w["id"] for w in worksheet if not w["ai_answer"].strip()]
    if empties:
        print(f"WARNING: empty ai_answer for: {', '.join(empties)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
