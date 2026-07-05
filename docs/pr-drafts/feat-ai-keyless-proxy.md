# feat/ai-keyless-proxy — hosted AI proxy so graders get live AI with no key

> Paste target: `gh pr create --title "feat: keyless hosted AI proxy for the graded build" --body-file docs/pr-drafts/feat-ai-keyless-proxy.md`
> Repos: **MCAT** (proxy + client + docs) and **anki-MCAT** (app pill/status wiring) — open as paired PRs, same branch name, cross-linked.

## Summary (the "why")

Graders won't have — and shouldn't need — an LLM API key, but the marquee
post-MVP feature is a live, per-choice "why is *this* answer wrong" AI Assistant.
This PR adds a **thin authenticated proxy** that holds the upstream key
**server-side only**, so the app does live AI on a grader's machine with **zero
key entered by them**. Scores, questions, and flashcards stay **100% local** —
only the optional AI call touches the network — and the app degrades gracefully
to the offline, source-grounded explanation whenever the proxy is unset,
unreachable, or blocked. It also fixes an honesty bug: the header pill now
reflects the *actual* backend state ("AI: On / Not set up / Off") instead of
claiming "On" while the panel said "not configured."

## What changed

**MCAT (proxy + client + docs)**
- `proxy/worker.js` + `proxy/wrangler.toml` — Cloudflare Worker relay (recommended
  host): one wire contract, one-command deploy.
- `proxy/mcat_ai_proxy.py` — Python-stdlib reference proxy with a `--mock` mode
  (keyless local echo) for verification / optional self-host.
- `proxy/mcat-ai-proxy.example.json` — bundle-config template (URL + token
  placeholders; **never a key**).
- `proxy/README.md` — overview + wire contract (`POST` with
  `X-MCAT-Bundle-Token`; `GET /health`).
- `scripts/ai_explain.py` — new **proxy provider**, selected by
  `build_live_call_model_from_env` when no direct provider is set but a proxy is
  configured; `load_proxy_config` reads `MCAT_AI_PROXY_URL/TOKEN` or a
  `mcat-ai-proxy.json`; canonical `safety_block` gate + `serve_explanation`
  (live → gate → static fallback). *(Shared file — coordinate final content.)*
- `.env.example` — documents `MCAT_AI_PROXY_URL` / `MCAT_AI_PROXY_TOKEN`.
- `Makefile` — `test-ai-proxy` and `proxy-mock` targets. *(Shared file.)*
- `docs/AI-PROXY-SETUP.md` — ~10-min deploy runbook (**hard spend cap first**,
  throwaway/scoped key, deploy, paste URL+token, `/health` check).
- `docs/DECISIONS.md` §32 "Hosted AI proxy — keyless live AI." *(Shared file.)*

**MCAT (tests)**
- `proxy/test_mcat_ai_proxy.py` — 12 proxy-server tests: token (constant-time),
  model allowlist, oversized-prompt + too-many-messages rejection, rate-limit
  trip, mock mode, health.
- `scripts/test_ai_proxy_client.py` — 11 app-side tests: `load_proxy_config`
  precedence + placeholder guard, provider dispatch (proxy vs direct vs AI-off),
  and end-to-end through a **local mock proxy** on an ephemeral port, incl.
  unreachable/bad-token → static fallback.

**anki-MCAT (app wiring)**
- `qt/aqt/mcat/ai_bridge.py` — `ai_provider_configured()`: a toggle-independent,
  network-free config check that drives the pill.
- `qt/aqt/mcat/performance_dialog.py` — honest pill ("AI: On" only when a backend
  is actually configured) + key-agnostic status/fallback copy.

## Security posture (endpoint is internet-reachable)

Enforced in the proxy: shared **bundle-token** header (constant-time compare),
**per-IP rate limiting** (20/60s), upstream **model allowlist** (`gpt-4o-mini`),
**oversized-prompt rejection**, bounded upstream timeout, forced
`temperature=0` + `max_tokens`, minimal key-safe logging. Human-side (documented,
mandatory): a **hard monthly spend cap** + a **throwaway/scoped** key. The key is
**server-side only** — never in the app, bundle, config, or git.

## Test plan

Local (all offline, no key, no network egress — mocked LLM + local mock proxy):

```bash
# app-side + proxy server tests (23 tests)
make test-ai-proxy
# or explicitly:
py -3.12 -m unittest scripts.test_ai_proxy_client proxy.test_mcat_ai_proxy -v
```

Expected: **OK** (23 passed). These run inside **CI** as part of the
`Unit tests` step of `mcat-ci` — see the green check on this PR.

Manual keyless end-to-end (optional):
```bash
make proxy-mock   # starts the local mock on :8787 (no real key)
# point the app/tests at MCAT_AI_PROXY_URL=http://127.0.0.1:8787/ + token
```

## Screenshots / artifacts

- [ ] Header pill in all three states: **AI: On** / **AI: Not set up** / **AI: Off**.
- [ ] Missed-question → ✨ Assistant live per-choice explanation (proxy configured).
- [ ] Same miss with proxy unset → identical **offline source-grounded** fallback.
- [ ] `GET /health` → `{"ok":true,...}` from the deployed Worker.

## Risks / rollback

- **Abuse of the shipped token.** Bounded by spend cap + rate limit + allowlist;
  rotate the token / take the Worker down after grading.
- **Provider outage / latency.** 15s client timeout + safety gate → static
  fallback; the app never hangs or crashes.
- **Rollback:** delete `mcat-ai-proxy.json` (or leave the placeholder) → app
  reverts to fully-offline behavior. Revert the two `anki-MCAT` files to drop the
  pill change; the proxy dir is additive and inert without config.

## Honesty note

- This **intentionally** enables live AI at runtime for the **graded build only**,
  overriding the earlier "AI off at runtime" default (DECISIONS §29). The
  friend-tester build is unchanged and stays offline.
- The pill tells the truth: "AI: On" **only** when a backend is actually
  configured. No key is ever shipped or requested. AI-off / unreachable always
  serves the **static, source-grounded** explanation — so the app is honest and
  fully functional with AI disabled.
- No secrets committed (verified via `git diff --cached --name-only`).
