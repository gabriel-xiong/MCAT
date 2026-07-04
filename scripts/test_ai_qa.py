#!/usr/bin/env py -3.12
"""Tests for AI follow-up Q&A (mocked LLM, no network).

Run:  py -3.12 -m unittest scripts.test_ai_qa -v
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import ai_qa as qa  # noqa: E402


def _sample_question() -> dict:
    return {
        "id": "q_test_qa",
        "stem": "What is the pH of 0.01 M HCl?",
        "choices": ["12.0", "2.0", "7.0", "10.0"],
        "correct": "B",
        "topic_id": "cp_acids_bases",
        "section": "CP",
        "choice_diagnosis": [
            {"maps_to": "content_gap", "misconception": "confuses pH with pOH"},
            None,
            None,
            None,
        ],
        "choice_feedback": ["pOH not pH", "", "", ""],
        "explanation": "Strong acid: pH = 2.0.",
        "source_name": "OpenStax Chemistry 2e",
        "source_url": "https://openstax.org/x",
        "source_location": "Ch. 14",
    }


class TestFollowUpParse(unittest.TestCase):
    def test_good_json_parses(self):
        q = _sample_question()

        def call(prompt: str) -> str:
            return json.dumps(
                {
                    "answer": "12.0 is pOH, not pH; for 0.01 M HCl the pH is 2.0.",
                    "grounded": "yes",
                }
            )

        ans = qa.answer_followup(q, 0, "Why isn't the answer 12.0?", call, provider_label="mock")
        self.assertTrue(ans.is_grounded)
        self.assertIn("pOH", ans.answer)

    def test_ungrounded_blocked_by_serve(self):
        q = _sample_question()

        def call(prompt: str) -> str:
            return json.dumps({"answer": "guess", "grounded": "no"})

        served = qa.serve_followup(q, 0, "Why?", call, provider_label="mock")
        self.assertIsNone(served)


class TestEnvOff(unittest.TestCase):
    def test_live_caller_none_without_provider(self):
        caller, label = qa.live_followup_caller_from_env(env={})
        self.assertIsNone(caller)
        self.assertEqual(label, "")


class TestPrompt(unittest.TestCase):
    def test_prompt_includes_followup(self):
        q = _sample_question()
        p = qa.build_followup_prompt(q, 0, "Where does 2.0 come from?")
        self.assertIn("FOLLOWUP_QUESTION: Where does 2.0 come from?", p)
        self.assertIn("STUDENT_CHOSE: A", p)


if __name__ == "__main__":
    unittest.main(verbosity=2)
