"""SQLite response cache.

Model calls are the only part of this pipeline that costs money, so they are
cached permanently and keyed on the full request. This makes runs resumable
after an interruption, makes re-analysis free, and makes a repeated run
byte-identical -- which is what lets the paper claim reproducibility rather
than merely asserting it.

The cache is deliberately not invalidated by time. A pinned model version
returning a different answer later is a finding, not a cache bug; use
`--no-cache` to check for it.
"""

from __future__ import annotations

import json
import sqlite3
import threading
from contextlib import closing
from pathlib import Path
from typing import Any

from mizoeval.models.base import Message, Response, request_key

DEFAULT_PATH = Path(__file__).resolve().parents[3] / "results" / "cache.sqlite"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS responses (
    key             TEXT PRIMARY KEY,
    model           TEXT NOT NULL,
    provider        TEXT NOT NULL,
    text            TEXT NOT NULL,
    prompt_tokens   INTEGER DEFAULT 0,
    completion_tokens INTEGER DEFAULT 0,
    finish_reason   TEXT,
    latency_s       REAL DEFAULT 0,
    error           TEXT,
    params          TEXT,
    created_at      TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_responses_model ON responses(model);
"""


class ResponseCache:
    def __init__(self, path: Path | str | None = None) -> None:
        # Resolved at call time, not bound as a default, so tests can redirect
        # the cache by patching DEFAULT_PATH.
        self.path = Path(path) if path is not None else DEFAULT_PATH
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        with closing(self._connect()) as conn:
            conn.executescript(_SCHEMA)
            conn.commit()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=30)
        conn.row_factory = sqlite3.Row
        return conn

    def get(self, model: str, messages: list[Message], params: dict[str, Any]) -> Response | None:
        key = request_key(model, messages, params)
        with self._lock, closing(self._connect()) as conn:
            row = conn.execute("SELECT * FROM responses WHERE key = ?", (key,)).fetchone()
        if row is None:
            return None
        return Response(
            text=row["text"],
            model=row["model"],
            provider=row["provider"],
            prompt_tokens=row["prompt_tokens"],
            completion_tokens=row["completion_tokens"],
            finish_reason=row["finish_reason"],
            latency_s=row["latency_s"],
            cached=True,
            error=row["error"],
        )

    def put(
        self, model: str, messages: list[Message], params: dict[str, Any], resp: Response
    ) -> None:
        # Failures are not cached: a rate limit or a transport error must not
        # become a permanent answer that silently poisons every later run.
        if resp.error is not None:
            return
        key = request_key(model, messages, params)
        with self._lock, closing(self._connect()) as conn:
            conn.execute(
                """INSERT OR REPLACE INTO responses
                   (key, model, provider, text, prompt_tokens, completion_tokens,
                    finish_reason, latency_s, error, params)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (
                    key, resp.model, resp.provider, resp.text, resp.prompt_tokens,
                    resp.completion_tokens, resp.finish_reason, resp.latency_s,
                    resp.error, json.dumps(params, sort_keys=True),
                ),
            )
            conn.commit()

    def stats(self) -> dict[str, Any]:
        with closing(self._connect()) as conn:
            total = conn.execute("SELECT COUNT(*) AS n FROM responses").fetchone()["n"]
            by_model = {
                r["model"]: r["n"]
                for r in conn.execute(
                    "SELECT model, COUNT(*) AS n FROM responses GROUP BY model ORDER BY n DESC"
                )
            }
            tokens = conn.execute(
                "SELECT SUM(prompt_tokens) AS p, SUM(completion_tokens) AS c FROM responses"
            ).fetchone()
        return {
            "entries": total,
            "by_model": by_model,
            "prompt_tokens": tokens["p"] or 0,
            "completion_tokens": tokens["c"] or 0,
        }
