# MCAT Speedrun — hosted AI proxy

Small server that lets the in-app AI assistant work on a grader's machine **with
no API key entered by them**. The app POSTs the same prompts it already builds;
this proxy holds the upstream LLM key **server-side only** and returns the
completion. Scores, questions, and flashcards stay fully local — only the AI
call needs internet.

## Files

| File | What it is |
|---|---|
| `worker.js` + `wrangler.toml` | **Recommended host: Cloudflare Worker** (free, always-on, one-command deploy). |
| `mcat_ai_proxy.py` | Python stdlib reference proxy. `--mock` = local echo (no key) for verification; real mode = self-host on Render/Fly/Railway/VM. Identical wire contract. |
| `mcat-ai-proxy.example.json` | Bundle-config template. Copy to `mcat-ai-proxy.json` next to the launcher and paste your deployed URL + token. **No key here.** |
| `test_mcat_ai_proxy.py` | Proxy unit tests (mocked upstream, token/allowlist/oversize/rate-limit). |

## Quick local verification (no real key)

```bash
py -3.12 proxy/mcat_ai_proxy.py --mock --token testtoken --port 8787
# then, in another shell, point the app/tests at it:
#   MCAT_AI_PROXY_URL=http://127.0.0.1:8787/  MCAT_AI_PROXY_TOKEN=testtoken
```

## Deploy (real, ~10 min)

See **[`../docs/AI-PROXY-SETUP.md`](../docs/AI-PROXY-SETUP.md)** for exact steps
(create host, set key secret + spend cap, deploy, paste URL+token, verify).

## Wire contract

```
POST <proxy_url>            headers: X-MCAT-Bundle-Token: <token>
  body: {"model":"gpt-4o-mini","messages":[{role,content}...]}
  200:  {"content":"<model JSON text>","model":"gpt-4o-mini"}
  non-200: {"error":"..."}   -> app falls back to source-based explanation
GET /health -> {"ok":true,...}
```
