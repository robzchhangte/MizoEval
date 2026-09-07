"""A rotating pool of API keys.

Ollama Cloud's free tier is rate-limited per key. The project holds a file of
keys (`keys.txt`, one per line, git-ignored); this pool hands out the current
key and rotates to the next when a key reports itself exhausted, so a long run
can span more quota than any single key allows.

Keys are never logged. A rotation logs the *reason* and the key's index, not
its value.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_KEYS_FILE = ROOT / "keys.txt"


class AllKeysExhausted(RuntimeError):
    """Every key in the pool is cooling down; the caller should stop or wait."""


@dataclass
class _KeyState:
    index: int
    cooling_until: float = 0.0   # epoch seconds; 0 = available
    rotations: int = 0
    last_reason: str = ""


@dataclass
class KeyPool:
    keys: list[str]
    cooldown_s: float = 900.0    # how long a key rests after reporting exhaustion
    _pos: int = 0
    _state: dict[int, _KeyState] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def __post_init__(self) -> None:
        if not self.keys:
            raise ValueError("KeyPool needs at least one key")
        self._state = {i: _KeyState(index=i) for i in range(len(self.keys))}

    # ------------------------------------------------------------------ construction

    @classmethod
    def from_file(cls, path: Path | str = DEFAULT_KEYS_FILE, **kw) -> "KeyPool":
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(
                f"key file {p} not found; create it with one API key per line"
            )
        keys = [
            ln.strip()
            for ln in p.read_text(encoding="utf-8").splitlines()
            if ln.strip() and not ln.lstrip().startswith("#")
        ]
        if not keys:
            raise ValueError(f"{p} contains no keys")
        return cls(keys=keys, **kw)

    # ------------------------------------------------------------------ use

    def current(self) -> str:
        """The active key. Skips cooling keys; raises if all are cooling."""
        with self._lock:
            return self.keys[self._current_available_index()]

    def current_index(self) -> int:
        with self._lock:
            return self._current_available_index()

    def _current_available_index(self) -> int:
        now = time.time()
        n = len(self.keys)
        for step in range(n):
            i = (self._pos + step) % n
            if self._state[i].cooling_until <= now:
                self._pos = i
                return i
        # All cooling: report when the earliest one frees up.
        soonest = min(s.cooling_until for s in self._state.values())
        raise AllKeysExhausted(
            f"all {n} keys cooling; earliest frees in {soonest - now:.0f}s"
        )

    def rotate(self, reason: str) -> int:
        """Cool the current key and advance the pointer. Returns the new position.

        Does not itself raise when every key is now cooling -- that surfaces on
        the next `current()` call, so a caller that only rotates (without
        immediately reading) does not have to catch here. `reason` is a short
        string ("http 429", "quota") kept for the run log.
        """
        with self._lock:
            cur = self._pos
            st = self._state[cur]
            st.cooling_until = time.time() + self.cooldown_s
            st.rotations += 1
            st.last_reason = reason
            self._pos = (cur + 1) % len(self.keys)
            return self._pos

    # ------------------------------------------------------------------ reporting

    def status(self) -> dict[str, object]:
        now = time.time()
        with self._lock:
            return {
                "n_keys": len(self.keys),
                "active_index": self._pos,
                "cooling": [
                    {"index": i, "frees_in_s": round(s.cooling_until - now),
                     "reason": s.last_reason}
                    for i, s in self._state.items()
                    if s.cooling_until > now
                ],
                "total_rotations": sum(s.rotations for s in self._state.values()),
            }
