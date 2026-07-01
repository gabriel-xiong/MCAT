# Recording runbook — Wednesday proof packet

_Last updated: 2026-07-01._

Two "hit record and follow" shot-lists for the desktop recordings, plus a proof
appendix (Rust + Python tests, phone recording). Companion docs:
[`WEDNESDAY-CHECKLIST.md`](WEDNESDAY-CHECKLIST.md) (deliverables) and
[`RELEASE-INSTALLER.md`](RELEASE-INSTALLER.md) (commit + installer runbook).

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
