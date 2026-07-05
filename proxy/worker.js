/**
 * MCAT Speedrun — hosted AI proxy (Cloudflare Worker).
 *
 * Recommended turnkey host. Speaks the SAME wire contract as
 * proxy/mcat_ai_proxy.py so the app is host-agnostic:
 *
 *   POST /                 (also POST /v1/complete)
 *     headers: Content-Type: application/json
 *              X-MCAT-Bundle-Token: <bundle token>
 *     body:    {"model":"gpt-4o-mini",
 *               "messages":[{"role":"system","content":...},
 *                           {"role":"user","content":...}]}
 *     200:     {"content":"<model text>","model":"gpt-4o-mini"}
 *     non-200: {"error":"<reason>"}
 *
 *   GET / | /health        -> {"ok":true,"service":"mcat-ai-proxy",...}
 *
 * Secrets & config (set via `wrangler secret put` / `[vars]`, NEVER in code):
 *   OPENAI_API_KEY   (secret)  upstream key — server-side only, never returned.
 *   BUNDLE_TOKEN     (secret)  shared token the app must send.
 *   ALLOWED_MODELS   (var)     comma-separated allowlist (default gpt-4o-mini).
 *   UPSTREAM_URL     (var)     default https://api.openai.com/v1/chat/completions
 *   MAX_PROMPT_CHARS (var)     default 12000
 *   MAX_MESSAGES     (var)     default 8
 *
 * Security enforced here: bundle-token gate (constant-time), per-IP rate limit
 * (native ratelimits binding, see wrangler.toml), model allowlist, oversized-
 * prompt rejection, bounded upstream timeout, method/path allowlist, default-
 * deny CORS. The hard monthly SPEND CAP + a throwaway/scoped key are a HUMAN
 * step on the OpenAI dashboard (see docs/AI-PROXY-SETUP.md).
 */

const TOKEN_HEADER = "x-mcat-bundle-token";
const DEFAULT_UPSTREAM = "https://api.openai.com/v1/chat/completions";
const DEFAULT_MODELS = "gpt-4o-mini";
const HARD_BODY_BYTES = 64 * 1024;
const UPSTREAM_TEMPERATURE = 0;
const UPSTREAM_MAX_TOKENS = 1024;
const UPSTREAM_TIMEOUT_MS = 20000;

function json(status, obj) {
  return new Response(JSON.stringify(obj), {
    status,
    headers: {
      "content-type": "application/json",
      "cache-control": "no-store",
    },
  });
}

// Constant-time string compare (avoids leaking the token via timing).
function safeEqual(a, b) {
  if (typeof a !== "string" || typeof b !== "string") return false;
  if (a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i++) diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return diff === 0;
}

function clientKey(request) {
  const fwd = request.headers.get("CF-Connecting-IP") ||
    request.headers.get("x-forwarded-for") || "";
  return fwd ? fwd.split(",")[0].trim() : "unknown";
}

function validateBody(body, allowedModels, maxMessages, maxChars) {
  if (typeof body !== "object" || body === null) return "body must be a JSON object";
  const model = String(body.model || "").trim();
  if (!model) return "missing 'model'";
  if (allowedModels.length && !allowedModels.includes(model)) {
    return `model '${model}' is not allowed`;
  }
  const messages = body.messages;
  if (!Array.isArray(messages) || messages.length === 0) return "missing 'messages'";
  if (messages.length > maxMessages) return "too many messages";
  let total = 0;
  for (const m of messages) {
    if (typeof m !== "object" || m === null || !("role" in m) || !("content" in m)) {
      return "each message needs 'role' and 'content'";
    }
    total += String(m.content || "").length;
  }
  if (total > maxChars) return "prompt too large";
  return null;
}

async function callOpenAI(messages, model, apiKey, upstreamUrl) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), UPSTREAM_TIMEOUT_MS);
  let resp;
  try {
    resp = await fetch(upstreamUrl, {
      method: "POST",
      signal: controller.signal,
      headers: {
        "authorization": `Bearer ${apiKey}`,
        "content-type": "application/json",
      },
      body: JSON.stringify({
        model,
        temperature: UPSTREAM_TEMPERATURE,
        max_tokens: UPSTREAM_MAX_TOKENS,
        response_format: { type: "json_object" },
        messages,
      }),
    });
  } catch (e) {
    clearTimeout(timer);
    return { status: 504, error: "upstream transport error / timeout" };
  }
  clearTimeout(timer);
  if (!resp.ok) {
    let detail = "";
    try { detail = (await resp.text()).slice(0, 200); } catch (_) {}
    const status = resp.status === 408 || resp.status === 504 ? 504 : 502;
    return { status, error: `upstream HTTP ${resp.status}: ${detail}` };
  }
  let data;
  try { data = await resp.json(); } catch (_) {
    return { status: 502, error: "unexpected upstream body" };
  }
  const content = data?.choices?.[0]?.message?.content;
  if (content == null) return { status: 502, error: "unexpected upstream shape" };
  return { content };
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const path = url.pathname;
    const allowedModels = String(env.ALLOWED_MODELS || DEFAULT_MODELS)
      .split(",").map((s) => s.trim()).filter(Boolean);
    const maxMessages = parseInt(env.MAX_MESSAGES || "8", 10);
    const maxChars = parseInt(env.MAX_PROMPT_CHARS || "12000", 10);
    const upstreamUrl = env.UPSTREAM_URL || DEFAULT_UPSTREAM;

    if (request.method === "GET" && (path === "/" || path === "/health" || path === "/healthz")) {
      return json(200, {
        ok: true,
        service: "mcat-ai-proxy",
        mock: false,
        models: allowedModels,
      });
    }
    if (request.method !== "POST") return json(405, { error: "method not allowed" });
    if (path !== "/" && path !== "/v1/complete") return json(404, { error: "not found" });

    // Per-IP rate limiting via the native binding (see wrangler.toml). If the
    // binding isn't configured, fail OPEN here but rely on the spend cap.
    if (env.MCAT_RATE_LIMITER) {
      try {
        const { success } = await env.MCAT_RATE_LIMITER.limit({ key: clientKey(request) });
        if (!success) return json(429, { error: "rate limit exceeded" });
      } catch (_) { /* limiter unavailable -> continue; spend cap is the backstop */ }
    }

    if (!env.BUNDLE_TOKEN || !safeEqual(request.headers.get(TOKEN_HEADER) || "", env.BUNDLE_TOKEN)) {
      return json(401, { error: "unauthorized" });
    }
    if (!env.OPENAI_API_KEY) return json(500, { error: "proxy misconfigured (no upstream key)" });

    const lenHeader = parseInt(request.headers.get("content-length") || "0", 10);
    if (lenHeader > HARD_BODY_BYTES) return json(413, { error: "request too large" });

    let body;
    try { body = await request.json(); } catch (_) {
      return json(400, { error: "invalid JSON body" });
    }
    const bad = validateBody(body, allowedModels, maxMessages, maxChars);
    if (bad) return json(400, { error: bad });

    const result = await callOpenAI(body.messages, String(body.model).trim(), env.OPENAI_API_KEY, upstreamUrl);
    if (result.error) return json(result.status, { error: result.error });
    return json(200, { content: result.content, model: String(body.model).trim() });
  },
};
