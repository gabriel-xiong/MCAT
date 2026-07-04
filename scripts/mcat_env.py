"""Load optional MCAT Speedrun settings from a gitignored local ``.env``.

Keys are merged into ``os.environ`` only when not already set (shell exports
win). Values are never logged. Safe to import from Anki or CLI scripts.
"""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_LOADED = False


def mcat_root() -> Path:
    override = (os.environ.get("MCAT_ROOT") or "").strip()
    if override:
        return Path(override).expanduser().resolve()
    return ROOT


def load_dotenv_file(path: Path, env: dict[str, str] | None = None) -> None:
    """Parse ``KEY=VALUE`` lines into *env* without overwriting existing keys."""
    target = os.environ if env is None else env
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        if not key or key in target:
            continue
        val = val.strip()
        if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
            val = val[1:-1]
        # Ignore empty or template-placeholder values so a leftover
        # ``KEY=REPLACE_WITH_YOUR_KEY`` line can't shadow a real value set
        # on a later line (this loader is first-occurrence-wins).
        if not val or "REPLACE_WITH" in val:
            continue
        target[key] = val


def ensure_mcat_env_loaded() -> Path:
    """Load ``MCAT_ROOT/.env`` once. Returns the resolved MCAT root."""
    global _LOADED
    root = mcat_root()
    if not _LOADED:
        load_dotenv_file(root / ".env")
        _LOADED = True
    return root
