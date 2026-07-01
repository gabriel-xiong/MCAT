# Development environment setup

Last verified: 2026-06-30

## Installed / configured

| Tool | Status | Version / notes |
|------|--------|-----------------|
| **Git** | Already installed | 2.54.0.windows.1 |
| **Rust** | Installed + fixed | 1.96.1 via rustup |
| **Rust toolchain (Anki)** | Configured | `stable-x86_64-pc-windows-msvc` (default) |
| **Python** | Installed for Anki | **3.12.10** (`py -3.12`) — use this for Anki builds |
| **Python 3.14** | Also present | Default `python` — too new for Anki; avoid for build |
| **MSYS2 rsync** | Installed | `pacman -S rsync`; add `C:\msys64\usr\bin` to PATH (in `~/.bashrc`) |
| **Disk (C:)** | OK | ~624 GB free |

## Shell configuration (`~/.bashrc`)

Added:

```bash
export PATH="$HOME/.cargo/bin:$PATH"
export PY_PYTHON=3.12
```

**Open a new terminal** (or `source ~/.bashrc`) before building Anki.

## Verify in a new terminal

```bash
git --version
rustc --version    # should show 1.96.x msvc
cargo --version
py -3.12 --version # Python 3.12.10
node --version
```

| **Visual Studio 2022 Build Tools (C++)** | Installed | v17.14.35 via winget |

**Note:** `cl.exe` is not on a normal Git Bash PATH. Anki’s `./tools/build` usually finds MSVC automatically; if not, use **“x64 Native Tools Command Prompt for VS 2022”** or run the build from a fresh terminal after reboot.

## Not in the original list but needed later

- **Qt** — Anki build pulls this via `./tools/build` (see `anki/docs/build.md` after clone)
- **Anki repo clone** — next step: sibling folder `../anki`

## Anki build defaults (after clone)

```bash
cd ../anki
py -3.12 --version   # confirm before build
./tools/build        # first run: 30–90+ min
```

If native Windows build fails, use **WSL2 Ubuntu** and clone Anki inside WSL (often easier).
