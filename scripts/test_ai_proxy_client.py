#!/usr/bin/env py -3.12
"""App-side tests for the hosted-proxy provider path in ai_explain.py.

Two layers, NO real key and NO external network:
  * pure-config tests for ``load_proxy_config`` precedence + placeholder guard,
    and provider dispatch (proxy caller vs direct provider vs AI-off);
  * end-to-end tests that spin the LOCAL MOCK proxy (proxy/mcat_ai_proxy.py
    --mock-equivalent) on an ephemeral port and prove:
      - app path -> proxy -> gate-passing rendered Explanation (provider
        ``llm:proxy:...``), and follow-up Q&A answered;
      - an UNREACHABLE proxy degrades to the static, source-grounded fallback
        (never hangs / never raises).

Run:  py -3.12 -m unittest scripts.test_ai_proxy_client -v
"""

from __future__ import annotations

import json
import sys
import threading
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
PROXY = SCRIPTS.parent / "proxy"
for _p in (SCRIPTS, PROXY):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import ai_explain as ax  # noqa: E402
import ai_qa as qa  # noqa: E402
import mcat_ai_proxy as prx  # noqa: E402


def _sample_question() -> dict:
    return {
        "id": "q_test_proxy_1",
        "stem": "TEST STEM: which step does X?",
        "choices": ["a", "b", "c wrong", "d"],
        "correct": "B",
        "topic_id": "bb_enzymes",
        "section": "BB",
        "choice_diagnosis": [
            None, None,
            {"maps_to": "content_gap", "misconception": "thinks X makes GTP"},
            None,
        ],
        "choice_feedback": ["", "", "you picked c", ""],
        "explanation": "The correct answer is B. Static rationale for AI-off.",
        "source_name": "OpenStax Biology 2e",
        "source_url": "https://openstax.org/x",
        "source_location": "Ch. 7 Q9",
        "split": "held_out",
    }


class MockProxy:
    """Context manager: the real mock proxy on an ephemeral localhost port."""

    def __init__(self, token="testtoken"):
        self.token = token

    def __enter__(self):
        cfg = prx.ProxyConfig(
            bundle_token=self.token,
            allowed_models=frozenset({"gpt-4o-mini"}),
            mock=True,
        )
        self.httpd = prx.serve(cfg, "127.0.0.1", 0)
        self.port = self.httpd.server_address[1]
        self.url = f"http://127.0.0.1:{self.port}/"
        self._t = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self._t.start()
        return self

    def __exit__(self, *exc):
        self.httpd.shutdown()
        self.httpd.server_close()
        self._t.join(timeout=5)


class TestProxyConfig(unittest.TestCase):
    def test_env_config_resolves(self):
        cfg = ax.load_proxy_config(
            {"MCAT_AI_PROXY_URL": "https://x.workers.dev/",
             "MCAT_AI_PROXY_TOKEN": "tok"},
            allow_file=False,
        )
        self.assertIsNotNone(cfg)
        self.assertEqual(cfg["url"], "https://x.workers.dev/")
        self.assertEqual(cfg["token"], "tok")
        self.assertEqual(cfg["model"], "gpt-4o-mini")  # default applied

    def test_placeholder_url_is_off(self):
        self.assertIsNone(ax.load_proxy_config(
            {"MCAT_AI_PROXY_URL": "REPLACE_WITH_YOUR_PROXY_URL"}, allow_file=False))
        self.assertIsNone(ax.load_proxy_config(
            {"MCAT_AI_PROXY_URL": ""}, allow_file=False))
        self.assertIsNone(ax.load_proxy_config(
            {"MCAT_AI_PROXY_URL": "not-a-url", "MCAT_AI_PROXY_TOKEN": "tok"},
            allow_file=False,
        ))

    def test_http_post_rejects_blank_url(self):
        with self.assertRaises(ax.ProviderUnavailable):
            ax._http_post_json("", {}, {}, 5.0)

    def test_json_file_config(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "mcat-ai-proxy.json"
            p.write_text(json.dumps(
                {"proxy_url": "https://f.workers.dev/", "bundle_token": "ftok",
                 "model": "gpt-4o-mini"}), encoding="utf-8")
            cfg = ax.load_proxy_config(
                {"MCAT_AI_PROXY_CONFIG": str(p)}, allow_file=True)
            self.assertEqual(cfg["url"], "https://f.workers.dev/")
            self.assertEqual(cfg["token"], "ftok")

    def test_env_overrides_file(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "mcat-ai-proxy.json"
            p.write_text(json.dumps(
                {"proxy_url": "https://file.dev/", "bundle_token": "ftok"}),
                encoding="utf-8")
            cfg = ax.load_proxy_config(
                {"MCAT_AI_PROXY_CONFIG": str(p),
                 "MCAT_AI_PROXY_URL": "https://env.dev/",
                 "MCAT_AI_PROXY_TOKEN": "etok"},
                allow_file=True)
            self.assertEqual(cfg["url"], "https://env.dev/")
            self.assertEqual(cfg["token"], "etok")


class TestProviderDispatch(unittest.TestCase):
    def test_proxy_selected_when_no_direct_provider(self):
        caller, label = ax.build_live_call_model_from_env(
            env={"MCAT_AI_PROXY_URL": "https://x.workers.dev/",
                 "MCAT_AI_PROXY_TOKEN": "tok"})
        self.assertTrue(callable(caller))
        self.assertEqual(label, "proxy:gpt-4o-mini")

    def test_direct_provider_takes_precedence_over_proxy(self):
        caller, label = ax.build_live_call_model_from_env(
            env={"MCAT_LLM_PROVIDER": "openai",
                 "OPENAI_API_KEY": "sk-not-real",
                 "MCAT_AI_PROXY_URL": "https://x.workers.dev/",
                 "MCAT_AI_PROXY_TOKEN": "tok"})
        self.assertTrue(callable(caller))
        self.assertEqual(label, "openai:gpt-4o-mini")  # not proxy

    def test_ai_off_when_nothing_configured(self):
        caller, label = ax.build_live_call_model_from_env(env={})
        self.assertIsNone(caller)
        self.assertEqual(label, "")


class TestEndToEndThroughMockProxy(unittest.TestCase):
    def test_explainer_via_proxy_passes_gate(self):
        q = _sample_question()
        with MockProxy() as mp:
            provider = ax.live_provider_from_env(
                env={"MCAT_AI_PROXY_URL": mp.url, "MCAT_AI_PROXY_TOKEN": mp.token})
            self.assertIsNotNone(provider)
            served = ax.serve_explanation(q, 2, provider)
        # Went through the proxy path (label proxy:...), gate passed, correct
        # letter preserved from the prompt the mock echoed back.
        self.assertTrue(served.provider.startswith("llm:proxy:"))
        self.assertFalse(ax.safety_block(served, q))
        self.assertEqual(served.asserted_correct_letter, "B")

    def test_followup_via_proxy_answered(self):
        q = _sample_question()
        with MockProxy() as mp:
            caller, label = qa.live_followup_caller_from_env(
                env={"MCAT_AI_PROXY_URL": mp.url, "MCAT_AI_PROXY_TOKEN": mp.token})
            self.assertTrue(callable(caller))
            result = qa.serve_followup_result(
                q, 2, "Why isn't it 12.0?", caller, provider_label=label)
        self.assertEqual(result.status, "answered")
        self.assertIsNotNone(result.answer)
        self.assertTrue(result.answer.is_grounded)

    def test_unreachable_proxy_falls_back_to_static(self):
        q = _sample_question()
        # Nothing is listening on this port -> transport error -> fallback.
        provider = ax.live_provider_from_env(
            env={"MCAT_AI_PROXY_URL": "http://127.0.0.1:9/",
                 "MCAT_AI_PROXY_TOKEN": "tok"},
            timeout=2.0)
        served = ax.serve_explanation(q, 2, provider)
        self.assertEqual(served.provider, "static_fallback")
        self.assertFalse(ax.safety_block(served, q))
        self.assertIn("Static rationale", served.why_wrong)

    def test_bad_token_falls_back_to_static(self):
        q = _sample_question()
        with MockProxy(token="right") as mp:
            provider = ax.live_provider_from_env(
                env={"MCAT_AI_PROXY_URL": mp.url, "MCAT_AI_PROXY_TOKEN": "wrong"})
            served = ax.serve_explanation(q, 2, provider)
        self.assertEqual(served.provider, "static_fallback")


if __name__ == "__main__":
    unittest.main(verbosity=2)
