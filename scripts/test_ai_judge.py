#!/usr/bin/env py -3.12
"""Tests for the cross-model judge + hardened token scorer (no network).

Run:  py -3.12 -m unittest scripts.test_ai_judge -v
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import ai_eval_qa as e  # noqa: E402
import ai_judge as j  # noqa: E402


class TestNumericRobustness(unittest.TestCase):
    def test_exponents_are_distinct(self):
        self.assertNotEqual(
            e.extract_numbers("pH = -log(10^-2) = 2.0"),
            e.extract_numbers("pH = -log(10^-3) = 3.0"),
        )

    def test_scientific_forms_are_equivalent(self):
        self.assertEqual(e.extract_numbers("1.0x10^-3 M"), e.extract_numbers("10^-3"))

    def test_decimal_normalized(self):
        self.assertEqual(e.extract_numbers("pH 2.0"), e.extract_numbers("pH is 2"))


class TestNegationAwareMustNotSay(unittest.TestCase):
    def test_preceding_negation_not_flagged(self):
        # Correctly saying it is NOT 12.0 must not count as asserting 12.0.
        self.assertFalse(
            e.must_not_say_hit(
                "the pH of this solution is 12.0",
                "12.0 is the pOH, not the pH; the pH is 2.0.",
            )
        )

    def test_rather_than_not_flagged(self):
        self.assertFalse(
            e.must_not_say_hit(
                "the pH drops as sharply as it would in pure water",
                "the buffer's pH drops only slightly rather than sharply as in water.",
            )
        )

    def test_plain_assertion_flagged(self):
        self.assertTrue(
            e.must_not_say_hit("the pH is 12.0", "the pH of this solution is 12.0.")
        )


class TestJudgeParse(unittest.TestCase):
    def test_coerce_lengths_and_clamp(self):
        r = j.parse_judge_result(
            json.dumps({"atoms_covered": [True, "yes"], "coverage_fraction": 1.7}),
            n_atoms=4,
            n_must_not=2,
        )
        self.assertEqual(len(r.atoms_covered), 4)
        self.assertEqual(len(r.must_not_say_violated), 2)
        self.assertEqual(r.coverage_fraction, 1.0)

    def test_fenced_json_parses(self):
        raw = "```json\n{\"atoms_covered\":[true],\"coverage_fraction\":1.0}\n```"
        r = j.parse_judge_result(raw, 1, 0)
        self.assertEqual(r.atoms_covered, [True])

    def test_missing_coverage_falls_back_to_bools(self):
        r = j.parse_judge_result(json.dumps({"atoms_covered": [True, False]}), 2, 0)
        self.assertAlmostEqual(r.coverage_fraction, 0.5)


class TestJudgeSeam(unittest.TestCase):
    def test_judge_answer_with_mock_call_model(self):
        def call(prompt: str) -> str:
            self.assertIn("FACT_ATOMS", prompt)
            return json.dumps(
                {
                    "atoms_covered": [True, True],
                    "must_not_say_violated": [False],
                    "coverage_fraction": 1.0,
                    "notes": "ok",
                }
            )

        r = j.judge_answer("q?", "answer", ["a1", "a2"], ["bad"], call)
        self.assertEqual(r.coverage_fraction, 1.0)
        self.assertFalse(r.any_violation)


class TestCrossModelGuard(unittest.TestCase):
    def test_missing_key_returns_note(self):
        c, _, note = j.build_judge_caller_from_env(env={}, answer_provider="openai")
        self.assertIsNone(c)
        self.assertIn("no judge API key", note)

    def test_same_family_refused(self):
        c, _, note = j.build_judge_caller_from_env(
            env={"MCAT_JUDGE_PROVIDER": "openai", "OPENAI_API_KEY": "x"},
            answer_provider="openai",
        )
        self.assertIsNone(c)
        self.assertIn("circular", note.lower())

    def test_cross_model_builds_caller(self):
        c, label, note = j.build_judge_caller_from_env(
            env={"ANTHROPIC_API_KEY": "x"}, answer_provider="openai"
        )
        self.assertIsNotNone(c)  # built, not called (no network here)
        self.assertTrue(label.startswith("anthropic:"))
        self.assertEqual(note, "")


if __name__ == "__main__":
    unittest.main(verbosity=2)
