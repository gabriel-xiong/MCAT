# Rust change note — MCAT Speedrun (anki-MCAT fork)

## Mastery query (v1)

**Why Rust:** FSRS retrievability + revlog aggregation at collection scale (50k+ cards); read-only, undo-safe.

**Upstream touch:**

| Area | Files |
|------|--------|
| Proto | `proto/anki/mcat.proto` |
| Rust | `rslib/src/mcat/topic_mastery.rs`, `service.rs` |
| Python | `pylib/anki/collection.py` — `get_topic_mastery()` |

**API:** `TopicMastery` per `topic:{id}` note tag — `cards_seen`, `good_or_easy_count`, `avg_retrievability`, `performance_unlocked` (≥3 seen, ≥5 Good/Easy).

**Merge difficulty:** Low — isolated `mcat/` module; no scheduler changes.

**Spec:** `MCAT/docs/MASTERY-QUERY-SPEC.md`
