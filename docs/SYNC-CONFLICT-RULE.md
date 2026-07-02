# Sync conflict / merge rule for reviews (Friday §7b artifact)

_Last updated: 2026-07-02._

This is the **required written artifact** for the Speedrun spec §7b sync test. It
documents exactly how the MCAT fork merges reviews when the desktop Anki fork and
the AnkiDroid fork sync, why **no review is lost**, and why **no review is
double-counted**, including the "same card reviewed on both devices offline" case
and the **clear, correct winner** rule.

The companion click-by-click test procedure is in
[`RECORDING-RUNBOOK.md`](RECORDING-RUNBOOK.md) (section **§7b — Two-way sync
test**).

---

## 0. Why we can state this precisely (shared engine)

Both forks run the **same Rust sync engine** (`rslib/src/sync/`). AnkiDroid does
not reimplement sync — it calls the shared backend. So the merge behaviour is
identical on both ends, and both are simply **clients of one sync server**. Per
`docs/DECISIONS.md` and `AGENTS.md`, the perf tables live in the same collection
DB and ride the stock Anki sync; the rules below are stock Anki collection-sync
semantics, which we inherit unchanged.

Decision for the demo: **self-hosted local sync server** (Anki's built-in
`--syncserver`). See §5 for the recommendation rationale and the exact command.

---

## 1. The two data structures that carry a "review"

A single review touches **two** tables, and they merge by **different rules**:

| Data | What it is | Merge rule | Source |
|------|-----------|-----------|--------|
| **`revlog` row** | The immutable *history* event ("card X graded Good at time T, took N ms"). Drives the **Memory** score (FSRS/recall count). | **Append-only, keyed by review id.** `INSERT OR IGNORE` on the id. | `rslib/src/sync/collection/chunks.rs::merge_revlog` → `storage/revlog/add.sql` |
| **`cards` row** | The card's *current* scheduling state (due date, interval, reps, ease, queue). One row per card. | **Newer-writer-wins by `mtime`** (whole-row replace). | `chunks.rs::add_or_update_card_if_newer` |

Keeping these separate is exactly why "no lost / no double-count" holds — see §2
and §3.

---

## 2. Revlog: append-only, so nothing is lost and nothing is double-counted

Each revlog entry's **id is the epoch-millisecond timestamp of the moment the
card was graded**. When a chunk of revlog rows arrives from the other device, the
engine does (`rslib/src/sync/collection/chunks.rs`, `merge_revlog`):

```rust
fn merge_revlog(&self, entries: Vec<RevlogEntry>) -> Result<()> {
    for entry in entries {
        self.storage.add_revlog_entry(&entry, false)?;  // uniquify = false
    }
    Ok(())
}
```

which runs `INSERT OR IGNORE` on the review id (`rslib/src/storage/revlog/add.sql`):

```sql
INSERT
  OR IGNORE INTO revlog (
    id, cid, usn, ease, ivl, lastIvl, factor, time, type
  )
VALUES ( ... )
```

Consequences for §7b:

- **Two reviews on two devices → two distinct millisecond ids → both rows are
  inserted.** Even reviewing the *same card* on both devices produces two
  different ids (different wall-clock ms), so **both review events are preserved**
  in history. → **nothing lost.**
- **Re-syncing a review that is already present is a no-op** — `OR IGNORE` drops
  the duplicate id. So syncing repeatedly, or a card that round-trips through the
  server, never inserts the same review twice. → **nothing double-counted.**
- The **Memory** score (which counts revlog recall events) therefore equals the
  union of both devices' reviews: 10 + 10 = **20**, exactly once each.

---

## 3. Card scheduling state: last-review-wins by modification time

The `cards` row is a single mutable row per card, so it *can* conflict. The rule
(`rslib/src/sync/collection/chunks.rs`, `add_or_update_card_if_newer`):

```rust
fn add_or_update_card_if_newer(&self, entry: CardEntry, pending_usn: Usn) -> Result<()> {
    let proceed = if let Some(existing_card) = self.storage.get_card(entry.id)? {
        !existing_card.usn.is_pending_sync(pending_usn) || existing_card.mtime < entry.mtime
    } else {
        true
    };
    if proceed {
        let card = entry.into();
        self.storage.add_or_update_card(&card)?;
    }
    Ok(())
}
```

Read it as: **apply the incoming card row if** the local copy was *not* modified
since the last sync (`!is_pending_sync`) **or** the local copy is *older*
(`existing.mtime < incoming.mtime`). Combined with the fact that the device which
syncs *second* pulls the first device's state before pushing its own, this
resolves to a single deterministic outcome:

> **The card's surviving scheduling state is the one from the review with the
> greater `mtime` (the review performed later in wall-clock time). This is
> independent of which device happened to sync first.**

Why it's order-independent: if device B synced second and its local card is
"pending" (reviewed offline), B adopts A's row only when `A.mtime > B.mtime`;
otherwise B keeps its own newer row and uploads it, overwriting the server. Either
way the winner is `max(mtime)`.

Crucially, the winning row **replaces** the loser — `reps`, `due`, `ivl` are taken
from the winner, **not summed**. So a card reviewed on both devices advances **once
to the later state**, never twice. That is the "no double-count" guarantee at the
scheduling level, complementing the append-only history in §2.

Tie note: the comparison is strict (`<`). If two reviews share the identical
`mtime` second and the local row is pending, the local row is kept — a stable,
deterministic tie-break (not a crash or a merge).

---

## 4. The §7b scenarios, resolved

**Scenario 1 — 10 on phone + 10 *different* cards on desktop, both offline, then
sync.** The two card sets are disjoint, so there is no `cards`-row conflict at
all: all 20 card rows apply, and all 20 revlog rows insert under distinct ids.
After both devices sync, both collections show **20 reviews, each counted once —
none lost, none doubled.**

**Scenario 2 — the *same* card reviewed on both devices offline, then sync
(conflict case).**
- **History (`revlog`):** both grades are kept as two separate events (distinct
  ms ids). The full study history is preserved on both devices.
- **Scheduling (`cards`):** the row from the **later** review (greater `mtime`)
  wins and defines the card's current due/interval/reps; the earlier review's
  scheduling change is superseded. The card advances **once**, not twice.

**The winner rule, stated for the artifact (drop-in):**

> **Winner rule:** Reviews are never overwritten as history — the `revlog` is
> append-only and keyed by the review's millisecond timestamp, so every grade
> from every device is preserved exactly once (`INSERT OR IGNORE` discards only
> exact-id duplicates). When the *same card* is graded on both devices offline,
> the card's **current scheduling state is set by the review with the later
> modification time (last-review-wins)**; the earlier review remains in history
> but does not re-advance the card. This is deterministic and independent of sync
> order, so no review is lost and none is counted twice.

---

## 5. Recommendation: self-hosted local `--syncserver` (not AnkiWeb)

**Recommended: run Anki's built-in sync server locally** for the demo/recording.

Why, over AnkiWeb:
- **No credentials / no account setup** — AnkiWeb needs a real registered
  account for the shared login; the local server accepts any `SYNC_USER1=user:pass`
  you invent.
- **Fully offline-capable and self-contained** — perfect for a clean, repeatable
  recording; the only network needed is the LAN between the desktop and the phone
  (or emulator ↔ host loopback).
- **Both forks already support pointing at a custom endpoint** (desktop:
  Preferences → *Self-hosted sync server* URL; AnkiDroid: Advanced → *Custom sync
  server* → *Sync URL*), and they share the same Rust protocol, so a single local
  endpoint serves both.
- **No protocol-skew risk** — the server is the *same build* as the client, so
  there is no third-party-server lag (which the manual explicitly warns about).

Trade-off documented: the built-in server binds **unencrypted HTTP** and is meant
for local/family use — fine for a LAN demo, not for public exposure.

### Exact command (verified working from the FROZEN build — no `./run` rebuild)

Run from Git Bash. This uses the already-packaged desktop binary, so it does **not**
touch or rebuild the frozen `./run` tree:

```bash
cd "/c/Users/gpdxi/Downloads/alphaProjects/anki-MCAT/out/installer/build/anki/windows/app/src"
export SYNC_USER1="mcat:mcat"          # username:password you will type into both clients
export SYNC_HOST="0.0.0.0"             # listen on all interfaces so the phone can reach it
export SYNC_PORT="8080"
export SYNC_BASE="/c/Users/gpdxi/Downloads/alphaProjects/anki-MCAT/.syncserver-demo"  # must NOT be your normal Anki data folder
mkdir -p "$SYNC_BASE"
./Anki.exe --syncserver
```

Verified on 2026-07-02: `GET http://localhost:8080/health` → **HTTP 200**, and the
`/sync/*` collection route is live. `--syncserver` is handled headlessly before any
GUI init (`qt/aqt/__init__.py`), so no window opens.

**Equivalent alternatives** (documented, not required):
- After installing the `.msi`: `set SYNC_USER1=mcat:mcat` then
  `"\Program Files\Anki\anki-console.exe" --syncserver` (per the Anki manual).
- Standalone via pip: `pip install anki` then
  `SYNC_USER1=mcat:mcat python -m anki.syncserver`.

### Endpoint URLs to give the clients

- LAN IP of this machine (detected 2026-07-02): **`10.10.1.132`** (re-check with
  `ipconfig` before recording; DHCP can change it).
- **Desktop client** (same machine as server): `http://127.0.0.1:8080/` (or the
  LAN IP).
- **Android emulator** reaches the host loopback at the special alias
  **`10.0.2.2`**, so use `http://10.0.2.2:8080/`.
- **Physical Android phone** on the same Wi-Fi: `http://10.10.1.132:8080/`.
- Modern clients (this fork) take just the **base URL** with a trailing slash;
  they derive `/sync/` and `/msync/` automatically. Only pre-2.16 clients need the
  split `SYNC_ENDPOINT` / `SYNC_ENDPOINT_MEDIA` form.

---

## 6. Two operational cautions baked into the runbook

1. **Establish a baseline BEFORE the offline test.** The very first sync between
   two previously-independent collections is resolved by a **full sync**
   (upload/download whole collection), *not* the per-object merge above. To make
   §7b actually demonstrate the merge rule, first get both devices to a common
   base: sync the desktop **up** to the fresh server, then sync the phone **down**
   from it. After that, subsequent syncs are **normal incremental** syncs and the
   §2/§3 rules apply.
2. **Do a normal sync for the test — do not force a full sync.** Changing the
   schema or ticking an "upload to server" / "download from server" full-sync
   option replaces one side wholesale and would mask the merge (and could lose the
   other side's reviews). The §7b test must use ordinary "Sync" on both ends.
