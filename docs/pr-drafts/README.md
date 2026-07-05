# PR drafts — feature-branch decomposition (for the final-submission commit step)

These are **ready-to-use PR descriptions** for replaying the current uncommitted /
recently-committed work as **clean, feature-scoped branches + PRs**, so the
Speedrun grader sees a real engineering workflow (feature branches → PRs → green
CI) instead of one monolithic dump.

> **Status of this doc (updated 2026-07-05):** originally written by the
> "engineering-workflow" pass as a *plan*. The 8 feature branches below have
> since been **created and committed** locally (each = its baseline + its
> commit(s), 0 behind), but **nothing is pushed** (`MCAT` still has no remote) —
> so the descriptions below remain the ready-to-paste PR bodies and the push /
> remote-auth setup in `docs/FINAL-SUBMISSION-PLAN.md §5` is still pending. The
> verified branch → commit map is in `SUBMISSION-READINESS-AUDIT.md §6`.

The decomposition is grounded in a **read-only** inspection of all three repos on
2026-07-04 (`git status`, `git diff --stat`, `git log`, `git ls-files`). It spans
two repos — `MCAT` (data/eval/docs + proxy) and `anki-MCAT` (the compiled app) —
plus an optional `anki-android-MCAT` branch (§6).

---

## Branch → files map (verified, per repo)

### `feat/ai-keyless-proxy` — hosted AI proxy + app wiring + honest pill
Lets the in-app AI Assistant run on a grader's machine with **no key entered by
them** (key lives server-side on a proxy), with an honest "AI: On / Not set up /
Off" header pill and a graceful offline fallback.

| Repo | File | State | What it is |
|------|------|-------|------------|
| MCAT | `proxy/worker.js` | untracked (new) | Cloudflare Worker relay (recommended host) |
| MCAT | `proxy/wrangler.toml` | untracked (new) | Worker deploy config |
| MCAT | `proxy/mcat_ai_proxy.py` | untracked (new) | Python stdlib reference proxy + `--mock` |
| MCAT | `proxy/test_mcat_ai_proxy.py` | untracked (new) | 12 proxy server tests (token/allowlist/oversize/rate-limit) |
| MCAT | `proxy/README.md` | untracked (new) | proxy overview + wire contract |
| MCAT | `proxy/mcat-ai-proxy.example.json` | untracked (new) | bundle-config template (**no key**) |
| MCAT | `scripts/ai_explain.py` | **modified** (shared*) | proxy provider + `load_proxy_config` + `serve_explanation` |
| MCAT | `scripts/test_ai_proxy_client.py` | untracked (new) | 11 app-side provider/dispatch/e2e tests |
| MCAT | `.env.example` | **modified** | `MCAT_AI_PROXY_URL` / `MCAT_AI_PROXY_TOKEN` docs |
| MCAT | `Makefile` | **modified** (shared*) | `test-ai-proxy`, `proxy-mock` targets |
| MCAT | `docs/AI-PROXY-SETUP.md` | untracked (new) | ~10-min deploy runbook (spend cap first) |
| MCAT | `docs/DECISIONS.md` | **modified** (shared*) | §31 "Hosted AI proxy — keyless live AI" |
| anki-MCAT | `qt/aqt/mcat/ai_bridge.py` | **modified** | `ai_provider_configured()` (network-free config check) |
| anki-MCAT | `qt/aqt/mcat/performance_dialog.py` | **modified** | honest pill/status + key-agnostic copy |

### `feat/graded-strict-build` — strict scoring profile + keyless graded bundle
The graded MSI compiles `SCORE_PROFILE="strict"` (full-course abstention gates)
and the launcher bundle ships the AI-proxy config so the URL/token are set
without a rebuild.

| Repo | File | State | What it is |
|------|------|-------|------------|
| anki-MCAT | `pylib/anki/mcat_scores.py` | committed `2757868ab` | `SCORE_PROFILE` block (strict vs tester gates) |
| anki-MCAT | `qt/aqt/deckbrowser.py` | committed `2757868ab` | provisional-badge + profile-aware dashboard copy |
| anki-MCAT | `tools/mcat_seed_tester.py` | **modified** | `--with-ai-proxy` assembles the launcher bundle (+ FSRS/v3 enable) |
| MCAT | `docs/GRADED-QUICKSTART.md` | untracked (new) | grader-facing "why the scores abstain" quickstart |
| MCAT | `docs/TESTER-QUICKSTART.md` | **modified** (shared*) | graded-build note |
| MCAT | `docs/DECISIONS.md` | **modified** (shared*) | §31 "friend-tester ENGAGEMENT thresholds — NOT graded" |

### `feat/honest-eval-artifacts` — held-out scorer, leakage, AI baseline, summaries
The data-independent proof harness + the honest eval writeups (real leakage/AI
baseline now; held-out Performance abstains, with a clearly-labelled synthetic
pipeline demo standing in until real tester answers arrive).

| Repo | File | State | What it is |
|------|------|-------|------------|
| MCAT | `scripts/score_heldout.py` | committed | held-out grader: accuracy + Wilson 95% CI + per-section/topic; `--demo`, `--responses`, `--make-template` |
| MCAT | `scripts/eval_leakage.py` | committed | dev↔held_out exact/substring + Jaccard; **REAL, reproducible** |
| MCAT | `scripts/ai_eval_explanations.py` | committed | AI-vs-static-vs-TF-IDF choice-specificity (offline); **REAL** |
| MCAT | `scripts/qa_baseline_compare.py` | committed | QA follow-up baseline under cross-model judge; **REAL** |
| MCAT | `scripts/pool_heldout.py` | **in flight (other worker)** | multi-sheet wrapper over `score_heldout.score()` |
| MCAT | `scripts/gen_synthetic_heldout.py` | **in flight (other worker)** | seeded Bernoulli synthetic responder (labelled) |
| MCAT | `docs/EVAL-SUMMARY-GRADED.md` | untracked (new, shared*) | the three graded verdicts (2 abstain, honesty fields) |
| MCAT | `docs/EVAL-SUMMARY-HELDOUT-SYNTHETIC.md` | untracked (new) | labelled-synthetic held-out pipeline demo |
| MCAT | `docs/artifacts/memory-calibration-real.{png,bins.csv,summary.json}` | untracked (new) | REAL calibration (Brier 0.0082, n_test=39) |
| MCAT | `docs/artifacts/ai-explainer-eval.summary.json` | **modified** | refreshed AI-eval artifact |
| MCAT | `out/heldout-collection/answer-sheet.TEMPLATE.json` | untracked (new) | blank tester answer sheet (collection kit) |

### `ci/github-actions` — CI evidence (this pass authored it)
Small, fast, deterministic MCAT-only workflow. **Green on the first run**
(every step verified locally — see `ci-github-actions.md`).

| Repo | File | State | What it is |
|------|------|-------|------------|
| MCAT | `.github/workflows/mcat-ci.yml` | untracked (new) | validate-data + leakage + held-out demo + offline AI eval + paraphrase + 56 unit tests |

### `docs/final-submission` — submission plan, demo scripts, PR drafts
| Repo | File | State | What it is |
|------|------|-------|------------|
| MCAT | `docs/FINAL-SUBMISSION-PLAN.md` | untracked (new, shared*) | tonight/Sunday sequencing + critical path |
| MCAT | `docs/demo/product-ai-demo-runofshow.md` | untracked (new) | combined product+AI demo run-of-show |
| MCAT | `docs/demo/results-demo-outline.md` | untracked (new) | eval-results demo scaffold (fill-in slots) |
| MCAT | `docs/pr-drafts/*` | untracked (new) | these PR drafts + this map |

### `feat/android-three-scores` (optional, §6) — AnkiDroid companion
| Repo | File | State | What it is |
|------|------|-------|------------|
| anki-android-MCAT | (commit `d9dc9b6`) | committed, **stranded** | three-score dashboard (memory/performance/readiness) |
| anki-android-MCAT | (commit `62e9dd0`) | committed, **stranded** | memory-score parity + abstention gates, signing/engine docs, tests |
| anki-android-MCAT | `README.md` | **modified** | fork/build/credit notes |

`*shared` = a file another concurrent worker also owns this weekend. Do not
hand-edit it as part of branch creation beyond `git add`-ing the state it is
already in; coordinate the final content with that worker (see "Shared-file
coordination" below).

---

## Suggested PR order + dependencies

The branches are mostly independent, but two ordering rules make CI green and the
history clean:

```
1. feat/honest-eval-artifacts   (eval scripts, data summaries, artifacts)
2. feat/ai-keyless-proxy        (proxy/ dir + scripts/test_ai_proxy_client.py + app wiring)
3. feat/graded-strict-build     (depends on the proxy for --with-ai-proxy bundling)
4. ci/github-actions            (MUST come after 1 + 2 — see hard dependency below)
5. docs/final-submission        (references all of the above; safe to land last)
6. feat/android-three-scores    (optional; independent repo; needs a personal fork remote)
```

**HARD dependency for a green first CI run.** `.github/workflows/mcat-ci.yml`
runs `proxy.test_mcat_ai_proxy` and `scripts.test_ai_proxy_client`, and imports
the `proxy/` package. Those files live on **`feat/ai-keyless-proxy`**. So the
`ci/github-actions` branch must be cut from a tree that already contains the
proxy work + the eval scripts + `data/` — i.e. **branch it off `main` after
PRs 1 and 2 have merged** (or rebase it on top of them). If CI lands before the
proxy files exist, the two proxy test steps fail with `ModuleNotFoundError`.

**Two-repo note.** `feat/ai-keyless-proxy` and `feat/graded-strict-build` touch
**both** `MCAT` and `anki-MCAT`. Open them as **paired PRs** (one per repo, same
branch name, cross-link them in the descriptions). `MCAT` currently has **no git
remote** and `anki-android-MCAT`'s `origin` is upstream AnkiDroid — see
`docs/FINAL-SUBMISSION-PLAN.md §1a/§5` for the remote/auth setup those pushes
need.

---

## Do-not-commit / coordination notes

- **`scripts/_tmp_judge_worksheet.py`** — scratch file (`_tmp_` prefix). Exclude
  from every branch; delete or leave untracked.
- **`out/`** and **`build/`** — `build/` is gitignored; `out/` holds large
  build/eval scratch in `anki-MCAT` and only the small `heldout-collection/`
  answer-sheet template in `MCAT`. Commit **only** the template
  (`out/heldout-collection/answer-sheet.TEMPLATE.json`), not build logs/MSIs.
- **Secrets:** never stage `.env`, `*.key`, `*.pem`, `credentials.json`, or a
  filled `mcat-ai-proxy.json`. Only the `*.example.json` / `.env.example`
  templates are committed. Run `git diff --cached --name-only` before each commit
  (per `.cursor/rules/command-allowlist.mdc`).
- **Shared-file coordination:** `scripts/ai_explain.py`, `Makefile`,
  `docs/DECISIONS.md`, `docs/EVAL-SUMMARY-GRADED.md`, `docs/FINAL-SUBMISSION-PLAN.md`,
  and `docs/TESTER-QUICKSTART.md` are being edited by a concurrent worker. Take
  their final content as-is when branching; do not re-edit them here.

Each `*.md` beside this file is a full PR description ready to paste into
`gh pr create --body-file …` (or the GitHub UI).
