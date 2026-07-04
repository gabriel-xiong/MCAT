# Undo + collection-integrity proof

_Artifact 3 of the MVP-evidence push (reviewer next-focus #3). Last updated
2026-07-03._

> **Reviewer ask:** "Undo and collection integrity proof." Demonstrate undo works
> and the collection stays consistent (no lost / double-counted reviews) across
> review + the performance sidecar.

## What was run

A scripted, reproducible check against the **real modified Anki backend** (the
fork's built `rslib`) plus the real `anki.mcat_perf` sidecar code:

```
anki-MCAT/out/pyenv/Scripts/python.exe anki-MCAT/tools/mcat_undo_integrity_check.py
```

No network, no AI. It asserts a set of invariants and exits non-zero on any
failure; a JSON summary is written to
`MCAT/docs/artifacts/undo-integrity-results.json`.

## Result: **15 / 15 checks PASS**

```
[A] Review + undo reversibility (revlog exactness)
  [PASS] revlog starts empty — baseline=0
  [PASS] reviewing N cards appends exactly N revlog rows — 0 -> 6 (N=6)
  [PASS] each undo removes exactly one revlog row — undo op label(s)=['Answer Card']
  [PASS] after undoing all reviews, revlog returns to baseline (none lost/doubled) — final=0
  [PASS] redo re-applies exactly N reviews — redone=6
  [PASS] undo again returns to baseline (idempotent round-trip)

[B/C] Perf sidecar isolation + append-only idempotent sync
  [PASS] question bank loaded — 10 questions selected
  [PASS] logging K attempts yields exactly K rows — count=10, K=10
  [PASS] accuracy reflects logged attempts (no double count) — attempts=10 correct=5 acc=0.5
  [PASS] memory review+undo does NOT change perf attempt count (stores isolated) — perf count still 10
  [PASS] export bundle carries all K attempts — bundle attempts=10
  [PASS] first import adds exactly K attempts (union merge) — added=10 skipped=0
  [PASS] re-import is idempotent — adds 0, skips K (no double count) — added=0 skipped=10
  [PASS] second device converged to the exact union (K attempts) — device-B count=10

[D] Collection integrity check
  [PASS] col.fix_integrity() reports OK — Database rebuilt and optimized.
```

## What each block proves

**[A] Reviews are exactly reversible — no lost or double-counted reviews.**
Reviewing N cards appends exactly N `revlog` rows; each `undo()` removes exactly
one row (the undo op is labelled `Answer Card`), and after undoing all N the
`revlog` count returns to the pre-review baseline. `redo()` re-applies them
exactly, and undoing again returns to baseline — a clean round-trip with no
drift. This is the core "undo works and nothing is lost or double-counted"
claim, measured directly on the review log the memory score is computed from.

**[B] The performance sidecar is isolated from memory undo.** After logging K
performance attempts, churning the *memory* side (review + undo cycles) leaves
the perf `attempt_count` unchanged. The two stores (`collection.anki2` revlog vs.
`collection.mcat_perf.db`) cannot corrupt or double-count each other — consistent
with the sidecar design in `DECISIONS.md §5`.

**[C] Perf attempts are append-only and sync merges are idempotent.** Exporting a
bundle and importing it into a second device adds each attempt exactly once
(`added=K, skipped=0`); re-importing the same bundle adds **zero**
(`added=0, skipped=K`) — no double counting — and the second device converges to
the exact union. This is the cross-device consistency guarantee from
`DECISIONS.md §22`, exercised end-to-end.

**[D] The collection stays consistent.** After all the review / undo / redo
churn, `col.fix_integrity()` (the same "Check Database" the Tools menu runs)
reports OK ("Database rebuilt and optimized").

## Fully proven vs. needs a human

- **Fully proven (automated):** everything above — review/undo revlog exactness,
  perf-sidecar isolation, append-only + idempotent sync merge, and post-churn DB
  integrity.
- **Overlaps but distinct:** memory-review sync across two *real* devices over
  the local sync server (the graded §7b flow) is a separate, GUI/emulator-driven
  recording — see `docs/RECORDING-RUNBOOK.md §D` and `docs/SYNC-CONFLICT-RULE.md`.
  This script covers the *perf-data* bundle sync (§E) headlessly; the memory-sync
  conflict-winner demo remains an on-camera human step.

## Reproduce
```bash
cd anki-MCAT
./out/pyenv/Scripts/python.exe tools/mcat_undo_integrity_check.py
# -> prints the table above, writes MCAT/docs/artifacts/undo-integrity-results.json
```
