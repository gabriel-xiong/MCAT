# Application-Practice Remediation Pool

Status: **content + validation complete**; UI/routing wiring is a **separate later pass**.

## Why this exists

The science error-diagnosis engine routes a miss to one of two remediation channels
(see `docs/ERROR-DIAGNOSIS-SPEC.md`):

- **`content_gap`** — the student holds a false belief → review the specific backing
  memory concept.
- **`application`** — the student *had* the content but failed to **deploy** it on an
  integration question → **targeted practice on similar integration items**.

That practice destination did not exist, so the `application` next-action degraded to a
generic *"practice more applied items in \[topic]."* This pool is the concrete
destination so the routing can hand the student real integration items.

## Where it lives

- **Pool data:** `data/application-practice.json` (generated; do not hand-edit).
- **Builder (source of record):** `scripts/build_application_practice.py`
  — deterministic, named-source-grounded, **AI off**. Re-run to regenerate the JSON.
- **Validation:** `scripts/validate_data.py` → `validate_application_practice()`.
- **Leakage guard:** `scripts/eval_leakage.py` → `check_pool_vs_questions()`.

The pool is a **separate file from `data/questions.json`** on purpose: the main bank is
the eval/performance bank (dev + held_out), and mixing remediation items into it would
create leakage confusion. Nothing here touches `questions.json`.

## Scope

- **Science only** (`CP`, `BB`, `PS`). The `application` diagnosis is a science-engine
  signal; CARS is performance-only with no `cognitive_demand`, so it is excluded.
- **45 items, 3 per topic** across all 15 science topics in `data/mcat-outline.v1.json`.
- Every item is **`application` or `synthesis`** (multi-step / deploy-the-concept) —
  **never `recall`**.

## Storage schema & markers (how the wiring pass queries the pool)

Each item is a superset of the main-bank question schema plus three markers:

| Field | Value / meaning |
|---|---|
| `pool` | `"application_practice"` — identifies membership in this pool |
| `split` | `"remediation"` — keeps it out of all dev/held_out logic |
| `concept` | short slug (e.g. `henderson_hasselbalch`) — the sub-concept the item drills |
| `id` | `ap_<topic_id>_<NN>` (e.g. `ap_cp_acids_bases_02`) |
| `topic_id` | one of the 15 science topics; use this to filter by topic |
| `cognitive_demand` | `application` \| `synthesis` |
| `choice_diagnosis` | list aligned 1:1 with `choices`; correct index is `null`; distractors are `{maps_to: content_gap, misconception}` or `{maps_to: null, trap: <enum>}` |

All standard fields are also present: `stem`, `choices` (4), `correct` (A–D),
`section`, `skill`, `explanation` (static, source-grounded), `source_name`,
`source_url`, `source_location`.

**Query by topic** (illustrative):

```python
import json
pool = json.load(open("data/application-practice.json", encoding="utf-8"))
by_topic = {}
for it in pool:                       # pool membership is implied by the file,
    by_topic.setdefault(it["topic_id"], []).append(it)   # but each item also
                                                          # carries pool == "application_practice"
```

## Spec for the wiring pass (routing → remediation set)

**Trigger.** A missed performance question resolves to diagnosis `application` for
`topic_id = T`, and the missed item exposes a `concept` slug `C` (the just-missed
sub-concept — the missed item's own `concept`, or the concept implied by its
`choice_diagnosis`).

**Selection algorithm** (deterministic, AI-off, reads only the local pool):

1. **Filter** the pool to `topic_id == T` and `pool == "application_practice"`.
2. **Exclude the just-missed concept:** drop items whose `concept == C`, so the student
   practices *sibling* integration items rather than re-seeing the exact concept they
   just missed. (If this empties the set, fall back to including same-concept items.)
3. **Exclude already-seen items:** drop any pool `id` the student has already answered
   in this remediation channel (track a seen-set), so repeated `application` misses in a
   topic surface *new* practice.
4. **Rank** for variety: prefer covering distinct `concept` slugs; within that, prefer
   `synthesis` for repeat misses and `application` for a first miss (optional heuristic).
5. **Take `N`** items — suggest **N = 2** for a lightweight nudge (each topic has 3, so
   excluding the missed concept leaves ≥2). Make `N` a config constant.
6. **Serve** them as a short, separate remediation set. Scoring: these are practice, not
   eval — **do not** fold them into the performance score or the held_out eval; log them
   under their own remediation channel.

**Degradation contract.** If the pool has no eligible items for `T` (e.g. a topic added
later without pool coverage), fall back to the current generic
*"practice more applied items in \[topic]"* message rather than erroring — honesty over a
fake destination.

**Non-leakage invariant the wiring must preserve.** Never promote a `remediation` item
into `questions.json` or into a scored performance/eval session. The leakage guard
(`scripts/eval_leakage.py`) enforces distinctness of stems today; keeping the pool in its
own file and its own channel preserves that at runtime.

## Reproduce / verify

```bash
python scripts/build_application_practice.py   # regenerate data/application-practice.json
python scripts/validate_data.py                # validates the pool with main-bank rigor
python scripts/eval_leakage.py                 # pool vs questions.json (dev + held_out)
```

Leakage uses exact/substring match **plus** a token-overlap (Jaccard) near-duplicate
threshold of `0.60`; the current pool's worst-case similarity to any bank stem is `0.41`.
