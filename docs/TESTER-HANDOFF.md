# Tester handoff — builder reference for returned data

_Last updated: 2026-07-03._

> **Testers:** you don't need this page. The friendly 2-minute install/study/
> export guide you should follow (and the one to send to friends) is
> [`TESTER-QUICKSTART.md`](TESTER-QUICKSTART.md). The builder shipping the
> package should follow [`DISTRIBUTION-CHECKLIST.md`](DISTRIBUTION-CHECKLIST.md).

This page is the **builder-side reference**: exactly what a returned file
contains and how it feeds the memory-calibration harness. Companion docs:
[`RELEASE-INSTALLER.md`](RELEASE-INSTALLER.md) (how the preseeded build is
assembled), [`EVAL-DATA-RUNBOOK.md`](EVAL-DATA-RUNBOOK.md) (running the harness),
and [`ARCHITECTURE.md`](ARCHITECTURE.md) (the three scores).

## What testers do (one-paragraph recap)

The build ships **preseeded** (MCAT deck + question bank + scoring all loaded —
no import, no sign-in, no AI, no internet). On **desktop** they install
`anki-26.05-win-x64.msi`, unzip `MCAT-Speedrun.zip`, and launch
`Start MCAT Speedrun.cmd`; they review flashcards (and optionally answer practice
questions) over 2–3 days, then click **"Export my data"** to produce **one**
`MCAT-data_<who>_<date>.perf_bundle.json` and send it back. **Android** testers
install the signed APK, import `mcat-deck.apkg`, review, and return one
`.colpkg`. **One file per person, never merged** — merging destroys per-tester
attribution. Full tester wording lives in
[`TESTER-QUICKSTART.md`](TESTER-QUICKSTART.md).

---

## What's in the file (builder reference)

The desktop "Export my data" button writes the portable **perf sync bundle**
(`format: mcat_perf_bundle`, DECISIONS §22) with two ADDITIVE additions for
memory calibration:

| Key | Contents |
|----|----|
| `participant` | Tester label/initials, embedded in the payload (attribution no longer depends on the filename). |
| `memory_revlog` | Raw `revlog` rows read read-only from the tester's `collection.anki2`: `id` (epoch-ms), `cid`, `usn`, `ease`, `ivl`, `lastIvl`, `factor`, `time`, `type`. |
| `memory_revlog_columns` | The column order for `memory_revlog` (self-describing). |
| `attempts`, `questions` | Unchanged performance-mode contents (same as before). |

Nothing else changed: older builds still import these bundles (the perf merge
only reads `attempts`/`questions`), and `format_version` is unchanged. The
Android `.colpkg` carries the whole `collection.anki2` (revlog inside), fed via
Path B below.

---

## Feeding it to the memory-calibration harness

The harness (`scripts/eval_memory.py`, owned separately) reads a
`collection.anki2` `revlog` via `--collection`. Two supported paths:

### Path A — bundle → sqlite adapter (revlog-driven, default — Desktop)

Convert a returned desktop bundle into a minimal `collection.anki2`-shaped
sqlite, then point the harness at it. **No changes to `eval_memory.py` required.**

```bash
py -3.12 scripts/revlog_from_bundle.py \
    --bundle MCAT-data_AB_2026-07-05.perf_bundle.json \
    --out    build/AB.collection.sqlite

py -3.12 scripts/eval_memory.py --collection build/AB.collection.sqlite   # + harness args
```

The emitted sqlite has stock **schema11** `col` / `cards` / `revlog` tables. The
`revlog` table is reconstructed **faithfully** (the exact exported columns).
`cards` is stubbed (one neutral row per distinct `cid`) and `col` is a single
default row with a best-effort `crt` (UTC midnight of the earliest review).
FSRS parameters and per-review predicted retrievability are **re-fit / replayed
from the review history** — which is exactly how an FSRS optimizer works — so
revlog alone is sufficient for the revlog-driven calibration path.

### Path B — full collection (robust fallback; Android `.colpkg` lands here)

If a harness variant needs the collection's **stored** per-card FSRS memory
state (stability/difficulty) or its **tuned FSRS weights** — neither of which
lives in the desktop bundle — or the tester is on **Android** (which returns a
`.colpkg`), use the whole collection. Import the `.colpkg` in desktop Anki (or
unzip it to extract the embedded `collection.anki2`) and run the harness
directly:

```bash
py -3.12 scripts/eval_memory.py --collection /path/to/collection.anki2   # + harness args
```

Path A is the default for desktop because it's a small, privacy-light JSON the
tester produces with one click; Path B is the belt-and-suspenders option (and
the only path for Android colpkg data).

---

## Builder vs tester data split

- **Memory calibration can bootstrap on the builder's own `revlog`** (the
  builder has the longest, densest review history — the most calibration
  signal). Report that number honestly with its small-n caveat.
- **Testers strengthen it.** Each returned, separately-labelled file adds an
  independent recall history, so calibration is measured across multiple people
  rather than just the builder. Keep files per-tester (never merged) so the
  harness can report per-participant as well as pooled calibration.
