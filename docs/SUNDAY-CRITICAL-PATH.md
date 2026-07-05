# MCAT Speedrun — Sunday critical path (~4 hours)

_Generated: **2026-07-05 15:00 CDT**. Assumes ~4 hours until submission deadline.
Graded bundle at `anki-MCAT/out/tester-dist-graded/` already has live
`mcat-ai-proxy.json` filled by builder._

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
| PR #3 (anki-MCAT) | **OPEN, MERGEABLE** — needs push + merge |
| Graded MSI | **STALE** (Jul 4, 619 MB) — rebuild required |
| Push to GitHub | **BLOCKED** — `git push` prompts for HTTPS credentials |

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

**Expect:** revlog=0, perf_attempts=0, 66 cards, 62 perf Qs.

**Proxy JSON:** User already filled `out/tester-dist-graded/MCAT-Speedrun/mcat-ai-proxy.json`.
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

**Label in submission:** all held-out / memory / paraphrase numbers in
`docs/artifacts/` are **SYNTHETIC** unless you have real tester sheets.

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
| 5 | 5:00–6:30 | **Proof slide:** leakage OK, synthetic eval labelled, CI green screenshot |
| 6 | 6:30–8:00 | Honest gaps: no sync video, readiness abstains, small-n |

Numbers to cite: [`demo/results-demo-outline.md`](demo/results-demo-outline.md)

---

### T+210 — Upload package list (~30 min)

| Artifact | Path | Notes |
|----------|------|-------|
| Graded MSI | `anki-MCAT/out/graded-build/MCAT-Speedrun-graded.msi` | Strict profile; rebuild today |
| Graded bundle ZIP | `anki-MCAT/out/tester-dist-graded/MCAT-Speedrun/` | Includes filled `mcat-ai-proxy.json` |
| Friend MSI (optional) | `out/graded-build/MCAT-Speedrun-friend.msi` | Tester profile; stale Jul 4 |
| Demo video | your recording | 6–8 min per outline above |
| CI screenshot | GitHub Actions green run | [mcat-ci workflow](https://github.com/gabriel-xiong/MCAT/actions) |
| PR links | anki-MCAT #1–3, MCAT #1–5 | Show feature-branch workflow |
| Eval docs | `docs/SUBMISSION-RESULTS.md`, `docs/EVAL-SUMMARY-GRADED.md` | Label synthetic |
| BrainLift | `docs/BRAINLIFT.md` | Thesis + error typing |
| Quickstarts | `docs/GRADED-QUICKSTART.md`, `docs/TESTER-QUICKSTART.md` | Grader vs friend |
| Leakage proof | `docs/artifacts/leakage-check.summary.json` | Jaccard 0.56 < 0.70 |
| AI baseline | `docs/QA-BASELINE-COMPARISON.md` | AI vs static vs TF-IDF |

---

## Ordered checklist — run NOW

```
[ ] 1. git push anki-MCAT feat/dashboard-ai-toggle  (auth required)
[ ] 2. gh pr merge 3 -R gabriel-xiong/anki-MCAT --merge
[ ] 3. git pull origin main  (anki-MCAT)
[ ] 4. Edit mcat_scores.py line 52 → SCORE_PROFILE = "strict"
[ ] 5. Reseed: mcat_seed_tester.py --out out/tester-dist-graded --with-ai-proxy --keep
[ ] 6. Verify clean: _verify_history_clean.py
[ ] 7. START MSI build (only if ninja ready): tools\run.bat then tools\build-installer.bat
[ ] 8. REVERT mcat_scores.py line 52 → "tester" after MSI done
[ ] 9. Smoke test graded MSI (30 min checklist)
[ ] 10. make eval-all-synthetic && make ci-local  (MCAT repo)
[ ] 11. Record demo video (6–8 min)
[ ] 12. Upload package list above
```

---

## Commits made this session (local — push pending)

| Repo | Branch | Commit | Message |
|------|--------|--------|---------|
| anki-MCAT | `feat/dashboard-ai-toggle` | `8e997d0c3` | fix(ai): treat blank proxy URL as "off" |
| anki-MCAT | (same branch, prior) | `91deeef69`, `c8de416c9` | Memory abstain fixes |
| MCAT | `chore/pre-demo-verification` | `2f277df` | fix(ai): reject blank/malformed proxy URLs |
| MCAT | (same branch, prior) | `9f38e86` | full AAMC exam outline |

---

## Blockers

1. **Git push auth** — `git push` prompts for GitHub username/password. Use PAT,
   SSH remote, or `gh auth login` before merge.
2. **MSI rebuild** — Jul 4 MSIs predate today's merges; graded build mandatory.
3. **PR #3 not merged yet** — dashboard coverage + AI toggle not on `main`.
4. **No real held-out tester data** — Performance score abstains; use synthetic
   demo with honest labels.

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
