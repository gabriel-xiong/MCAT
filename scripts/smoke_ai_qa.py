#!/usr/bin/env py -3.12
"""Smoke check for AI follow-up Q&A wiring (no network unless --live).

Default: mocked provider proves import + parse path.
With --live: one real call (requires MCAT/.env with MCAT_LLM_PROVIDER + key).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import ai_explain as ax  # noqa: E402
import ai_qa as qa  # noqa: E402
from mcat_env import ensure_mcat_env_loaded  # noqa: E402


def _mock_caller(q: dict, idx: int):
    def call(prompt: str) -> str:
        return json.dumps(
            {
                "answer": f"Mock answer for {q['id']} chose {ax.LETTERS[idx]}.",
                "grounded": "yes",
            }
        )

    return call


def main() -> int:
    live = "--live" in sys.argv
    ensure_mcat_env_loaded()
    questions = ax.load_questions()
    q = next((x for x in questions if x.get("split") == "held_out"), questions[0])
    idx = 0 if q["correct"] != "A" else 1
    followup = "Why is my choice wrong?"

    if live:
        ans = qa.serve_followup(q, idx, followup)
        if ans is None:
            print("FAIL: live follow-up returned None (check MCAT_LLM_PROVIDER + key).")
            return 1
        print("OK live:", ans.render()[:120], "...")
        return 0

    ans = qa.serve_followup(
        q, idx, followup, _mock_caller(q, idx), provider_label="mock:smoke"
    )
    if ans is None:
        print("FAIL: mocked follow-up path broken.")
        return 1
    print("OK mocked:", ans.render()[:120], "...")
    return 0


if __name__ == "__main__":
    sys.exit(main())
