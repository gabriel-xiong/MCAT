# Recording runbook — Wednesday proof packet

_Last updated: 2026-07-01._

Two "hit record and follow" shot-lists for the desktop recordings, plus a proof
appendix (Rust + Python tests, phone recording). Companion docs:
[`WEDNESDAY-CHECKLIST.md`](WEDNESDAY-CHECKLIST.md) (deliverables) and
[`RELEASE-INSTALLER.md`](RELEASE-INSTALLER.md) (commit + installer runbook).

**Friday deliverables:** sections **(D)**–**(F)** below cover the Friday sync
shot-lists — **(D)** the graded §7b collection review sync, **(E)** the two
performance-data bundle shot-lists ("Two-way sync verified" and "Offline review →
sync"), and **(F)** the phone three-score dashboard.

Two important truths to keep the packet honest:

- **Recording (A)** runs the app **from source** (`./run`) so it shows **today's**
  v2 diagnosis UI and current content.
- **Recording (B)** runs the **prebuilt `.msi`**, which was **built overnight and
  predates today's UI changes**. It exists only to prove a clean-machine install
  — not to show the latest features. Say this on camera.

---

## (A) Desktop memory-review + performance / diagnosis demo (`./run`)

**Goal:** show three separate scores, a real memory review, Performance mode, a
science miss surfacing the **v2 confidence-gated diagnosis panel**, and the
deck-delete → dashboard-resets moment.

### Preconditions (do these BEFORE you hit record)

1. **Fully quit Anki**, then relaunch from source so the v2 dialog code is
   loaded (not a stale process):

```bash
cd /c/Users/gpdxi/Downloads/alphaProjects/anki-MCAT
./run
```

2. **Import the regenerated flashcards** (one-click — the CSVs now carry Anki
   import directives, so there is **no header note to delete**):
   - `File → Import…` → `MCAT/data/flashcards-dev-cloze.csv` → Import
   - `File → Import…` → `MCAT/data/flashcards-dev-basic.csv` → Import
   - The `#notetype` / `#columns` / `#tags column` directives set the note type
     (Cloze / Basic), field mapping, and `topic:<id>` tags automatically.
     (106 cloze + 27 basic = 133 cards.)
3. **Load the question bank:** `Tools → MCAT: Load question bank…` → pick
   `MCAT/data/questions.json` (140 questions).
4. **Warm up ONE science topic so Performance mode has eligible items.** The gate
   is **≥3 distinct cards seen + ≥5 Good/Easy reviews per topic**; fresh imports
   start locked. Do a quick offline review (grade Good/Easy) on ~6 cards of a
   single science topic, e.g. `tag:topic:bb_enzymes`, until it unlocks. (You can
   verify in `Tools → MCAT: Topic mastery…`.) CARS needs no gate, but we want a
   **science** miss on camera.
5. **Reset only the performance score, keep the unlock:** `Tools → MCAT: Reset
   performance data…` (defaults to No — click Yes). This clears logged attempts
   so Performance starts clean, but **keeps the loaded bank and the memory
   unlock** from step 4. **Do NOT delete the deck yet** — that would re-lock the
   topic; the deck-delete is the finale.

### On-camera sequence

1. **Home dashboard — three scores.** Open the deck browser (home). Point to the
   "MCAT Speedrun · three separate scores · never blended" header and the three
   cards: **Memory** (review count), **Performance** (accuracy · correct/attempts
   · topics unlocked), **Readiness (472–528)**. Show the **coverage bar**
   (`N/18 topics measured`) and the **Next** action line.
   - _Narration:_ "Three separate scores — memory, performance, readiness. We
     never blend them into one fake 'percent ready.'"
   - _Highlight:_ any card showing the grey **"not enough data"** badge — that's
     honest abstention, not a zero.

2. **Memory review.** Study the topic you warmed up; grade a few cards Good/Easy.
   Return to home — the **Memory** review count ticks up.
   - _Narration:_ "This is ordinary Anki memory review — FSRS recall. Doing well
     here is what *unlocks* a topic for performance testing."
   - _Highlight:_ memory and performance are different measurements.

3. **Enter Performance mode.** From the dashboard click **Interleaved session**
   (or **Blocked session**), or `Tools → MCAT: Performance session (interleaved)`.
   - _Narration:_ "Performance mode is a *separate* session — we never flip a
     flashcard reveal straight into a scored question. Only unlocked topics
     appear; CARS is the one lane with no memory gate."

4. **Deliberately miss a science question → v2 diagnosis panel.** Pick a wrong
   answer on a science MCQ. The panel shows the **inferred** hypothesis and
   confidence: **"Looks like: _<type>_ · NN%"** (types are Content gap / Applied
   reasoning / Misread), with a **Confirm** button and an **"Actually, something
   else ▾"** override.
   - Click **Confirm** on one miss to accept the inferred type.
   - On another miss, expand **"Actually, something else ▾"** — note it lists the
     *other* two types (the suggested one is hidden; Confirm covers it) — and pick
     one to override.
   - If you hit a **low-confidence** miss, the panel skips the hypothesis and just
     shows the three self-report buttons — mention that fallback if it appears.
   - _Narration:_ "The error type is **inferred** from the question and the
     distractor you picked — not a blank 'how do you feel' self-report. You
     confirm with one tap, or override. That inference is what drives the
     dashboard's next action."
   - _Highlight:_ inferred diagnosis + confidence %, one-tap confirm, honest
     override. Finish the session to show the end summary ("This performance
     score is separate from your memory score").

5. **Deck-delete → dashboard resets (finale).** Back on home, delete the MCAT
   deck (right-click deck → Delete, or the gear menu). Because the deck holds
   `topic:*`-tagged cards, MCAT performance/readiness attempts are cleared
   **before** removal, so the re-rendered dashboard drops back to the honest
   **"not enough data"** state.
   - _Narration:_ "Delete the MCAT cards and the scores don't lie — performance
     and readiness reset to 'not enough data' instead of showing stale numbers."
   - _Highlight:_ scores are evidence-bound; no data → no score.

---

## (B) Clean-machine install (existing `.msi`)

**Goal:** prove the fork installs and launches on a machine that never had a
build toolchain. Uses the artifact already built overnight.

### Preconditions

- A **clean Windows VM** (or fresh user) with **no** Anki, Rust, or Python build
  tools installed.
- The installer copied in from the build machine:
  `anki-MCAT/out/installer/dist/anki-26.05-win-x64.msi` (~636 MB). **Use it
  as-is — do NOT rebuild.**

### On-camera sequence

1. **Show the clean machine.** Briefly show there's no Anki installed (empty
   Start-menu search for "Anki", or an empty install dir).
   - _Narration:_ "Clean Windows VM — no build tools, no Anki."
2. **Copy + run the installer.** Copy `anki-26.05-win-x64.msi` onto the VM,
   double-click it, and step through the installer to completion.
   - _Narration:_ "This is the MCAT Speedrun fork's own installer, built from the
     fork with `./ninja installer:package`."
3. **Launch the app.** Start Anki from the Start menu / desktop shortcut.
4. **Show it opens as the fork.** `Help → About` → **Anki 26.05 (Qt 6.11)**.
   Show the **MCAT** entries under the **Tools** menu (Performance session,
   Topic mastery, Load question bank, Export/Reset performance data) to prove the
   MCAT features shipped in the build.
   - _Narration:_ "Anki 26.05 on Qt 6.11, and the MCAT Tools actions are present —
     so the fork's features are in the installed binary, not just in source."
5. **Honest caveat (say this explicitly).**
   - _Narration:_ "One caveat: this `.msi` was built overnight and **predates
     today's UI changes** — the diagnosis panel here is the older version. It's in
     the packet to prove a clean install works end-to-end; the **first recording
     (from source)** shows the current v2 diagnosis flow and today's content."

---

## (C) Proof-capture appendix

Screen-capture the terminal for each test block so the output (pass counts) is
visible in-frame.

### Rust — mastery query unit tests (4 tests)

```bash
cd /c/Users/gpdxi/Downloads/alphaProjects/anki-MCAT
cargo test -p anki mcat
```

### Python — mastery / perf / scoring tests

The Python tests import the built backend, so set `PYTHONPATH` per the fork
README before running (run from the `anki-MCAT` repo root, in Git Bash):

```bash
cd /c/Users/gpdxi/Downloads/alphaProjects/anki-MCAT
export PYTHONPATH="$(pwd)/out/pylib:$(pwd)/pylib"
python -m pytest pylib/tests/test_mcat_mastery.py \
                 pylib/tests/test_mcat_perf.py \
                 pylib/tests/test_mcat_scores.py
```

### No-AI claim

Already verified: the MCAT runtime modules contain no network/LLM calls (only
SQLite + AGPL header URLs). No re-capture needed unless you want it on camera —
if so, grep the MCAT modules for `http`/`requests`/`openai` and show zero hits.

### Phone review recording

Already captured during the mobile track (AnkiDroid import + graded review on
the emulator). Per the checklist it lives under **`MCAT/assets/`** — confirm the
file is present there before assembling the packet (the `assets/` folder is not
currently checked into the repo tree, so make sure the recording was saved/copied
in before you zip the deliverables).

---

## (D) §7b — Two-way sync test (Friday GRADED CORE)

> **Two different sync channels — read this first.** This section **(D)** is the
> **shared-engine collection/review sync** (revlog + card scheduling over the
> local sync server) — the **graded §7b requirement**. It is a *different* channel
> from **(E)** below, which is the project's custom performance-data *bundle*
> side-channel. (D) proves memory-review sync; (E) proves perf-attempt sync.

**Goal (spec §7b):** review 10 cards on the phone offline + 10 *different* cards on
the desktop offline, reconnect, sync both, and show **all 20 reviews land in one
place, none lost, none double-counted**; then review the **same card** on both
devices offline, sync, and show the conflict rule picks a **clear, correct
winner**. Also captures the required proof: **a card reviewed on the phone showing
up on the desktop after sync.**

The merge/winner rule this test demonstrates is written up in
[`SYNC-CONFLICT-RULE.md`](SYNC-CONFLICT-RULE.md) — have it open to narrate.

**Decision (documented):** we use a **self-hosted local sync server** (Anki's
built-in `--syncserver`), not AnkiWeb — no account/credentials, works offline on
the LAN, same build serves both forks. Rationale in `SYNC-CONFLICT-RULE.md §5`.

### D.0 Preconditions (before recording)

- Desktop Anki fork running from source (`./run`) with the MCAT deck imported (see
  §A preconditions), and the AnkiDroid fork installed on the emulator/phone with
  the same deck present (mobile track).
- Know this machine's LAN IP: run `ipconfig` in Git Bash and read the IPv4 (was
  **`10.10.1.132`** on 2026-07-02; re-check, DHCP can change it).
- Client endpoint URL to use:
  - Desktop (same machine as server): `http://127.0.0.1:8080/`
  - **Android emulator**: `http://10.0.2.2:8080/` (10.0.2.2 = host loopback alias)
  - Physical phone on same Wi-Fi: `http://10.10.1.132:8080/`

### D.1 Start the local sync server (Git Bash — uses the FROZEN build, no rebuild)

```bash
cd "/c/Users/gpdxi/Downloads/alphaProjects/anki-MCAT/out/installer/build/anki/windows/app/src"
export SYNC_USER1="mcat:mcat"
export SYNC_HOST="0.0.0.0"
export SYNC_PORT="8080"
export SYNC_BASE="/c/Users/gpdxi/Downloads/alphaProjects/anki-MCAT/.syncserver-demo"
mkdir -p "$SYNC_BASE"
./Anki.exe --syncserver
```

Leave this terminal running and **on camera**. Verify in a second terminal:

```bash
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8080/health   # expect 200
```

(`--syncserver` is headless — no Anki window opens. `SYNC_BASE` must NOT be your
normal Anki data folder; the server keeps its own copy.)

### D.2 Point the desktop client at the local server

1. In Anki: **Tools → Preferences → Syncing** (the "Syncing" tab).
2. In the **Self-hosted sync server** field, enter: `http://127.0.0.1:8080/`
   (trailing slash). Close Preferences.
3. Click the **Sync** button (circular-arrows, top toolbar). Log in with
   **`mcat` / `mcat`**. Because the server is empty, choose **Upload to server**
   when prompted — this establishes the shared baseline.

### D.3 Point the AnkiDroid client at the same server

1. In AnkiDroid: **☰ / gear → Settings → Sync**.
2. Tap **Custom sync server** → in **Sync URL** enter the emulator/phone URL:
   `http://10.0.2.2:8080/` (emulator) or `http://10.10.1.132:8080/` (phone).
   Leave the certificate field blank. Back out to save.
3. Back on Settings → Sync, set the **AnkiWeb account** login to **`mcat` /
   `mcat`** (it authenticates against your custom server, despite the "AnkiWeb"
   label).
4. Trigger a sync (the sync icon / **Synchronize**). Since the desktop already
   uploaded the baseline, choose **Download from server** when prompted so both
   devices start from the identical baseline.

> Baseline check: both devices now show the same card counts. From here on, syncs
> are **normal incremental** merges — do **not** pick a full upload/download again
> during the test (that would overwrite one side; see `SYNC-CONFLICT-RULE.md §6`).

### D.4 The 20-review test (none lost, none doubled)

1. **Go offline on both.** Phone: enable **Airplane mode** (or turn off Wi-Fi).
   Desktop: you can leave the server up but simply *don't press Sync yet* (or
   disconnect the network) — the point is each device reviews independently before
   syncing.
2. **Phone — review 10 cards.** Study 10 cards, grading each (Good/Easy is fine).
   Note the 10 cards (e.g. first 10 of a topic).
3. **Desktop — review 10 DIFFERENT cards.** Study 10 *other* cards (a different
   deck/topic, or the next 10) so the two sets do not overlap. Grade each.
4. **Reconnect the phone** (Airplane mode off) and ensure the desktop is online.
5. **Sync the desktop** (Sync button) — it uploads its 10 reviews.
6. **Sync the phone** (Synchronize) — it uploads its 10 and pulls the desktop's 10.
7. **Sync the desktop once more** so it pulls the phone's 10.
8. **Verify all 20 landed once, on both devices:**
   - On the desktop, open **Stats** (or the deck's review count / today's reviews)
     and show **20 reviews today**.
   - Open the phone Stats and show the **same 20**.
   - Spot-check: a specific card you reviewed on the **phone** now shows its
     updated due/interval on the **desktop** (this is the required phone→desktop
     proof — keep it clearly in frame).
   - _Narration:_ "20 reviews total, 10 from each device, each counted exactly
     once — the revlog is append-only keyed by review timestamp, so nothing is
     lost and nothing is double-counted."

### D.5 The same-card conflict (clear, correct winner)

1. **Go offline on both again** (phone Airplane mode; desktop don't-sync).
2. **Pick ONE specific card both devices have.** On the **phone**, review it and
   grade it **Again** (or Hard). Note the time.
3. On the **desktop**, review the *same* card and grade it **Easy** a few seconds
   **later** (so the desktop review has the later modification time).
4. **Reconnect and sync**: phone Sync, then desktop Sync, then phone Sync (order
   doesn't matter — the winner is by review time, not sync order).
5. **Show the winner:** open that card's info (**Browse → select card →** *Info*,
   or Card Info) on both devices. The card's **current scheduling reflects the
   later review (the desktop "Easy")** — the later-in-time review wins. Open the
   card's **revlog / review history** and show **both** grades are still listed
   (the earlier "Again" is preserved as history; it just didn't re-advance the
   card).
   - _Narration:_ "Same card reviewed on both devices offline. The conflict rule
     is **last-review-wins by modification time** for the card's scheduling, while
     the review history keeps *both* events. So there's a clear, correct winner —
     the later review — and no review is lost or double-counted. The rule is
     written up in `SYNC-CONFLICT-RULE.md`."

### D.6 If you can't drive the emulator on camera (blocker → manual)

The emulator GUI and AnkiDroid taps can't be scripted from this shell. If you're
short on time, the **minimum spec-satisfying proof** is D.1–D.4 plus the
phone→desktop card-appears spot-check (D.4.8). Steps D.2, D.3, D.4, D.5 are all
manual GUI/emulator actions — follow the exact menu paths above.

---

## (E) Friday — two-way performance-data sync (`./run`)

> **Two different sync channels — read this first.** This section **(E)** is the
> project's custom **performance-data bundle** side-channel that carries the
> `mcat_perf.db` attempts (and, on the phone, lights up Performance/Readiness).
> It is a *different* channel from **(D)** above, which is the shared-engine
> collection/review sync (the graded §7b requirement). (D) proves memory-review
> sync; (E) proves perf-attempt sync.

**Goal:** prove performance-mode data (the append-only `perf_attempts`) syncs
**both ways** across two devices via a portable **export/import bundle**, and
that the two sides **converge** to the union of attempts. Stock Anki sync does
NOT carry our sidecar tables (that's *why* we built the bundle — see
`DECISIONS.md §22`), so this is the perf-data sync story.

**Two "devices" without two machines:** use **two Anki profiles** (`File →
Switch Profile…` → `Add` → e.g. `Device-A` and `Device-B`). Each profile has its
own `collection.anki2` **and its own sidecar `collection.mcat_perf.db`**, so two
profiles behave exactly like two devices for perf data. (On a real second
machine / AnkiDroid the steps are identical — just copy the `.json` bundle
across instead of it already being on disk.)

### Preconditions (BEFORE you hit record)

1. Launch from source so the sync menu actions are loaded:

```bash
cd /c/Users/gpdxi/Downloads/alphaProjects/anki-MCAT
./run
```

2. In **both** profiles (`Device-A` and `Device-B`), get Performance mode ready:
   - `File → Import…` the two flashcard CSVs (as in shot-list A), then
     `Tools → MCAT: Load question bank…` → `MCAT/data/questions.json`.
   - Warm up **one** science topic to unlock it (≥3 cards seen + ≥5 Good/Easy),
     e.g. `tag:topic:bb_enzymes`. (CARS needs no gate if you'd rather keep it
     quick.)
   - `Tools → MCAT: Reset performance data…` (Yes) in both so each starts from a
     clean, empty attempt set on camera.

---

### (E1) "Two-way sync verified"

**Story:** each device answers *different* questions, they exchange bundles, and
both end up with the **same** combined set of attempts.

1. **Device-A — do a short session.** `File → Switch Profile… → Device-A`.
   `Tools → MCAT: Performance session (interleaved)`. Answer **3–4** questions
   (mix a correct and a miss). Finish. _Narration:_ "Device A just recorded a few
   performance attempts locally."
2. **Export A's bundle.** `Tools → MCAT: Export sync bundle…` → save as
   `Device-A.perf_bundle.json` (e.g. to the Desktop). Note the tooltip: "Exported
   sync bundle (N attempts, M questions)".
3. **Device-B — do a DIFFERENT short session.** `File → Switch Profile… →
   Device-B`. Run a performance session and answer a **different** handful of
   questions. Finish.
4. **Export B's bundle.** `Tools → MCAT: Export sync bundle…` →
   `Device-B.perf_bundle.json`.
5. **Import A→B.** Still on Device-B: `Tools → MCAT: Import sync bundle…` → pick
   `Device-A.perf_bundle.json`. Read the tooltip: **"Imported N new attempts
   (0 already present; …)"**. _Narration:_ "Device B just merged in Device A's
   attempts — union merge, nothing overwritten."
6. **Import B→A.** `File → Switch Profile… → Device-A` → `Tools → MCAT: Import
   sync bundle…` → pick `Device-B.perf_bundle.json`. Tooltip shows the new
   attempts added.
7. **Show convergence.** On each profile open **Home** (the three-score
   dashboard) and point at the **Performance** card — the **correct/attempts**
   count is now the **same total on both**. _Narration:_ "Both devices converge
   to the union — identical performance data after a two-way exchange."
8. **Prove it's idempotent (optional, strong).** On Device-A, import
   `Device-B.perf_bundle.json` **again** → tooltip reads **"Imported 0 new
   attempts (K already present)"**. _Narration:_ "Re-importing the same bundle
   changes nothing — dedup on a stable per-attempt id."

_Highlight:_ two-way exchange, union merge, convergence, idempotent re-import.

---

### (E2) "Offline review → sync"

**Story:** do performance work while "offline," then carry just a file to the
other device — no network, no cloud.

1. **Go offline (on camera).** Turn off Wi-Fi / pull the network (or just say
   "note there's no network — this never phones home"). _Narration:_ "No network.
   Performance mode is fully local; sync is a file, not a server."
2. **Device-A — offline performance session.** `File → Switch Profile… →
   Device-A` → `Tools → MCAT: Performance session (blocked)`. Answer several
   questions, including at least one **miss** so the v2 diagnosis panel appears.
   Finish — the summary shows the (separate) performance score.
3. **Export the bundle to a file.** `Tools → MCAT: Export sync bundle…` →
   `offline-session.perf_bundle.json`. _Narration:_ "That's the whole sync
   payload — one portable JSON file."
4. **Carry the file to Device-B.** (On one machine it's already on disk; on a
   real phone/second PC, copy the `.json` over — USB, drive, AirDrop, whatever.)
   Show the file in the file picker to make the "carry a file" point.
5. **Device-B — import while still offline.** `File → Switch Profile… →
   Device-B` → `Tools → MCAT: Import sync bundle…` → pick
   `offline-session.perf_bundle.json`. Tooltip: **"Imported N new attempts …"**.
6. **Show it landed.** Open **Home** on Device-B — the **Performance** score now
   reflects the offline session's attempts. _Narration:_ "The offline session's
   attempts are now on the second device — still no network involved."

_Highlight:_ offline-first, file-based sync, no AI / no network, perf score
transfers.

> **Headless alternative (for a terminal-only capture).** The same flow scripts
> cleanly — useful if you'd rather show the merge counts than click menus:
>
> ```bash
> cd /c/Users/gpdxi/Downloads/alphaProjects/anki-MCAT
> export PYTHONPATH="$(pwd)/out/pylib:$(pwd)/pylib"
> PY=./out/pyenv/Scripts/python.exe
> # export each device's sidecar, then cross-import
> $PY tools/mcat_export_bundle.py --db /path/Device-A/collection.mcat_perf.db --out A.json
> $PY tools/mcat_export_bundle.py --db /path/Device-B/collection.mcat_perf.db --out B.json
> $PY tools/mcat_import_perf.py --db /path/Device-B/collection.mcat_perf.db --bundle A.json
> $PY tools/mcat_import_perf.py --db /path/Device-A/collection.mcat_perf.db --bundle B.json
> # re-run either import to show "0 new attempts" (idempotent)
> ```

---

## (F) Friday — phone three-score dashboard (AnkiDroid)

**Goal (Friday spec):** "The phone shows the three scores with ranges and follows
the give-up rule." Show the AnkiDroid dashboard rendering **Memory**,
**Performance**, and **Readiness (472–528)** as three separate, never-blended
scores, with the readiness **range + coverage % + confidence + last-updated +
next action**, and the **abstain / give-up** state below the coverage threshold.

The phone dashboard mirrors the desktop scoring: it replicates the Rust mastery
query and `mcat_scores.py` thresholds in Kotlin against the SAME
`scoring-config.json` values, so desktop and phone agree.

### What is real vs degraded on the phone (say this if asked)

- **Memory** — REAL. Computed live from the collection on-device (review count,
  topics studied, topics unlocked) — same definitions as the desktop mastery
  query.
- **Performance / Readiness** — REAL **when the perf sidecar is on the phone**.
  The phone reads `collection.mcat_perf.db` next to the collection (the same
  sidecar the desktop writes and the sync bundle carries). If that file is not on
  the device yet, Performance shows **"no data yet"** and Readiness **abstains** —
  it never fabricates a number.

### Preconditions (before recording)

1. Build/install the AnkiDroid fork on the emulator/phone (Kotlin compile is
   verified — see the build command in the deliverable notes / `WEDNESDAY-CHECKLIST.md`).
2. Have the MCAT deck present on the phone (mobile track import) so the Memory
   card shows real review counts. Do a few graded reviews if the count is 0.
3. (Optional, to light up Performance/Readiness) Copy a
   `collection.mcat_perf.db` sidecar next to the phone's collection — e.g. export
   a sync bundle on the desktop and land it on the phone via the sync workstream,
   or push the sidecar file directly. Without it, the abstain state is the honest,
   on-camera-correct default.

### On-camera sequence

1. **Open the dashboard.** On the AnkiDroid home (DeckPicker), tap the **⋮
   overflow menu → "MCAT: Dashboard"**. The dashboard screen opens.
   - _Narration:_ "Same three scores as the desktop, now on the phone — memory,
     performance, readiness, never blended."
2. **Three separate cards.** Point to **MEMORY** (review count · topics · unlocked),
   **PERFORMANCE** (accuracy · correct/attempts), and **READINESS (472–528)**.
   Show the **coverage bar** (`N/18 topics measured`).
3. **Readiness honesty / give-up rule.** If below threshold, the readiness card
   shows **no number** ("—"), the coverage % with `(need ≥50%)`, and the
   missing-data reason ("coverage < 50%; attempts < 30; …"), plus the single
   **Next** action.
   - _Narration:_ "Below the coverage give-up threshold the phone shows **no
     readiness number** — just why, and the one next action. That's the honesty
     rule: no score without range, coverage, confidence, and a next step."
   - If the sidecar IS present and thresholds are met, show the readiness
     **range** (e.g. `508–520`), **low confidence**, and **last-updated** time.
4. **Abstain badges.** Point out any grey **"not enough data"** badge on a card —
   honest abstention, not a fake zero.

_Highlight:_ three scores with ranges on the phone; readiness abstains and shows
the give-up reason + next action below threshold — matching the desktop and
`scoring-config.json`.
