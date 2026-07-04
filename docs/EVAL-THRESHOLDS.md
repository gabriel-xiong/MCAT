# Score thresholds — two pre-registered profiles

> **Scope label:** the **tester** profile below is a set of **friend-tester
> ENGAGEMENT thresholds — NOT used for graded readiness claims.** Graded
> evaluation uses the **strict** profile only. See
> [`DECISIONS.md` §31](DECISIONS.md) and §13/§14.

The on-device scorer (`anki-MCAT/pylib/anki/mcat_scores.py`) ships **two**
pre-registered threshold profiles, selected by the module constant
`SCORE_PROFILE`:

- `"strict"` — the full-course production gates. What a **graded** readiness
  claim uses. Mirrors `MCAT/data/scoring-config.json` (`give_up`).
- `"tester"` — **friend-tester engagement** gates. Deliberately low so a casual
  friend who studies for a single **~15–20 min sitting** (≈10–20 cards reviewed,
  ≈8–12 questions across 1–2 topics) still sees all three **PROVISIONAL** scores
  populate. **This build ships `"tester"`.**

Switching the constant back to `"strict"` (and rebuilding) restores the graded
gates with no other code change.

## Thresholds

| Gate | Constant | Strict (graded) | Tester (this build) |
|------|----------|-----------------|---------------------|
| Memory — graded reviews | `MIN_MEMORY_REVIEWS` | 200 | **10** |
| Memory — require 21-day maturity | `REQUIRE_MEMORY_MATURITY` | `True` | **`False`** |
| Memory — started-card floor | `MIN_STARTED_CARDS_FOR_MEMORY` | 0 (maturity governs) | **10** |
| Performance — attempts | `MIN_PERF_ATTEMPTS` | 30 | **8** |
| Readiness — unlocked topics | `MIN_UNLOCKED_TOPICS` | 1 | 1 |
| Readiness — coverage % | `MIN_COVERAGE_PCT` | 50 | 50 |
| Readiness — science section attempts | `MIN_ATTEMPTS_PER_SCIENCE_SECTION` | 5 | **3** |
| Readiness — CARS attempts | `MIN_CARS_ATTEMPTS` | 5 | **3** |

Coverage is unchanged: the shipped 3-topic scope makes 2/3 = 66% reachable, so a
50% gate is both honest **and** attainable in one short sitting. Section gates are
scoped to the sections THIS build actually ships (CP + BB here), so an absent
PS/CARS section never blocks a scoped tester (see `shipped_scope_sections`).

## Why these are attainable for a casual tester

- **Memory (≥10 reviews, ≥10 cards, no maturity):** one pass through part of the
  66-card deck. FSRS must be ON for a retrievability estimate to exist — the seed
  tool (`tools/mcat_seed_tester.py`) enables FSRS + the v3 scheduler in the
  shipped base, so every tester review populates a card `memory_state`.
- **Performance (≥8 attempts, ≥3/section):** the practice pool (dev split) ships
  **CP=7, BB=4** questions; one short practice set clears 8 total with ≥3 in each
  shipped section.
- **Readiness:** unblocks once Memory reviews + Performance attempts + coverage +
  per-section gates clear — all reachable in the same sitting.

## Memory basis differs by profile

- **strict:** Recall strength = **retrievability × deck maturity** (rewards
  durable, long-interval memory; needs ≥1 card at interval ≥21d).
- **tester:** **EARLY RECALL STRENGTH = retrievability only** (maturity factor
  forced to 1.0). Measures "how well you'd recall right now what you've
  reviewed", **not** long-term durability. Labeled provisional / early-recall in
  the UI and gated on the ≥10-card floor so the average isn't from 1–2 cards.

## Honesty safeguards (what makes low gates defensible)

1. **0 data always abstains.** A truly empty profile shows "No score yet" on all
   three; the gates never fabricate a number.
   (Tests: `test_empty_profile_still_abstains_under_tester_gates`,
   `test_all_cards_abstain_on_empty_profile`.)
2. **Confidence intervals stay VERY WIDE at small n — no false precision.**
   - **Memory** uses a boundary-safe **Wilson** interval on the mean recall
     probability. (The plain normal SE `z·√(R(1−R)/n)` collapses to ±0 as R→1.0,
     which happens right after a review — that was replaced.) Example: 18/18 cards
     just reviewed → score 100, CI **82–100**.
   - **Performance** keeps its Bayesian-shrinkage headline + Wilson credible
     band. Example at the tester gate: 6/10 → score 57, CI **32–82**.
   - **Readiness** widens the mapped range at small n: `_readiness_half_width`
     grows the half-width from the strict ±6 up to ~±24 at the tester attempt
     count. Example short session: range width **34** points.
3. **Provisional labels + fields on every computed score.** A `provisional` flag
   drives a `provisional` badge (never the plain `measured` badge) and each score
   carries coverage %, a missing-data/next-action note. The three scores are
   **never blended**.
4. **Accuracy number XOR "not enough data"** — the earlier accuracy-card fix is
   preserved (a computed number and the abstain badge can never co-exist).

## End-to-end verification (this build)

`out/mcat_tester_scale_verify.py` runs against a scratch copy of the freshly
seeded shipped base:

| Profile | Memory | Accuracy | Readiness |
|---------|--------|----------|-----------|
| FRESH (0/0) | abstain — "No score yet" | abstain | abstain |
| SHORT (18 reviews + 10 Qs) | 100/100, CI **82–100**, provisional | 57/100, CI **32–82**, provisional | 472–506 (width **34**), coverage 100%, conf 46, provisional |

## Regenerating / flipping profiles

- Flip: set `SCORE_PROFILE = "strict"` in `mcat_scores.py`, rebuild.
- The strict numbers stay mirrored in `MCAT/data/scoring-config.json` (`give_up`)
  and `DECISIONS.md` §14 for graded use.
