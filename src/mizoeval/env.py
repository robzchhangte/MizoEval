"""Minimal .env loader.

Reads `KEY=VALUE` lines from a `.env` file at the repo root and sets any that
are not already in the environment (so an explicit shell export always wins).
No dependency on python-dotenv, and it never prints values.
"""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ENV = ROOT / ".env"


def load_env(path: Path | str = DEFAULT_ENV, override: bool = False) -> list[str]:
    p = Path(path)
    if not p.exists():
        return []
    loaded: list[str] = []
    for raw in p.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key, val = key.strip(), val.strip().strip('"').strip("'")
        if override or key not in os.environ:
            os.environ[key] = val
            loaded.append(key)
    return loaded
