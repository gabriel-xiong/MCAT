#!/usr/bin/env bash
# One-shot Anki build environment fix + first run (Git Bash on Windows)
# Usage: bash scripts/setup-anki-build.sh

set -euo pipefail

ANKI_DIR="${ANKI_DIR:-$HOME/Downloads/alphaProjects/anki-MCAT}"
BASHRC="$HOME/.bashrc"

append_bashrc() {
  local line="$1"
  if ! grep -Fq "$line" "$BASHRC" 2>/dev/null; then
    echo "$line" >> "$BASHRC"
    echo "Added to ~/.bashrc: $line"
  fi
}

echo "==> Configuring shell (session + ~/.bashrc)"
append_bashrc 'export PATH="$HOME/.cargo/bin:$PATH"'
append_bashrc 'export PATH="/c/msys64/usr/bin:$PATH"'
append_bashrc 'export MSYS2_ENV_CONV_EXCL="${MSYS2_ENV_CONV_EXCL:+$MSYS2_ENV_CONV_EXCL; }TMP;TEMP;TMPDIR"'
append_bashrc 'export TMP="$(cygpath -w "$LOCALAPPDATA/Temp")"'
append_bashrc 'export TEMP="$TMP"'
append_bashrc 'export TMPDIR="$TMP"'
append_bashrc 'export PY_PYTHON=3.12'

export PATH="$HOME/.cargo/bin:/c/msys64/usr/bin:$PATH"
export MSYS2_ENV_CONV_EXCL="${MSYS2_ENV_CONV_EXCL:+$MSYS2_ENV_CONV_EXCL; }TMP;TEMP;TMPDIR"
export TMP="$(cygpath -w "$LOCALAPPDATA/Temp")"
export TEMP="$TMP"
export TMPDIR="$TMP"
export PY_PYTHON=3.12
export CARGO_TARGET_DIR="$ANKI_DIR/target-install"

echo "==> Checking prerequisites"
command -v git >/dev/null || { echo "ERROR: git not found"; exit 1; }
command -v rsync >/dev/null || { echo "ERROR: rsync not found — run: /c/msys64/usr/bin/pacman.exe -S rsync"; exit 1; }
command -v py >/dev/null || command -v python >/dev/null || { echo "ERROR: Python not found"; exit 1; }

if command -v py >/dev/null; then
  py -3.12 --version
else
  python --version
fi

echo "==> Installing Anki-pinned Rust (1.92.0 MSVC)"
rustup toolchain install 1.92.0-x86_64-pc-windows-msvc

if [[ ! -d "$ANKI_DIR" ]]; then
  echo "ERROR: Anki repo not found at $ANKI_DIR"
  echo "Set ANKI_DIR or clone: git clone https://github.com/gabriel-xiong/anki-MCAT.git"
  exit 1
fi

cd "$ANKI_DIR"
rustup override set 1.92.0-x86_64-pc-windows-msvc

echo "==> Toolchain check"
rustc --version
cargo --version
which rsync

echo "==> Installing n2 build runner"
bash tools/install-n2

echo "==> Starting Anki build + run (first time: 30-90+ min)"
./run
