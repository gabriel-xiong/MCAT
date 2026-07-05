# MCAT Speedrun — FINAL-SUBMISSION execution plan

_Authored: 2026-07-04 (Sat eve). Owner: Gabriel (solo builder). Deadline: Sun
2026-07-05, with ~3 independent tester datasets expected **by ~3PM Sun**._

> **How to read this.** Everything below is grounded in the actual repos as of
> tonight (read-only git + file inspection — see "Verified state"). This is a
> sequencing/critical-path plan, not new specs. It answers one question above all:
> **what must happen TONIGHT so the Sunday deadline lands even though the tester
> data doesn't arrive until ~3PM.**

---

## 0. TL;DR — the tonight answer (read this first)

**Yes — you must spend ~2.5–3.5h tonight.** Not on features; on the three things
that are (a) on the critical path, (b) slow/uncertain, and (c) the grader
explicitly called out. If any of these slips to Sunday, the deadline is at risk:

1. **De-risk the 3PM data drop — held-out answers are NOT currently being
   collected (highest risk).** `docs/TESTER-QUICKSTART.md` tells testers to review
   flashcards + *optionally* answer **dev-split practice** questions. It does **not**
   ask them to answer the **105 frozen `held_out`** questions, and the exported
   `*.perf_bundle.json` carries **practice (dev) answers + memory revlog**, not
   `held_out` responses. So by default the 3PM datasets unblock **Memory
   calibration**, **not** the held-out **Performance** score the grader wants.
   **Tonight:** confirm what the 3 testers were actually asked; if held-out isn't
   part of their task, send them the held-out questionnaire + blank answer sheet
   **tonight** so answers can arrive by 3PM, and pre-test the scorer end-to-end.
2. **Engineering workflow foundation (unstarted + grader-called-out + auth is
   unproven).** `MCAT` has **no git remote at all**; `anki-android-MCAT`'s `origin`
   points at **upstream ankidroid** (can't push — 2 commits stranded); there is
   **no `gh` CLI and no git credential helper** on this machine; and there are
   **zero feature branches / PRs anywhere**. Prove push auth works and land first
   pushes tonight — if auth fails you want to find out now, not at noon Sunday.
3. **Deploy the AI proxy (~10 min).** It's a hard external dependency (Cloudflare +
   OpenAI key + spend cap). Do it tonight to take it off Sunday's plate entirely.

Everything else (feature-branch/PR workflow, CI workflow, demo script, most
recordings, the eval-summary rewrite) is data-independent and fits into Sunday —
**but only if the auth/remote foundation and the held-out collection path are laid
tonight.** The good news: the **eval harness is already built and dry-run-proven**,
so the 3PM data drop is a *quick pre-tested run*, not new engineering.

---

## 1. Verified state (DONE vs OPEN) — grounded in the repos tonight

### 1a. Engineering-workflow / git state (read-only `git` in all three repos)

| Repo | Branch | Remote(s) | Pushed? | Working tree | Branches / PRs |
|------|--------|-----------|---------|--------------|----------------|
| `MCAT` | `master` | **NONE** | n/a — no remote exists | dirty: `proxy/` (untracked), `docs/AI-PROXY-SETUP.md`, `docs/EVAL-SUMMARY-GRADED.md`, `docs/GRADED-QUICKSTART.md`, artifacts, `scripts/*`, modified `Makefile`, `.env.example`, `docs/DECISIONS.md`, `docs/TESTER-QUICKSTART.md`, `scripts/ai_explain.py` | **none** |
| `anki-MCAT` | `main` | `origin` = `github.com/gabriel-xiong/anki-MCAT`, `upstream` = ankitects/anki | `origin/main` tracks **`5ff403f42`**; local is **ahead by 1** (`2757868ab` friend build, **unpushed**) | dirty: `qt/aqt/mcat/ai_bridge.py`, `qt/aqt/mcat/performance_dialog.py`, `tools/mcat_seed_tester.py` | **none** |
| `anki-android-MCAT` | `main` | `origin` = **`github.com/ankidroid/Anki-Android`** (UPSTREAM, not a fork) | local **ahead by 2** (`62e9dd0`, `d9dc9b6`) — **stranded** (no push rights to upstream) | dirty: `README.md` | **none** |

**Auth tooling:** `gh` is **not installed**; `credential.helper` is **not set** in
`anki-MCAT`. Any push needs auth set up first (PAT-in-URL, git credential manager,
or install `gh` + `gh auth login`).

> **Honesty note / discrepancy to verify.** The task brief said "anki-MCAT was
> reportedly never pushed." The git data disagrees: `origin/main` points at a
> builder MCAT commit (`5ff403f42`), which can only happen via a **successful push
> or fetch** — i.e. the fork *was* published through `5ff403f42`. This may be a
> stale remote-tracking ref, so **verify live** (open `github.com/gabriel-xiong/anki-MCAT`
> once creds work). Either way, the actionable facts are unchanged: the final
> friend-build commit + 3 working-tree edits are unpushed, and **no feature
> branches or PRs exist in any repo.**

### 1b. CI state (`.github/workflows/` in all three)

- `MCAT`: **no `.github/` at all → no CI.** This is the repo that holds the eval
  harness + data + docs, so it's the natural home for lightweight, green,
  MCAT-specific CI evidence.
- `anki-MCAT`: inherits **upstream Anki's** heavy workflows (`ci.yml`,
  `release.yml`, `prepare-release.yml`, `docs-site.yml`, …). These build all of
  Anki and expect upstream secrets/runners — they are **not good "CI evidence"** on
  a fork (slow, likely red/skipped). Prefer a small MCAT-scoped job.
- `anki-android-MCAT`: inherits **upstream AnkiDroid's** 16 workflows (emulator
  tests, CodeQL, screenshot compare, …) — same problem.

**Conclusion:** CI evidence should be a **new, small workflow** (run the MCAT
Python tests + `validate-data` + `eval-leakage`), not the inherited upstream CI.
Template provided in §5.

### 1c. Eval / proof-artifact state — **the harness is largely BUILT**

| Grader ask | Artifact / script (exists) | State |
|------------|---------------------------|-------|
| **Held-out eval results** | `scripts/score_heldout.py` (accuracy + Wilson 95% CI + per-section/topic; `--make-template`, `--responses`, `--demo`, `--emit-attempts`) | **Harness READY & dry-run-proven** (`build/heldout-answers.TEMPLATE.json` etc. already generated). **Blocked only on real tester `held_out` answers.** |
| **Baseline comparison** | `scripts/qa_baseline_compare.py` → `docs/QA-BASELINE-COMPARISON.md` (AI vs static vs keyword, token scorer + cross-model semantic judge) | **DONE** (data-independent). Add a trivial held-out "vs 25% chance" line post-3PM. |
| **Leakage check** | `scripts/eval_leakage.py` (`make eval-leakage`): dev↔held_out exact/substring + Jaccard; pool leakage; paraphrase-pair check | **DONE & reproducible** (Jaccard 0.56 < 0.70). Data-independent. |
| Memory calibration | `scripts/eval_memory.py` (`make eval-memory`), real + synthetic; `docs/artifacts/memory-calibration-real.*` | **REAL & reportable** (Brier 0.0082, n_test=39) but **0 mature cards** → strict Memory **score** abstains. |
| Paraphrase (transfer) gap | `scripts/eval_paraphrase.py` (`make eval-performance`) | Harness ready; real numbers need tester recall+attempts. |
| Study-feature ablation | `scripts/eval_study_feature.py` (`make study`) → `docs/STUDY-FEATURE-RESULTS.md` | **Synthetic** only; real needs assigned arms (not collected). Keep labeled synthetic; do not fake. |

**Question bank (verified by direct count of `data/questions.json`):** 170 total =
**65 dev + 105 held_out**; held_out sections = **CP 45 / BB 38 / PS 15 / CARS 7**.
The instrument is complete; coverage is not the blocker.

**Current graded scores (`docs/EVAL-SUMMARY-GRADED.md`, strict profile):** Memory
score **ABSTAIN** (calibration real; 0 mature cards), Performance **ABSTAIN** (91
attempts, all **dev**, all builder), Readiness **ABSTAIN**.

### 1d. Build / distribution / recordings

- **Builds exist:** `anki-MCAT/out/graded-build/MCAT-Speedrun-graded.msi` (strict)
  + `MCAT-Speedrun-friend.msi` (tester). Tester dist package READY
  (`out/tester-dist/MCAT-Speedrun/`).
- **AI proxy:** capability compiled into the MSI; **~10-min human deploy remains**
  (Cloudflare Worker + OpenAI key + hard spend cap → paste URL/token into
  `mcat-ai-proxy.json`; no rebuild). See `docs/AI-PROXY-SETUP.md`.
- **Recordings still open** (`docs/RECORDING-RUNBOOK.md`, LOOSE-ENDS "Carried
  over"): desktop memory-review from source **(A)**, clean-machine MSI install
  **(B)**, phone review **video** clip **R4** (only screenshots exist), sync
  **(D/E)**, commit-hash/clean-build recording.

### 1e. Open LOOSE-ENDS relevant to submission

Most LOOSE-ENDS items are research/tuning/`v2` deferrals explicitly **out of scope
for the deadline** (e.g. `w_mis` tuning, probe-confirmed IDK, CARS diagnosis
refinement, gold set, small-n honesty). The submission-relevant ones are the
**"Carried over"** recordings in §1d and the honesty framing (below). Do **not**
attempt the deferred design work this weekend.

---

## 2. Dependency & critical-path analysis

### 2a. What is DATA-DEPENDENT (must wait for the ~3PM tester drop)

- **Held-out Performance accuracy** (`score_heldout.py --responses`) — needs real
  `held_out` answers.
- **Multi-participant Memory calibration** (`eval_memory` via `revlog_from_bundle`)
  — needs the testers' revlog (this the standard bundle **does** carry).
- **Held-out "vs chance" baseline line** and **paraphrase-gap real numbers** —
  derive from the held-out answers.
- **The `EVAL-SUMMARY-GRADED.md` rewrite** of the Performance section (numbers).

**Each of these is a *quick run* of an already-built, already-dry-run script** —
minutes, not hours — **provided the input format is nailed tonight.**

### 2b. What is DATA-INDEPENDENT (do tonight / Sunday-AM)

Push auth + remotes + first pushes; feature-branch/PR workflow; CI workflow +
first green run; AI-proxy deploy; leakage check (already done); AI baseline (done);
demo script; recordings A/B/(D/E/F); committing the working tree; the
`EVAL-SUMMARY` *template/scaffold* (leave numeric blanks to fill at 3PM).

### 2c. Critical path (longest dependency chain)

```
TONIGHT: fix auth ──► create/point remotes ──► first push ──► (Sun AM) feature branches + PRs
                                            └─► (Sun AM) add CI workflow ──► first green CI run ──► CI-evidence screenshot
TONIGHT: lock held-out collection method ──► testers answer 105 held_out ──► (~3PM) responses arrive
                                                                              └─► score_heldout run ──► EVAL-SUMMARY numbers ──► demo/proof
```

Two independent chains. The **auth→push→PR/CI** chain is *entirely in your
control tonight* and is the one the grader flagged. The **held-out** chain has a
**human hard-gate at 3PM** you cannot compress — so the only lever is making the
downstream run instant (pre-tested) and making sure the testers are actually
producing the right data.

### 2d. Honesty constraint that shapes the outcome (bake in — do not overpromise)

Even with 3 testers' held-out answers:

- **Memory (strict score): still ABSTAINS.** Card maturity (≥1 card at ≥21-day
  interval) is **physically impossible** in this timeframe. Calibration stays REAL
  & reportable; the *score* withholds. Say so.
- **Performance (strict): becomes REAL** — leakage-free (dev↔held_out proven
  clean), with a Wilson 95% CI, if ≥30 independent held-out attempts land across
  sections. **This is the win.**
- **Readiness (strict): still ABSTAINS** — its Memory input abstains (no mature
  card), so a range now would be fake precision. **Do not emit a readiness range.**
  Report it as an honest abstention with the missing-data note.

Every reported number keeps: **range/CI, coverage %, confidence, missing-data
note, single next action**; the three scores are **never blended**; **synthetic is
labeled synthetic**.

---

## 3. Time-boxed schedule

### 🌙 TONIGHT (Sat eve) — target ~2.5–3.5h, front-load risk

| # | Task | Est | Why tonight (dependency/risk) |
|---|------|-----|-------------------------------|
| T1 | **Lock the held-out collection path.** Confirm exactly what the 3 testers were told. If they're **not** set to answer the 105 held_out Q, send them tonight: (a) a **held-out questionnaire** (stems+choices, **no key** — filter `data/questions.json` to `split=="held_out"`), and (b) the **blank answer sheet** (`scripts/score_heldout.py --make-template …`). Confirm the return format = a letter-per-qid sheet `score_heldout.py` accepts. Re-run `score_heldout.py --demo` to reprove the pipeline. | 45–60m | **Highest risk.** Default tester flow yields dev-practice answers + revlog, **not** held_out. Without this, the grader's #1 item can't be produced Sunday. Hard 3PM gate. |
| T2 | **Prove push auth + lay remotes.** Install `gh` (`gh auth login`) **or** configure a credential helper / PAT. Then: create a GitHub repo for **`MCAT`** and `git remote add origin …`; add a **personal fork** remote for **`anki-android-MCAT`** (origin is upstream); confirm `anki-MCAT` origin. **Do a first push on each** (see §5 for exact commands). | 45–75m | Unstarted, grader-called-out, **auth unproven**. Discover failures now. Blocks PRs + CI. |
| T3 | **Commit the working trees** (no secrets). `MCAT`: `proxy/`, new docs, artifacts, script edits. `anki-MCAT`: the 3 modified files. `anki-android-MCAT`: `README.md`. Verify `git diff --cached --name-only` shows **no** `.env`/keys before each commit. | 15–20m | Nothing lost; gives CI real content to run against; precedes push. |
| T4 | **Deploy the AI proxy (~10 min)** per `docs/AI-PROXY-SETUP.md`: OpenAI key → **hard $5 spend cap first** → `wrangler deploy` → paste URL+token into the bundle's `mcat-ai-proxy.json` → `/health` check + one in-app "AI: On" verification. | 20–30m | Hard external dependency; removes it from Sunday. Do only if Cloudflare/OpenAI accounts are ready — else move to Sun-AM A2. |

> **If time is tight tonight, do T1 and T2 and stop.** They are the two
> irreversible-if-missed items. T3 is quick; T4 can slip to Sunday AM.

### ☀️ SUNDAY AM (pre-3PM) — target ~4–4.5h

| # | Task | Est | Notes |
|---|------|-----|-------|
| A1 | **Feature-branch + PR workflow** (grader ask). On each repo, replay recent work as **named feature branches** off the pushed baseline and open **PRs** (they can be self-merged; the grader wants the *artifact*). Suggested branches: `feat/three-score-dashboard`, `feat/v2-error-diagnosis`, `feat/perf-mode-ui`, `feat/ai-assistant-proxy`, `feat/held-out-eval-harness`. At minimum: **1–2 clean PRs per repo** with a real diff + description. | 75–90m | Depends on T2. Don't rewrite history destructively — branch from the current tip and PR forward, or open PRs for the already-pushed commits. |
| A2 | **CI workflow + first green run** (grader ask). Add `MCAT/.github/workflows/ci.yml` (template §5): `make validate-data`, `make eval-leakage`, `python -m unittest` (script tests), `score_heldout.py --demo`. Push, watch it go green, **screenshot the green check** for the proof packet. (Optional: a tiny `anki-MCAT` job running `pylib/tests/test_mcat_*.py`.) | 45–60m | Depends on T2/T3. Keep it small so it's fast + green. This is the "CI evidence." |
| A3 | **AI-proxy deploy** — only if not done in T4. | 20–30m | See T4. |
| A4 | **Data-independent recordings.** (A) desktop memory-review + v2 diagnosis from source; (B) clean-machine MSI install; optionally (F) phone dashboard. Follow `docs/RECORDING-RUNBOOK.md`. | 60–75m | These don't need tester data. Capturing the R4 phone **video** here clears a LOOSE-END. |
| A5 | **Scaffold `EVAL-SUMMARY-GRADED.md` update + demo script** with numeric **blanks** to fill at 3PM (Performance CI, per-section table). Draft the demo narrative (§6). | 30–40m | Makes the 3PM turnaround instant. |

**AM subtotal ≈ 3.5–4.75h.** If A1+A2 run long, **cut A4's phone video (F) and the
optional anki-MCAT CI job first** — feature-branches/PRs + one green MCAT CI run are
the grader-critical pair.

### 🌆 SUNDAY PM (post-3PM data drop) — target ~2.5–3h

| # | Task | Est | Notes |
|---|------|-----|-------|
| P1 | **Ingest + score held-out data.** For each returned sheet: `score_heldout.py --responses <file>` → accuracy + Wilson CI + per-section/topic. Pool the 3 testers (report per-tester **and** pooled — never merge files). | 30–45m | Pure run of the pre-tested harness. |
| P2 | **Memory calibration on tester revlog.** `revlog_from_bundle.py` → `eval_memory.py` per tester (Path A). Refresh `docs/artifacts/`. | 20–30m | Multi-participant calibration; still label the strict Memory **score** as abstaining (no maturity). |
| P3 | **Fill the proof artifacts.** Update `EVAL-SUMMARY-GRADED.md` Performance section with real numbers + CI + missing-data note; add the **held-out vs 25%-chance baseline** line; re-run `make eval-leakage` and paste the OK result as the **leakage check** evidence next to the held-out numbers. | 45–60m | Keep honesty fields on every score; Readiness stays ABSTAIN. |
| P4 | **Held-out results demo take + final packet assembly.** Short screen capture of the score run + the updated summary; assemble recordings + CI screenshot + PRs + eval docs into the submission. | 45–60m | The one demo segment that needed data. |

**PM subtotal ≈ 2.5–3.25h. Tomorrow total ≈ 6–8h — fits the ~8h budget** with A4
(phone video) as the release valve if AM overruns.

---

## 4. Do-I-need-extra-time-tonight? — the crisp answer

**Yes, ~2.5–3.5h tonight, on exactly these (in priority order):**

1. **T1 — Guarantee held-out answers will actually arrive by 3PM.** This is the
   single biggest risk because the current tester instructions *don't collect it*.
   Get the 3 testers the held-out questionnaire + blank sheet tonight and re-verify
   `score_heldout.py` end-to-end. Without this, Sunday's headline proof can't exist.
2. **T2 — Make `git push` work and land first pushes on all three repos.** No `gh`,
   no credential helper, `MCAT` has no remote, and `anki-android-MCAT` points at
   upstream. This is the grader-flagged, unstarted, *uncertain* item — you must know
   tonight that auth works, or PRs + CI are impossible Sunday.
3. **T3 — Commit the working trees** (secret-safe) so pushes/CI have real content.
4. **T4 — Deploy the AI proxy** if your Cloudflare/OpenAI accounts are ready (else
   first thing Sunday AM).

Everything else can wait for Sunday **because** these are done tonight.

---

## 5. Reference commands & CI template (for Gabriel — not run by the agent)

> Read-only git only from the agent; **you** run the writes below. Never stage
> `.env`/keys — check `git diff --cached --name-only` before each commit.

**Auth (pick one):**

```bash
# Option A: GitHub CLI
winget install --id GitHub.cli   # or: choco install gh
gh auth login                    # HTTPS + browser; sets a credential helper

# Option B: git credential manager already bundled with Git for Windows
git config --global credential.helper manager
# first push will pop a browser/device auth
```

**MCAT — create remote + first push (no remote today):**

```bash
cd /c/Users/gpdxi/Downloads/alphaProjects/MCAT
gh repo create MCAT --private --source=. --remote=origin   # or add a manually-created repo
git add -A                 # ensure no .env staged:
git diff --cached --name-only | grep -Ei '(^|/)\.env|\.pem$|\.key$|credentials|secret' && echo "STOP: secret staged" || true
git commit -m "MCAT Speedrun: eval harness, docs, AI proxy, data"
git branch -M main
git push -u origin main
```

**anki-android-MCAT — add a personal fork remote (origin is upstream):**

```bash
cd /c/Users/gpdxi/Downloads/alphaProjects/anki-android-MCAT
gh repo create anki-android-MCAT --private --source=. --remote=fork
git commit -am "mcat: README + dashboard/memory-score notes"
git push -u fork main       # the 2 stranded mcat commits now have a home
```

**anki-MCAT — push the unpushed commit + working tree:**

```bash
cd /c/Users/gpdxi/Downloads/alphaProjects/anki-MCAT
git commit -am "mcat: AI bridge + perf dialog + tester seed tweaks"
git push origin main        # publishes 2757868ab + the new commit
```

**Feature-branch + PR (repeat per logical change):**

```bash
git switch -c feat/held-out-eval-harness
# (branch already contains the work, or cherry-pick/commit the slice)
git push -u origin feat/held-out-eval-harness
gh pr create --fill --base main
```

**CI evidence — `MCAT/.github/workflows/ci.yml` (small, fast, green):**

```yaml
name: mcat-ci
on: [push, pull_request]
jobs:
  checks:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install -r requirements.txt
      - name: Validate data
        run: python scripts/validate_data.py
      - name: Leakage check
        run: python scripts/eval_leakage.py
      - name: Held-out scorer self-test (synthetic)
        run: python scripts/score_heldout.py --demo
      - name: Unit tests
        run: python -m unittest scripts.test_ai_explain_live scripts.test_ai_qa scripts.test_ai_judge scripts.test_ai_proxy_client -v
```

> Note: the `Makefile` targets invoke `py -3.12` (Windows). CI on `ubuntu-latest`
> should call `python` directly as above (don't rely on the `py` launcher).

**Held-out scoring (Sunday PM):**

```bash
cd /c/Users/gpdxi/Downloads/alphaProjects/MCAT
python scripts/score_heldout.py --make-template build/heldout.TEMPLATE.json     # (already done — reuse)
python scripts/score_heldout.py --responses build/heldout_testerA.json
python scripts/score_heldout.py --responses build/heldout_testerB.json --emit-attempts build/attemptsB.json
make eval-leakage        # paste the OK result as the leakage-check evidence
```

---

## 6. Demo guidance (per the grader note)

Grader verbatim: combine product + AI demo (they build on each other) **or** keep
them separate but **shorten the product demo**; **spend more time on features that
changed since the MVP, not just sync.**

**Recommendation: combine into one ~arc.** Lead with the *post-MVP* changes, treat
sync as a short beat, and let the AI feature flow from the same performance-mode
miss.

Suggested ~6–8 min arc:

1. **Three-score dashboard w/ honest abstention (post-MVP).** Show Memory /
   Performance / Readiness never blended, coverage bar, "not enough data" as a
   *feature* not a bug, and the **Focus area** next-action card.
2. **Performance mode + v2 error-diagnosis (post-MVP, the marquee change).** Miss a
   science question → the **inferred** hypothesis + confidence panel ("Looks like:
   *content gap* · NN%"), one-tap Confirm / override, the **re-check probe**, and
   **application-practice remediation** (clearly unscored). Emphasize "infer, don't
   ask."
3. **AI Assistant (fold in here — same miss).** Open the ✨ Assistant on that
   choice → live per-choice explanation; note the **keyless hosted proxy** + the
   graceful **offline fallback**. Cite the **baseline comparison**
   (`docs/QA-BASELINE-COMPARISON.md`): AI beats static + keyword on the hard
   differentiation set under the cross-model judge.
4. **Sync — a short beat, not the show.** ~30–45s: phone review → desktop appears
   (§7b), or the perf-bundle two-way merge (E). Don't dwell.
5. **Proof artifacts (close on honesty).** Held-out accuracy + Wilson CI +
   per-section, the **leakage-check OK**, memory **calibration** curve (real vs the
   labeled synthetic control), and the **green CI check + PR list**. State plainly:
   Performance is real & leakage-free; Memory *calibration* is real but the *score*
   abstains (no mature cards); **Readiness abstains** — with its missing-data note.

---

## 7. Risks & mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| **Testers return standard `perf_bundle` (dev practice + revlog), no held-out answers** | **High (default flow)** | Kills the grader's #1 item | **T1 tonight:** send held-out questionnaire + blank sheet now; confirm return = a letter-per-qid sheet; pre-test `score_heldout.py`. Fallback: builder self-answers nothing on held_out (that's dev-only self-grading — forbidden); instead solicit even **1** independent held-out sheet — one real run beats zero. |
| **Push auth still broken (no gh/helper)** | Medium | Blocks PRs + CI (both grader asks) | **T2 tonight** to surface early. Fallbacks: PAT-in-URL push; or GitHub web UI upload for `MCAT` + a PR from a branch. Worst case: show local branches/PRs on a fork you *can* reach (`anki-MCAT` already has origin). |
| **Tester data late / thin (<30 held-out attempts, or 1 tester)** | Medium | Performance CI stays wide; may not clear strict 30 | Report honestly with the small-n warning `score_heldout` already prints; pool what arrives; keep Performance labeled indicative if <30. Don't fabricate. |
| **CI setup eats time / upstream workflows fire and go red** | Medium | Time sink; confusing red checks | Use the **small MCAT-only** workflow (§5); if inherited upstream Anki/AnkiDroid CI triggers on push and fails noisily, that's expected — point the grader at the **green MCAT CI**, not the upstream jobs. Timebox A2 to 60m. |
| **Proxy deploy blocked (no Cloudflare/OpenAI account)** | Low–Med | AI demo shows "AI: Not set up" | App still fully functional offline (documented). Do T4 early; if blocked, demo the **offline fallback** honestly + the baseline-comparison doc. |
| **Readiness pressure to show a number** | Low | Honesty auto-fail if you blend | **Never** emit a readiness range this weekend — Memory maturity is impossible; abstain with the missing-data note. This is the correct, defensible outcome. |
| **Recording overrun (esp. sync/emulator, R4 video)** | Medium | Squeezes P-tasks | Sync is a *short beat* now (§6); the emulator R4 video is the first thing to cut (A4) if AM overruns — screenshots already exist. |

---

## 8. One-line status per grader ask

- **Held-out eval results** — harness DONE & dry-run-proven; **blocked on 3PM data**; de-risk collection **tonight (T1)**.
- **Baseline comparison** — **DONE** (`docs/QA-BASELINE-COMPARISON.md`); add held-out-vs-chance line post-3PM.
- **Leakage check** — **DONE & reproducible** (`make eval-leakage`, Jaccard 0.56<0.70); surface next to held-out numbers.
- **CI evidence** — **OPEN**; add small MCAT workflow + first green run **Sun AM (A2)**; depends on tonight's push auth.
- **Feature branches + PRs** — **OPEN** (none exist); **Sun AM (A1)**; depends on tonight's push auth (T2).
- **Demo strategy** — combine product+AI, shorten sync, lead with post-MVP changes (§6).
- **AI-proxy deploy** — **~10 min**, do **tonight (T4)** or Sun-AM (A3).
