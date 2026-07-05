# AI Proxy Setup — keyless live AI for the graded build (~10 min)

_Goal:_ make the in-app AI assistant work on **graders' own machines with NO API
key entered by them**, by routing requests through a tiny **hosted proxy** that
holds the real upstream key **server-side only**. Flashcards, questions, and all
three scores stay 100% local and offline — **only the AI call needs internet.**

You (the builder) do this **once**. After it's deployed, you paste the URL +
token into one small JSON file in the tester bundle — **no app rebuild needed**
to set or change the URL.

> **You will NOT commit any secret.** The upstream LLM key lives only as an
> encrypted secret on the proxy host. The bundle "token" in the config file is a
> low-grade shared gate (not a real credential) — see [Security](#security).

---

## What you're deploying

`proxy/worker.js` — a ~150-line Cloudflare Worker. It accepts the app's
explanation / follow-up requests, calls OpenAI (`gpt-4o-mini`) with a key stored
as a Worker **secret**, and returns the completion. It enforces: a bundle-token
header, per-IP rate limiting, a model allowlist, oversized-prompt rejection, and
a bounded upstream timeout.

**Why Cloudflare Workers** (over Render/Fly/Railway/Vercel): free tier that
**does not sleep** (no cold-start "first request hangs 30s" like Render's free
web service), a **single-command deploy** (`wrangler deploy`), **one-command
secrets** (`wrangler secret put`), and it returns a working `https://…workers.dev`
URL immediately. Simplest "create project → set secret → deploy → get URL" flow.
(If you'd rather self-host, `proxy/mcat_ai_proxy.py` speaks the identical
contract — run it on any box and use its URL instead; see the bottom.)

---

## Steps

### 0. Prerequisites (~2 min)
- A **Cloudflare account** (free): <https://dash.cloudflare.com/sign-up>.
- An **OpenAI API key** — create a **fresh, scoped, throwaway** key at
  <https://platform.openai.com/api-keys>.
- **Node + wrangler** (the Cloudflare CLI), version **≥ 4.36** (needed for the
  stable rate-limit binding):
  ```bash
  npm install -g wrangler
  wrangler --version        # confirm >= 4.36.0
  ```

### 1. Set a HARD spend cap on the OpenAI key (~1 min) — do this FIRST
OpenAI dashboard → **Settings → Limits** → set a **hard monthly budget** (e.g.
**$5**). This is your real cost backstop if the token ever leaks. Prefer a key
scoped to only what's needed. **Do this before deploying**, not after.

### 2. Deploy the Worker (~3 min)
```bash
cd MCAT/proxy
wrangler login                         # opens a browser once
wrangler secret put OPENAI_API_KEY     # paste your throwaway OpenAI key
wrangler secret put BUNDLE_TOKEN       # paste a token YOU invent (see below)
wrangler deploy                        # prints: https://mcat-ai-proxy.<you>.workers.dev
```
- **Invent the BUNDLE_TOKEN** yourself — any long random string, e.g. run
  `python -c "import secrets;print(secrets.token_urlsafe(24))"`. You'll paste the
  **same** value into the bundle config in step 4.
- Copy the printed **`https://…workers.dev`** URL.

### 3. Verify the deploy is up (~1 min)
```bash
curl https://mcat-ai-proxy.<you>.workers.dev/health
# -> {"ok":true,"service":"mcat-ai-proxy","mock":false,"models":["gpt-4o-mini"]}
```
Optional full round-trip (uses a little quota):
```bash
curl -s -X POST https://mcat-ai-proxy.<you>.workers.dev/ \
  -H "Content-Type: application/json" \
  -H "X-MCAT-Bundle-Token: <your BUNDLE_TOKEN>" \
  -d '{"model":"gpt-4o-mini","messages":[{"role":"system","content":"Reply with JSON {\"ok\":true}"},{"role":"user","content":"ping"}]}'
# -> {"content":"{ ... }","model":"gpt-4o-mini"}
# A wrong/missing token returns {"error":"unauthorized"} (401) — good.
```

### 4. Paste URL + token into the bundle config (~1 min) — NO rebuild
In the tester bundle folder (the unzipped **`MCAT-Speedrun/`**, next to
`Start MCAT Speedrun.cmd`), open **`mcat-ai-proxy.json`** and fill in:
```json
{
  "proxy_url": "https://mcat-ai-proxy.<you>.workers.dev/",
  "bundle_token": "<the same BUNDLE_TOKEN you set in step 2>",
  "model": "gpt-4o-mini"
}
```
> This is the **only** file to edit, and it is **not compiled into the MSI** —
> the launcher points the app at it. Change the URL/token here anytime with no
> rebuild. **Do NOT put the OpenAI key here** — it stays on the proxy.

### 5. Verify in the app (~1 min)
Launch via **`Start MCAT Speedrun.cmd`**, start a Practice session, miss a
question, open the **✨ Assistant**. The pill should read **"AI: On"** and the
explanation is the live, per-choice answer. If the pill says **"AI: Not set up"**
the JSON wasn't found/filled; if it says a source-based fallback, the proxy was
unreachable (check the URL/token and `/health`).

Done. Graders never see any of this — they just get live AI.

---

## Security

The endpoint is internet-reachable, so these are enforced (see `proxy/worker.js`
and `proxy/mcat_ai_proxy.py`) — and a few are on **you**:

| Control | Where | Notes |
|---|---|---|
| Upstream key server-side only | host secret | Never in the app, bundle, config, or git. |
| **Hard monthly spend cap** | **you (OpenAI dashboard)** | The real cost backstop — **mandatory**, step 1. |
| Throwaway / scoped key | **you** | So it can be revoked without collateral. |
| Bundle-token header | proxy | Constant-time compare; blocks casual/open abuse. |
| Per-IP rate limiting | proxy | 20 req / 60s per IP (tune in `wrangler.toml`). |
| Model allowlist | proxy | Only `gpt-4o-mini` by default — no model-shopping. |
| Oversized-prompt rejection | proxy | Byte + message-count + char caps. |
| Bounded upstream timeout | proxy | ~20s server-side; app keeps its 15s client timeout. |
| Forced `temperature=0` + `max_tokens` | proxy | Bounds behavior + per-call cost. |

**Residual risk:** the bundle token ships to graders, so a determined grader (or
someone who extracts it) could use the proxy as a *constrained* gpt-4o-mini relay
(allowlisted model, rate-limited, size-capped). **Mitigations:** the hard spend
cap caps worst-case dollars; the rate limit blunts bursts; rotate `BUNDLE_TOKEN`
(re-run `wrangler secret put BUNDLE_TOKEN` and update the JSON) or take the Worker
down after grading. This is an accepted trade-off for keyless grading.

---

## Alternative host (self-hosted Python)

`proxy/mcat_ai_proxy.py` implements the **identical** contract with the Python
standard library (no deps). Real mode:
```bash
export OPENAI_API_KEY=sk-...          # host env; never committed
export MCAT_BUNDLE_TOKEN=<token>
py -3.12 proxy/mcat_ai_proxy.py --host 0.0.0.0 --port 8787
```
Deploy that process behind HTTPS on Render / Fly.io / Railway / a VM, then use
its public URL in `mcat-ai-proxy.json`. For **local testing with no key at all**,
use `--mock` (see `proxy/README.md`).
