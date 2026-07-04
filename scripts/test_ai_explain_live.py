#!/usr/bin/env py -3.12
"""Tests for the live LLM seam of the AI post-answer explainer.

NO NETWORK. A fake `call_model` stands in for the real SDK so we can prove:
  * env-driven provider dispatch (openai/anthropic/AI-off) works and reads the
    key ONLY from the environment;
  * the LLMProvider prompt/parse round-trip produces a gate-passing Explanation;
  * the SAFETY GATE blocks wrong-choice / ungrounded live output and the serving
    path falls back to the static explanation;
  * AI-OFF (no provider configured) still serves the static explanation;
  * the eval harness runs end-to-end against a mocked live provider.

Run:  py -3.12 -m unittest scripts.test_ai_explain_live -v
  or:  py -3.12 scripts/test_ai_explain_live.py
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import ai_explain as ax  # noqa: E402


def _sample_question() -> dict:
    """A content_gap item: chosen C encodes a specific misconception."""
    return {
        "id": "q_test_001",
        "stem": "TEST STEM: which step does X?",
        "choices": ["choice a", "choice b", "choice c wrong", "choice d"],
        "correct": "B",
        "topic_id": "bb_citric_acid",
        "section": "BB",
        "choice_diagnosis": [
            None,
            None,
            {
                "maps_to": "content_gap",
                "misconception": "thinks the hydration step produces GTP",
            },
            None,
        ],
        "explanation": "The correct answer is B. Static rationale for AI-off.",
        "source_name": "OpenStax Biology 2e",
        "source_url": "https://openstax.org/x",
        "source_location": "Ch. 7 Q9",
        "split": "held_out",
    }


def _good_json_caller(q: dict, chosen_index: int):
    """A fake model that echoes the diagnosis faithfully -> should PASS the gate."""
    diag = q["choice_diagnosis"][chosen_index] or {}
    misc = diag.get("misconception", "a near-miss with no single misconception")

    def call(prompt: str) -> str:
        return json.dumps(
            {
                "correct_letter": q["correct"],
                "why_wrong": f"Choice {ax.LETTERS[chosen_index]} is wrong: {misc}.",
                "correct_solution": f"The correct answer is {q['correct']}.",
                "next_action": "Review the backing concept and retry.",
            }
        )

    return call


class TestEnvDispatch(unittest.TestCase):
    def test_ai_off_when_no_provider(self):
        caller, label = ax.build_live_call_model_from_env(env={})
        self.assertIsNone(caller)
        self.assertEqual(label, "")
        self.assertIsNone(ax.live_provider_from_env(env={}))

    def test_openai_dispatch_builds_caller_without_network(self):
        # Building the caller must NOT import the SDK or hit the network.
        caller, label = ax.build_live_call_model_from_env(
            env={
                "MCAT_LLM_PROVIDER": "openai",
                "MCAT_LLM_MODEL": "gpt-4o-mini",
                "OPENAI_API_KEY": "sk-not-real-test-key",
            }
        )
        self.assertTrue(callable(caller))
        self.assertEqual(label, "openai:gpt-4o-mini")

    def test_anthropic_dispatch_and_generic_key(self):
        caller, label = ax.build_live_call_model_from_env(
            env={
                "MCAT_LLM_PROVIDER": "anthropic",
                "MCAT_LLM_API_KEY": "generic-test-key",
            }
        )
        self.assertTrue(callable(caller))
        self.assertTrue(label.startswith("anthropic:"))

    def test_missing_key_raises(self):
        with self.assertRaises(ax.ProviderUnavailable):
            ax.build_live_call_model_from_env(
                env={"MCAT_LLM_PROVIDER": "openai"}
            )

    def test_unknown_provider_raises(self):
        with self.assertRaises(ValueError):
            ax.build_live_call_model_from_env(
                env={"MCAT_LLM_PROVIDER": "gemini", "MCAT_LLM_API_KEY": "k"}
            )


class TestLLMProviderParse(unittest.TestCase):
    def test_good_output_passes_gate(self):
        q = _sample_question()
        idx = 2  # content_gap distractor
        provider = ax.LLMProvider(call_model=_good_json_caller(q, idx),
                                  model_label="mock:test")
        expl = provider.explain(q, idx)
        self.assertEqual(expl.asserted_correct_letter, "B")
        self.assertTrue(expl.is_grounded)
        self.assertFalse(ax.safety_block(expl, q))
        self.assertIn("hydration step produces GTP", expl.why_wrong)
        self.assertTrue(expl.provider.startswith("llm:"))

    def test_code_fenced_json_is_parsed(self):
        q = _sample_question()

        def call(prompt: str) -> str:
            return "```json\n" + json.dumps(
                {
                    "correct_letter": "B",
                    "why_wrong": "fenced why",
                    "correct_solution": "fenced sol",
                    "next_action": "fenced next",
                }
            ) + "\n```"

        expl = ax.LLMProvider(call_model=call).explain(q, 2)
        self.assertEqual(expl.why_wrong, "fenced why")

    def test_unparseable_output_raises(self):
        q = _sample_question()
        provider = ax.LLMProvider(call_model=lambda p: "not json at all")
        with self.assertRaises(ax.ProviderUnavailable):
            provider.explain(q, 2)


class TestSafetyGate(unittest.TestCase):
    def test_wrong_letter_is_blocked(self):
        q = _sample_question()

        def call(prompt: str) -> str:
            return json.dumps(
                {
                    "correct_letter": "A",  # WRONG (key is B)
                    "why_wrong": "misinforms",
                    "correct_solution": "wrong",
                    "next_action": "n",
                }
            )

        expl = ax.LLMProvider(call_model=call).explain(q, 2)
        self.assertTrue(ax.safety_block(expl, q))

    def test_ungrounded_is_blocked(self):
        q = _sample_question()
        q_no_src = {**q, "source_name": ""}

        def call(prompt: str) -> str:
            return json.dumps(
                {
                    "correct_letter": "B",
                    "why_wrong": "w",
                    "correct_solution": "s",
                    "next_action": "n",
                }
            )

        expl = ax.LLMProvider(call_model=call).explain(q_no_src, 2)
        self.assertTrue(ax.safety_block(expl, q_no_src))


class TestServeFallback(unittest.TestCase):
    def test_serve_uses_live_when_good(self):
        q = _sample_question()
        provider = ax.LLMProvider(call_model=_good_json_caller(q, 2))
        served = ax.serve_explanation(q, 2, provider)
        self.assertTrue(served.provider.startswith("llm"))
        self.assertFalse(ax.safety_block(served, q))

    def test_serve_falls_back_on_wrong_letter(self):
        q = _sample_question()
        provider = ax.LLMProvider(
            call_model=lambda p: json.dumps(
                {
                    "correct_letter": "A",
                    "why_wrong": "w",
                    "correct_solution": "s",
                    "next_action": "n",
                }
            )
        )
        served = ax.serve_explanation(q, 2, provider)
        self.assertEqual(served.provider, "static_fallback")
        self.assertEqual(served.asserted_correct_letter, "B")

    def test_serve_falls_back_on_model_exception(self):
        q = _sample_question()

        def boom(prompt: str) -> str:
            raise RuntimeError("network down")

        provider = ax.LLMProvider(call_model=boom)
        served = ax.serve_explanation(q, 2, provider)
        self.assertEqual(served.provider, "static_fallback")
        self.assertFalse(ax.safety_block(served, q))

    def test_ai_off_serves_static(self):
        q = _sample_question()
        served = ax.serve_explanation(q, 2, provider=None)
        self.assertEqual(served.provider, "static_fallback")
        self.assertIn("Static rationale", served.why_wrong)


class TestEvalAgainstMockedLive(unittest.TestCase):
    """The eval harness must run end-to-end against a mocked live provider."""

    def test_eval_ai_with_mocked_live_provider(self):
        import ai_eval_explanations as ev

        class MockLive(ax.ExplainerProvider):
            name = "mock_live"

            def explain(self, q, chosen_index):
                return ax.LLMProvider(
                    call_model=_good_json_caller(q, chosen_index),
                    model_label="mock:test",
                ).explain(q, chosen_index)

        questions = ax.load_questions()
        held = [q for q in questions if q.get("split") == "held_out"][:5]
        pairs = ev.build_pairs(held)
        by_id = {q["id"]: q for q in questions}
        m = ev.eval_ai(MockLive(), pairs, by_id)
        # Faithful mock -> grounded everywhere, correct answer everywhere.
        self.assertEqual(m["grounding_rate"], 1.0)
        self.assertEqual(m["wrong_answer_rate"], 0.0)
        self.assertEqual(m["errored"], 0)

    def test_eval_ai_gate_catches_bad_live_provider(self):
        import ai_eval_explanations as ev

        class BadLive(ax.ExplainerProvider):
            name = "bad_live"

            def explain(self, q, chosen_index):
                # Always names the wrong choice -> gate must block -> static.
                return ax.LLMProvider(
                    call_model=lambda p: json.dumps(
                        {
                            "correct_letter": "Z",
                            "why_wrong": "w",
                            "correct_solution": "s",
                            "next_action": "n",
                        }
                    )
                ).explain(q, chosen_index)

        questions = ax.load_questions()
        held = [q for q in questions if q.get("split") == "held_out"][:5]
        pairs = ev.build_pairs(held)
        m = ev.eval_ai(BadLive(), pairs, {})
        # Every output blocked -> served static -> still grounded + correct.
        self.assertEqual(m["blocked"], m["n"])
        self.assertEqual(m["grounding_rate"], 1.0)
        self.assertEqual(m["wrong_answer_rate"], 0.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
