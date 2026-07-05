# AI Proxy — deploy now (~10 min, Windows PowerShell)

You deploy the proxy **once**. Graders never enter an API key. After deploy, paste
the Worker URL + bundle token into `mcat-ai-proxy.json` in the **graded** bundle
folder — **no MSI rebuild**.

Full background: [`AI-PROXY-SETUP.md`](AI-PROXY-SETUP.md). Wire contract:
[`proxy/README.md`](../proxy/README.md).

---

## Before you start (mandatory)

1. **OpenAI hard spend cap** — Dashboard → Settings → Limits → set a **hard monthly
   budget** (e.g. **$5**). Use a **throwaway/scoped** API key.
2. **Cloudflare account** (free): <https://dash.cloudflare.com/sign-up>
3. **Node.js** installed (for `npm` / `wrangler`)

---

## Step 1 — Install wrangler (PowerShell)

```powershell
npm install -g wrangler
wrangler --version
# Must be >= 4.36.0 (rate-limit binding)
```

If `wrangler` is not found, close and reopen PowerShell after install.

---

## Step 2 — Log in to Cloudflare (PowerShell)

```powershell
wrangler login
```

Browser opens once; approve access.

Check login:

```powershell
wrangler whoami
```

---

## Step 3 — Invent a bundle token (PowerShell)

This is **not** the OpenAI key — it is a shared gate the app sends to your Worker.

```powershell
python -c "import secrets; print(secrets.token_urlsafe(24))"
```

Copy the output; you will use it in **Step 4** and **Step 6**.

---

## Step 4 — Set secrets and deploy (PowerShell)

```powershell
cd C:\Users\gpdxi\Downloads\alphaProjects\MCAT\proxy

wrangler secret put OPENAI_API_KEY
# Paste your throwaway OpenAI key when prompted (input is hidden)

wrangler secret put BUNDLE_TOKEN
# Paste the bundle token from Step 3

wrangler deploy
```

Copy the printed URL, e.g. `https://mcat-ai-proxy.<you>.workers.dev`

---

## Step 5 — Verify deploy (PowerShell)

Health (no token required):

```powershell
curl.exe https://mcat-ai-proxy.<you>.workers.dev/health
```

Expected:

```json
{"ok":true,"service":"mcat-ai-proxy","mock":false,"models":["gpt-4o-mini"]}
```

Optional full round-trip (uses a little quota):

```powershell
$token = "<your BUNDLE_TOKEN from Step 3>"
curl.exe -s -X POST "https://mcat-ai-proxy.<you>.workers.dev/" `
  -H "Content-Type: application/json" `
  -H "X-MCAT-Bundle-Token: $token" `
  -d '{\"model\":\"gpt-4o-mini\",\"messages\":[{\"role\":\"system\",\"content\":\"Reply with JSON {\\\"ok\\\":true}\"},{\"role\":\"user\",\"content\":\"ping\"}]}'
```

Wrong/missing token should return `401` with `{"error":"unauthorized"}`.

---

## Step 6 — Fill graded bundle config (no rebuild)

In the **graded** tester folder (unzipped `MCAT-Speedrun/` next to
`Start MCAT Speedrun.cmd`), edit **`mcat-ai-proxy.json`**:

```json
{
  "proxy_url": "https://mcat-ai-proxy.<you>.workers.dev/",
  "bundle_token": "<same BUNDLE_TOKEN as Step 4>",
  "model": "gpt-4o-mini"
}
```

Template with placeholders: [`proxy/mcat-ai-proxy.TEMPLATE.json`](../proxy/mcat-ai-proxy.TEMPLATE.json)

The graded launcher already sets `MCAT_AI_PROXY_CONFIG` to this file. **Do not**
put the OpenAI key here.

If you re-seed the graded bundle:

```powershell
cd C:\Users\gpdxi\Downloads\alphaProjects\anki-MCAT
out\pyenv\Scripts\python.exe tools\mcat_seed_tester.py --out out\tester-dist-graded --with-ai-proxy --keep
```

Then paste real URL + token into the new `mcat-ai-proxy.json`.

---

## Step 7 — Verify in the app (~1 min)

1. Install **`MCAT-Speedrun-graded.msi`** (rebuild first if needed — see
   [`PRE-DEMO-VERIFICATION.md`](PRE-DEMO-VERIFICATION.md)).
2. Double-click **`Start MCAT Speedrun.cmd`** in the graded bundle folder.
3. Start **Practice**, miss a question, open **✨ Assistant**.
4. Pill should read **"AI: On"** with a live per-choice explanation.

| Pill | Likely cause |
|------|----------------|
| **AI: Not set up** | `mcat-ai-proxy.json` missing, placeholder URL, or launcher env not set |
| Source-based fallback | Proxy unreachable — re-check URL, token, `/health` |

---

## Post-deploy verification (copy-paste)

Replace `<URL>` and `<TOKEN>` with your real values:

```powershell
# 1) Health
curl.exe https://<URL>/health

# 2) Auth + completion
curl.exe -s -X POST "https://<URL>/" `
  -H "Content-Type: application/json" `
  -H "X-MCAT-Bundle-Token: <TOKEN>" `
  -d '{\"model\":\"gpt-4o-mini\",\"messages\":[{\"role\":\"user\",\"content\":\"Reply OK\"}]}'

# 3) Local contract tests (no network, no key) — from MCAT repo
cd C:\Users\gpdxi\Downloads\alphaProjects\MCAT
make test-ai-proxy
```

---

## Spend cap reminder

The **hard monthly spend cap on the OpenAI key** is your real cost backstop. The
Worker also rate-limits (20 req / 60 s per IP) and allowlists `gpt-4o-mini` only.
After grading, rotate `BUNDLE_TOKEN` or take the Worker down.

---

## What we cannot automate here

- Creating your Cloudflare account
- Pasting your OpenAI key into `wrangler secret put`
- Running `wrangler deploy` with your credentials

Those steps are **yours** — this doc is the exact sequence.
