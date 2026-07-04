# Basic latency / reliability numbers

_Artifact 4 of the MVP-evidence push (reviewer next-focus #4). Last updated
2026-07-03._

> **Reviewer ask:** "Basic latency or reliability numbers." Simple measured
> numbers for the mastery query / performance-mode round-trip (and sync if
> feasible).

## Method (honest, small-n)

A scripted benchmark against the **real modified Anki backend** (fork `rslib`)
and the real `anki.mcat_perf` sidecar:

```
anki-MCAT/out/pyenv/Scripts/python.exe anki-MCAT/tools/mcat_latency_bench.py
```

- **Deck:** 198 synthetic cards across 18 topics, 40 graded reviews (the mastery
  query still iterates all 198 cards + does a per-card `revlog` lookup, so it
  does real work).
- **Samples:** 200 timed calls each (25 for the sync round-trip), 5 warm-up calls
  discarded, `time.perf_counter()`, values in **milliseconds**.
- **Hardware / env:** Python 3.13.13, Windows 11 (10.0.26200), Intel 13th/14th-gen
  laptop CPU. **Single machine, dev build, no isolation** — treat as a
  latency *floor / sanity check*, not a scale benchmark.

Raw JSON: `MCAT/docs/artifacts/latency-results.json`.

## Numbers

| Measurement | n | min | median | p95 | max |
|-------------|---|-----|--------|-----|-----|
| Mastery query — all topics (`get_topic_mastery`) | 200 | 0.86 | **1.04** | 1.32 | 4.32 |
| Mastery query — one topic (`get_topic_mastery_one`) | 200 | 0.86 | **1.09** | 1.30 | 2.02 |
| Perf attempt write (sidecar `INSERT`+commit) | 200 | 1.36 | **1.68** | 2.78 | 4.72 |
| Perf write + score round-trip (`log_attempt`+`accuracy`) | 200 | 1.67 | **2.28** | 3.79 | 6.76 |
| Perf-data sync round-trip (`export_bundle`+`import_bundle`) | 25 | 22.2 | **26.0** | 28.3 | 29.7 |

_All values in milliseconds._

## Reading the numbers

- **Mastery query** (the Speedrun Rust change) is **~1 ms median** at ~200 cards,
  p95 under 2 ms — comfortably interactive for the dashboard / eligibility gate.
- **Perf write** and the **write+score round-trip** are **~1.7 / ~2.3 ms median**
  — a single synchronous SQLite commit each; well within a tap's budget.
- **Perf-data sync round-trip** (export the whole bundle to JSON + union-merge it
  into another device's sidecar) is **~26 ms median** for this dataset. This is
  the perf side-channel (`DECISIONS.md §22`), not Anki's collection sync.

## Honesty caveats

- **Small-n, dev hardware, synthetic deck.** Numbers will differ on other
  machines and grow with collection size.
- **This table is a small-n floor, not a scale benchmark.** The mastery query
  iterates notes/cards and pulls `revlog` per card. Scale to 50k cards is now
  measured separately — see **"50k-scale benchmark"** below (`make bench`).
- **Desktop backend timings.** These are measured on the desktop fork's Python
  binding into the modified Rust engine. On-device (Android) latency would differ
  and depends on the mobile shared-engine work (see `SHARED-ENGINE-PROOF.md`).
- **Collection (memory) sync** latency over the local sync server is **not**
  measured here (needs the running `--syncserver` + a second client); the number
  above is the perf-bundle channel only.

## Reproduce
```bash
cd anki-MCAT
./out/pyenv/Scripts/python.exe tools/mcat_latency_bench.py
# options: --cards N --topics T --iters N --sync-iters N --out PATH
```

---

# 50k-scale benchmark (`make bench`)

_Addresses evidence **E-1** / **D-7** and scale risk **"RS"**: the dashboard-latency
and "scales to a real collection" claims were previously unproven. Added
2026-07-03._

## Why this exists

The table above is a ~200-card **latency floor**. The mastery query iterates every
tagged card and does a **per-card `revlog` lookup** (`get_revlog_entries_for_card`)
plus an FSRS retrievability calc, so its cost is **O(cards)**. The 3-score
dashboard (`anki.mcat_scores.dashboard_data`) calls the mastery query **~4×**
(memory + performance + readiness + focus) plus the perf-store queries. Neither
had been measured at a realistic collection size — this bench does that.

## Method (honest)

`anki-MCAT/tools/mcat_bench_50k.py`, run via `make bench`, against the **real,
already-built fork backend** (`out/pylib`) — a Python timing harness, **no fresh
Rust rebuild** (the dashboard claim lives in the Python/Qt path, and this avoids
contention with the long native build).

- **Deck:** 49,986 synthetic cards across 18 topics (`topic:{id}` tags), **5,000**
  graded Good (→ 5,000 `revlog` rows + FSRS memory state; the query still visits
  all ~50k cards). Seed cost: ~96 s to add, ~6 s to review.
- **Perf data:** questions bank + 120 seeded attempts so the performance/readiness
  scores do real work rather than instantly abstaining.
- **Samples:** 25 timed calls for the mastery queries, 15 for the dashboard, 3
  warm-ups discarded, `time.perf_counter()`, milliseconds.
- **Hardware / env:** Python 3.13, Windows 11 (10.0.26200), Intel 13th/14th-gen
  laptop CPU. **Single machine, dev build, no isolation.**

Raw JSON: `MCAT/docs/artifacts/bench-50k-results.json`.

## Numbers (49,986 cards / 5,000 reviews)

| Measurement | n | min | p50 | p95 | max |
|-------------|---|-----|-----|-----|-----|
| Mastery query — all topics (`get_topic_mastery`) | 25 | 286 | **304** | 355 | 368 |
| Mastery query — one topic (`get_topic_mastery_one`) | 25 | 297 | **329** | 416 | 433 |
| 3-score dashboard end-to-end (`dashboard_data`) | 15 | 2503 | **2893** | 5189 | 5189 |

_All values in **milliseconds**._

## Reading the numbers (the honest finding)

- **The mastery query is ~300 ms at 50k** (p50 304 ms, p95 355 ms) — up from ~1 ms
  at 200 cards, i.e. **~O(cards)** as predicted by the per-card `revlog` design.
  Borderline-interactive for a single eligibility check, but not snappy.
- **The single-topic query is NOT cheaper (~329 ms).** `topic_mastery_one`
  computes stats for **all** topics and then selects one (`topic_stats_by_id()`
  builds the full map). A per-topic caller pays the whole-collection cost.
- **The 3-score dashboard is ~2.9 s at 50k** (p50 2893 ms, p95 5.2 s). This is
  **not interactive** — it confirms scale risk "RS" is real. The cost is roughly
  `~4 × mastery query` because `dashboard_data` recomputes the mastery query in
  `memory_summary`, `unlocked_topic_ids` (perf + readiness), and `focus_area`.

## Bottleneck + recommended fix (measured, not yet applied)

Per the mastery-query spec's fallback plan, the dominant cost is the
**per-card `revlog` lookup executed once per card** (`topic_mastery.rs`
`topic_stats_by_id` → `get_revlog_entries_for_card` inside the card loop). Two
low-risk wins, **deferred here to avoid destabilizing correctness / triggering a
Rust rebuild during the active native build**:

1. **Cache the mastery result within one dashboard build.** `dashboard_data`
   currently calls `col.get_topic_mastery()` ~4× per render; computing it once
   and passing it down would cut the dashboard from ~2.9 s toward ~1× the query
   (~0.3 s) with no engine change. (Lives in `mcat_scores.py`, owned by another
   worker — flagged, not edited here.)
2. **Grouped single-pass SQL aggregation** in `topic_stats_by_id` — one query
   joining notes→cards→revlog grouped by card instead of N per-card `revlog`
   round-trips — should drop the ~300 ms query by an order of magnitude. This is
   a Rust change requiring a rebuild + re-running the mastery tests
   (`cargo test -p anki mcat`, `test_mcat_mastery.py`); recommended but **not**
   done in-session because it must not risk correctness of a shipped query.

Also: `topic_mastery_one` should short-circuit to a single topic's notes rather
than building the full map.

## Honesty caveats

- **Synthetic seeding, single dev machine, no isolation.** Absolute numbers will
  differ on other hardware and with real (heavier) note templates; treat the
  **shape (O(cards), ~4× fan-out)** as the durable finding, not the exact ms.
- **Only 5,000 of ~50k cards were graded** (v3 scheduler daily-limit realities);
  the remaining cards still incur the per-card `revlog` lookup (empty result),
  which is exactly the dominant cost being measured. A collection with more
  review history would push the query *higher*, not lower.
- **Desktop backend.** On-device (Android) latency differs (see
  `SHARED-ENGINE-PROOF.md`).
- **The fix in the previous section is measured/recommended, not applied** — the
  numbers above are for the current, unoptimized code.

## Reproduce
```bash
cd MCAT
make bench                       # full ~50k run (seed ~100 s + timing)
# or a faster smoke run:
make bench BENCH_ARGS="--cards 10000 --reviews 2000 --iters 15 --dash-iters 10"
# direct:
anki-MCAT/out/pyenv/Scripts/python.exe anki-MCAT/tools/mcat_bench_50k.py \
  --cards 50000 --reviews 5000 --iters 25 --dash-iters 15
```
