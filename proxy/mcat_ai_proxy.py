#!/usr/bin/env py -3.12
"""MCAT Speedrun — hosted AI proxy (Python stdlib reference + local mock).

Purpose
-------
Lets the in-app AI assistant work on a grader's machine with **no API key
entered by the grader**. The app POSTs the same system+user messages it already
builds (see ``scripts/ai_explain.py`` / ``scripts/ai_qa.py``) to this small
server; the server holds the upstream LLM key **server-side only**, calls the
model, and returns the completion. The upstream key is never sent to or exposed
to the client.

This file is BOTH:
  * a **local mock** (``--mock``) the agent/CI can run with NO real key, to prove
    the end-to-end app -> proxy -> rendered-explanation path (and the
    unreachable -> source-based-fallback path); and
  * a **runnable reference proxy** (real mode) you can self-host on any box that
    can run Python 3 (Render / Fly.io / Railway / a VM). The recommended
    turnkey host is a Cloudflare Worker (``proxy/worker.js``) — this Python proxy
    speaks the IDENTICAL wire contract, so the app can't tell them apart.

Wire contract (app <-> proxy)
-----------------------------
  POST <proxy_url>            (also accepts POST /v1/complete)
    headers: Content-Type: application/json
             X-MCAT-Bundle-Token: <bundle token>
    body:    {"model": "gpt-4o-mini",
              "messages": [{"role":"system","content":...},
                           {"role":"user","content":...}]}
    200:     {"content": "<model text (a JSON object string)>",
              "model": "gpt-4o-mini"}
    non-200: {"error": "<short reason>"}   (client falls back to static)

  GET /  or  GET /health      -> 200 {"ok": true, "service": "mcat-ai-proxy", ...}
                                 (no token required; lets a human verify deploy)

Security (all enforced here)
----------------------------
  * shared **bundle-token** header required (constant-time compare);
  * **per-IP rate limiting** (fixed window, in-process);
  * upstream **model allowlist** (default: gpt-4o-mini);
  * **oversized-prompt rejection** (byte cap + message-count/char caps);
  * bounded **upstream timeout**; method/path allowlist; minimal logging that
    NEVER prints the key or prompt bodies.
  * NOTE: the upstream key spend cap + throwaway/scoped key are a HUMAN step on
    the LLM provider dashboard — see docs/AI-PROXY-SETUP.md.

Run
---
  # local mock (no key needed) — for E2E verification:
  py -3.12 proxy/mcat_ai_proxy.py --mock --token testtoken --port 8787

  # real proxy (self-host): key ONLY from the environment, never a flag:
  set OPENAI_API_KEY=sk-...            # (do not commit; host secret)
  py -3.12 proxy/mcat_ai_proxy.py --token "$MCAT_BUNDLE_TOKEN" --port 8787
"""

from __future__ import annotations

import argparse
import hmac
import json
import os
import re
import sys
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# Header the app sends (mirrors ai_explain.PROXY_TOKEN_HEADER).
TOKEN_HEADER = "X-MCAT-Bundle-Token"

DEFAULT_ALLOWED_MODELS = ("gpt-4o-mini",)
DEFAULT_UPSTREAM_URL = "https://api.openai.com/v1/chat/completions"

# Caps: reject clearly-abusive payloads without limiting normal MCAT prompts.
# A single explainer/follow-up prompt is well under ~6k chars in practice.
DEFAULT_MAX_PROMPT_CHARS = 12_000
DEFAULT_MAX_MESSAGES = 8
HARD_BODY_BYTES = 64 * 1024  # refuse to even read a body larger than this

# Per-IP rate limit defaults (fixed window). Kept modest: the real cost backstop
# is the provider spend cap, but this blunts a leaked-token abuse burst.
DEFAULT_RATE_LIMIT = 20
DEFAULT_RATE_WINDOW = 60  # seconds

# Upstream generation params — FORCED here so a client can't run up cost or
# change behavior, and so responses match the app's direct-call rendering.
UPSTREAM_TEMPERATURE = 0
UPSTREAM_MAX_TOKENS = 1024
DEFAULT_UPSTREAM_TIMEOUT = 20.0


class UpstreamError(RuntimeError):
    """Upstream LLM call failed (network / HTTP / bad shape)."""

    def __init__(self, message: str, status: int = 502) -> None:
        super().__init__(message)
        self.status = status


@dataclass
class ProxyConfig:
    bundle_token: str
    allowed_models: frozenset[str]
    api_key: str = ""  # "" in mock mode; real key read from env ONLY
    upstream_url: str = DEFAULT_UPSTREAM_URL
    mock: bool = False
    max_prompt_chars: int = DEFAULT_MAX_PROMPT_CHARS
    max_messages: int = DEFAULT_MAX_MESSAGES
    rate_limit: int = DEFAULT_RATE_LIMIT
    rate_window: int = DEFAULT_RATE_WINDOW
    upstream_timeout: float = DEFAULT_UPSTREAM_TIMEOUT


class RateLimiter:
    """Thread-safe per-key fixed-window counter (best-effort, in-process)."""

    def __init__(self, limit: int, window: int) -> None:
        self.limit = limit
        self.window = window
        self._lock = threading.Lock()
        self._hits: dict[str, list[float]] = {}

    def allow(self, key: str, now: float | None = None) -> bool:
        if self.limit <= 0:
            return True
        now = time.monotonic() if now is None else now
        cutoff = now - self.window
        with self._lock:
            bucket = [t for t in self._hits.get(key, ()) if t > cutoff]
            if len(bucket) >= self.limit:
                self._hits[key] = bucket
                return False
            bucket.append(now)
            self._hits[key] = bucket
            return True


# --------------------------------------------------------------------------- #
# Upstream + mock completion
# --------------------------------------------------------------------------- #
def call_openai(
    messages: list[dict],
    model: str,
    api_key: str,
    upstream_url: str,
    timeout: float,
) -> str:
    """Call OpenAI chat completions and return the message content string.

    Forces temperature/max_tokens/response_format so behavior + cost are bounded
    and the returned JSON matches the app's direct-call rendering. Raises
    ``UpstreamError`` on any failure; the API key is NEVER placed in an error
    message.
    """
    payload = json.dumps(
        {
            "model": model,
            "temperature": UPSTREAM_TEMPERATURE,
            "max_tokens": UPSTREAM_MAX_TOKENS,
            "response_format": {"type": "json_object"},
            "messages": messages,
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        upstream_url,
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        # Surface a compact upstream status but never the key or full body.
        detail = ""
        try:
            detail = exc.read().decode("utf-8", "replace")[:200]
        except Exception:
            pass
        status = 504 if exc.code in (408, 504) else 502
        raise UpstreamError(f"upstream HTTP {exc.code}: {detail}", status) from exc
    except urllib.error.URLError as exc:
        raise UpstreamError(f"upstream transport error: {exc.reason}", 504) from exc
    except Exception as exc:  # pragma: no cover - defensive
        raise UpstreamError(f"upstream error: {exc}", 502) from exc

    try:
        content = data["choices"][0]["message"]["content"]
    except Exception as exc:
        raise UpstreamError(f"unexpected upstream shape: {exc}", 502) from exc
    return content or ""


_RE_CORRECT = re.compile(r"^CORRECT:\s*([A-D])", re.MULTILINE)
_RE_CHOSE = re.compile(r"^STUDENT_CHOSE:\s*([A-D])", re.MULTILINE)


def mock_completion(messages: list[dict]) -> str:
    """Deterministic canned completion for ``--mock`` (NO upstream, NO key).

    Inspects the built user prompt to decide explainer vs follow-up and returns
    a JSON object string in the SAME schema the real model would, so the app's
    ``LLMProvider.parse`` / ``ai_qa.parse_followup`` render it and the safety
    gate passes (it echoes the ground-truth ``CORRECT:`` letter from the prompt).
    """
    user = ""
    for m in messages:
        if m.get("role") == "user":
            user = str(m.get("content") or "")
    if "FOLLOWUP_QUESTION:" in user:
        return json.dumps(
            {
                "answer": (
                    "[mock-proxy] Based on the cited source, the key idea holds "
                    "and the direction of the relationship is as stated in the "
                    "explanation above."
                ),
                "grounded": "yes",
            }
        )
    correct = (_RE_CORRECT.search(user) or [None, "A"])[1]
    chose_m = _RE_CHOSE.search(user)
    chose = chose_m.group(1) if chose_m else "?"
    return json.dumps(
        {
            "correct_letter": correct,
            "why_wrong": (
                f"[mock-proxy] Choice {chose} does not follow from the cited "
                f"source for what this item asks."
            ),
            "correct_solution": (
                f"The correct answer is {correct}; trace it to the named source."
            ),
            "next_action": "Review the cited source and retry this item.",
        }
    )


# --------------------------------------------------------------------------- #
# Request handling
# --------------------------------------------------------------------------- #
def _validate_body(body: dict, config: ProxyConfig) -> tuple[str, list[dict]]:
    """Return (model, messages) or raise ValueError with a client-safe reason."""
    if not isinstance(body, dict):
        raise ValueError("body must be a JSON object")
    model = str(body.get("model") or "").strip()
    if not model:
        raise ValueError("missing 'model'")
    if config.allowed_models and model not in config.allowed_models:
        raise ValueError(f"model '{model}' is not allowed")
    messages = body.get("messages")
    if not isinstance(messages, list) or not messages:
        raise ValueError("missing 'messages'")
    if len(messages) > config.max_messages:
        raise ValueError("too many messages")
    total = 0
    for m in messages:
        if not isinstance(m, dict) or "role" not in m or "content" not in m:
            raise ValueError("each message needs 'role' and 'content'")
        total += len(str(m.get("content") or ""))
    if total > config.max_prompt_chars:
        raise ValueError("prompt too large")
    return model, messages


def make_handler(config: ProxyConfig, limiter: RateLimiter):
    class Handler(BaseHTTPRequestHandler):
        server_version = "mcat-ai-proxy/1.0"
        protocol_version = "HTTP/1.1"

        # ---- helpers ----
        def _send_json(self, status: int, obj: dict) -> None:
            payload = json.dumps(obj).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            # Default-deny CORS: the desktop client is not a browser, so no
            # Access-Control-Allow-Origin is emitted. (Add one intentionally if
            # you ever call this from a web page.)
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(payload)

        def _client_key(self) -> str:
            fwd = self.headers.get("X-Forwarded-For", "")
            if fwd:
                return fwd.split(",")[0].strip()
            return self.client_address[0] if self.client_address else "unknown"

        def _token_ok(self) -> bool:
            got = self.headers.get(TOKEN_HEADER, "")
            return bool(config.bundle_token) and hmac.compare_digest(
                got, config.bundle_token
            )

        # ---- routes ----
        def do_GET(self) -> None:  # noqa: N802
            path = self.path.split("?", 1)[0]
            if path in ("/", "/health", "/healthz"):
                self._send_json(
                    200,
                    {
                        "ok": True,
                        "service": "mcat-ai-proxy",
                        "mock": config.mock,
                        "models": sorted(config.allowed_models),
                    },
                )
            else:
                self._send_json(404, {"error": "not found"})

        def do_POST(self) -> None:  # noqa: N802
            path = self.path.split("?", 1)[0]
            if path not in ("/", "/v1/complete"):
                self._send_json(404, {"error": "not found"})
                return
            if not limiter.allow(self._client_key()):
                self._send_json(429, {"error": "rate limit exceeded"})
                return
            if not self._token_ok():
                self._send_json(401, {"error": "unauthorized"})
                return
            try:
                length = int(self.headers.get("Content-Length") or 0)
            except ValueError:
                length = 0
            if length > HARD_BODY_BYTES:
                self._send_json(413, {"error": "request too large"})
                return
            raw = self.rfile.read(length) if length > 0 else b""
            try:
                body = json.loads(raw.decode("utf-8"))
            except Exception:
                self._send_json(400, {"error": "invalid JSON body"})
                return
            try:
                model, messages = _validate_body(body, config)
            except ValueError as exc:
                self._send_json(400, {"error": str(exc)})
                return

            try:
                if config.mock:
                    content = mock_completion(messages)
                else:
                    content = call_openai(
                        messages,
                        model,
                        config.api_key,
                        config.upstream_url,
                        config.upstream_timeout,
                    )
            except UpstreamError as exc:
                self._send_json(exc.status, {"error": str(exc)})
                return
            except Exception as exc:  # pragma: no cover - defensive
                self._send_json(502, {"error": f"proxy error: {exc}"})
                return
            self._send_json(200, {"content": content, "model": model})

        # Minimal, key-safe logging: method + path + status + IP, never bodies.
        def log_message(self, fmt: str, *args) -> None:  # noqa: A003
            sys.stderr.write(
                "%s - %s\n" % (self._client_key(), fmt % args)
            )

    return Handler


# --------------------------------------------------------------------------- #
# Config + CLI
# --------------------------------------------------------------------------- #
def build_config(args: argparse.Namespace) -> ProxyConfig:
    token = (args.token or os.environ.get("MCAT_BUNDLE_TOKEN") or "").strip()
    if not token:
        raise SystemExit(
            "A bundle token is required. Pass --token or set MCAT_BUNDLE_TOKEN "
            "(this is the shared value the app sends; not the LLM key)."
        )
    models_raw = (
        args.allowed_models
        or os.environ.get("MCAT_ALLOWED_MODELS")
        or ",".join(DEFAULT_ALLOWED_MODELS)
    )
    allowed = frozenset(m.strip() for m in models_raw.split(",") if m.strip())

    api_key = ""
    if not args.mock:
        api_key = (os.environ.get("OPENAI_API_KEY") or "").strip()
        if not api_key:
            raise SystemExit(
                "Real mode needs OPENAI_API_KEY in the environment (never a "
                "flag, never committed). Use --mock to run without a key."
            )
    return ProxyConfig(
        bundle_token=token,
        allowed_models=allowed,
        api_key=api_key,
        upstream_url=(
            args.upstream_url
            or os.environ.get("MCAT_UPSTREAM_URL")
            or DEFAULT_UPSTREAM_URL
        ),
        mock=bool(args.mock),
        max_prompt_chars=args.max_prompt_chars,
        max_messages=args.max_messages,
        rate_limit=args.rate_limit,
        rate_window=args.rate_window,
        upstream_timeout=args.upstream_timeout,
    )


def serve(config: ProxyConfig, host: str, port: int) -> ThreadingHTTPServer:
    limiter = RateLimiter(config.rate_limit, config.rate_window)
    httpd = ThreadingHTTPServer((host, port), make_handler(config, limiter))
    return httpd


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="MCAT Speedrun hosted AI proxy.")
    ap.add_argument("--host", default="127.0.0.1", help="bind host")
    ap.add_argument("--port", type=int, default=8787, help="bind port")
    ap.add_argument("--token", default=None, help="bundle token (or MCAT_BUNDLE_TOKEN)")
    ap.add_argument(
        "--mock",
        action="store_true",
        help="echo canned completions (NO upstream, NO key) for local testing",
    )
    ap.add_argument("--allowed-models", default=None, help="comma-separated allowlist")
    ap.add_argument("--upstream-url", default=None)
    ap.add_argument("--max-prompt-chars", type=int, default=DEFAULT_MAX_PROMPT_CHARS)
    ap.add_argument("--max-messages", type=int, default=DEFAULT_MAX_MESSAGES)
    ap.add_argument("--rate-limit", type=int, default=DEFAULT_RATE_LIMIT)
    ap.add_argument("--rate-window", type=int, default=DEFAULT_RATE_WINDOW)
    ap.add_argument("--upstream-timeout", type=float, default=DEFAULT_UPSTREAM_TIMEOUT)
    args = ap.parse_args(argv)

    config = build_config(args)
    httpd = serve(config, args.host, args.port)
    mode = "MOCK (no upstream)" if config.mock else "LIVE (OpenAI upstream)"
    sys.stderr.write(
        f"mcat-ai-proxy listening on http://{args.host}:{args.port}  [{mode}]\n"
        f"  models={sorted(config.allowed_models)} "
        f"rate={config.rate_limit}/{config.rate_window}s\n"
    )
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
