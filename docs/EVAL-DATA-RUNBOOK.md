# Real eval-data runbook — memory calibration + held-out performance

_Last updated: 2026-07-03._

Copy-paste runbook for the **two real-data eval pipelines** that need a human to
generate the data (the builder actually studies; a friend actually answers the
frozen questions). Everything downstream is scripted and **verified working** —
see the "Proven" note under each pipeline. Companion docs:
[`TESTER-QUICKSTART.md`](TESTER-QUICKSTART.md) (what to tell testers),
[`TESTER-HANDOFF.md`](TESTER-HANDOFF.md) (what a returned file contains) and
[`RECORDING-CHECKLIST.md`](RECORDING-CHECKLIST.md) (what to film).

> **No AI, no network.** Both pipelines are local file transforms + arithmetic.
> Nothing here calls an LLM or phones home.

All commands run from the MCAT repo root in Git Bash:

```bash
cd /c/Users/gpdxi/Downloads/alphaProjects/MCAT
```

`build/` is a scratch dir for outputs; the calibration artifacts land in
`docs/artifacts/`.

---

## Pipeline A — Memory calibration (real Brier / log-loss + reliability PNG)

**What it proves:** the FSRS memory model is *calibrated* — when it predicts
recall probability R, cards at that R are actually recalled ~R of the time on
**held-out** reviews (chronological 70/30 split). Output is a **Brier score**,
**log-loss**, **ECE**, and a **reliability-diagram PNG**.

**Human step:** the builder (and optionally weekend testers) must **actually
review flashcards over 2–3 days** — dozens of reviews, not five. Calibration is
about recall *over time*; same-day cramming does not calibrate. (This is exactly
what `TESTER-HANDOFF.md` asks testers to do.)

### A.0 Get the review data — pick ONE source

| Source | When to use | How to get it |
|--------|-------------|---------------|
| **Builder's own collection** | Default — the builder has the longest, densest revlog (most signal) | Use the live `collection.anki2` path (below). Read-only; the harness opens it `mode=ro&immutable=1`. |
| **A tester's exported bundle** | A weekend tester sent back a `*.perf_bundle.json` | Convert with `revlog_from_bundle.py` (Path A below). |
| **A tester's full collection** | A harness variant needs *stored* FSRS state/weights | Use their `collection.anki2` directly. |

The builder's desktop collection on this machine is typically:

```
C:\Users\gpdxi\AppData\Roaming\Anki2\<ProfileName>\collection.anki2
```

Find it (read-only) with:

```bash
ls -la "$APPDATA/Anki2"/*/collection.anki2
```

> Quit Anki before pointing the harness at the live file if you hit a lock; the
> harness already falls back to a read-only temp copy, so this is usually
> unnecessary.

### A.1 Run calibration on the builder's collection (direct path)

```bash
py -3.12 scripts/eval_memory.py \
  --collection "$APPDATA/Anki2/User 1/collection.anki2" \
  --out docs/artifacts/memory-calibration.png
```

Or via the Makefile (same thing):

```bash
make eval-memory MCAT_COLLECTION="$APPDATA/Anki2/User 1/collection.anki2"
```

### A.2 Tester bundle → sqlite → calibration (Path A, no eval_memory edits)

When a tester returns `MCAT-data_<who>_<date>.perf_bundle.json` (the desktop
"Export my data" button — see `TESTER-HANDOFF.md`):

```bash
py -3.12 scripts/revlog_from_bundle.py \
  --bundle MCAT-data_AB_2026-07-05.perf_bundle.json \
  --out    build/AB.collection.sqlite

py -3.12 scripts/eval_memory.py \
  --collection build/AB.collection.sqlite \
  --out docs/artifacts/memory-calibration-AB.png
```

`revlog_from_bundle.py` rebuilds a minimal, stock-shaped `collection.anki2`
(schema11 `col`/`cards`/`revlog`) from the bundle's `memory_revlog`; FSRS params
and per-review R are re-fit/replayed from the revlog, so revlog alone suffices.

### A.3 Expected outputs

The harness prints and writes:

```
=== MEMORY CALIBRATION (held-out reviews) ===
train-ratio      : 0.70
n_train (context): <int>
n_test  (scored) : <int>
Brier score      : <0..1, lower better>
log-loss         : <lower better>
ECE              : <mean |pred-obs|>
mean predicted R : <...>
mean observed    : <...>   (model OVER/under-confident by <...>)
  <10-row reliability bin table>
```

Artifacts (paths are derived from `--out`):

| File | Contents |
|------|----------|
| `docs/artifacts/memory-calibration.png` | reliability diagram (predicted R vs observed recall) |
| `docs/artifacts/memory-calibration.bins.csv` | per-bin n / mean_pred / obs_recall / gap |
| `docs/artifacts/memory-calibration.summary.json` | machine-readable summary (Brier, log-loss, ECE, bins) |

> **Honesty gate (built in):** if total graded reviews `< 200`
> (`data/scoring-config.json → give_up.memory.min_total_reviews`) the harness
> prints a `[HONESTY]` warning that the memory score would be **withheld** —
> report the number as indicative-only with the small-n caveat. The summary JSON
> records `param_source`; if it says "DEFAULT_PARAMETERS … WARNING" the numbers
> reflect *default* FSRS weights, not the collection's optimized weights.

### A.4 Proven

The full **bundle → adapter → harness** chain and the direct-collection path were
run end-to-end against a synthetic collection (5,098 revlog rows, 600 cards):
`revlog_from_bundle.py` wrote the sqlite, `eval_memory.py` produced a Brier/
log-loss report + PNG + CSV + summary JSON. The `--synthetic` self-test
(`make eval-memory` with no `MCAT_COLLECTION`) also passes and injects a known
miscalibration to prove the metrics respond correctly. Only the **real review
data** is the human step.

---

## Pipeline B — Held-out performance accuracy (real, frozen split)

**What it proves:** real **performance accuracy** on the frozen `held_out` split
— questions the volunteer has never seen in a dev performance session — scored
against the bank's answer key, with a Wilson 95% CI and per-section/topic
breakdown.

**Human step:** a **friend/volunteer answers the held-out questions.** They must
not have used the dev bank. There are **105** `held_out` questions in
`data/questions.json` (verified: `split=="held_out"`, letter answer key in
`correct`, 4 choices each).

### B.0 Where the frozen split lives

```
data/questions.json     # split=="held_out"  → 105 questions (dev==65)
```

Each question: `id`, `stem`, `choices` (list), `correct` (letter A–D),
`topic_id`, `section` (BB/CP/PS/CARS), `skill`, `cognitive_demand`.

### B.1 Make a blank answer sheet for the volunteer (no key leaked)

```bash
py -3.12 scripts/score_heldout.py \
  --make-template build/heldout-answers.TEMPLATE.json
```

This writes one row per held-out question with `answer: ""` and **no** correct
answer / explanation — safe to hand to a volunteer. They fill in the `answer`
field with a **letter** (A/B/C/D). (For presenting the actual stems + choices to
the volunteer, print them from `data/questions.json` filtered to
`split=="held_out"`, or drive them through the app's Performance mode on a device
loaded only with the held-out bank.)

Accepted answer formats (per question, in the responses file): a **letter**
(`"A"`, case-insensitive), the **exact choice text**, or a **0-based integer
index**. Blank/`null`/`""` = unanswered.

The responses file may also be a flat dict:

```json
{ "q_ho_001": "A", "q_ho_002": "C", "q_ho_003": "B" }
```

### B.2 Score the returned answers

```bash
py -3.12 scripts/score_heldout.py \
  --responses build/heldout-answers_friend.json
```

Output:

```
HELD-OUT PERFORMANCE ACCURACY   [real data: heldout-answers_friend.json]
held_out questions in bank : 105
answered (graded)          : <n>
unanswered / blank         : <...>
OVERALL ACCURACY : <acc>  (<k>/<n>)
Wilson 95% CI    : [<lo>, <hi>]
  by section  (BB / CP / PS / CARS)
  by topic_id
```

`score_heldout.py` is **read-only** against the bank (it never edits
`questions.json` or any shared module). It flags unparseable answers and any
response ids that are not in the held-out split. With `< 30` graded answers it
prints a small-n honesty warning and the CI stays deliberately wide.

### B.3 (Optional) Paraphrase gap E-6

If the volunteer answered the paraphrase-pair questions
(`data/paraphrase-test.json`, e.g. `q_ho_061`…), emit an attempts file and feed
the existing §7d scorer:

```bash
# 1. emit a paraphrase-compatible attempts file from the same responses:
py -3.12 scripts/score_heldout.py \
  --responses build/heldout-answers_friend.json \
  --emit-attempts build/heldout-attempts.json

# 2. combine with a per-concept memory-recall file (recall rate per concept):
#    { "vmax_saturation": 0.90, "km_definition_and_affinity": 0.85, ... }
py -3.12 scripts/eval_paraphrase.py \
  --recall  build/paraphrase-recall.json \
  --attempts build/heldout-attempts.json
```

`paraphrase_gap = card_recall_rate − question_accuracy` per concept, aggregated
by topic and overall. A large positive gap = the performance score is measuring
transfer, not parroted memory. (`make eval-performance` runs the synthetic demo
version with no real data.)

### B.4 Proven

`score_heldout.py` was run end-to-end: `--help`, `--make-template` (105-question
blank sheet, no key), `--demo` (deterministic synthetic answers → 0.733 overall,
Wilson CI, per-section + per-topic tables), a mixed-format real round-trip
(letter + exact-text + integer-index all graded correctly; blank → unanswered;
unknown id flagged), and `--emit-attempts` → `eval_paraphrase.py` accepted the
attempts and printed a full §7d gap report. Only the **volunteer's real answers**
are the human step. See the parent report for the pasted proof output.

---

## What is fully scripted vs. needs a human

- **Fully scripted (verified):** bundle→sqlite adapter, memory-calibration
  harness (Brier/log-loss/ECE/PNG), held-out scorer (accuracy + Wilson CI +
  breakdowns), paraphrase-gap scorer, and the attempts hand-off between them.
- **Needs a human:** (A) the builder/testers actually reviewing flashcards over
  several days; (B) a friend actually answering the 105 frozen held-out
  questions. Do **not** fabricate either dataset — run the synthetic/demo modes
  for wiring proof, and only report "real" numbers once real data exists.
