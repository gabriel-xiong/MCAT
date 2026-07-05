# Pre-demo verification checklist

Generated: **2026-07-05** (local run on pulled `origin/MCAT` + `origin/main`).

Use this before demo/submission. Automated checks were run locally; manual
smoke tests are **your** responsibility on a clean Windows VM or second profile.

Related: [`AI-PROXY-DEPLOY-NOW.md`](AI-PROXY-DEPLOY-NOW.md) (live AI proxy deploy).

---

## Automated results (2026-07-05)

| Check | Command / source | Result | Notes |
|-------|------------------|--------|-------|
| Data validation | `make validate-data` | **PASS** | 170 questions, 18 topics |
| Leakage check | `make eval-leakage` | **PASS** | dev/held_out + pool jaccard OK |
| Synthetic eval battery | `make eval-all-synthetic` | **PASS** | memory, paraphrase, held-out demo, step2, study, AI eval |
| Unit tests | `make test` | **PASS** | 44/44 |
| CI mirror | `make ci-local` | **PASS** | 56/56 (includes proxy server + client) |
| AI proxy tests | `make test-ai-proxy` | **PASS** | 23/23 (mock upstream + local mock server E2E) |
| Rust mastery query | `cargo test -p anki mcat` (anki-MCAT) | **PASS** | 4/4 |
| GitHub Actions | [mcat-ci run #28750817652](https://github.com/gabriel-xiong/MCAT/actions/runs/28750817652) | **PASS** | Merge of `ci/github-actions` → `MCAT` |
| Friend bundle DB clean | `_verify_history_clean.py` on `out/tester-dist/.../mcat-base` | **PASS** | revlog=0, perf_attempts=0, 66 cards, 62 perf Qs |
| Friend bundle AI proxy files | inspect `out/tester-dist/MCAT-Speedrun/` | **FAIL** | Missing `mcat-ai-proxy.json`, `mcat-ai/`, launcher env vars (seeded Jul 4 pre-merge) |
| Graded bundle proxy placeholder | `out/tester-dist-graded/MCAT-Speedrun/mcat-ai-proxy.json` | **PASS** | Placeholder present; needs real URL after deploy |
| Graded MSI exists | `out/graded-build/MCAT-Speedrun-graded.msi` | **STALE** | 619 MB, **2026-07-04 14:35** — built before today's `main` merge |
| Friend MSI exists | `out/graded-build/MCAT-Speedrun-friend.msi` | **STALE** | 637 MB, **2026-07-04 12:03** — predates merge + proxy bundle |
| Live AI proxy deployed | `wrangler whoami` | **NOT DONE** | `wrangler` not installed on this machine; human deploy required |
| wrangler logged in | — | **N/A** | Install wrangler first (see AI-PROXY-DEPLOY-NOW.md) |

---

## Config consistency (proxy)

| Artifact | Status |
|----------|--------|
| `proxy/wrangler.toml` | OK — name, vars, ratelimit binding documented |
| `proxy/worker.js` | OK — matches Python proxy wire contract |
| `proxy/mcat-ai-proxy.example.json` | OK — keys `proxy_url`, `bundle_token`, `model` |
| `proxy/mcat-ai-proxy.TEMPLATE.json` | OK — filled template with placeholders (no secrets) |
| `.env.example` | OK — documents `MCAT_AI_PROXY_URL/TOKEN/MODEL` |
| `scripts/ai_explain.py` `load_proxy_config` | OK — env overrides file; placeholder URLs => proxy OFF |

---

## Rebuild / re-upload decisions

### Friend bundle (Drive zip)

| Item | Verdict |
|------|---------|
| DB history | **Clean** — no reseed required for contamination |
| Bundle contents | **Reseed recommended** — current zip lacks `--with-ai-proxy` artifacts; friend build does not need live AI, but reseed aligns launcher/docs if you ship an updated zip |
| Re-upload to Drive? | **Optional for friend** (DB clean). **Yes** if you reseed or change quickstart |

Reseed command (friend, no AI proxy bits):

```powershell
cd C:\Users\gpdxi\Downloads\alphaProjects\anki-MCAT
out\pyenv\Scripts\python.exe tools\mcat_seed_tester.py --out out\tester-dist
out\pyenv\Scripts\python.exe out\_verify_history_clean.py out\tester-dist\MCAT-Speedrun\mcat-base
```

### Graded MSI + bundle

| Item | Verdict |
|------|---------|
| MSI vs friend | **Different** — graded strict profile (~619 MB) vs friend (~637 MB); sizes differ by design |
| Rebuild after `main` merge? | **YES** — `ai_bridge.py`, `performance_dialog.py`, `mcat_seed_tester.py` merged **2026-07-05**; MSIs dated **Jul 4** |
| Proxy config | Reseed graded bundle with `--with-ai-proxy`, deploy proxy, paste URL into `mcat-ai-proxy.json` |

Graded reseed + proxy placeholder:

```powershell
cd C:\Users\gpdxi\Downloads\alphaProjects\anki-MCAT
out\pyenv\Scripts\python.exe tools\mcat_seed_tester.py --out out\tester-dist-graded --with-ai-proxy
# Then rebuild graded MSI per your existing strict-profile build script
```

---

## Manual smoke test order (~30 min)

Do these on Windows after rebuilding graded MSI and deploying the proxy.

1. **Install graded MSI** (~5 min) — `MCAT-Speedrun-graded.msi`; confirm Anki launches.
2. **Launcher** (~2 min) — from graded bundle folder, run `Start MCAT Speedrun.cmd`; lands on MCAT home (not blank profile).
3. **Three scores** (~5 min) — Dashboard shows **Memory**, **Performance**, **Readiness** separately (not blended). Readiness shows range/coverage or abstention.
4. **Memory mode** (~5 min) — Study flashcards; confirm normal Anki review flow.
5. **Performance gate** (~5 min) — Practice blocked until topic gate (≥3 cards seen, ≥5 Good/Easy); CARS available without gate.
6. **Performance miss + AI** (~5 min) — Miss a question → Assistant panel → pill **"AI: On"** (after proxy deploy + filled JSON). Try follow-up Q&A.
7. **Export data** (~3 min) — Export bundle; confirm JSON sidecar includes perf data.

Friend build smoke (shorter, ~15 min): install friend MSI, launcher, study + export — **no** live AI expected.

---

## Failures to fix before demo

| Priority | Issue | Action |
|----------|-------|--------|
| **P0** | Live AI proxy not deployed | Follow [`AI-PROXY-DEPLOY-NOW.md`](AI-PROXY-DEPLOY-NOW.md); paste URL into graded `mcat-ai-proxy.json` |
| **P0** | Graded MSI stale (Jul 4) | Rebuild strict-profile MSI after `git pull origin main` on anki-MCAT |
| **P1** | Graded bundle proxy JSON still placeholder | Fill after deploy; pill stays "Not set up" until then |
| **P2** | Friend zip missing proxy artifacts | Only matters if you want parity; friend build is offline-by-design |
| **P2** | `wrangler` not installed locally | Install on deploy machine only; not required for CI |

---

## Quick re-run (automated)

```powershell
cd C:\Users\gpdxi\Downloads\alphaProjects\MCAT
git pull origin MCAT
make validate-data
make eval-leakage
make eval-all-synthetic
make test
make ci-local
make test-ai-proxy
```

```powershell
cd C:\Users\gpdxi\Downloads\alphaProjects\anki-MCAT
git pull origin main
cargo test -p anki mcat
out\pyenv\Scripts\python.exe out\_verify_history_clean.py out\tester-dist\MCAT-Speedrun\mcat-base
```

---

## CI reference

Latest green workflow: **mcat-ci** on push to `MCAT` —
https://github.com/gabriel-xiong/MCAT/actions/runs/28750817652

Local mirror: `make ci-local` (same steps as `.github/workflows/mcat-ci.yml`).
