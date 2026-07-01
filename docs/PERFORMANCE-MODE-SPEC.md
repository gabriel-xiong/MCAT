# Performance mode — implementation spec (v1)

**Status:** Mastery query ✅ verified. Building perf mode in phases (storage → eligibility → UI → entry → score).

## Architecture decisions (locked 2026-06-30)

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Perf storage | **Local sidecar `mcat_perf.db`** next to `collection.anki2` | Avoids Check-DB / full-sync wipe of custom tables; clean schema ownership (see `DECISIONS.md` §5) |
| Storage code | **Python** (`sqlite3` on sidecar) | No new Rust; mastery query stays the only Rust change |
| UI | **Native Qt `QDialog`** | Fastest to a working loop; webview polish later |
| Entry point | Tools menu → "MCAT Performance" | No `moveToState` surgery for v1 |
| Loader | Idempotent upsert from `questions.json` | Re-runnable; AI off at runtime |
| Scoring | Accuracy on `perf_attempts`, never blended with memory | Honesty rule |
| External/cloud DB | **None in v1** — local-first | Anki is per-device; cloud deferred to if/when cloud features needed |

Sidecar path: same directory as `col.path`, filename `mcat_perf.db`.

---

## User flow

1. Dashboard shows **Performance** button (enabled when ≥1 topic unlocked).
2. User starts **separate session** (not reviewer).
3. Load questions where:
   - `topic_id` is performance-unlocked, **or** `section == CARS`
   - `split == dev` during development (held_out reserved for friend eval)
4. Present MCQ → user answers → show correct/incorrect.
5. On **miss:** show 4 error-type buttons (from `scoring-config.json`).
6. Log `PerformanceAttempt` to collection.
7. End session → refresh performance score on dashboard.

**Study feature flag:** session config `interleaved: bool` — shuffle topics vs blocked by topic.

---

## SQLite tables (sidecar `mcat_perf.db`)

```sql
CREATE TABLE perf_questions (
  id TEXT PRIMARY KEY,
  stem TEXT NOT NULL,
  choices_json TEXT NOT NULL,
  correct TEXT NOT NULL,
  topic_id TEXT NOT NULL,
  section TEXT NOT NULL,
  skill TEXT,
  source_name TEXT NOT NULL,
  source_url TEXT,
  source_location TEXT,
  split TEXT NOT NULL CHECK (split IN ('dev', 'held_out'))
);

CREATE TABLE perf_attempts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  question_id TEXT NOT NULL,
  correct INTEGER NOT NULL,
  error_type TEXT,
  time_seconds REAL,
  interleaved INTEGER NOT NULL DEFAULT 0,
  ts INTEGER NOT NULL,
  FOREIGN KEY (question_id) REFERENCES perf_questions(id)
);
```

**Loader:** import `data/questions.json` on first run or via dev menu.

---

## Eligibility check (Python)

Read `col.get_topic_mastery()` from Rust (when implemented) or compute from tags + revlog:

```python
# Mirror data/scoring-config.json
performance_unlocked = (
    cards_seen >= 3 and good_or_easy >= 5
)
```

CARS questions skip gate.

---

## Files to add in Anki fork (planned)

| Area | Path (TBD after exploring qt/) |
|------|--------------------------------|
| Performance UI | `qt/aqt/performance/` or add-on panel |
| Dashboard | `qt/aqt/mcat_dashboard.py` |
| Loader | `pylib/perf/import_questions.py` |
| Rust | `rslib/.../topic_mastery.rs` |

---

## Wednesday minimum

- Load ≥1 question; one full attempt logged; error type saved; score updates (even if crude).
