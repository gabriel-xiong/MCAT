#!/usr/bin/env py -3.12
"""Adapter: MCAT "Export my data" bundle -> minimal collection.anki2-shaped sqlite.

WHY: the memory-calibration harness (``scripts/eval_memory.py``) reads a
collection's ``revlog`` table via ``--collection <collection.anki2>``. Testers,
however, hand back the portable **perf bundle** produced by the desktop
dashboard's "Export my data" button. Since that bundle now ADDITIVELY carries
the tester's raw revlog rows (key ``memory_revlog``) plus a ``participant``
label, this standalone script rebuilds a MINIMAL sqlite file — shaped like a
stock ``collection.anki2`` (schema11: ``col`` / ``cards`` / ``revlog``) — so it
can be fed straight to the harness WITHOUT modifying ``eval_memory.py``:

    py -3.12 scripts/revlog_from_bundle.py \
        --bundle MCAT-data_AB_2026-07-05.perf_bundle.json \
        --out    /tmp/AB.collection.sqlite
    py -3.12 scripts/eval_memory.py --collection /tmp/AB.collection.sqlite ...

WHAT IS AND ISN'T RECONSTRUCTED
  * ``revlog`` is reconstructed FAITHFULLY (the exact stock columns:
    id [epoch-ms], cid, usn, ease, ivl, lastIvl, factor, time, type). This is
    the calibration-critical signal: FSRS parameters and per-review predicted
    retrievability can be *re-fit / replayed* from review history alone, which
    is exactly what an FSRS optimizer does.
  * ``cards`` is stubbed (one row per distinct ``cid`` with neutral defaults and
    empty ``data``) and ``col`` is a single default row. Stored per-card FSRS
    memory state (stability/difficulty) and the collection's tuned FSRS weights
    are NOT in the bundle, so they are NOT reconstructed here.

ROBUST FALLBACK (documented + preferred when in doubt): if a harness variant
needs the collection's *stored* FSRS state or tuned weights (rather than
re-fitting from revlog), the tester should send their whole ``collection.anki2``
and the harness reads it directly via ``--collection``. This adapter covers the
revlog-driven path; the full-collection path covers everything else. See
docs/TESTER-HANDOFF.md.

No AI, no network — a plain local file transform.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any

# Stock Anki revlog columns, in order (mirrors anki-MCAT rslib schema11.sql and
# pylib/anki/mcat_perf.REVLOG_COLUMNS). All are NOT NULL in the real schema.
REVLOG_COLUMNS = ("id", "cid", "usn", "ease", "ivl", "lastIvl", "factor", "time", "type")

# Neutral integer default for any missing revlog field (defensive; a well-formed
# export always carries every column).
_REVLOG_DEFAULT = 0

# Minimal schema11 subset: the three tables a revlog-driven harness may touch.
# Kept byte-compatible with stock Anki so eval_memory.py's raw SQL just works.
_SCHEMA = """
CREATE TABLE IF NOT EXISTS col (
  id integer PRIMARY KEY,
  crt integer NOT NULL,
  mod integer NOT NULL,
  scm integer NOT NULL,
  ver integer NOT NULL,
  dty integer NOT NULL,
  usn integer NOT NULL,
  ls integer NOT NULL,
  conf text NOT NULL,
  models text NOT NULL,
  decks text NOT NULL,
  dconf text NOT NULL,
  tags text NOT NULL
);
CREATE TABLE IF NOT EXISTS cards (
  id integer PRIMARY KEY,
  nid integer NOT NULL,
  did integer NOT NULL,
  ord integer NOT NULL,
  mod integer NOT NULL,
  usn integer NOT NULL,
  type integer NOT NULL,
  queue integer NOT NULL,
  due integer NOT NULL,
  ivl integer NOT NULL,
  factor integer NOT NULL,
  reps integer NOT NULL,
  lapses integer NOT NULL,
  left integer NOT NULL,
  odue integer NOT NULL,
  odid integer NOT NULL,
  flags integer NOT NULL,
  data text NOT NULL
);
CREATE TABLE IF NOT EXISTS revlog (
  id integer PRIMARY KEY,
  cid integer NOT NULL,
  usn integer NOT NULL,
  ease integer NOT NULL,
  ivl integer NOT NULL,
  lastIvl integer NOT NULL,
  factor integer NOT NULL,
  time integer NOT NULL,
  type integer NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_revlog_cid ON revlog (cid);
CREATE INDEX IF NOT EXISTS ix_revlog_usn ON revlog (usn);
"""


def _load_bundle(path: Path) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        bundle = json.load(f)
    if not isinstance(bundle, dict):
        raise ValueError("bundle must be a JSON object")
    fmt = bundle.get("format")
    if fmt not in (None, "mcat_perf_bundle"):
        raise ValueError(f"unexpected bundle format {fmt!r} (expected mcat_perf_bundle)")
    return bundle


def _coerce_int(value: Any) -> int:
    if value is None:
        return _REVLOG_DEFAULT
    try:
        return int(value)
    except (TypeError, ValueError):
        return _REVLOG_DEFAULT


def _revlog_tuple(row: dict[str, Any]) -> tuple[int, ...]:
    return tuple(_coerce_int(row.get(col)) for col in REVLOG_COLUMNS)


def _derive_crt(revlog_rows: list[tuple[int, ...]]) -> int:
    """Best-effort collection creation time (seconds) = UTC midnight of the
    earliest review. FSRS buckets reviews into days relative to ``crt``; the
    exact value only matters for stored-state replay (see fallback in header)."""
    if not revlog_rows:
        return 0
    earliest_ms = min(r[0] for r in revlog_rows)  # revlog.id is epoch-ms
    earliest_s = earliest_ms // 1000
    return earliest_s - (earliest_s % 86400)


def write_revlog_sqlite(bundle: dict[str, Any], out_path: Path) -> dict[str, Any]:
    """Emit a minimal collection.anki2-shaped sqlite from a bundle. Returns a
    small summary dict (participant + row counts)."""
    raw_revlog = bundle.get("memory_revlog")
    if raw_revlog is None:
        raw_revlog = []
        missing_memory = True
    else:
        missing_memory = False
    if not isinstance(raw_revlog, list):
        raise ValueError("memory_revlog must be a JSON array of review rows")

    rows = [_revlog_tuple(r) for r in raw_revlog]
    cids = sorted({r[1] for r in rows})
    crt = _derive_crt(rows)
    participant = bundle.get("participant")

    if out_path.exists():
        out_path.unlink()

    conn = sqlite3.connect(str(out_path))
    try:
        conn.executescript(_SCHEMA)
        # Single default col row (empty JSON blobs, like a fresh Anki collection).
        conn.execute(
            "INSERT INTO col "
            "(id, crt, mod, scm, ver, dty, usn, ls, conf, models, decks, dconf, tags) "
            "VALUES (1, ?, 0, 0, 11, 0, 0, 0, '{}', '{}', '{}', '{}', '{}')",
            (crt,),
        )
        # Stub one card per distinct cid so JOINs on cards.id resolve. Neutral
        # defaults; empty data (no stored FSRS memory state — by design).
        conn.executemany(
            "INSERT INTO cards "
            "(id, nid, did, ord, mod, usn, type, queue, due, ivl, factor, reps, "
            " lapses, left, odue, odid, flags, data) "
            "VALUES (?, ?, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, '')",
            [(cid, cid) for cid in cids],
        )
        conn.executemany(
            "INSERT OR REPLACE INTO revlog "
            "(id, cid, usn, ease, ivl, lastIvl, factor, time, type) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            rows,
        )
        conn.commit()
    finally:
        conn.close()

    return {
        "participant": participant,
        "revlog_rows": len(rows),
        "cards": len(cids),
        "crt": crt,
        "missing_memory_revlog": missing_memory,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--bundle", required=True, help="path to an 'Export my data' perf bundle (JSON)"
    )
    ap.add_argument(
        "--out",
        required=True,
        help="output sqlite path (feed to eval_memory.py --collection)",
    )
    args = ap.parse_args()

    bundle_path = Path(args.bundle)
    if not bundle_path.exists():
        print(f"bundle not found: {bundle_path}", file=sys.stderr)
        return 2

    bundle = _load_bundle(bundle_path)
    summary = write_revlog_sqlite(bundle, Path(args.out))

    who = summary["participant"] or "(no participant label in bundle!)"
    print(f"participant: {who}")
    print(
        f"wrote {summary['revlog_rows']} revlog rows "
        f"({summary['cards']} distinct cards, crt={summary['crt']}) -> {args.out}"
    )
    if summary["missing_memory_revlog"]:
        print(
            "WARNING: bundle has no 'memory_revlog' key (predates memory export). "
            "Emitted an empty revlog table. Ask the tester to re-export with the "
            "updated build, or to send their full collection.anki2 instead "
            "(harness reads it directly via --collection). See docs/TESTER-HANDOFF.md.",
            file=sys.stderr,
        )
    if summary["revlog_rows"] == 0 and not summary["missing_memory_revlog"]:
        print(
            "WARNING: memory_revlog is empty (tester did no card reviews). "
            "Calibration needs a meaningful number of reviews.",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
