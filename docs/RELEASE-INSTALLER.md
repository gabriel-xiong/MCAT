# Release & installer runbook

Covers the two remaining Wednesday desktop items: **committing** the fork work
and producing an **installer that runs on a clean machine**. Nothing here was
committed or pushed overnight — that needs your explicit go-ahead.

## Repo state (as of 2026-06-30 overnight)

- `anki-MCAT` remote `origin` = `https://github.com/gabriel-xiong/anki-MCAT.git`
  (the fork is already on GitHub), branch `main`, `.version` = `26.05`.
- All MCAT work is **uncommitted** (modified + untracked files).
- A **local** installer build completed overnight
  (`./ninja installer:package`, exit 0, ~195s). The artifact is:
  **`anki-MCAT/out/installer/dist/anki-26.05-win-x64.msi`** (~636 MB). You can
  skip straight to testing it on a clean VM (Step 3, Option A).

## Step 1 — Commit the fork work

From `anki-MCAT/`. First confirm no secrets are staged:

```bash
git status
git add -A
git diff --cached --name-only        # sanity check — no .env / keys / creds
git commit -m "$(cat <<'EOF'
MCAT Speedrun: mastery query, performance mode, three-score dashboard

- rslib/src/mcat: per-topic mastery query (Rust) + protobuf service
- pylib: mcat_perf (sidecar DB + performance session), mcat_scores (3 scores)
- qt/aqt/mcat: performance + topic-mastery dialogs; dashboard on deck browser
- README: MCAT product statement + AGPL/upstream credit
EOF
)"
```

> Note `target-install/` and `tools/git-bash-temp.sh` are local build/scratch
> artifacts — consider adding them to `.gitignore` rather than committing.

Also commit the companion `MCAT/` repo (question bank, flashcards, docs).

## Step 2 — Push

```bash
git push origin main        # or a feature branch, then open a PR
```

Record the commit hash for the proof packet: `git rev-parse HEAD`.

## Step 3 — Installer

### Option A (preferred): local build — DONE overnight

The `.msi` already exists at
`anki-MCAT/out/installer/dist/anki-26.05-win-x64.msi`. To rebuild:

```bash
cd anki-MCAT
./ninja installer:package
ls out/installer/dist/      # -> anki-26.05-win-x64.msi
```

Copy the `.msi` to a clean Windows VM and run it. Screen-record the install +
first launch for the proof packet.

### Option B: GitHub Actions release build

The fork carries Anki's `.github/workflows/release.yml` (dispatch-triggered).
It builds `installer-windows` from `out/installer/dist/` on `windows-latest`.

```bash
# needs gh installed + authenticated (not installed on this machine yet)
gh workflow run release.yml -f version=26.05 -f skip-ci-check=true
# then download the artifact once the run finishes:
gh run download --name installer-windows
```

Or via the web UI: **Actions → Release → Run workflow**, set `version=26.05`,
leave `sign=false`, run; download the `installer-windows` artifact from the
finished run. (Signing needs the `release` environment secrets and is **not**
required for a clean-machine install demo.)

## Step 4 — Proof packet

- Commit hash (`git rev-parse HEAD`)
- Clean-build recording (`./run` or the installer build)
- Test output: `cargo test -p anki mcat` + the three `pylib/tests/test_mcat_*`
- Clean-machine install recording (from Option A or B)
- Phone review recording — already captured in `MCAT/assets/`

---

## Step 5 — Preseeded tester distribution (turnkey, ZERO import)

Goal: a friend installs and **immediately** has the MCAT deck + question bank +
scoring — **no deck import, no "Load question bank", no config**. See
[`TESTER-QUICKSTART.md`](TESTER-QUICKSTART.md) for the tester-facing steps (and
[`DISTRIBUTION-CHECKLIST.md`](DISTRIBUTION-CHECKLIST.md) for the builder ship-list).

### Mechanism — preseeded base, NOT a code bootstrap

We ship a **preseeded Anki base folder** and launch Anki against it with
`Anki.exe -b <base>`. This was chosen over a first-run auto-import code hook
because it touches **no application source** (nothing to break while the app is
mid-recording) and needs **no tester action**.

Why this is all that's needed:

- **Configs are already in the binary.** The eligibility gates (≥3 cards seen +
  ≥5 Good/Easy per topic; CARS = no memory gate), the three separate scores
  (memory / performance / readiness, never blended), Bayesian-shrinkage
  performance, FSRS memory, numeric readiness confidence, give-up thresholds and
  the outline/coverage denominator are compiled into
  `pylib/anki/mcat_scores.py` + `pylib/anki/mcat_perf.py`. There is **no config
  file to ship**.
- **Only per-user content needs seeding:** (a) the deck — notes with `topic:<id>`
  tags, and (b) the sidecar `collection.mcat_perf.db` (question bank +
  application-practice pool). Both are seeded headlessly.
- **AI is OFF by default** (`MCAT_LLM_PROVIDER` unset) and **no key is bundled**;
  the app still serves all three scores + the static per-question explanations
  offline. Nothing depends on the builder's LAN sync server — testers review
  locally and return data via the export bundle.

### Build the distribution (scripted)

Runs headlessly against the fork's own build venv — it **never** opens the live
`%APPDATA%/Anki2` profile (guarded; refuses to write there):

```bash
cd anki-MCAT
out/pyenv/Scripts/python.exe tools/mcat_seed_tester.py
# -> out/tester-dist/MCAT-Speedrun/
#      mcat-base/prefs21.db
#      mcat-base/User 1/collection.anki2         (deck: 158 topic-tagged notes)
#      mcat-base/User 1/collection.mcat_perf.db  (170 questions + 45 remediation)
#      Start MCAT Speedrun.cmd                    (double-click launcher)
#      READ ME FIRST.txt
```

Verified headlessly (fresh state, AI off): all three scores compute and
**honestly abstain** at 0 reviews (memory "needs ≥200", performance "needs ≥30
attempts + ≥1 unlocked topic", readiness "coverage < 50%"); 15 topic-mastery
rows; 170 questions loaded. Testers earn the performance unlock by reviewing.

### Package + ship

1. Zip `out/tester-dist/MCAT-Speedrun/` → `MCAT-Speedrun.zip` (small — the base
   is only the collection + sidecar; the app itself is the MSI).
2. Ship **two files**: the `.msi` (Step 3) and `MCAT-Speedrun.zip`.
3. Tester: run the MSI, unzip, double-click **`Start MCAT Speedrun.cmd`**.

### What is READY / SCRIPTED / needs a HUMAN

| State | Item |
|-------|------|
| **READY (assembled now)** | `anki-MCAT/out/tester-dist/MCAT-Speedrun/` (preseeded base + launcher + readme); the `.msi` at `anki-MCAT/out/installer/dist/anki-26.05-win-x64.msi`. |
| **SCRIPTED (one command)** | `tools/mcat_seed_tester.py` rebuilds the base from `MCAT/data/*` any time the deck/bank changes. |
| **HUMAN** | Zip + **host the download** (Drive/GitHub Release); verify on a clean Windows VM that the installed `Anki.exe` forwards `-b` and opens the preseeded profile (record it — same clean-VM pass as Step 3). Code-signing the `.msi` is optional and not required for install. |

### Android (see the mobile repo)

The Android fork has **no asset auto-import**, so a true preseeded APK would need
new Kotlin (a film-blocker). The simplest import-free path today is a **signed
APK + a hosted `mcat-deck.apkg`** the tester taps to import (existing intent
filters). Sign per `anki-android-MCAT/docs/RELEASE-SIGNING-RUNBOOK.md` (human:
generate keystore, set `KEYSTOREPATH`/`KEYSTOREPWD`/`KEYALIAS`/`KEYPWD`, build
`:AnkiDroid:assembleFullRelease -Duniversal-apk=true`, host the APK + apkg).
Export the `.apkg` from desktop Anki after importing `data/flashcards-dev*.csv`.
Android testers contribute the **memory revlog** (returned as a `.colpkg`);
performance mode is desktop-only, so the phone dashboard honestly abstains on
Performance/Readiness.
