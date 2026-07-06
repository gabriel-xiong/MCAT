# MCAT Speedrun — Sunday critical path (~4 hours)

_Generated: **2026-07-05 15:00 CDT**; updated **16:00 CDT** after verification pack.
Graded bundle at `anki-MCAT/out/tester-dist-graded/` — **`mcat-ai-proxy.json` still
has placeholders** until you paste deployed URL + token._

> **Grader entry point:** [`HOW-TO-VERIFY.md`](HOW-TO-VERIFY.md) — 22-row claim→evidence
> table, 5-minute verifier path, honest GAPS. Demo narration: [`MVP-TO-FINAL.md`](MVP-TO-FINAL.md).

> **Honest gaps you must label in the submission (not bugs):**
> - **No sync recording** — two-way sync proof is doc + code, not a captured video.
> - **Synthetic eval** — held-out performance, memory calibration demo, paraphrase
>   gap, and study-feature ablation use labelled synthetic data until real tester
>   sheets arrive.
> - **Readiness + Memory scores abstain** on graded MSI — strict profile by design;
>   a short session cannot populate full-course gates.
> - **MSIs dated Jul 4 are stale** — must rebuild after merging PR #3 + flipping
>   `SCORE_PROFILE`.

---

## Pre-flight (agent completed 2026-07-05)

| Item | Status |
|------|--------|
| `make ci-local` (MCAT) | **PASS** — 57/57 tests |
| anki-MCAT `ai_bridge.py` blank-URL fix | **Committed** `8e997d0c3` (not pushed — auth blocked) |
| MCAT `ai_explain.py` blank-URL guard | **Committed** `2f277df` on `chore/pre-demo-verification` |
| `data/mcat-outline.full.json` | **Committed** `9f38e86` on `chore/pre-demo-verification` |
| PR #3 (anki-MCAT) | **MERGED** on `main` (coverage + AI toggle) |
| Verification pack | **DONE** — `HOW-TO-VERIFY.md`, `MVP-TO-FINAL.md`, `SYNC-DEMO-SCRIPT.md`; MCAT `1116623`, anki-MCAT `9c4e8ca04` (local) |
| Graded MSI | **PARTIAL** — `MCAT-Speedrun-graded.msi` copy dated Jul 5 but **byte-identical to Jul 4 dist**; run full `tools/build-installer.bat` (package step) with `SCORE_PROFILE = "strict"` |
| Push to GitHub | MCAT `chore/pre-demo-verification` unpushed; anki-MCAT `main` may be pushed |

---

## Minute-by-minute plan

### T+0 — Merge PR #3 (~10 min)

**Repo:** `anki-MCAT` — [PR #3](https://github.com/gabriel-xiong/anki-MCAT/pull/3)
`feat/dashboard-ai-toggle` → `main`

**What it ships:** AI on/off dashboard pill, honest dual coverage (full AAMC outline
denominator + shipped-scope label), Memory abstain fixes, blank-proxy-URL pill fix.

```powershell
cd C:\Users\gpdxi\Downloads\alphaProjects\anki-MCAT
git push -u origin feat/dashboard-ai-toggle
gh pr merge 3 -R gabriel-xiong/anki-MCAT --merge
git checkout main
git pull origin main
```

**Verify:** `git log -1 --oneline` shows merge of PR #3.

---

### T+10 — Strict profile + reseed graded bundle (~20 min)

#### 1. Flip `SCORE_PROFILE` to strict

**File:** `anki-MCAT/pylib/anki/mcat_scores.py` **line 52**

```python
# BEFORE (friend/tester build — revert to this after graded MSI):
SCORE_PROFILE = "tester"  # "tester" | "strict"

# AFTER (graded MSI only):
SCORE_PROFILE = "strict"  # "tester" | "strict"
```

> **Reminder:** Revert line 52 back to `"tester"` immediately after the graded MSI
> is built. Friend MSI must never ship with strict gates.

#### 2. Reseed graded bundle (verify clean history)

```powershell
cd C:\Users\gpdxi\Downloads\alphaProjects\anki-MCAT
out\pyenv\Scripts\python.exe tools\mcat_seed_tester.py --out out\tester-dist-graded --with-ai-proxy --mcat ..\MCAT
out\pyenv\Scripts\python.exe out\_verify_history_clean.py out\tester-dist-graded\MCAT-Speedrun\mcat-base
```

**Expect:** revlog=0, perf_attempts=0, 66 cards, 62 perf Qs, seed line
`auto-sync : off` (`autoSync=False` in prefs — manual Sync still works).

**Proxy JSON:** Still **`REPLACE_WITH_…`** in
`out/tester-dist-graded/MCAT-Speedrun/mcat-ai-proxy.json` — paste deployed values
per [`AI-PROXY-DEPLOY-NOW.md`](AI-PROXY-DEPLOY-NOW.md), then re-zip if uploading bundle.
Reseed with `--keep` if you need to preserve it:

```powershell
out\pyenv\Scripts\python.exe tools\mcat_seed_tester.py --out out\tester-dist-graded --with-ai-proxy --keep --mcat ..\MCAT
```

Zip for upload: `out\tester-dist-graded\MCAT-Speedrun\` → `MCAT-Speedrun.zip`.

---

### T+30 — Start MSI build (runs T+30 → T+90–120)

**Do NOT start unless `tools\ninja` works** (first build ~1–2 h on Windows).

```powershell
cd C:\Users\gpdxi\Downloads\alphaProjects\anki-MCAT

# Full compile (pylib + qt + rust mastery query)
tools\run.bat
# OR incremental after first build:
tools\ninja pylib qt

# Windows installer (~10–20 min after compile)
set RELEASE=2
tools\build-installer.bat
```

**Output:** `out/installer/` or `out/wheels/` per ninja target — copy/rename to:

```
out\graded-build\MCAT-Speedrun-graded.msi
```

**While MSI builds:** push MCAT branch, merge docs if needed:

```powershell
cd C:\Users\gpdxi\Downloads\alphaProjects\MCAT
git push -u origin chore/pre-demo-verification
# Optional: open PR into MCAT branch for outline + proxy guard fixes
```

**After MSI finishes:** revert `SCORE_PROFILE` to `"tester"` and commit or stash.

---

### T+120 — Smoke test checklist (~30 min)

On a clean Windows profile or VM, with graded MSI + filled proxy JSON:

| # | Check | Pass criteria |
|---|-------|---------------|
| 1 | Install MSI | Anki launches, MCAT home visible |
| 2 | Launcher | `Start MCAT Speedrun.cmd` → preloaded deck, no import |
| 3 | Three scores | Memory / Performance / Readiness **separate**, no `provisional` badge |
| 4 | Strict abstention | All three say "not enough data" on fresh profile |
| 5 | Memory mode | Normal Anki review flow works |
| 6 | Performance gate | Blocked until ≥3 cards + ≥5 Good/Easy; CARS ungated |
| 7 | AI pill | **"AI: On"** after proxy filled (or "Not set up" if offline — honest) |
| 8 | Performance miss | Assistant panel shows per-choice explanation |
| 9 | Export | `*.perf_bundle.json` includes perf sidecar data |

Full script: [`PRE-DEMO-VERIFICATION.md`](PRE-DEMO-VERIFICATION.md) § Manual smoke test.

---

### T+150 — Eval battery + CI mirror (~30 min)

```powershell
cd C:\Users\gpdxi\Downloads\alphaProjects\MCAT
make eval-all-synthetic
make ci-local
make test
```

**Label in submission:** held-out perf and study ablation are **SYNTHETIC**; **REAL**
memory calibration for participant alt is in
[`memory-calibration-alt.summary.json`](artifacts/memory-calibration-alt.summary.json).
Held-out perf for alt is **`scorable: false`** — see
[`heldout-performance-REAL-alt.summary.json`](artifacts/heldout-performance-REAL-alt.summary.json).

**Real held-out (if sheet arrives):**

```powershell
py -3.12 scripts/score_heldout.py build/heldout-REAL_tester1.json
```

---

### T+180 — Demo video outline (~30 min)

**Target:** 6–8 min screen recording. Script: [`demo/product-ai-demo-runofshow.md`](demo/product-ai-demo-runofshow.md)

| Segment | Time | Content |
|---------|------|---------|
| 1 | 0:00–1:30 | Three-score dashboard, honest abstention, dual coverage bar |
| 2 | 1:30–3:30 | Performance miss → error typing → AI Assistant (live or offline fallback) |
| 3 | 3:30–4:15 | Memory mode flashcard review (separate from performance) |
| 4 | 4:15–5:00 | Export data button → show sidecar JSON |
| 5 | 5:00–6:30 | **Proof slide:** open `HOW-TO-VERIFY.md` — leakage OK, REAL alt memory, synthetic labelled |
| 6 | 6:30–8:00 | MVP→final callouts per [`MVP-TO-FINAL.md`](MVP-TO-FINAL.md); honest gaps (no sync video) |

Numbers to cite: [`SUBMISSION-RESULTS.md`](SUBMISSION-RESULTS.md), [`HOW-TO-VERIFY.md`](HOW-TO-VERIFY.md)

---

### T+210 — Upload package list (~30 min)

| Artifact | Path | Notes |
|----------|------|-------|
| Graded MSI | `anki-MCAT/out/graded-build/MCAT-Speedrun-graded.msi` | Must be **new package** (dist MSI mtime Jul 5+), not Jul 4 copy |
| Graded bundle ZIP | `anki-MCAT/out/tester-dist-graded/MCAT-Speedrun/` | Placeholder `mcat-ai-proxy.json` — fill before demo |
| Friend MSI (optional) | `out/graded-build/MCAT-Speedrun-friend.msi` | Tester profile; stale Jul 4 |
| Demo video | your recording | 6–8 min per outline above |
| CI screenshot | GitHub Actions green run | [mcat-ci workflow](https://github.com/gabriel-xiong/MCAT/actions) |
| PR links | anki-MCAT #1–3, MCAT #1–5 | Show feature-branch workflow |
| **Grader hub** | `docs/HOW-TO-VERIFY.md` | **Lead with this** — 5 min + 30 min paths |
| Eval docs | `docs/SUBMISSION-RESULTS.md`, `docs/EVAL-SUMMARY-GRADED.md` | REAL alt memory + synthetic labels |
| MVP delta | `docs/MVP-TO-FINAL.md` | Demo narration |
| Graded handoff | `anki-MCAT/docs/GRADED-HANDOFF.md` | MSI install, strict profile, auto-sync off |
| BrainLift | `docs/BRAINLIFT.md` | Thesis + error typing |
| Quickstarts | `docs/GRADED-QUICKSTART.md`, `docs/TESTER-QUICKSTART.md` | Grader vs friend |
| Leakage proof | `docs/artifacts/leakage-check.summary.json` | Jaccard 0.56 < 0.70 |
| AI baseline | `docs/QA-BASELINE-COMPARISON.md` | AI vs static vs TF-IDF |

---

## Ordered checklist — run NOW

```
[x] 1. PR #3 merged on anki-MCAT main
[ ] 2. Full MSI **package** (not copy-only) — `SCORE_PROFILE = "strict"`, close Anki first, then `tools/build-installer.bat`
[ ] 3. Fill mcat-ai-proxy.json in out/tester-dist-graded/MCAT-Speedrun/
[ ] 4. git push MCAT chore/pre-demo-verification  (verification pack commit 1116623)
[ ] 5. git push anki-MCAT main  (GRADED-HANDOFF 9c4e8ca04; SCORE_PROFILE reverted to tester)
[ ] 6. Smoke test graded MSI (30 min checklist)
[ ] 7. make eval-all-synthetic && make ci-local  (MCAT repo)
[ ] 8. Record demo video — script in demo/product-ai-demo-runofshow.md + MVP-TO-FINAL.md
[ ] 9. Upload package list above; cite HOW-TO-VERIFY.md in cover note
```

---

## Commits made this session (local — push pending)

| Repo | Branch | Commit | Message |
|------|--------|--------|---------|
| anki-MCAT | `feat/dashboard-ai-toggle` | `8e997d0c3` | fix(ai): treat blank proxy URL as "off" |
| anki-MCAT | (same branch, prior) | `91deeef69`, `c8de416c9` | Memory abstain fixes |
| MCAT | `chore/pre-demo-verification` | `2f277df` | fix(ai): reject blank/malformed proxy URLs |
| MCAT | `chore/pre-demo-verification` | `1116623` | HOW-TO-VERIFY + REAL alt eval artifacts |
| MCAT | (same branch, prior) | `9f38e86` | full AAMC exam outline |
| anki-MCAT | `main` | `9c4e8ca04` | GRADED-HANDOFF.md |

---

## Blockers

1. **Fill proxy JSON** — graded bundle still has placeholders; blocks live AI demo.
2. **MCAT branch push** — verification pack local only until `chore/pre-demo-verification` pushed.
3. **No real held-out tester data** — Performance score abstains; alt bundle `scorable: false`.
4. **No sync recording** — optional script in `SYNC-DEMO-SCRIPT.md`; label gap in submission.

---

## Quick reference commands

**Merge PR #3:**
```powershell
gh pr merge 3 -R gabriel-xiong/anki-MCAT --merge
```

**SCORE_PROFILE strict (line 52 only):**
```python
SCORE_PROFILE = "strict"  # revert to "tester" after graded MSI
```

**MSI build sequence:**
```powershell
cd C:\Users\gpdxi\Downloads\alphaProjects\anki-MCAT
tools\run.bat
tools\build-installer.bat
copy out\installer\*.msi out\graded-build\MCAT-Speedrun-graded.msi
```

**Eval + CI:**
```powershell
cd C:\Users\gpdxi\Downloads\alphaProjects\MCAT
make eval-all-synthetic
make ci-local
```
