"""Counts of checks by verdict and source. No chat text, file name or score is ever stored."""

import logging
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, Optional

from .schemas import Origin, Source, Verdict

log = logging.getLogger("scamguard")

SetOriginResult = Literal["ok", "missing", "not_allowed"]

CREATE = """
CREATE TABLE IF NOT EXISTS checks (
    id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    verdict TEXT NOT NULL,
    input_format TEXT NOT NULL,
    origin TEXT
)
"""


class StatsStore:
    def __init__(self, url: str):
        self.postgres = url.startswith(("postgres://", "postgresql://"))
        self.url = url
        self.mark = "%s" if self.postgres else "?"
        self._lock = threading.Lock()
        self._sqlite: Optional[sqlite3.Connection] = None
        self._ready = False
        if not self.postgres:
            path = url.removeprefix("sqlite:///")
            if path != ":memory:":
                Path(path).parent.mkdir(parents=True, exist_ok=True)
            self._sqlite = sqlite3.connect(path, check_same_thread=False)
        try:
            self._run(CREATE)
        except Exception as exc:
            # The checker keeps working without counts; the table is created on the next write.
            log.error("stats store unavailable: %s", type(exc).__name__)

    def _run(self, sql: str, params: tuple = (), fetch: bool = False):
        sql = sql.replace("?", self.mark)
        if self.postgres:
            import psycopg

            with psycopg.connect(self.url, autocommit=True, connect_timeout=5) as conn:
                if not self._ready:
                    conn.execute(CREATE)
                cur = conn.execute(sql, params)
                self._ready = True
                return cur.fetchall() if fetch else cur.rowcount
        with self._lock:
            if not self._ready:
                self._sqlite.execute(CREATE)
            cur = self._sqlite.execute(sql, params)
            self._sqlite.commit()
            self._ready = True
            return cur.fetchall() if fetch else cur.rowcount

    def record(self, verdict: Verdict, input_format: Source) -> str:
        record_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        self._run(
            "INSERT INTO checks (id, created_at, verdict, input_format) VALUES (?, ?, ?, ?)",
            (record_id, now, verdict, input_format),
        )
        return record_id

    def set_origin(self, record_id: str, origin: Origin) -> SetOriginResult:
        updated = self._run(
            "UPDATE checks SET origin = ? WHERE id = ? AND verdict = 'scam' AND origin IS NULL",
            (origin, record_id),
        )
        if updated:
            return "ok"
        exists = self._run("SELECT 1 FROM checks WHERE id = ?", (record_id,), fetch=True)
        return "not_allowed" if exists else "missing"

    def counts(self) -> list[tuple[str, str, Optional[str], int]]:
        """Rows of (verdict, input_format, origin, count)."""
        rows = self._run(
            "SELECT verdict, input_format, origin, COUNT(*) FROM checks GROUP BY verdict, input_format, origin",
            fetch=True,
        )
        return [(v, f, o, int(n)) for v, f, o, n in rows]
