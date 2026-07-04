# Clean-install proof (desktop installer + mobile sideload)

_Artifact 2 of the MVP-evidence push (reviewer next-focus #2). Last updated
2026-07-03._

> **Reviewer ask:** "Clean install proof." Prove the packaged desktop installer
> and the sideloaded APK install and run on clean devices.

## Summary

| Path | Status | Evidence |
|------|--------|----------|
| **Mobile** sideload (APK → device with no prior data) | **PROVEN (automated)** | `adb uninstall` → confirmed gone → fresh `adb install` succeeds → app launches to the **first-run** screen (proves no prior data) → process alive → screenshot |
| **Desktop** installer artifact exists + is a valid MSI | **PROVEN** | `anki-26.05-win-x64.msi` present, valid OLE/MSI package, 636 MB, sha256 pinned |
| **Desktop** install on a *pristine Windows VM* | **HUMAN STEP** | Cannot drive a separate clean Windows VM from this environment; runbook + on-camera checklist below |

---

## A. Mobile clean-install — PROVEN on the emulator

Device: AVD `mcat_avd` (android-35, **x86_64**), booted. APK: freshly built
`AnkiDroid-full-x86_64-debug.apk` (commit `d9dc9b6`).

**Artifact identity + signature** (Android SDK build-tools):
```
package     : com.ichi2.anki.debug
versionName : 2.25.0alpha1-debug   versionCode 22500101
minSdk 24   targetSdk 35
signer #1   : CN=Android Debug, O=Android, C=US
  SHA-256   : 1708b74ce428d01ffd45189848748fb7c67625ed8143bdc03ea1acf79b89f9d2
apk sha256  : d510e53bca637aff573b02485e28f0bd0d77d4a0a8628da49c6718a168e15068  (x86_64)
```

**Clean install run** (`anki-android-MCAT/tools/clean_install_emulator.sh`):
```
== 1. uninstall (make device clean of the app) ==
Success
packages matching after uninstall: 0   (device is now clean of the app)
== 2. clean install (timed) ==
Performing Streamed Install
Success
install_ms ≈ 2300–10200   (streamed install of the ~82 MB APK; varies with emulator load)
== 3. confirm + launch ==
package:com.ichi2.anki.debug
versionName=2.25.0alpha1-debug
top activity: com.ichi2.anki.debug/com.ichi2.anki.IntroductionActivity   (first-run onboarding)
pid: <non-empty>   (running, not crashed)
```

The app cold-launches to **`IntroductionActivity`** ("Study less / Remember
more" onboarding) — the screen shown only when there is **no existing
collection/data**, which is exactly what a clean install must show. Screenshot:
`anki-android-MCAT/docs/artifacts/clean_install_launch.png`.

> ⚠️ Side effect (owned honestly): this proof **uninstalled** the emulator's
> existing AnkiDroid, which wipes on-device app data (any demo collection).
> Re-import the deck via the mobile-track import steps if you need it back. (The
> phone-review **video clip** is **still pending capture** — not yet in the repo;
> see `RECORDING-CHECKLIST.md` item **R4**. Still screenshots of the mobile
> import/review flow are saved under `MCAT/assets/`.)

**Reproduce:**
```bash
export PATH="$ANDROID_HOME/platform-tools:$PATH"
cd anki-android-MCAT
bash tools/clean_install_emulator.sh emulator-5554 x86_64
```
For a *truly* pristine device, first `emulator -avd mcat_avd -wipe-data` (fresh
system image) and then run the same script — the install/launch assertions are
identical.

---

## B. Desktop installer — artifact verified; clean-VM run is the human step

The packaged Windows installer built by `./ninja installer:package` exists:
```
path   : anki-MCAT/out/installer/dist/anki-26.05-win-x64.msi
size   : 636,551,586 bytes (~636 MB)
type   : valid Windows Installer (OLE compound, magic d0 cf 11 e0)
sha256 : 4c7924f10f776774ca5ab7038def67949e76f9e8e3be24841378486bec7df124
```

`msiexec`/actually installing on a *separate clean Windows VM* cannot be
performed from this build machine (no nested VM available, and installing on the
build box itself is not a "clean machine" test). That is the remaining **human
recording step**.

### Clean-Windows-VM checklist (on-camera)
1. Show a clean Windows VM: Start-menu search "Anki" → empty; no Rust/Python.
2. Copy `anki-26.05-win-x64.msi` to the VM (optionally verify the sha256 above).
3. Double-click → step through the installer to completion.
4. Launch Anki → **Help → About** shows **Anki 26.05**.
5. Show **Tools → MCAT: …** actions (Performance session, Topic mastery, Load
   question bank, Export/Reset performance data) — proves the fork's features are
   in the installed binary.
6. Say the caveat on camera: this `.msi` predates the latest UI (built
   2026-06-30); it exists to prove a clean install works end-to-end, while the
   from-source recording shows the current v2 flow. (See
   `docs/RECORDING-RUNBOOK.md §B` and `docs/RELEASE-INSTALLER.md`.)

### Rebuild the installer (if needed)
```bash
cd anki-MCAT
./ninja installer:package
ls out/installer/dist/     # -> anki-26.05-win-x64.msi
```

---

## What is fully proven vs. needs a human

- **Fully proven (automated, reproducible):** the mobile APK installs cleanly on
  a device with no prior data and launches to the first-run screen; the desktop
  `.msi` exists and is a valid installer package with a pinned hash.
- **Needs a human:** (1) recording the `.msi` installing + launching on a
  pristine Windows VM; (2) optionally, the same mobile flow on a `-wipe-data`
  emulator or a physical phone, on camera.
