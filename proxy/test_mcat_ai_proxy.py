#!/usr/bin/env py -3.12
"""Unit tests for the hosted AI proxy (proxy/mcat_ai_proxy.py). NO NETWORK.

Starts the real proxy on an ephemeral port in a thread and drives it over HTTP,
with the OpenAI upstream MOCKED (monkeypatched). Proves the security bar and the
happy path without a real key:
  * bundle-token gate (401), model allowlist (400), oversized prompt (400),
    wrong method/path (405/404), per-IP rate limit (429), health (200);
  * real-mode forwarding returns the (mocked) upstream content;
  * --mock mode echoes a gate-passing completion with the ground-truth letter.

Run:  py -3.12 -m unittest proxy.test_mcat_ai_proxy -v
  or: py -3.12 proxy/test_mcat_ai_proxy.py
"""

from __future__ import annotations

import json
import sys
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import mcat_ai_proxy as prx  # noqa: E402


def _post(url, body, token=None, raw=None):
    headers = {"Content-Type": "application/json"}
    if token is not None:
        headers[prx.TOKEN_HEADER] = token
    data = raw if raw is not None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode("utf-8"))


def _get(url):
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode("utf-8"))


class ProxyServerCase(unittest.TestCase):
    """Base: spin a proxy with an overridable config; mock the upstream."""

    mock_mode = False
    rate_limit = 100

    def setUp(self) -> None:
        self._orig_call = prx.call_openai
        # Deterministic fake upstream (records the last call).
        self.calls: list[dict] = []

        def fake_upstream(messages, model, api_key, upstream_url, timeout):
            self.calls.append({"model": model, "messages": messages, "key": api_key})
            return json.dumps({"correct_letter": "B", "why_wrong": "w",
                               "correct_solution": "s", "next_action": "n"})

        prx.call_openai = fake_upstream  # type: ignore[assignment]

        self.config = prx.ProxyConfig(
            bundle_token="secret-token",
            allowed_models=frozenset({"gpt-4o-mini"}),
            api_key="" if self.mock_mode else "sk-fake-not-real",
            mock=self.mock_mode,
            max_prompt_chars=200,
            max_messages=4,
            rate_limit=self.rate_limit,
            rate_window=60,
        )
        self.httpd = prx.serve(self.config, "127.0.0.1", 0)
        self.port = self.httpd.server_address[1]
        self.url = f"http://127.0.0.1:{self.port}/"
        self._thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self._thread.start()

    def tearDown(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()
        self._thread.join(timeout=5)
        prx.call_openai = self._orig_call  # type: ignore[assignment]

    def _good_body(self):
        return {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": "sys"},
                {"role": "user", "content": "CORRECT: B\nSTUDENT_CHOSE: C\nhi"},
            ],
        }


class TestHappyAndSecurity(ProxyServerCase):
    def test_health_no_token(self):
        status, body = _get(self.url + "health")
        self.assertEqual(status, 200)
        self.assertTrue(body["ok"])
        self.assertIn("gpt-4o-mini", body["models"])

    def test_valid_request_forwards_upstream(self):
        status, body = _post(self.url, self._good_body(), token="secret-token")
        self.assertEqual(status, 200)
        self.assertEqual(body["model"], "gpt-4o-mini")
        parsed = json.loads(body["content"])
        self.assertEqual(parsed["correct_letter"], "B")
        # Upstream was actually called once with the app's messages + key.
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(self.calls[0]["key"], "sk-fake-not-real")

    def test_missing_token_rejected(self):
        status, body = _post(self.url, self._good_body(), token=None)
        self.assertEqual(status, 401)
        self.assertEqual(len(self.calls), 0)

    def test_wrong_token_rejected(self):
        status, body = _post(self.url, self._good_body(), token="nope")
        self.assertEqual(status, 401)

    def test_disallowed_model_rejected(self):
        b = self._good_body()
        b["model"] = "gpt-4o"  # not in allowlist
        status, body = _post(self.url, b, token="secret-token")
        self.assertEqual(status, 400)
        self.assertIn("not allowed", body["error"])
        self.assertEqual(len(self.calls), 0)

    def test_oversized_prompt_rejected(self):
        b = self._good_body()
        b["messages"][1]["content"] = "x" * 500  # > max_prompt_chars (200)
        status, body = _post(self.url, b, token="secret-token")
        self.assertEqual(status, 400)
        self.assertIn("too large", body["error"])

    def test_too_many_messages_rejected(self):
        b = self._good_body()
        b["messages"] = [{"role": "user", "content": "x"}] * 5  # > max_messages (4)
        status, body = _post(self.url, b, token="secret-token")
        self.assertEqual(status, 400)

    def test_invalid_json_rejected(self):
        status, body = _post(self.url, None, token="secret-token", raw=b"{not json")
        self.assertEqual(status, 400)

    def test_wrong_method_and_path(self):
        # GET on an unknown path -> 404
        status, _ = _get(self.url + "nope")
        self.assertEqual(status, 404)


class TestRateLimit(ProxyServerCase):
    rate_limit = 3

    def test_rate_limit_trips(self):
        seen = []
        for _ in range(5):
            status, _ = _post(self.url, self._good_body(), token="secret-token")
            seen.append(status)
        self.assertIn(429, seen)
        self.assertEqual(seen.count(200), 3)  # exactly the limit succeeded


class TestMockMode(ProxyServerCase):
    mock_mode = True

    def test_mock_echoes_ground_truth_letter(self):
        status, body = _post(self.url, self._good_body(), token="secret-token")
        self.assertEqual(status, 200)
        parsed = json.loads(body["content"])
        # Mock reads CORRECT: B from the prompt and echoes it (gate will pass).
        self.assertEqual(parsed["correct_letter"], "B")
        self.assertIn("mock-proxy", parsed["why_wrong"])
        # No upstream call in mock mode.
        self.assertEqual(len(self.calls), 0)

    def test_mock_followup_shape(self):
        b = self._good_body()
        b["messages"][1]["content"] = "FOLLOWUP_QUESTION: why not 12.0?"
        status, body = _post(self.url, b, token="secret-token")
        self.assertEqual(status, 200)
        parsed = json.loads(body["content"])
        self.assertIn("answer", parsed)
        self.assertEqual(parsed["grounded"], "yes")


if __name__ == "__main__":
    unittest.main(verbosity=2)
