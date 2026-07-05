# MCAT Speedrun — SUBMISSION-READINESS AUDIT

> **Start here for grading:** [`HOW-TO-VERIFY.md`](HOW-TO-VERIFY.md) consolidates
> this audit into a single claim → evidence table with Pass/Fail/Gap status and a
> 5-minute verifier path (`make ci-local`, artifact JSONs).

_Authored 2026-07-05 (overnight hardening pass). Read-only audit of the actual
repos + a fresh green re-verification. Maps every **grader ask** and every **core
product claim** to concrete evidence, flags gaps/weak spots, and ends with a
**prioritized punch-list for the 8-hour Sunday**._

> **Scope note.** This is an evidence/readiness map, not new specs. Baselines,
> branch structure, and eval numbers below were verified live (`git`, local eval
> runs) on 2026-07-05. Honesty rules (three scores never blended; synthetic always
> labelled; abstain rather than fabricate) are treated as pass/fail gates.

---

## 0. TL;DR readiness verdict

**Green where it can be, honestly abstaining where it can't — and the remaining
work is mostly data-independent + on the human-only critical path (push/auth).**

- ✅ **Re-verified GREEN** (2026-07-05): all 6 CI steps + the 5 offline evals pass,
  and the full unit suite is **56 tests OK** on `py -3.12` (and `python` 3.14).
- ✅ **Real, defensible proofs**: leakage/split-integrity (Jaccard 0.56 < 0.70),
  AI-vs-baseline (choice-specificity 1.000 vs 0.000/0.010; QA semantic-judge 90.7%
  vs 59.6%/45.0%), Memory *calibration* (Brier 0.0082, n_test=39).
- ⚠️ **Two scores honestly ABSTAIN** (Performance: no independent held_out answers
  yet; Memory *score*: 0 mature cards; Readiness: both inputs abstain). This is
  **by design**, not a bug — but the grader must be told clearly.
- 🔴 **Top risk is not the code — it's the push/auth foundation.** `MCAT` has **no
  git remote**, `anki-android-MCAT`'s origin is **upstream AnkiDroid** (can't push),
  and **nothing is pushed**, so there is **no live PR list and no green CI run to
  screenshot yet.** Everything is committed on clean feature branches, ready.

---

## 1. Green re-verification snapshot (2026-07-05)

Ran the exact CI steps + offline evals locally. All pass.

| Step (as CI runs it) | Result | Notes |
|---|---|---|
| `scripts/validate_data.py` | ✅ PASS | 170 Q (65 dev / 105 held_out), 18 topics, 45-item pool, 28 paraphrase anchors |
| `scripts/eval_leakage.py` | ✅ PASS | `Leakage check OK`; max stem Jaccard **0.56 < 0.70** |
| `scripts/score_heldout.py --demo` | ✅ PASS | **SYNTHETIC** demo 0.733 (77/105), Wilson [0.642, 0.809] |
| `scripts/ai_eval_explanations.py` | ✅ PASS | OVERALL PASS; choice-spec 1.000 vs 0.000/0.010; gap +0.990; goldset 9/9 |
| `scripts/eval_paraphrase.py` | ✅ PASS | SYNTHETIC-labelled; recall 0.83 − q_acc 0.67 = **gap +0.16** |
| `unittest` (5 modules) | ✅ **56 tests OK** | 33 explainer/QA/judge + 23 proxy client/server; mocked LLM + ephemeral-port mock proxy, no network/key |

Environment: local `py -3.12` = 3.12.10 (**matches CI's `python-version: "3.12"`**);
also green under `python` 3.14.4. Eval scripts are **pure stdlib** (no numpy/scipy/
pandas); `matplotlib` is only lazily imported by `eval_memory.py` / `eval_study_feature.py`,
neither of which CI runs. Running `ai_eval_explanations.py` rewrites a `generated_utc`
timestamp in `docs/artifacts/ai-explainer-eval.summary.json` (numbers byte-identical) —
harmless on CI's ephemeral checkout; the baseline tree was restored locally.

---

## 2. Grader-ask → evidence map

| Grader ask | Concrete evidence (path) | Status | What a grader could challenge |
|---|---|---|---|
| **Held-out eval results** | `scripts/score_heldout.py` (+ `pool_heldout.py`); `docs/EVAL-SUMMARY-GRADED.md` §2; `docs/EVAL-SUMMARY-HELDOUT-SYNTHETIC.md`; `docs/artifacts/heldout-performance-SYNTHETIC.{summary.json,txt}` | ⚠️ **Harness READY; real score ABSTAINS** (0 independent held_out attempts). Labelled-synthetic pipeline demo stands in. | "No real Performance number." → true; abstains by design; a real sheet drops in via one command; instrument is leakage-free. |
| **Baseline comparison** | `scripts/ai_eval_explanations.py` → `docs/artifacts/ai-explainer-eval.summary.json`; `scripts/qa_baseline_compare.py` → `docs/QA-BASELINE-COMPARISON.md` | ✅ **REAL & reproducible** | AI choice-spec 1.000 "too clean" (offline provider is deterministic by construction) → point to the FAIR cross-model semantic judge (90.7/59.6/45.0), which is honest about the parity loss + 1 must_not_say slip. |
| **Leakage check** | `scripts/eval_leakage.py` (`make eval-leakage`) | ✅ **REAL & reproducible** | Jaccard 0.56 "close" to 0.70? → exact/substring overlap is **zero**; 0.56 is the *max* over 28 pairs. |
| **CI evidence** | `.github/workflows/mcat-ci.yml` (branch `ci/github-actions`); README badge | ⚠️ **Green once merged** (see §4 hard dependency); not pushed yet | No live green run to link. → merge order fixes it; verified green locally. |
| **Feature branches + PRs** | 8 branches across 3 repos; 6 PR drafts in `docs/pr-drafts/` | ⚠️ **Committed, NOT pushed** (no remote on `MCAT`) | No live PRs yet → push/auth is the Sunday-AM P0. |
| **Demo strategy** | `docs/demo/product-ai-demo-runofshow.md` (timed narration script); `docs/demo/results-demo-outline.md` (numbers filled) | ✅ **Scripted & filled** (real held-out swap = TODO after 3PM) | Recordings not yet captured (P1). |

## 3. Product-claim → evidence map

| Product claim | Concrete evidence (path) | Status | Notes / weak spots |
|---|---|---|---|
| **Three honest scores, never blended** | `anki-MCAT/pylib/anki/mcat_scores.py` (`SCORE_PROFILE` strict gates, abstention), `pylib/tests/test_mcat_scores.py`, `qt/aqt/deckbrowser.py` (dashboard), `qt/aqt/mcat/mastery_dialog.py`; `docs/EVAL-SUMMARY-GRADED.md`, `docs/PERFORMANCE-MODE-SPEC.md`, `docs/MASTERY-QUERY-SPEC.md` | ✅ code + tests + honest verdicts | Memory score & Readiness abstain today (0 mature cards; no held_out). By design; narrate it. |
| **Why-you-missed / error-typing** | `anki-MCAT/qt/aqt/mcat/performance_dialog.py`, `error_report_dialog.py`, `remediation_dialog.py`, `pylib/anki/mcat_perf.py`, `pylib/tests/test_mcat_perf.py`; `docs/ERROR-DIAGNOSIS-SPEC.md`; bank `choice_feedback`/choice-tags in `data/questions.json` | ✅ code + spec + tests | Error-type inference is heuristic ("hypothesis, not verdict"); `w_mis` tuning is explicitly deferred (LOOSE-ENDS). Fine for prototype. |
| **AI tutor + AI-off fallback** | `MCAT/scripts/ai_explain.py` (`serve_explanation`, offline fallback, lazy SDKs), `MCAT/proxy/*` (keyless hosted proxy + 12 server tests), `scripts/test_ai_proxy_client.py` (11 tests), `anki-MCAT/qt/aqt/mcat/ai_bridge.py` (network-free config check), `performance_dialog.py` (honest pill); `docs/AI-FEATURE.md`, `docs/AI-PROXY-SETUP.md`, `docs/QA-BASELINE-COMPARISON.md` | ✅ code + tests + baseline eval | Proxy **deploy** (Cloudflare + key + spend cap) is a ~10-min human step (not done here — needs creds). Until then the pill honestly reads "Not set up". |
| **Observability / honesty instrumentation** | `anki-MCAT/tools/mcat_export_perf.py`, `mcat_import_perf.py`, `mcat_export_bundle.py`, `mcat_undo_integrity_check.py`, `mcat_latency_bench.py`; `docs/LATENCY-RELIABILITY.md`, `docs/UNDO-INTEGRITY-PROOF.md`, `docs/ARCHITECTURE.md` | ✅ export/calibration tools + docs | Local sidecar only; no telemetry/network/AI in scoring path — matches the claim. |

## 4. Honesty / leakage / synthetic-labelling audit (highest-scrutiny)

This is where a Speedrun grader will push hardest (honesty is an automatic-fail
gate). Findings — all **PASS**, with the caveats named:

- **No score blending.** Memory / Performance / Readiness are computed and displayed
  separately; Readiness is a mapped range or abstains — never a blend, never a bare
  number. Enforced in `mcat_scores.py` and asserted across `EVAL-SUMMARY-GRADED.md`.
  ✅
- **Abstention integrity.** Every reported score carries the required honesty fields
  (value-or-abstain, n, coverage %, confidence/CI, missing-data note, single next
  action). Memory score abstains (0/133 mature; longest interval 4 d), Performance
  abstains (0 independent held_out), Readiness abstains (both inputs do). ✅
- **Synthetic labelling is rigorous and verifiable.** `heldout-performance-SYNTHETIC.summary.json`
  carries `"synthetic": true`, `"is_real_data": false`, per-file `synthetic:true`,
  and a `missing_data_note`; the `.txt` opens with a **`[SYNTHETIC — PIPELINE DEMO
  ONLY, NOT REAL DATA]`** banner; filenames contain `SYNTHETIC`; `score_heldout.py
  --demo` prints a `[SYNTHETIC demo … NOT real … data]` header; `eval_paraphrase.py`
  prints `[synthetic demo …]`. The synthetic responder is a documented, seeded
  Bernoulli generator (`gen_synthetic_heldout.py`) capped at p ≤ 0.90 so it can
  never trivially hit 100%. ✅
- **Leakage is real and reproducible.** dev(65)/held_out(105) have zero exact/
  substring overlap; max paraphrase-pair Jaccard 0.56 < 0.70; pool check passes.
  Deterministic — re-runs byte-identical. ✅
- **AI eval separates the confounded from the fair instrument.** The offline
  choice-specificity (1.000) is deterministic-by-construction and labelled as such;
  the honest headline is the **cross-model semantic judge** (Anthropic grading
  OpenAI answers; same-family judging is refused by `ai_judge.py`), which reports
  AI 90.7% vs static 59.6% vs keyword 45.0% **and** openly states the parity-item
  loss (90.8% vs 94.4%) and the single `must_not_say` violation (g060). ✅
- **No AI in the Wednesday deliverable / scoring path.** AI is post-answer
  explanation only; scoring reads the local bank/sidecar; provider SDKs are lazy. ✅

**Residual honesty risk to manage on camera:** the *only* real performance-style
numbers are synthetic (labelled) or builder-self-test on the dev split. Do **not**
let the synthetic 0.733/0.559 be read as a learning outcome — always say "pipeline
demo, not a result," and swap in the real held_out sheet the moment it arrives.

## 5. GitHub-CI gotcha findings (from a clean-runner perspective)

Inspected `.github/workflows/mcat-ci.yml` + `requirements.txt` for things that pass
locally but could fail on a fresh `ubuntu-latest` runner.

1. 🔴 **HARD dependency (do not "fix" by vendoring): the two proxy test steps live
   on another branch.** CI runs `scripts.test_ai_proxy_client` + `proxy.test_mcat_ai_proxy`
   and imports `proxy/`; those files exist **only on `feat/ai-keyless-proxy`**. The
   `ci/github-actions` branch was cut from the *old* `master`, so its tree lacks
   `proxy/` → those two steps fail with `ModuleNotFoundError` if run before the proxy
   work is in the tree. **Resolution (already documented in the workflow header +
   `pr-drafts/README.md`): cut/rebase `ci/github-actions` off `main` AFTER
   `feat/ai-keyless-proxy` (and eval-artifacts) merge.** Not a code bug — a merge-order
   requirement. With the proxy files present, the exact line is green locally (56/56).
2. 🟡 **`requirements.txt` pins are unverifiable offline.** `openai==2.44.0`,
   `anthropic==0.115.1` must resolve on PyPI for py3.12/ubuntu or the *install* step
   fails (RED) before any test — even though **no CI step needs them** (offline/mocked).
   Verify both resolve on first push. (Not blind-editing: they were "resolved 2026-07-02"
   so are probably valid; a bad pin is the single highest-impact avoidable RED.)
3. 🟢 **No hidden third-party imports; data paths are `__file__`-relative** (working-
   directory independent), so no CWD assumption breaks on the runner.
4. 🟡 **README badge slug** points at `github.com/gabriel-xiong/MCAT` (consistent with
   the `anki-MCAT` owner). It 404s until the `MCAT` repo is pushed under exactly that
   owner/name (case-sensitive). Verify on push.
5. 🟢 **`on: push`/`pull_request` unfiltered** + `concurrency` cancel-in-progress —
   fine; just note every branch push triggers a run, so only push `ci/github-actions`
   once its tree contains the proxy files (see #1).

**Contained fixes applied:** none. The one structural issue (#1) is explicitly
off-limits to "fix," and #2/#4 are unverifiable offline (blind edits would risk the
clean, working state). All reported for the human to action on push.

## 6. Branch / PR integrity (verified read-only, 2026-07-05)

Baselines match exactly, every feature branch is baseline **+ its commit(s), 0 behind**:

| Repo | Baseline | Feature branches (ahead by 1) |
|---|---|---|
| `MCAT` | `master` @ `1d7db18` (no remote) | `feat/honest-eval-artifacts` `7b3f919`, `feat/ai-keyless-proxy` `6fa7137`, `feat/graded-strict-build` `4478fe2`, `ci/github-actions` `b64ccc3`, `docs/final-submission` `6a3bbea` |
| `anki-MCAT` | `main` @ `2757868ab` (origin ahead 1, pre-existing) | `feat/ai-keyless-proxy` `d3f604c0f`, `feat/graded-strict-build` `0d407afb2` |
| `anki-android-MCAT` | `main` @ `62e9dd0` (origin = upstream AnkiDroid) | `feat/android-three-scores` `9206c22` |

8 feature branches total; **6 PR drafts** cover them (`feat/ai-keyless-proxy` and
`feat/graded-strict-build` are **paired** across `MCAT` + `anki-MCAT`, one draft each).
Push order (from `pr-drafts/README.md`): honest-eval-artifacts → ai-keyless-proxy →
graded-strict-build → **ci/github-actions (after the first two)** → docs/final-submission
→ android (optional). **No discrepancies.** Pre-existing facts (not introduced here):
`MCAT` has no remote; `anki-MCAT/main` is 1 ahead of `origin`; the android `origin`
is upstream (feature branch needs a personal fork to publish).

---

## 7. Prioritized punch-list for the 8-hour Sunday

**P0 — must land or the deadline is at risk (data-independent; human/creds-gated):**
1. **Prove push auth + push everything.** Create/point the `MCAT` remote; ensure a
   push path for the android fork. Push all 8 branches, open the 6 PRs from the
   drafts (paired PRs cross-linked). Without this there is no live PR list / CI run.
2. **Make CI actually green on GitHub:** cut/rebase `ci/github-actions` off `main`
   only **after** `feat/ai-keyless-proxy` (+ eval-artifacts) merge, so the tree has
   `proxy/`. Confirm the first run is green; screenshot it. Verify the two
   `requirements.txt` pins resolve (§5.2) and the badge slug (§5.4).
3. **Confirm the 3PM held_out collection path end-to-end** with a dry-run sheet, so
   when real answers arrive the swap is one command (`pool_heldout.py`).

**P1 — high value, mostly data-independent:**
4. **Deploy the AI proxy** (~10 min: Cloudflare Worker + OpenAI key + hard spend cap
   → paste URL/token into `mcat-ai-proxy.json`, no rebuild). Flips the pill to "AI: On"
   for the demo.
5. **Record the demo** using the now-timed `product-ai-demo-runofshow.md`; capture
   the open recordings (desktop memory-review from source, clean-machine MSI install,
   phone-review video, sync clip).
6. **At 3PM:** run the real held_out sheet(s) → fill `results-demo-outline.md` D2 +
   `EVAL-SUMMARY-GRADED.md` §2; keep per-tester + pooled, never merged; report vs the
   0.25 chance floor. If <30 attempts, label INDICATIVE (not a strict graded score);
   if zero arrive, keep ABSTAIN + the labelled-synthetic demo — do **not** fabricate.

**P2 — nice-to-have / verify:**
7. Publish the `anki-android-MCAT` branch to a **personal fork** (origin is upstream;
   optional companion PR).
8. Optionally refresh Memory calibration on a tester's revlog (`make eval-memory
   MCAT_COLLECTION=…`) — still abstains on the score (maturity takes weeks), but the
   calibration plot gets more points.
9. Assemble the artifact packet (checklist at the bottom of `results-demo-outline.md`).

---

## 8. Things a grader could challenge — and the honest answer

- **"Your Performance score is synthetic."** → It **abstains**; the synthetic run is
  a *labelled pipeline demonstration*, not a score. The instrument is complete and
  leakage-free; a real independent sheet converts it to a real, Wilson-bounded value
  with one command.
- **"n=1 for Memory."** → Correct and stated. Memory *calibration* is real (Brier
  0.0082, n_test=39) but the *score* abstains (no mature card — physically impossible
  at ~3 days of history). We show restraint, not a flattering guess.
- **"AI choice-specificity 1.000 is suspicious."** → That offline metric is
  deterministic by construction and labelled; the fair evidence is the cross-model
  semantic judge (90.7/59.6/45.0), which is honest about where AI *loses* (parity
  items) and its one `must_not_say` slip.
- **"CI isn't green in the repo."** → It's verified green locally (56/56); on GitHub
  it goes green once the proxy branch is in the tree (documented merge order). A RED
  build would be worse than none — hence the deliberately small, fast MCAT-only
  workflow rather than the heavy inherited Anki/AnkiDroid CI.
