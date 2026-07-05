#!/usr/bin/env py -3.12
"""Unit tests for scripts/eval_step2_prediction.py — no network."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from eval_step2_prediction import (
    AttemptRow,
    accuracy_at_threshold,
    brier_score,
    build_features,
    log_loss,
    predict_logistic,
    sigmoid,
    synth_attempts,
    wilson_ci,
)


class TestMath(unittest.TestCase):
    def test_sigmoid_midpoint(self) -> None:
        self.assertAlmostEqual(sigmoid(0.0), 0.5)

    def test_brier_perfect(self) -> None:
        self.assertAlmostEqual(brier_score([1.0, 0.0], [1, 0]), 0.0)

    def test_log_loss_finite(self) -> None:
        ll = log_loss([0.9, 0.1], [1, 0])
        self.assertTrue(0.0 < ll < 1.0)


class TestDeterminism(unittest.TestCase):
    def test_synth_attempts_reproducible(self) -> None:
        qs = [
            {"id": "q_ho_001", "split": "held_out", "topic_id": "bb_enzymes",
             "section": "BB", "cognitive_demand": "application", "correct": "A",
             "choices": ["a", "b", "c", "d"]},
            {"id": "q_ho_002", "split": "held_out", "topic_id": "cp_kinetics",
             "section": "CP", "cognitive_demand": "recall", "correct": "B",
             "choices": ["a", "b", "c", "d"]},
        ]
        covered = {"bb_enzymes"}
        a1 = synth_attempts(qs, seed=99, covered_topics=covered)
        a2 = synth_attempts(qs, seed=99, covered_topics=covered)
        self.assertEqual([(x.question_id, x.correct) for x in a1],
                         [(x.question_id, x.correct) for x in a2])

    def test_predict_logistic_monotone_in_mastery(self) -> None:
        low = predict_logistic(0.4, 0.5, 0.5, 1.0)
        high = predict_logistic(0.8, 0.5, 0.5, 1.0)
        self.assertGreater(high, low)


class TestAccuracyMetrics(unittest.TestCase):
    def test_accuracy_at_threshold(self) -> None:
        from eval_step2_prediction import FeatureRow

        rows = [
            FeatureRow("q1", 0.5, 0.5, 0.5, 1.0, 0.8, 1),
            FeatureRow("q2", 0.5, 0.5, 0.5, 1.0, 0.2, 0),
        ]
        k, n, acc = accuracy_at_threshold(rows, 0.5)
        self.assertEqual(n, 2)
        self.assertEqual(k, 2)
        self.assertAlmostEqual(acc, 1.0)

    def test_wilson_ci_bounds(self) -> None:
        lo, hi = wilson_ci(7, 10)
        self.assertLess(lo, 0.7)
        self.assertGreater(hi, 0.7)


class TestMainArtifact(unittest.TestCase):
    def test_main_writes_summary_json(self) -> None:
        import eval_step2_prediction as mod

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "step2.summary.json"
            old_argv = mod.sys.argv
            try:
                mod.sys.argv = [
                    "eval_step2_prediction.py",
                    "--out", str(out),
                    "--seed", "12345",
                ]
                code = mod.main()
            finally:
                mod.sys.argv = old_argv
            self.assertEqual(code, 0)
            self.assertTrue(out.exists())
            doc = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(doc["mode"], "synthetic")
            self.assertIn("missing_data_note", doc)
            self.assertIn("next_action", doc)
            self.assertIn("brier", doc["metrics"])


if __name__ == "__main__":
    unittest.main()
