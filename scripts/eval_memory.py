#!/usr/bin/env py -3.12
"""Memory-model CALIBRATION harness for MCAT Speedrun (Sunday deliverable).

Question answered
-----------------
Is the FSRS memory model **calibrated**? i.e. when the model says a due card has
predicted retrievability R (probability of recall), do cards with that R actually
get recalled ~R of the time on held-out reviews?

What it does
------------
1. Reads the ``revlog`` table from an Anki ``collection.anki2`` (SQLite).
2. Sorts every review chronologically and does a **time-split**: the first
   ``--train-ratio`` (default 0.7) of reviews are TRAIN context; the last ~0.3 are
   the held-out TEST reviews that we actually score.
3. For every TEST review it computes:
     * PREDICTED R  = FSRS power-forgetting curve  R = (1 + FACTOR·t/S)^(-decay)
       evaluated at the days elapsed ``t`` since that card's previous review,
       using stability ``S`` reconstructed by replaying the card's own prior
       review history through the FSRS-6 update equations.
     * OBSERVED recall = 1 if the button pressed was NOT "Again" (ease >= 2),
       else 0. (Manual reschedules / set-due-date and filtered-deck "cram" rows
       are excluded — see ``has_rating_and_affects_scheduling`` in the fork.)
4. Reports **Brier score** and **log-loss** over the test reviews and writes a
   **reliability diagram** PNG (~10 equal-width bins of predicted R vs empirical
   recall, with the y=x diagonal and per-bin counts). A per-bin CSV and a JSON
   summary are always written too.

Predicted-R source (in priority order, printed loudly at runtime)
-----------------------------------------------------------------
  1. ``--params`` CLI override (comma-separated 21 FSRS-6 weights), else
  2. the collection's own trained ``fsrs_params_6`` read from the ``deck_config``
     table (best-effort protobuf scan; the Default preset / most-common set), else
  3. the FSRS-6 DEFAULT_PARAMETERS shipped with the fork's ``fsrs`` crate
     (fsrs-rs 5.2.0). If defaults are used on a real collection the numbers reflect
     *default*-weight calibration, not the user's optimised weights — stated below.

If the ``fsrs`` (py-fsrs) package is importable it is *not* required: this script
contains a faithful pure-Python port of the fork's FSRS-6 equations
(see anki-MCAT/rslib .../fsrs and fsrs-rs 5.2.0 model.rs). Matplotlib/numpy are
optional; without matplotlib a self-contained pure-stdlib PNG renderer is used, so
a chart is produced regardless of the environment.

Honesty / limitations (n=1 builder-as-subject)
----------------------------------------------
* Builder-as-subject means small n; if the held-out set is thin the diagram is
  noisy. We print a give-up warning when total graded reviews < 200
  (data/scoring-config.json). Report small n honestly.
* ``delta_t`` is day-granular using a rollover-hour cutoff (``--day-cutoff-hour``,
  default 4, UTC). Anki's true rollover is local-time; the mismatch shifts at most
  a minority of reviews by +/-1 day. Documented approximation.
* Calibration uses ONE global parameter set (override / Default preset / defaults),
  not per-deck presets. For a single-preset collection this is exact.

Usage
-----
    py -3.12 scripts/eval_memory.py --collection /path/to/collection.anki2
    py -3.12 scripts/eval_memory.py --synthetic      # provable end-to-end, no real data

Exit 0 on success.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import random
import shutil
import sqlite3
import struct
import sys
import tempfile
import zlib
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "docs" / "artifacts" / "memory-calibration.png"
SCORING_CONFIG = ROOT / "data" / "scoring-config.json"

# ---------------------------------------------------------------------------
# FSRS-6 model (pure-Python port of fsrs-rs 5.2.0 model.rs, the crate the
# anki-MCAT fork depends on). Verified against that crate's unit tests.
# ---------------------------------------------------------------------------

# fsrs-rs 5.2.0  DEFAULT_PARAMETERS (FSRS-6, 21 weights). w[20] is the decay.
DEFAULT_PARAMETERS = [
    0.212, 1.2931, 2.3065, 8.2956, 6.4133, 0.8334, 3.0194, 0.001,
    1.8722, 0.1666, 0.796, 1.4835, 0.0614, 0.2629, 1.6483, 0.6014,
    1.8729, 0.5425, 0.0912, 0.0658, 0.1542,
]
FSRS5_DEFAULT_DECAY = 0.5
FSRS6_DEFAULT_DECAY = 0.1542

S_MIN, S_MAX = 0.001, 36500.0
D_MIN, D_MAX = 1.0, 10.0


def _clamp(x: float, lo: float, hi: float) -> float:
    return lo if x < lo else hi if x > hi else x


@dataclass
class MemoryState:
    stability: float
    difficulty: float


class FSRS6:
    """Faithful FSRS-6 forward model (recall probability + state updates)."""

    def __init__(self, params: list[float] | None = None):
        w = list(params) if params else list(DEFAULT_PARAMETERS)
        w = self._check_and_fill(w)
        self.w = w
        # decay stored positive (== w[20]); the curve exponent is -decay.
        self.decay = w[20]
        self.factor = 0.9 ** (-1.0 / self.decay) - 1.0

    @staticmethod
    def _check_and_fill(w: list[float]) -> list[float]:
        n = len(w)
        if n == 21:
            return w
        if n == 19:
            return w + [0.0, FSRS5_DEFAULT_DECAY]
        if n == 17:
            w = list(w)
            w[4] = w[5] * 2.0 + w[4]
            w[5] = math.log(w[5] * 3.0 + 1.0) / 3.0
            w[6] = w[6] + 0.5
            return w + [0.0, 0.0, 0.0, FSRS5_DEFAULT_DECAY]
        if n == 0:
            return list(DEFAULT_PARAMETERS)
        raise ValueError(f"unsupported FSRS parameter length: {n}")

    # R = (1 + FACTOR * t/S) ^ (-decay)
    def retrievability(self, delta_t_days: float, stability: float) -> float:
        s = _clamp(stability, S_MIN, S_MAX)
        return (delta_t_days / s * self.factor + 1.0) ** (-self.decay)

    def next_interval(self, stability: float, desired_retention: float) -> float:
        # inverse of the forgetting curve; days at which R == desired_retention
        return stability / self.factor * (desired_retention ** (-1.0 / self.decay) - 1.0)

    def init_stability(self, rating: int) -> float:
        return self.w[rating - 1]

    def init_difficulty(self, rating: int) -> float:
        return self.w[4] - math.exp(self.w[5] * (rating - 1)) + 1.0

    def _next_difficulty(self, d: float, rating: int) -> float:
        delta_d = -self.w[6] * (rating - 3)
        damped = (10.0 - d) * delta_d / 9.0
        new_d = d + damped
        # mean reversion toward the init difficulty of an "Easy" (rating 4) card
        return self.w[7] * (self.init_difficulty(4) - new_d) + new_d

    def _s_success(self, s: float, d: float, r: float, rating: int) -> float:
        hard_penalty = self.w[15] if rating == 2 else 1.0
        easy_bonus = self.w[16] if rating == 4 else 1.0
        return s * (
            math.exp(self.w[8])
            * (11.0 - d)
            * (s ** (-self.w[9]))
            * (math.expm1((1.0 - r) * self.w[10]))
            * hard_penalty
            * easy_bonus
            + 1.0
        )

    def _s_failure(self, s: float, d: float, r: float) -> float:
        new_s = (
            self.w[11]
            * (d ** (-self.w[12]))
            * ((s + 1.0) ** self.w[13] - 1.0)
            * math.exp((1.0 - r) * self.w[14])
        )
        new_s_min = s / math.exp(self.w[17] * self.w[18])
        return min(new_s, new_s_min)

    def _s_short_term(self, s: float, rating: int) -> float:
        sinc = math.exp(self.w[17] * (rating - 3 + self.w[18])) * (s ** (-self.w[19]))
        if rating >= 3:
            sinc = max(sinc, 1.0)
        return s * sinc

    def step(self, delta_t_days: float, rating: int, state: MemoryState | None) -> MemoryState:
        """Advance memory state by one review. ``state`` None == brand-new card."""
        if state is None:
            new_s = self.init_stability(_clamp(rating, 1, 4))
            new_d = _clamp(self.init_difficulty(_clamp(rating, 1, 4)), D_MIN, D_MAX)
            return MemoryState(_clamp(new_s, S_MIN, S_MAX), new_d)

        last_s = _clamp(state.stability, S_MIN, S_MAX)
        last_d = _clamp(state.difficulty, D_MIN, D_MAX)
        r = self.retrievability(delta_t_days, last_s)

        if delta_t_days == 0:
            new_s = self._s_short_term(last_s, rating)
        elif rating == 1:
            new_s = self._s_failure(last_s, last_d, r)
        else:
            new_s = self._s_success(last_s, last_d, r, rating)

        new_d = _clamp(self._next_difficulty(last_d, rating), D_MIN, D_MAX)
        return MemoryState(_clamp(new_s, S_MIN, S_MAX), new_d)

    def memory_state_from_sm2(self, ease_factor: float, interval: float, sm2_retention: float) -> MemoryState:
        stability = max(interval, S_MIN) * self.factor / (sm2_retention ** (-1.0 / self.decay) - 1.0)
        difficulty = 11.0 - (ease_factor - 1.0) / (
            math.exp(self.w[8]) * (stability ** (-self.w[9])) * math.expm1((1.0 - sm2_retention) * self.w[10])
        )
        return MemoryState(_clamp(stability, S_MIN, S_MAX), _clamp(difficulty, D_MIN, D_MAX))


# ---------------------------------------------------------------------------
# Revlog reading + FSRS item reconstruction
# ---------------------------------------------------------------------------

# Anki revlog.type values
KIND_LEARNING = 0
KIND_REVIEW = 1
KIND_RELEARNING = 2
KIND_FILTERED = 3   # "cram" when factor==0
KIND_MANUAL = 4     # reschedule / set-due / reset when factor==0
KIND_RESCHEDULED = 5


@dataclass
class Rev:
    id: int          # epoch-ms
    cid: int
    ease: int        # button 1..4 (0 == manual/reschedule)
    ivl: int
    last_ivl: int
    type: int
    factor: int


@dataclass
class Scored:
    time: int        # review id (epoch-ms)
    cid: int
    pred: float      # predicted retrievability R in (0,1)
    y: int           # observed recall (1 == not Again)


def _is_cramming(r: Rev) -> bool:
    return r.type == KIND_FILTERED and r.factor == 0


def _is_reset(r: Rev) -> bool:
    return r.type == KIND_MANUAL and r.factor == 0


def _affects_scheduling(r: Rev) -> bool:
    # not manual/reschedule (button 0) and not cram
    return r.ease > 0 and not _is_cramming(r)


def read_revlog(path: Path) -> list[Rev]:
    """Read the revlog table read-only (handles a live/locked collection)."""
    uri = f"file:{path.as_posix()}?mode=ro&immutable=1"
    try:
        con = sqlite3.connect(uri, uri=True)
    except sqlite3.OperationalError:
        tmp = Path(tempfile.mkdtemp(prefix="mcat-col-")) / "collection.anki2"
        shutil.copy2(path, tmp)
        con = sqlite3.connect(f"file:{tmp.as_posix()}?mode=ro", uri=True)
    try:
        cur = con.execute(
            "SELECT id, cid, ease, ivl, lastIvl, type, factor FROM revlog ORDER BY id ASC"
        )
        return [Rev(*row) for row in cur.fetchall()]
    finally:
        con.close()


def read_collection_params(path: Path) -> tuple[list[float] | None, str]:
    """Best-effort read of the collection's trained fsrs_params_6 (else 5/4).

    Scans each deck_config row's protobuf ``config`` blob for the FSRS param
    fields (6 -> fsrs_params_6, 5 -> fsrs_params_5, 3 -> fsrs_params_4), all
    packed repeated floats. Returns (params or None, human description).
    """
    uri = f"file:{path.as_posix()}?mode=ro&immutable=1"
    try:
        con = sqlite3.connect(uri, uri=True)
    except sqlite3.OperationalError:
        return None, "deck_config unreadable"
    try:
        try:
            rows = con.execute("SELECT id, config FROM deck_config").fetchall()
        except sqlite3.OperationalError:
            return None, "no deck_config table"
    finally:
        con.close()

    best: dict[int, tuple[int, list[float]]] = {}  # config_id -> (field_no, params)
    for cid, blob in rows:
        if not blob:
            continue
        found = _scan_fsrs_params(bytes(blob))
        if found:
            best[cid] = found
    if not best:
        return None, "no fsrs params stored in deck_config"

    # Prefer the Default preset (id == 1); else the most common param set.
    if 1 in best:
        field_no, params = best[1]
        which = "Default preset (id=1)"
    else:
        # pick the longest / most common
        cid = max(best, key=lambda k: len(best[k][1]))
        field_no, params = best[cid]
        which = f"preset id={cid}"
    ver = {6: "fsrs_params_6", 5: "fsrs_params_5", 3: "fsrs_params_4"}.get(field_no, "?")
    n_presets = len(best)
    suffix = f" ({n_presets} presets with params; used {which})" if n_presets > 1 else f" ({which})"
    return params, ver + suffix


def _scan_fsrs_params(buf: bytes) -> tuple[int, list[float]] | None:
    """Walk a protobuf message; return (field_no, floats) for FSRS params.

    Looks for packed repeated-float fields 6, 5, 3 (in that preference order).
    """
    candidates: dict[int, list[float]] = {}
    i, n = 0, len(buf)

    def read_varint(pos: int) -> tuple[int, int]:
        shift = 0
        val = 0
        while pos < n:
            b = buf[pos]
            val |= (b & 0x7F) << shift
            pos += 1
            if not (b & 0x80):
                return val, pos
            shift += 7
        raise ValueError("truncated varint")

    try:
        while i < n:
            tag, i = read_varint(i)
            field_no = tag >> 3
            wire = tag & 7
            if wire == 0:      # varint
                _, i = read_varint(i)
            elif wire == 1:    # 64-bit
                i += 8
            elif wire == 2:    # length-delimited
                length, i = read_varint(i)
                chunk = buf[i:i + length]
                i += length
                if field_no in (3, 5, 6) and length % 4 == 0 and length >= 4:
                    floats = list(struct.unpack("<%df" % (length // 4), chunk))
                    # FSRS params are small positive-ish weights; sanity check.
                    if all(math.isfinite(f) for f in floats) and len(floats) in (17, 19, 21):
                        candidates[field_no] = floats
            elif wire == 5:    # 32-bit
                i += 4
            else:
                return None
    except (ValueError, struct.error):
        pass

    for pref in (6, 5, 3):
        if pref in candidates:
            return pref, candidates[pref]
    return None


def day_number(secs: float, next_day_at_secs: float) -> int:
    """Days-elapsed count matching the fork's RevlogEntry::days_elapsed."""
    return max(0, int((next_day_at_secs - secs) // 86400))


def reconstruct_card(entries: list[Rev], fsrs: FSRS6, next_day_at_secs: float,
                     historical_retention: float) -> list[Scored]:
    """Replay one card's history; return the scoreable (pred, y) per review.

    Mirrors reviews_for_fsrs + fsrs_item_for_memory_state in the fork: trims to
    the start of the last learning group, drops cram/manual rows, computes
    day-granular delta_t, and only scores reviews with index>=1 and delta_t>0
    (same rule the trainer uses to emit FSRS items).
    """
    entries = sorted(entries, key=lambda r: r.id)

    # --- locate start of last learning group (backward scan) ---
    first_learn = None
    first_grade = None
    for idx in range(len(entries) - 1, -1, -1):
        e = entries[idx]
        if _is_cramming(e):
            continue
        user_graded = e.ease > 0
        interday = e.ivl >= 1 or e.ivl <= -86400
        if user_graded and interday:
            first_grade = idx
        if user_graded and e.type == KIND_LEARNING:
            first_learn = idx
        elif _is_reset(e):
            if first_learn is not None or first_grade is not None:
                break
            return []
        elif first_learn is not None:
            break

    truncated = False
    if first_learn is not None:
        entries = entries[first_learn:]
    elif first_grade is not None:
        entries = entries[first_grade:]
        truncated = True
    else:
        return []

    filtered = [e for e in filter(_affects_scheduling, entries)]
    if len(filtered) < 2:
        return []

    days = [day_number(e.id / 1000.0, next_day_at_secs) for e in filtered]
    delta = [0] + [days[i - 1] - days[i] for i in range(1, len(filtered))]

    scored: list[Scored] = []
    if truncated:
        e0 = filtered[0]
        ef = (e0.factor if e0.factor else 2500) / 1000.0
        state = fsrs.memory_state_from_sm2(ef, max(1, e0.ivl), historical_retention)
        if ef <= 1.1:  # revlog entry generated by FSRS: recover difficulty directly
            state.difficulty = _clamp((ef - 0.1) * 9.0 + 1.0, D_MIN, D_MAX)
        start = 1
    else:
        state = fsrs.step(0, filtered[0].ease, None)  # init from first learning grade
        start = 1

    for i in range(start, len(filtered)):
        e = filtered[i]
        dt = delta[i]
        if dt > 0:
            r = fsrs.retrievability(dt, state.stability)
            scored.append(Scored(time=e.id, cid=e.cid, pred=r, y=1 if e.ease >= 2 else 0))
        state = fsrs.step(dt, e.ease, state)
    return scored


def build_scored(revs: list[Rev], fsrs: FSRS6, day_cutoff_hour: int,
                 historical_retention: float) -> tuple[list[Scored], float]:
    """Return all scoreable reviews (across all cards) and next_day_at_secs."""
    if not revs:
        return [], 0.0
    max_secs = max(r.id for r in revs) / 1000.0
    cutoff = day_cutoff_hour * 3600
    # smallest rollover boundary strictly after the last review
    k = math.floor((max_secs - cutoff) / 86400) + 1
    next_day_at_secs = k * 86400 + cutoff

    by_card: dict[int, list[Rev]] = {}
    for r in revs:
        by_card.setdefault(r.cid, []).append(r)

    scored: list[Scored] = []
    for entries in by_card.values():
        scored.extend(reconstruct_card(entries, fsrs, next_day_at_secs, historical_retention))
    scored.sort(key=lambda s: s.time)
    return scored, next_day_at_secs


# ---------------------------------------------------------------------------
# Metrics + binning
# ---------------------------------------------------------------------------

LOGLOSS_EPS = 1e-6


def brier_score(rows: list[Scored]) -> float:
    return sum((s.pred - s.y) ** 2 for s in rows) / len(rows)


def log_loss(rows: list[Scored]) -> float:
    total = 0.0
    for s in rows:
        p = _clamp(s.pred, LOGLOSS_EPS, 1.0 - LOGLOSS_EPS)
        total += -(s.y * math.log(p) + (1 - s.y) * math.log(1.0 - p))
    return total / len(rows)


@dataclass
class Bin:
    lo: float
    hi: float
    n: int
    mean_pred: float
    obs_recall: float


def reliability_bins(rows: list[Scored], n_bins: int) -> list[Bin]:
    buckets: list[list[Scored]] = [[] for _ in range(n_bins)]
    for s in rows:
        idx = min(n_bins - 1, int(s.pred * n_bins))
        buckets[idx].append(s)
    bins: list[Bin] = []
    for i, b in enumerate(buckets):
        lo, hi = i / n_bins, (i + 1) / n_bins
        if b:
            mean_pred = sum(x.pred for x in b) / len(b)
            obs = sum(x.y for x in b) / len(b)
        else:
            mean_pred = float("nan")
            obs = float("nan")
        bins.append(Bin(lo, hi, len(b), mean_pred, obs))
    return bins


def expected_calibration_error(bins: list[Bin], n_total: int) -> float:
    ece = 0.0
    for b in bins:
        if b.n:
            ece += (b.n / n_total) * abs(b.mean_pred - b.obs_recall)
    return ece


# ---------------------------------------------------------------------------
# Synthetic revlog generator (known, mild miscalibration)
# ---------------------------------------------------------------------------

def generate_synthetic_revlog(n_cards: int, days_span: int, gamma: float,
                              seed: int) -> list[Rev]:
    """Simulate FSRS-consistent review histories whose TRUE recall probability is
    a mild miscalibration of the model's predicted R: p_true = R_model ** gamma.

    gamma > 1  => the model is OVER-confident (observed recall < predicted), so
    the reliability curve bows BELOW the y=x diagonal. This is a *known* ground
    truth used to prove the whole pipeline end-to-end without real data.
    """
    rng = random.Random(seed)
    fsrs = FSRS6(DEFAULT_PARAMETERS)
    base_secs = 1_600_000_000  # ~2020-09, safely in the past
    rows: list[Rev] = []
    uid = 0

    for c in range(n_cards):
        cid = 1_000_000 + c
        start_day = rng.randint(0, max(1, days_span // 3))
        # Different decks/cards target different retention, and users review late.
        # Both spread predicted R across the bins (not just the ~0.9 cluster).
        desired_retention = rng.uniform(0.75, 0.95)

        # first learning grade (mostly Good, some Easy/Hard)
        rating = rng.choices([2, 3, 4], weights=[10, 70, 20])[0]
        state = fsrs.step(0, rating, None)
        uid += 1
        secs = base_secs + start_day * 86400 + rng.randint(0, 80000)
        ivl = max(1, round(fsrs.next_interval(state.stability, desired_retention)))
        rows.append(Rev(id=secs * 1000 + (uid % 1000), cid=cid, ease=rating,
                        ivl=ivl, last_ivl=0, type=KIND_LEARNING,
                        factor=round(state.difficulty * 1000)))
        prev_day = start_day
        prev_ivl = ivl
        prev_fail = False

        while True:
            # ~25% of reviews happen "late" (overdue) -> lower R, fills mid/low bins.
            if rng.random() < 0.25:
                mult = rng.uniform(1.4, 3.2)
            else:
                mult = rng.uniform(0.85, 1.15)
            gap = max(1, round(prev_ivl * mult))
            day = prev_day + gap
            if day > days_span:
                break
            dt = day - prev_day
            r_model = fsrs.retrievability(dt, state.stability)
            p_true = r_model ** gamma
            success = rng.random() < p_true
            if success:
                rating = rng.choices([2, 3, 4], weights=[15, 70, 15])[0]
                kind = KIND_RELEARNING if prev_fail else KIND_REVIEW
                prev_fail = False
            else:
                rating = 1
                kind = KIND_REVIEW
                prev_fail = True

            state = fsrs.step(dt, rating, state)
            if rating >= 2:
                new_ivl = max(1, round(fsrs.next_interval(state.stability, desired_retention)))
            else:
                new_ivl = 1  # relearn shortly
            uid += 1
            secs = base_secs + day * 86400 + rng.randint(0, 80000)
            rows.append(Rev(id=secs * 1000 + (uid % 1000), cid=cid, ease=rating,
                            ivl=new_ivl, last_ivl=prev_ivl, type=kind,
                            factor=round(state.difficulty * 1000)))
            prev_day = day
            prev_ivl = new_ivl

    rows.sort(key=lambda r: r.id)
    return rows


def write_synthetic_db(rows: list[Rev], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()
    con = sqlite3.connect(str(path))
    try:
        con.execute(
            "CREATE TABLE revlog (id INTEGER PRIMARY KEY, cid INTEGER NOT NULL, "
            "usn INTEGER NOT NULL DEFAULT 0, ease INTEGER NOT NULL, ivl INTEGER NOT NULL, "
            "lastIvl INTEGER NOT NULL, factor INTEGER NOT NULL, time INTEGER NOT NULL DEFAULT 0, "
            "type INTEGER NOT NULL DEFAULT 0)"
        )
        con.executemany(
            "INSERT INTO revlog (id, cid, ease, ivl, lastIvl, factor, type) "
            "VALUES (?,?,?,?,?,?,?)",
            [(r.id, r.cid, r.ease, r.ivl, r.last_ivl, r.factor, r.type) for r in rows],
        )
        con.commit()
    finally:
        con.close()


# ---------------------------------------------------------------------------
# Reliability-diagram PNG (matplotlib if present, else pure-stdlib renderer)
# ---------------------------------------------------------------------------

def write_png_matplotlib(out: Path, bins: list[Bin], brier: float, logloss: float,
                         n_test: int, source: str) -> bool:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        return False

    line_min = max(1, round(0.01 * n_test))  # ignore tiny, noisy bins in the trend line
    pts = [b for b in bins if b.n]
    solid = [b for b in bins if b.n >= line_min]
    fig, ax = plt.subplots(figsize=(6, 6), dpi=110)
    ax.plot([0, 1], [0, 1], "--", color="#888", label="perfect calibration")
    if solid:
        ax.plot([b.mean_pred for b in solid], [b.obs_recall for b in solid], "-",
                color="#1f77b4", label=f"observed (bins n>={line_min})")
    ax.scatter([b.mean_pred for b in pts], [b.obs_recall for b in pts],
               s=[20 + 120 * math.sqrt(b.n / max(x.n for x in pts)) for b in pts],
               color="#1f77b4", alpha=0.8, zorder=3)
    for b in pts:
        ax.annotate(str(b.n), (b.mean_pred, b.obs_recall), textcoords="offset points",
                    xytext=(5, 4), fontsize=7)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_xlabel("predicted retrievability R (binned mean)")
    ax.set_ylabel("observed recall (empirical)")
    ax.set_title(f"FSRS memory calibration\nBrier={brier:.4f}  log-loss={logloss:.4f}  n={n_test}")
    ax.legend(loc="upper left", fontsize=8)
    ax.text(0.98, 0.02, source, ha="right", va="bottom", fontsize=6, color="#666",
            transform=ax.transAxes)
    ax.grid(True, color="#eee")
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(out)
    plt.close(fig)
    return True


# --- tiny 5x7 bitmap font for the pure-stdlib fallback renderer ---
_FONT: dict[str, list[str]] = {
    " ": ["....."] * 7,
    "0": [".###.", "#...#", "#..##", "#.#.#", "##..#", "#...#", ".###."],
    "1": ["..#..", ".##..", "..#..", "..#..", "..#..", "..#..", ".###."],
    "2": [".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####"],
    "3": ["#####", "...#.", "..#..", "...#.", "....#", "#...#", ".###."],
    "4": ["...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."],
    "5": ["#####", "#....", "####.", "....#", "....#", "#...#", ".###."],
    "6": ["..##.", ".#...", "#....", "####.", "#...#", "#...#", ".###."],
    "7": ["#####", "....#", "...#.", "..#..", ".#...", ".#...", ".#..."],
    "8": [".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."],
    "9": [".###.", "#...#", "#...#", ".####", "....#", "...#.", ".##.."],
    ".": [".....", ".....", ".....", ".....", ".....", ".##..", ".##.."],
    "-": [".....", ".....", ".....", "#####", ".....", ".....", "....."],
    "=": [".....", ".....", "#####", ".....", "#####", ".....", "....."],
    ":": [".....", ".##..", ".##..", ".....", ".##..", ".##..", "....."],
    "%": ["##..#", "##..#", "...#.", "..#..", ".#...", "#..##", "#..##"],
    "(": ["..#..", ".#...", "#....", "#....", "#....", ".#...", "..#.."],
    ")": ["..#..", "...#.", "....#", "....#", "....#", "...#.", "..#.."],
    "_": [".....", ".....", ".....", ".....", ".....", ".....", "#####"],
    "/": ["....#", "....#", "...#.", "..#..", ".#...", "#....", "#...."],
    ",": [".....", ".....", ".....", ".....", ".....", ".##..", ".#..."],
    "a": [".....", ".....", ".###.", "....#", ".####", "#...#", ".####"],
    "b": ["#....", "#....", "####.", "#...#", "#...#", "#...#", "####."],
    "c": [".....", ".....", ".####", "#....", "#....", "#....", ".####"],
    "d": ["....#", "....#", ".####", "#...#", "#...#", "#...#", ".####"],
    "e": [".....", ".....", ".###.", "#...#", "#####", "#....", ".####"],
    "f": ["..##.", ".#..#", ".#...", "###..", ".#...", ".#...", ".#..."],
    "g": [".....", ".####", "#...#", "#...#", ".####", "....#", ".###."],
    "h": ["#....", "#....", "####.", "#...#", "#...#", "#...#", "#...#"],
    "i": ["..#..", ".....", ".##..", "..#..", "..#..", "..#..", ".###."],
    "k": ["#....", "#....", "#..#.", "#.#..", "##...", "#.#..", "#..#."],
    "l": [".##..", "..#..", "..#..", "..#..", "..#..", "..#..", ".###."],
    "m": [".....", ".....", "##.#.", "#.#.#", "#.#.#", "#...#", "#...#"],
    "n": [".....", ".....", "####.", "#...#", "#...#", "#...#", "#...#"],
    "o": [".....", ".....", ".###.", "#...#", "#...#", "#...#", ".###."],
    "p": [".....", ".....", "####.", "#...#", "####.", "#....", "#...."],
    "r": [".....", ".....", "#.##.", "##..#", "#....", "#....", "#...."],
    "s": [".....", ".....", ".####", "#....", ".###.", "....#", "####."],
    "t": [".#...", ".#...", "###..", ".#...", ".#...", ".#..#", "..##."],
    "u": [".....", ".....", "#...#", "#...#", "#...#", "#..##", ".##.#"],
    "v": [".....", ".....", "#...#", "#...#", "#...#", ".#.#.", "..#.."],
    "w": [".....", ".....", "#...#", "#...#", "#.#.#", "#.#.#", ".#.#."],
    "x": [".....", ".....", "#...#", ".#.#.", "..#..", ".#.#.", "#...#"],
    "y": [".....", "#...#", "#...#", "#...#", ".####", "....#", ".###."],
    "B": ["####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."],
    "F": ["#####", "#....", "#....", "####.", "#....", "#....", "#...."],
    "M": ["#...#", "##.##", "#.#.#", "#.#.#", "#...#", "#...#", "#...#"],
    "R": ["####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"],
    "S": [".####", "#....", "#....", ".###.", "....#", "....#", "####."],
}


class _Canvas:
    def __init__(self, w: int, h: int, bg=(255, 255, 255)):
        self.w, self.h = w, h
        self.buf = bytearray(bg * (w * h))

    def px(self, x: int, y: int, rgb):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.buf[i:i + 3] = bytes(rgb)

    def rect(self, x0, y0, x1, y1, rgb):
        for y in range(min(y0, y1), max(y0, y1) + 1):
            for x in range(min(x0, x1), max(x0, x1) + 1):
                self.px(x, y, rgb)

    def line(self, x0, y0, x1, y1, rgb, dashed=False):
        x0, y0, x1, y1 = int(x0), int(y0), int(x1), int(y1)
        dx, dy = abs(x1 - x0), -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        step = 0
        while True:
            if not dashed or (step // 4) % 2 == 0:
                self.px(x0, y0, rgb)
            step += 1
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def disk(self, cx, cy, rad, rgb):
        for y in range(-rad, rad + 1):
            for x in range(-rad, rad + 1):
                if x * x + y * y <= rad * rad:
                    self.px(cx + x, cy + y, rgb)

    def text(self, x, y, s, rgb, scale=1):
        cx = x
        for ch in s:
            glyph = _FONT.get(ch, _FONT.get(ch.lower(), _FONT[" "]))
            for gy, row in enumerate(glyph):
                for gx, c in enumerate(row):
                    if c == "#":
                        for sy in range(scale):
                            for sx in range(scale):
                                self.px(cx + gx * scale + sx, y + gy * scale + sy, rgb)
            cx += (5 + 1) * scale

    def png(self) -> bytes:
        def chunk(typ: bytes, data: bytes) -> bytes:
            body = typ + data
            return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xffffffff)
        sig = b"\x89PNG\r\n\x1a\n"
        ihdr = struct.pack(">IIBBBBB", self.w, self.h, 8, 2, 0, 0, 0)
        stride = self.w * 3
        raw = bytearray()
        for y in range(self.h):
            raw.append(0)
            raw.extend(self.buf[y * stride:(y + 1) * stride])
        idat = zlib.compress(bytes(raw), 9)
        return sig + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")


def write_png_fallback(out: Path, bins: list[Bin], brier: float, logloss: float,
                       n_test: int, source: str) -> None:
    W, H = 620, 560
    L, T = 90, 60           # plot origin (top-left of plot box)
    PW, PH = 460, 400       # plot width/height
    B = T + PH              # bottom pixel row of plot
    R = L + PW
    cv = _Canvas(W, H)
    ink = (30, 30, 30)
    grey = (170, 170, 170)
    light = (225, 225, 225)
    blue = (31, 119, 180)

    def X(v):  # data x in [0,1] -> pixel
        return int(L + v * PW)

    def Y(v):  # data y in [0,1] -> pixel
        return int(B - v * PH)

    # grid + ticks
    for t in range(5):
        v = t / 4.0
        cv.line(X(v), T, X(v), B, light)
        cv.line(L, Y(v), R, Y(v), light)
        cv.text(X(v) - 8, B + 8, f"{v:.2f}", ink, 1)
        cv.text(L - 34, Y(v) - 3, f"{v:.2f}", ink, 1)
    # axes box
    cv.rect(L, T, R, T, grey)
    cv.rect(L, B, R, B, grey)
    cv.rect(L, T, L, B, grey)
    cv.rect(R, T, R, B, grey)
    # diagonal (perfect calibration)
    cv.line(X(0), Y(0), X(1), Y(1), grey, dashed=True)

    # observed curve + points sized by count. Connect only substantial bins so
    # tiny, noisy bins (n=1..a few) don't dominate the trend line.
    pts = [b for b in bins if b.n]
    line_min = max(1, round(0.01 * n_test))
    solid = [b for b in bins if b.n >= line_min]
    max_n = max((b.n for b in pts), default=1)
    prev = None
    for b in solid:
        cx, cy = X(b.mean_pred), Y(b.obs_recall)
        if prev is not None:
            cv.line(prev[0], prev[1], cx, cy, blue)
        prev = (cx, cy)
    for b in pts:
        cx, cy = X(b.mean_pred), Y(b.obs_recall)
        rad = 2 + int(6 * math.sqrt(b.n / max_n))
        cv.disk(cx, cy, rad, blue)
        cv.text(cx + rad + 1, cy - 3, str(b.n), ink, 1)

    # titles
    cv.text(L, 16, "FSRS memory calibration", ink, 2)
    cv.text(L, 40, f"Brier={brier:.4f}  logloss={logloss:.4f}  n={n_test}", ink, 1)
    cv.text(L, B + 30, "predicted retrievability R", ink, 1)
    # y caption (drawn horizontally near top-left of axis)
    cv.text(4, T - 14, "observed recall", ink, 1)
    # source string lowercased so it uses the well-covered lowercase glyph set
    cv.text(L, H - 14, ("src: " + source).lower()[:70], grey, 1)

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(cv.png())


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def default_train_ratio() -> float:
    try:
        cfg = json.loads(SCORING_CONFIG.read_text(encoding="utf-8"))
        return float(cfg["eval_splits"]["review_train_ratio"])
    except Exception:
        return 0.7


def give_up_min_reviews() -> int:
    try:
        cfg = json.loads(SCORING_CONFIG.read_text(encoding="utf-8"))
        return int(cfg["give_up"]["memory"]["min_total_reviews"])
    except Exception:
        return 200


def print_bin_table(bins: list[Bin]) -> None:
    print("\n  bin range     n     mean_pred   obs_recall   gap")
    print("  " + "-" * 52)
    for b in bins:
        if b.n:
            gap = b.obs_recall - b.mean_pred
            print(f"  [{b.lo:.1f},{b.hi:.1f})  {b.n:5d}    {b.mean_pred:8.4f}    "
                  f"{b.obs_recall:8.4f}   {gap:+.4f}")
        else:
            print(f"  [{b.lo:.1f},{b.hi:.1f})  {0:5d}    {'--':>8}    {'--':>8}   {'--':>6}")


def write_csv(path: Path, bins: list[Bin]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["bin_lo", "bin_hi", "n", "mean_pred", "obs_recall", "gap"])
        for b in bins:
            if b.n:
                w.writerow([f"{b.lo:.4f}", f"{b.hi:.4f}", b.n,
                            f"{b.mean_pred:.6f}", f"{b.obs_recall:.6f}",
                            f"{b.obs_recall - b.mean_pred:.6f}"])
            else:
                w.writerow([f"{b.lo:.4f}", f"{b.hi:.4f}", 0, "", "", ""])


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="eval_memory.py",
        description="FSRS memory-model calibration (Brier / log-loss + reliability diagram) "
                    "on a chronological 70/30 time-split of an Anki revlog.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Examples:\n"
               "  py -3.12 scripts/eval_memory.py --collection ~/Anki/User/collection.anki2\n"
               "  py -3.12 scripts/eval_memory.py --synthetic   # end-to-end demo, no real data\n",
    )
    ap.add_argument("--collection", type=Path,
                    help="path to a collection.anki2 (SQLite with a revlog table)")
    ap.add_argument("--train-ratio", type=float, default=None,
                    help="chronological train fraction (default from scoring-config.json = "
                         f"{default_train_ratio():.2f})")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT,
                    help=f"reliability diagram PNG path (default {DEFAULT_OUT.relative_to(ROOT)})")
    ap.add_argument("--bins", type=int, default=10, help="number of equal-width bins (default 10)")
    ap.add_argument("--params", type=str, default=None,
                    help="comma-separated FSRS-6 weights override (17/19/21 values)")
    ap.add_argument("--historical-retention", type=float, default=0.9,
                    help="SM2 fallback retention for truncated histories (default 0.9)")
    ap.add_argument("--day-cutoff-hour", type=int, default=4,
                    help="UTC rollover hour for day-granular delta_t (default 4)")
    ap.add_argument("--synthetic", action="store_true",
                    help="generate a synthetic revlog with a KNOWN mild miscalibration and run "
                         "the full pipeline end-to-end (no real collection needed)")
    ap.add_argument("--synthetic-cards", type=int, default=600)
    ap.add_argument("--synthetic-days", type=int, default=450)
    ap.add_argument("--synthetic-gamma", type=float, default=1.35,
                    help="miscalibration strength: true recall = R_model ** gamma "
                         "(>1 = overconfident model; default 1.35)")
    ap.add_argument("--seed", type=int, default=20260703)
    ap.add_argument("--keep-synthetic-db", type=Path, default=None,
                    help="write the synthetic collection.anki2 here instead of a temp file")
    args = ap.parse_args(argv)

    train_ratio = args.train_ratio if args.train_ratio is not None else default_train_ratio()
    if not 0.05 < train_ratio < 0.95:
        ap.error("--train-ratio must be between 0.05 and 0.95")

    # --- resolve parameter source ---
    params: list[float] | None = None
    param_source = ""
    if args.params:
        params = [float(x) for x in args.params.replace(" ", "").split(",") if x]
        param_source = f"CLI --params ({len(params)} weights)"

    # --- obtain revlog ---
    tmp_dir: Path | None = None
    if args.synthetic:
        print("=== SYNTHETIC MODE ===")
        print(f"generating {args.synthetic_cards} cards over {args.synthetic_days} days; "
              f"true recall = R_model ** {args.synthetic_gamma} (seed={args.seed})")
        rows = generate_synthetic_revlog(args.synthetic_cards, args.synthetic_days,
                                         args.synthetic_gamma, args.seed)
        if args.keep_synthetic_db:
            db_path = args.keep_synthetic_db
        else:
            tmp_dir = Path(tempfile.mkdtemp(prefix="mcat-synth-"))
            db_path = tmp_dir / "collection.anki2"
        write_synthetic_db(rows, db_path)
        print(f"wrote synthetic collection: {db_path}  ({len(rows)} revlog rows)")
        revs = read_revlog(db_path)
        if params is None:
            params = list(DEFAULT_PARAMETERS)
            param_source = ("FSRS-6 DEFAULT_PARAMETERS (synthetic dynamics use the same "
                            "weights; miscalibration is injected on outcomes)")
    else:
        if not args.collection:
            ap.error("provide --collection PATH or use --synthetic")
        if not args.collection.is_file():
            ap.error(f"collection not found: {args.collection}")
        revs = read_revlog(args.collection)
        if params is None:
            got, desc = read_collection_params(args.collection)
            if got:
                params = got
                param_source = f"collection deck_config: {desc}"
            else:
                params = list(DEFAULT_PARAMETERS)
                param_source = (f"FSRS-6 DEFAULT_PARAMETERS ({desc}) -- WARNING: not the "
                                "collection's optimised weights; calibration reflects defaults")

    fsrs = FSRS6(params)
    print(f"\nFSRS parameter source: {param_source}")
    print(f"decay w[20]={fsrs.decay:.4f}  (curve exponent -{fsrs.decay:.4f})")

    total_affecting = sum(1 for r in revs if _affects_scheduling(r))
    print(f"revlog rows: {len(revs)} total, {total_affecting} rating-affecting "
          f"(non-cram, non-manual)")

    scored, _ = build_scored(revs, fsrs, args.day_cutoff_hour, args.historical_retention)
    if not scored:
        print("\nERROR: no scoreable reviews (need cards with >=2 spaced reviews).",
              file=sys.stderr)
        return 1

    # --- chronological time-split ---
    scored.sort(key=lambda s: s.time)
    all_times = sorted(r.id for r in revs if _affects_scheduling(r))
    cut_idx = int(len(all_times) * train_ratio)
    boundary = all_times[min(cut_idx, len(all_times) - 1)]
    n_train = sum(1 for t in all_times if t < boundary)
    test = [s for s in scored if s.time >= boundary]
    n_test = len(test)

    if n_test == 0:
        print("\nERROR: time-split left 0 test reviews; lower --train-ratio.", file=sys.stderr)
        return 1

    brier = brier_score(test)
    ll = log_loss(test)
    bins = reliability_bins(test, args.bins)
    ece = expected_calibration_error(bins, n_test)
    mean_pred_all = sum(s.pred for s in test) / n_test
    mean_obs_all = sum(s.y for s in test) / n_test

    print("\n=== MEMORY CALIBRATION (held-out reviews) ===")
    print(f"train-ratio      : {train_ratio:.2f}")
    print(f"n_train (context): {n_train}")
    print(f"n_test  (scored) : {n_test}")
    print(f"Brier score      : {brier:.4f}   (lower is better; 0 = perfect)")
    print(f"log-loss         : {ll:.4f}   (lower is better)")
    print(f"ECE              : {ece:.4f}   (mean |pred-obs| across bins)")
    print(f"mean predicted R : {mean_pred_all:.4f}")
    print(f"mean observed    : {mean_obs_all:.4f}   "
          f"({'model OVER-confident' if mean_pred_all > mean_obs_all else 'model under-confident'} "
          f"by {abs(mean_pred_all - mean_obs_all):.4f})")
    print_bin_table(bins)

    give_up = give_up_min_reviews()
    if total_affecting < give_up:
        print(f"\n[HONESTY] Only {total_affecting} graded reviews (< {give_up}). "
              "Per scoring-config the memory score would be WITHHELD; treat this "
              "calibration as indicative only (small n).")

    # --- artifacts ---
    out_png = args.out
    csv_path = out_png.with_suffix(".bins.csv")
    json_path = out_png.with_suffix(".summary.json")
    write_csv(csv_path, bins)

    used_mpl = write_png_matplotlib(out_png, bins, brier, ll, n_test, param_source)
    if used_mpl:
        chart_note = f"chart (matplotlib): {out_png}"
    else:
        write_png_fallback(out_png, bins, brier, ll, n_test, param_source)
        chart_note = (f"chart (pure-stdlib PNG; matplotlib not installed): {out_png}")

    summary = {
        "mode": "synthetic" if args.synthetic else "collection",
        "param_source": param_source,
        "train_ratio": train_ratio,
        "n_train": n_train,
        "n_test": n_test,
        "n_total_affecting": total_affecting,
        "brier": brier,
        "log_loss": ll,
        "ece": ece,
        "mean_predicted": mean_pred_all,
        "mean_observed": mean_obs_all,
        "bins": [
            {"lo": b.lo, "hi": b.hi, "n": b.n,
             "mean_pred": None if not b.n else b.mean_pred,
             "obs_recall": None if not b.n else b.obs_recall}
            for b in bins
        ],
        "recall_definition": "ease >= 2 (any button that is not 'Again')",
        "predicted_R_definition": "FSRS power-forgetting curve at days-elapsed since prior review",
    }
    json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(f"\n{chart_note}")
    print(f"per-bin CSV : {csv_path}")
    print(f"summary JSON: {json_path}")

    if tmp_dir is not None:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
