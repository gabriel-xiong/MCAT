# Mastery Query — Rust API Spec (v1)

**Status:** ✅ Verified (v1) — 4 Rust unit tests + Python integration test pass; confirmed live in `./run` on a tagged 16-note dev deck (all 3 topics flipped `performance_unlocked=True` after ≥5 Good/Easy).  
**Speedrun requirement:** ≥3 Rust unit tests, ≥1 Python integration test, undo safe — met.

**Known v1 note:** `avg_retrievability` reports `0.0` until FSRS `memory_state` exists (FSRS enabled + review history). Unlock logic does not depend on it.

**⚠️ Scale not yet validated:** verified only on a ~16-note dev deck. The current implementation iterates notes/cards and pulls revlog per card in Rust — fine for a small deck, but **must be benched at scale (target 50k cards) later** before relying on it for the dashboard or frequent calls. If per-card revlog lookups dominate, move aggregation into a single grouped SQL query over `revlog`/`cards`. Track via `make bench`.

---

## Purpose

Fast per-topic stats for:

1. **Performance eligibility** (`scoring-config.json` thresholds)
2. **Dashboard** (memory score breakdown, coverage)
3. **`make bench`** at 50k cards

---

## Proposed API (Rust)

```rust
/// One row per topic tag present in the collection.
pub struct TopicMastery {
    pub topic_id: String,
    pub cards_total: u32,
    pub cards_seen: u32,           // ≥1 review
    pub good_or_easy_count: u32,
    pub avg_retrievability: f32,   // FSRS mean over cards in topic (0..1)
    pub performance_unlocked: bool,
}

pub fn topic_mastery_all(collection: &Collection) -> Result<Vec<TopicMastery>>;
pub fn topic_mastery_one(collection: &Collection, topic_id: &str) -> Result<TopicMastery>;
```

**`performance_unlocked` logic** (mirror config):

```
cards_seen >= 3 AND good_or_easy_count >= 5
```

(CARS topics handled in app layer — no card gate.)

---

## Data sources (existing Anki tables)

| Field | Source |
|-------|--------|
| `cards_total`, `cards_seen` | `cards` + `revlog` grouped by note tag / deck tag |
| `good_or_easy_count` | `revlog` where ease ≥ Good |
| `avg_retrievability` | FSRS state per card → aggregate by topic |

**Tag convention:** notes tagged `topic:bb_glycolysis` → topic_id `bb_glycolysis`  
(See `data/deck-tagging.md`.)

---

## Python exposure

Protobuf + `Collection` methods (in `anki-MCAT`):

```python
mastery = col.get_topic_mastery()       # list[TopicMastery]
one = col.get_topic_mastery_one("bb_enzymes")
```

Integration test: `pylib/tests/test_mcat_mastery.py`

---

## Implementation (anki-MCAT)

| Layer | Path |
|-------|------|
| Proto | `proto/anki/mcat.proto` |
| Rust logic | `rslib/src/mcat/topic_mastery.rs` |
| Rust service | `rslib/src/mcat/service.rs` |
| Python | `pylib/anki/collection.py` |

Rust unit tests: `topic_mastery` module (4 tests in `topic_mastery.rs`).

---

## Files to explore first (after clone builds)

```
rslib/src/...        # collection, revlog, scheduler, FSRS
pylib/...            # Collection wrapper
proto/...            # new messages if needed
```

Grep starting points:

```bash
rg "revlog" rslib --glob "*.rs" | head
rg "retrievability" rslib --glob "*.rs" | head
rg "CollectionStats" rslib pylib
```

---

## Non-goals (v1)

- Reschedule cards (topic-aware scheduling = separate / later)
- Write path during query (read-only)
- Custom SQL from Python without Rust

---

## Merge note template (fill after implementation)

| Item | Value |
|------|--------|
| Upstream files touched | `proto/anki/mcat.proto`, `rslib/src/mcat/*`, `pylib/anki/collection.py` |
| Merge difficulty | low |
| Why Rust not Python | Needs FSRS + revlog at scale on 50k cards |

See also `docs/RUST-CHANGE-NOTE.md`.
