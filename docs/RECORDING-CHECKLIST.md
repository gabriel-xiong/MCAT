# Recording checklist — master index of required clips

_Last updated: 2026-07-03._

Single source of truth for **every recording the deliverable needs**, each with a
checkbox and the **precise proof** it must show on camera. Detailed shot-lists
live in the runbooks linked per row; this file adds the two **still-missing**
clips' exact scripts (esp. the §7b sync "winner" with pre/post revlog counts) and
tracks what's already captured. Companion docs:
[`RECORDING-RUNBOOK.md`](RECORDING-RUNBOOK.md) (desktop + sync shot-lists),
[`../../anki-android-MCAT/docs/SYNC-RECORDING-RUNBOOK.md`](../../anki-android-MCAT/docs/SYNC-RECORDING-RUNBOOK.md)
(two-way sync), and [`CLEAN-INSTALL-PROOF.md`](CLEAN-INSTALL-PROOF.md).

> These are **human steps** — this file is a copy-paste checklist, not a claim
> that the clips exist. Do not fabricate a recording or its result.

---

## Status board

| # | Recording | Proves | Detailed script | Status |
|---|-----------|--------|-----------------|--------|
| R1 | Desktop from-source demo (`./run`) | 3 scores, memory review, Performance mode, v2 diagnosis, deck-delete reset | `RECORDING-RUNBOOK.md §A` | shot-list ready |
| R2 | **Desktop clean-VM `.msi` install** | fork installs + launches + shows a score on a pristine Windows VM, **AI OFF** | `RECORDING-RUNBOOK.md §B`, `CLEAN-INSTALL-PROOF.md §B` + **§R2 below** | ⚠️ **MISSING — human step** |
| R3 | Proof-capture appendix (Rust + Python tests) | tests pass on camera | `RECORDING-RUNBOOK.md §C` | commands ready (auto) |
| R4 | Phone review → desktop sync | a phone review appears on desktop after sync | `SYNC-RECORDING-RUNBOOK.md §5A` | ⚠️ **CLIP NOT FOUND** (see note) |
| R5 | Desktop review → phone (two-way) | reverse direction | `SYNC-RECORDING-RUNBOOK.md §5B` | shot-list ready |
| R6 | Offline review → reconnect → sync | nothing lost offline | `SYNC-RECORDING-RUNBOOK.md §5C`, `RECORDING-RUNBOOK.md §D.4` | shot-list ready |
| R7 | **§7b same-card conflict "winner"** | last-review-wins merge is correct; no lost/double-counted reviews | `RECORDING-RUNBOOK.md §D.5` + **§R7 below** | ⚠️ **MISSING — human step** |
| R8 | Perf-data bundle two-way sync (E1/E2) | perf attempts sync via portable bundle | `RECORDING-RUNBOOK.md §E` | shot-list ready |
| R9 | Phone three-score dashboard | ranges + readiness abstain on phone | `RECORDING-RUNBOOK.md §F` | shot-list ready |

**Asset verification (2026-07-03):** searched both repos — there is **no
`assets/` directory and no video file** (`.mp4/.mov/.webm/.gif`) anywhere under
`MCAT/` or `anki-android-MCAT/`. The phone-review clip (R4) that
`RECORDING-RUNBOOK.md §C` says "lives under `MCAT/assets/`" is **not present**;
capture it (R4 shot-list) or copy it in before assembling the packet. Note that
the mobile clean-install screenshot `CLEAN-INSTALL-PROOF.md §A` references
(`anki-android-MCAT/docs/artifacts/clean_install_launch.png`) **is present**
(verified 2026-07-03); only the R4 **video** clip and the `assets/` dir are
missing.

The two clips flagged **MISSING — human step** below are the focus of this file.

---

## §R2 — Desktop clean-VM install (AI OFF) — exact capture script

Extends `RECORDING-RUNBOOK.md §B` / `CLEAN-INSTALL-PROOF.md §B` with the exact
on-camera beats and the **AI-OFF** proof the deliverable requires.

**Pre-reqs (off camera):**
- A **clean Windows VM** with no Anki, Rust, or Python. (Cannot be driven from the
  build box — this is why it's a human step.)
- Copy the installer to the VM:
  `anki-MCAT/out/installer/dist/anki-26.05-win-x64.msi` (~636 MB, sha256 pinned in
  `CLEAN-INSTALL-PROOF.md §B`). Optionally verify the hash on the VM.

**On camera (keep it ~2 min):**
1. **Show the machine is clean.** Start-menu search "Anki" → nothing; no Python/
   Rust. Say: *"Clean Windows VM — no build tools, no Anki."*
2. **(Optional) verify the artifact.** `certutil -hashfile anki-26.05-win-x64.msi SHA256`
   and show it matches the pinned hash.
3. **Install.** Double-click the `.msi` → step through to completion.
   Say: *"This is the MCAT Speedrun fork's own installer, built with
   `./ninja installer:package`."*
4. **Launch** from the Start menu / desktop shortcut.
5. **Prove it's the fork.** `Help → About` → **Anki 26.05 (Qt 6.11)**. Open
   **Tools** and show the **MCAT** actions (Performance session, Topic mastery,
   Load question bank, Export/Reset performance data).
6. **Produce a score with AI OFF (the required beat).**
   - Import the flashcard CSVs and `Tools → MCAT: Load question bank…`
     (`MCAT/data/questions.json`), warm up one topic, run a short **Performance
     session**, and return to the **home dashboard** so a real **Performance /
     Memory** number renders.
   - Say on camera: *"No API key configured, and the runtime makes no network
     calls — this score is computed fully offline. AI is OFF."* Optionally show
     there is **no `.env`/API key** on the VM and (if you want it in-frame) that
     the MCAT modules have zero `http/requests/openai` references
     (`RECORDING-RUNBOOK.md §C "No-AI claim"`).
7. **Honest caveat.** State the `.msi` was **built overnight and predates the
   latest UI** — it exists to prove a clean install end-to-end; the from-source
   clip (R1) shows the current v2 flow.

**Proof this clip must show:** clean machine → installer runs → app launches as
**Anki 26.05 fork with MCAT Tools** → a **real score renders with AI OFF**.

---

## §R7 — §7b two-device memory-sync "winner" — exact capture script

This is the clip that **closes the conflict-resolution proof**: review the **same
card** offline on phone and desktop, sync, and show **last-review-wins** merged
correctly with **no lost or double-counted reviews**. Extends
`RECORDING-RUNBOOK.md §D.5` with the exact offline steps, the **expected pre/post
`revlog` counts**, and what to show on camera.

**Pre-reqs:** complete `RECORDING-RUNBOOK.md §D.1–D.3` (local sync server up, both
devices on the same baseline collection). The conflict rule you'll narrate is in
[`SYNC-CONFLICT-RULE.md`](SYNC-CONFLICT-RULE.md) — have it open.

### Step 0 — Capture the baseline revlog count (BEFORE any offline review)

Do this on camera so the before/after is undeniable. Pick **one specific card**
both devices have (note its front text).

- **Desktop** (`Tools → Debug Console`, or `sqlite3` on the closed collection):
  ```sql
  SELECT count(*) FROM revlog;                                  -- call this  C0
  SELECT count(*) FROM revlog WHERE cid = <THE_CARD_ID>;        -- call this  Ccard0
  ```
- **Phone** (adb; or just read the on-screen review count if `run-as` is blocked):
  ```bash
  adb shell run-as com.ichi2.anki.debug \
    sqlite3 /data/data/com.ichi2.anki.debug/files/AnkiDroid/collection.anki2 \
    "SELECT count(*) FROM revlog;"                              -- should equal C0 after baseline sync
  ```
  Both devices are on the same baseline, so **phone count == desktop count == C0**.

### Step 1 — Go offline on both

Phone: **Airplane mode** (show the icon). Desktop: simply **don't press Sync**
(or disconnect the network). Each device now reviews independently.

### Step 2 — Review the SAME card on both, at different times

1. **Phone (earlier):** review the chosen card, grade **Again** (or Hard). Say the
   time out loud. This adds **1** revlog row on the phone.
2. **Desktop (later, a few seconds after):** review the **same** card, grade
   **Easy**. This adds **1** revlog row on the desktop, with a **later** review
   timestamp (this is what makes the desktop review the winner).

### Step 3 — Reconnect and sync (order doesn't matter — winner is by review time)

Phone **Sync** → Desktop **Sync** → Phone **Sync** (settle). Wait for each to say
complete.

### Step 4 — Show the counts converge (no lost, no double-count)

Re-run the Step 0 queries on **both** devices. Expected, exactly:

| Quantity | Before | After | Why |
|----------|--------|-------|-----|
| total `revlog` (each device) | `C0` | **`C0 + 2`** | one review from each device, each kept once |
| `revlog` for the conflict card | `Ccard0` | **`Ccard0 + 2`** | **both** grades preserved as history |
| desktop total vs phone total | equal | **still equal** | collections converge |

Narrate: *"Two reviews of the same card, one per device. The count goes up by
**exactly 2** on both — nothing lost, nothing double-counted. Re-syncing again
leaves it at C0+2 (idempotent, USN/id-keyed)."* Hit **Sync** one more time on
camera to show the count is **stable** (still `C0 + 2`).

### Step 5 — Show the WINNER is correct

Open the card's info on both devices (**Browse → select card → Info**, or Card
Info):
- The card's **current scheduling reflects the later review (the desktop
  "Easy")** — e.g. its next interval/state matches an Easy grade, not the phone's
  Again. **Last-review-wins by review time.**
- Open the card's **review history / revlog** and show **both** rows are present:
  the earlier phone **Again** *and* the later desktop **Easy**. The earlier review
  is preserved as history; it just didn't win the scheduling.

Narrate: *"Same card, reviewed on both devices offline. The later review wins the
card's scheduling, while the review history keeps **both** events — a clear,
correct winner, and no review is lost or double-counted. Rule:
[`SYNC-CONFLICT-RULE.md`](SYNC-CONFLICT-RULE.md)."*

**Proof this clip must show:** baseline counts equal → same card graded
differently offline on each device → after sync **total = C0+2 on both** and the
card carries **both** revlog rows → the card's **scheduling matches the later
(Easy) review** → repeated sync stays at `C0+2`.

> **If you can't drive the emulator on camera** (`RECORDING-RUNBOOK.md §D.6`): the
> minimum spec-satisfying fallback is the R6 offline-sync + the phone→desktop
> card-appears spot-check; but R7 is the graded §7b core — prefer capturing it.

---

## Assembly checklist

- [ ] R1 desktop from-source demo captured
- [ ] **R2 clean-VM `.msi` install captured (score renders, AI OFF)**
- [ ] R3 test-run terminal captured (Rust + Python pass counts in frame)
- [ ] R4 phone review → desktop clip captured / located (⚠️ not currently in repo)
- [ ] R5 desktop → phone (two-way) captured
- [ ] R6 offline → reconnect → sync captured
- [ ] **R7 §7b same-card winner captured (counts = C0+2 on both; later review wins)**
- [ ] R8 perf-bundle two-way sync captured
- [ ] R9 phone three-score dashboard captured
- [ ] All clips collected into the deliverable packet (create `MCAT/assets/` if it doesn't exist)
