# feat/android-three-scores — AnkiDroid companion (optional)

> Paste target: `gh pr create --title "feat(android): three-score dashboard + memory-score parity" --body-file docs/pr-drafts/feat-android-three-scores.md`
> Repo: **anki-android-MCAT**. **Optional** — include if time allows; it shows the shared-engine / cross-device story.

## Summary (the "why")

Demonstrates the "one engine, one signal across devices" requirement: the same
three scores (Memory / Performance / Readiness) with the same abstention gates on
Android, sharing the mastery logic rather than reimplementing a scheduler in
Kotlin. Two commits already exist locally; they are **stranded** because this
repo's `origin` points at **upstream AnkiDroid** (no push rights), so they need a
**personal fork remote** before they can be published.

## What changed

- *(commit `d9dc9b6`)* three-score dashboard (memory / performance / readiness) on
  the phone.
- *(commit `62e9dd0`)* memory-score parity with desktop + abstention gates;
  signing / engine docs; tests.
- `README.md` *(modified)* — fork/build/credit notes (AGPL-3.0-or-later; credit
  AnkiDroid upstream).

## Publishing prerequisite (from FINAL-SUBMISSION-PLAN §1a/§5)

`origin` = `github.com/ankidroid/Anki-Android` (upstream, not a fork). To push:
```bash
# create a personal fork remote, then push the branch there (NOT upstream)
gh repo create anki-android-MCAT --private --source=. --remote=fork
git push -u fork feat/android-three-scores
```

## Test plan

- [ ] AnkiDroid fork builds a signed APK (engine parity with desktop).
- [ ] Fresh profile: all three scores abstain with give-up copy (parity with the
      desktop strict profile).
- [ ] Phone review session recording (memory mode) for the demo packet.

## Screenshots / artifacts

- [ ] Phone three-score dashboard (abstaining state).
- [ ] Signed APK install on a clean device.

## Risks / rollback

- **Accidental push to upstream.** Guard by pushing only to the `fork` remote;
  never `git push origin`. Rollback = drop the fork branch.

## Honesty note

Scores use the **same** gates and abstention rules as desktop; nothing on the
phone blends the three scores or invents a readiness range. Same-card offline
review conflict handling follows the documented append-only / union merge rule.
