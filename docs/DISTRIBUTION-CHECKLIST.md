# Builder distribution checklist — shipping the tester build

_Last updated: 2026-07-03._

The step-by-step for the **builder** to get the tester package into a friend's
hands. The desktop package and installer already exist on disk; most of what's
left is **hosting** and the **Android signing** (both human steps). Companion
docs: [`TESTER-QUICKSTART.md`](TESTER-QUICKSTART.md) (the page you send testers),
[`TESTER-HANDOFF.md`](TESTER-HANDOFF.md) (data-flow / calibration reference),
[`RELEASE-INSTALLER.md`](RELEASE-INSTALLER.md) (how the preseeded build is
assembled), and
[`anki-android-MCAT/docs/RELEASE-SIGNING-RUNBOOK.md`](../../anki-android-MCAT/docs/RELEASE-SIGNING-RUNBOOK.md)
(APK signing).

> **No secrets in this repo.** Keystores, passwords, and API keys never get
> committed or pasted into any tracked file. AI stays **off** for testers (no key
> bundled). See the signing runbook's secrets policy.

---

## What exists on disk right now (verified 2026-07-03)

| Artifact | Path | Status |
|----------|------|--------|
| Windows installer | `anki-MCAT/out/installer/dist/anki-26.05-win-x64.msi` (~636 MB) | **READY** |
| Preseeded desktop package | `anki-MCAT/out/tester-dist/MCAT-Speedrun/` | **READY** |
| ↳ launcher | `MCAT-Speedrun/Start MCAT Speedrun.cmd` | present |
| ↳ readme | `MCAT-Speedrun/READ ME FIRST.txt` | present |
| ↳ preseeded base | `MCAT-Speedrun/mcat-base/` (`prefs21.db`, `User 1/collection.anki2`, `User 1/collection.mcat_perf.db`) | present |
| Deck contents (verified) | 158 topic-tagged notes / 158 cards | seeded |
| Question bank (verified) | 170 questions + 45 remediation items | seeded |
| Android release APK | `anki-android-MCAT/AnkiDroid/build/outputs/apk/full/release/` | **NOT BUILT YET** (human step §3) |
| Android deck `mcat-deck.apkg` | (to be exported from desktop Anki) | **NOT BUILT YET** (human step §3) |

> If the deck or question bank changed since the package was built, rebuild the
> base first (one command — see §1).

---

## 1. Reseed the preseeded base — clean, right before every upload

Rebuild whenever `MCAT/data/*` (deck CSVs or `questions.json`) changed **and
always immediately before zipping a bundle to upload** (see the ship-clean rule
below). Runs headlessly against the fork's own build venv, **refuses** to touch
the live `%APPDATA%/Anki2` profile, and wipes + recreates `out/tester-dist` — so
a fresh run always starts from an empty base:

```bash
cd /c/Users/gpdxi/Downloads/alphaProjects/anki-MCAT
out/pyenv/Scripts/python.exe tools/mcat_seed_tester.py
# -> out/tester-dist/MCAT-Speedrun/  (base + launcher + READ ME FIRST.txt)
```

Confirm the printed counts look right (notes / cards / topic-tagged / questions /
remediation).

> **Ship-clean rule (learned the hard way — a bundle once went out with the
> builder's own review/attempt data baked into it).** NEVER launch the app
> against the shippable `out/tester-dist/.../mcat-base`: doing so writes *your*
> revlog + perf attempts into the base, and that history then gets zipped and
> shipped to the tester. Self-test only on a **throwaway extracted copy** (unzip
> somewhere else and launch *that*), and **reseed fresh immediately before
> zipping** for upload.

**Verify the base is empty before you zip** — every history counter must be `0`
(Python `sqlite3`, read-only; the `sqlite3` CLI isn't installed on this box):

```bash
cd /c/Users/gpdxi/Downloads/alphaProjects/anki-MCAT
python - "out/tester-dist/MCAT-Speedrun/mcat-base/User 1" <<'PY'
import sqlite3, sys
p = sys.argv[1]
a = sqlite3.connect(f"file:{p}/collection.anki2?mode=ro", uri=True)
print("revlog       :", a.execute("SELECT COUNT(*) FROM revlog").fetchone()[0], "(want 0)")
print("cards reps>0 :", a.execute("SELECT COUNT(*) FROM cards WHERE reps>0").fetchone()[0], "(want 0)")
print("cards ivl>0  :", a.execute("SELECT COUNT(*) FROM cards WHERE ivl>0").fetchone()[0], "(want 0)")
print("cards total  :", a.execute("SELECT COUNT(*) FROM cards").fetchone()[0], "(want 66)")
d = sqlite3.connect(f"file:{p}/collection.mcat_perf.db?mode=ro", uri=True)
print("perf_attempts:", d.execute("SELECT COUNT(*) FROM perf_attempts").fetchone()[0], "(want 0)")
print("perf_quest.  :", d.execute("SELECT COUNT(*) FROM perf_questions").fetchone()[0], "(want 62)")
PY
```

If any history counter is non-zero, **STOP** — do not upload; reseed again on a
base no app has opened, then re-verify. (Reps `> 0` / a populated FSRS
memory-state imply reviews happened, so `revlog == 0` + `reps > 0 == 0` is the
quick tell.)

## 2. Desktop — zip and host

1. **Zip the package folder.** Zip `anki-MCAT/out/tester-dist/MCAT-Speedrun/`
   (the whole folder, so `Start MCAT Speedrun.cmd`, `READ ME FIRST.txt`, and
   `mcat-base/` are all inside) → **`MCAT-Speedrun.zip`**.
2. **Host two files** where friends can download them:
   - **`anki-26.05-win-x64.msi`** (~636 MB), and
   - **`MCAT-Speedrun.zip`**.
   Google Drive (share link, "anyone with link") or a **GitHub Release** on the
   `anki-MCAT` repo both work. A GitHub Release is cleaner for the ~636 MB MSI
   and gives a stable link.
3. **Optionally include `TESTER-QUICKSTART.md`** (or a link to it) alongside the
   downloads so testers have the full instructions.

## 3. Android — sign, build, host (HUMAN step, not yet done)

The Android APK is **not built yet**. Do this only if you're shipping the phone
version.

1. **Generate a release keystore** (one time) and set the signing env vars —
   follow [`RELEASE-SIGNING-RUNBOOK.md`](../../anki-android-MCAT/docs/RELEASE-SIGNING-RUNBOOK.md)
   §1–2. Keep the keystore **outside** the repo; never commit it or its
   passwords.
2. **Build the signed APK** (§3 of the signing runbook):
   ```bash
   cd /c/Users/gpdxi/Downloads/alphaProjects/anki-android-MCAT
   ./gradlew.bat :AnkiDroid:assembleFullRelease -Duniversal-apk=true
   # -> AnkiDroid/build/outputs/apk/full/release/AnkiDroid-full-universal-release.apk
   ```
   The **universal** APK is easiest to hand-install on one test phone.
3. **Verify the signature** (§5): `apksigner verify --print-certs` must report
   **Verifies** with **your** cert DN (not `CN=Android Debug`).
4. **Export the deck `mcat-deck.apkg`** from desktop Anki: import
   `MCAT/data/flashcards-dev-*.csv` into a scratch profile (or reuse the seeded
   deck), then **Export** → **Anki Deck Package (.apkg)** → name it
   `mcat-deck.apkg`.
5. **Host** the signed `.apk` and `mcat-deck.apkg` next to the desktop files.

> Android testers contribute only the **memory revlog** (returned as a
> `.colpkg`); performance mode is desktop-only, so the phone dashboard honestly
> abstains on Performance/Readiness. This is expected — call it out in the note
> to phone testers.

## 4. Clean-machine verification (before sending anything)

Do this on a **clean Windows VM** (no dev tools, no existing Anki) — it's the
single most important check:

- [ ] Run **`anki-26.05-win-x64.msi`** → installs without errors.
- [ ] Unzip **`MCAT-Speedrun.zip`**, double-click **`Start MCAT Speedrun.cmd`**.
- [ ] Anki opens on the **preseeded MCAT profile** (deck + dashboard present) —
      confirms the installed `Anki.exe` correctly forwards **`-b <base>`** to the
      bundled base folder. **This is the key thing that can silently break on a
      clean machine.**
- [ ] Dashboard shows all **three scores** honestly abstaining at 0 reviews
      (Memory "needs more reviews", Performance "needs attempts + an unlocked
      topic", Readiness "coverage < 50%").
- [ ] Do a few flashcard reviews → **"Export my data"** writes
      `MCAT-data_<label>_<date>.perf_bundle.json` to the Desktop and the
      confirmation dialog shows the path + "Open folder".
- [ ] (Recommended) screen-record this pass for the proof packet.

## 5. Pre-send verification list

- [ ] **Bundle freshly reseeded + verified empty** before zipping (§1): `revlog`,
      `reps>0`, `ivl>0`, `perf_attempts` all **0**; cards **66**, questions
      **62**. Never zip a base the app was launched against.
- [ ] Download links work from a **logged-out** browser / incognito (not just
      your own account).
- [ ] Both desktop files are hosted: `anki-26.05-win-x64.msi` **and**
      `MCAT-Speedrun.zip`.
- [ ] (If shipping Android) signed `.apk` + `mcat-deck.apkg` hosted, signature
      verified.
- [ ] `TESTER-QUICKSTART.md` (or its content) is available to testers.
- [ ] Cover message filled in with the real **download link** and **quickstart
      link** (template in `TESTER-QUICKSTART.md`).
- [ ] No secrets anywhere in what you're sending (no `.env`, no keystore, no
      keys). AI is off (no `MCAT_LLM_PROVIDER` / key bundled).
- [ ] You know how testers return data: desktop → one `.perf_bundle.json`;
      Android → one `.colpkg`. **One file per person, never merged.**

---

## Remaining human steps (distilled)

1. **Host the desktop downloads** (Drive or GitHub Release): the `.msi` +
   `MCAT-Speedrun.zip`.
2. **Android (if shipping):** generate the signing keystore, build & verify the
   signed release APK, export `mcat-deck.apkg`, host both.
3. **Verify on a clean Windows VM** that the installed launcher forwards `-b` and
   opens the preseeded profile (record it).
4. **Send** the cover message with real links.

Everything else (seeding the base, computing all three scores offline, the
one-click export, and the calibration/scoring harness that ingests returned
files) is already scripted and verified — see `TESTER-HANDOFF.md` and
`EVAL-DATA-RUNBOOK.md`.
