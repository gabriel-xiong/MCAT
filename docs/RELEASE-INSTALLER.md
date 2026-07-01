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
