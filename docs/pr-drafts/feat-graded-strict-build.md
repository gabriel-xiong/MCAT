# feat/graded-strict-build — strict scoring profile + keyless graded bundle

> Paste target: `gh pr create --title "feat: strict graded scoring profile + --with-ai-proxy bundle" --body-file docs/pr-drafts/feat-graded-strict-build.md`
> Repos: **anki-MCAT** (profile + bundle assembly) and **MCAT** (graded quickstart doc).

## Summary (the "why")

The graded deliverable must show **honest abstention**, not flattering numbers.
This PR ships the **strict `SCORE_PROFILE`** — the full-course gates (≥200
reviews **and** a mature card for Memory, ≥30 independent attempts for
Performance, coverage + per-section gates for Readiness) — compiled into the
graded MSI, so a short grading session correctly says *"not enough data yet"*
rather than inventing a score. It also assembles a **keyless launcher bundle**
(`--with-ai-proxy`) so the AI-proxy URL/token are config-driven and can be
set/changed **without an MSI rebuild**. The strict profile and the tester
engagement profile ship in the same code, selected at build time; this build is
the strict one.

## What changed

**anki-MCAT**
- `pylib/anki/mcat_scores.py` *(committed `2757868ab`)* — the `SCORE_PROFILE`
  block: strict (graded) vs tester (engagement) gates; Wilson bands; readiness
  half-width that widens at small n; empty-profile-still-abstains guarantee.
- `qt/aqt/deckbrowser.py` *(committed `2757868ab`)* — provisional-badge and
  profile-aware dashboard copy (graded shows plain **measured**; tester shows
  `provisional`).
- `tools/mcat_seed_tester.py` *(modified)* — `--with-ai-proxy` assembles the
  launcher bundle (deck + launcher + `mcat-ai-proxy.json` placeholder) and
  enables FSRS + scheduler v3 so retrievability exists for the dashboard.

**MCAT**
- `docs/GRADED-QUICKSTART.md` *(new)* — grader-facing quickstart that explains,
  up front, **why the scores abstain** in a short session (it's the honesty rule,
  not a bug) and how to verify this really is the strict build
  (`SCORE_PROFILE="strict"`, no `provisional` badge).
- `docs/TESTER-QUICKSTART.md` *(modified, shared)* — graded-build note.
- `docs/DECISIONS.md` §31 *(modified, shared)* — "friend-tester ENGAGEMENT
  thresholds — NOT the graded methodology": the low-gate profile is explicitly
  labelled non-graded.

## Test plan

The scoring logic is exercised by the `anki-MCAT` unit tests (require a built
Anki backend, so they run in that repo's environment, **not** in `mcat-ci`):

```bash
# in anki-MCAT (with the built pyenv):
out/pyenv/Scripts/python.exe -m pytest pylib/tests/test_mcat_scores.py -q
out/pyenv/Scripts/python.exe -m pytest qt/tests/test_mcat_dashboard_render.py -q
```

Expected: green, including `test_empty_profile_still_abstains_*` and
`test_idk_rows_are_invisible_to_readiness`. Bundle assembly is verified manually
by launching the graded MSI and confirming the strict abstention wording (see
`docs/GRADED-QUICKSTART.md §5`).

> Note: these tests are **not** in `mcat-ci` on purpose — that workflow avoids
> compiling Anki. See `ci-github-actions.md` for the rationale.

## Screenshots / artifacts

- [ ] Fresh graded profile: all three cards **abstain** with strict-gate wording
      (Memory *"Needs ≥200 graded reviews"*; Readiness lists failing gates).
- [ ] Score cards show **no `provisional` badge** (vs the tester build).
- [ ] `MCAT-Speedrun-graded.msi` + `MCAT-Speedrun.zip` bundle contents (launcher +
      `mcat-ai-proxy.json` placeholder, **no key**).

## Risks / rollback

- **Grader confusion at blank scores.** Mitigated by `GRADED-QUICKSTART.md §2/§6`
  framing abstention as intended honesty.
- **Wrong profile shipped.** Verifiable via the badge + `SCORE_PROFILE` note; the
  build log records which profile compiled.
- **Rollback:** rebuild with `SCORE_PROFILE="tester"` (the friend build) — the
  code path is unchanged, only the selected constant differs.

## Honesty note

- Strict and tester profiles are **both pre-registered and labelled**; the graded
  claims use **only** the strict profile. The tester profile exists purely for
  engagement and is labelled `provisional` in-app and in DECISIONS §31.
- A truly-empty profile **still abstains** on all three scores — the low gates
  never fabricate a number. CIs stay very wide at small n. The three scores are
  **never blended**.
