"""Counts of checks by verdict and source. No chat text, file name or score is ever stored."""

import logging
import sqlite3
import threading
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, Optional

from .schemas import Origin, Source, Verdict

log = logging.getLogger("scamguard")

SetOriginResult = Literal["ok", "missing", "not_allowed"]
CountRow = tuple[str, str, Optional[str], int]

CREATE = """
CREATE TABLE IF NOT EXISTS checks (
    id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    verdict TEXT NOT NULL,
    input_format TEXT NOT NULL,
    origin TEXT
)
"""


class StatsStore(ABC):
    """The queries are shared. Subclasses only say how to run SQL on their database."""

    placeholder = "?"

    def __init__(self):
        self._ready = False
        try:
            self._ensure_table()
        except Exception as exc:
            # The checker keeps working without counts; the table is created on the next write.
            log.error("stats store unavailable: %s", type(exc).__name__)

    @abstractmethod
    def _execute(self, sql: str, params: tuple, fetch: bool):
        """Run one statement. Returns the rows when fetch is true, else the number of rows changed."""

    def _ensure_table(self) -> None:
        if not self._ready:
            self._execute(CREATE, (), False)
            self._ready = True

    def _run(self, sql: str, params: tuple = (), fetch: bool = False):
        self._ensure_table()
        return self._execute(sql.replace("?", self.placeholder), params, fetch)

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

    def counts(self) -> list[CountRow]:
        """Rows of (verdict, input_format, origin, count)."""
        rows = self._run(
            "SELECT verdict, input_format, origin, COUNT(*) FROM checks GROUP BY verdict, input_format, origin",
            fetch=True,
        )
        return [(v, f, o, int(n)) for v, f, o, n in rows]


class SqliteStatsStore(StatsStore):
    """One shared connection behind a lock. ":memory:" works for tests."""

    def __init__(self, path: str):
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._lock = threading.Lock()
        super().__init__()

    def _execute(self, sql: str, params: tuple, fetch: bool):
        with self._lock:
            cur = self._conn.execute(sql, params)
            self._conn.commit()
            return cur.fetchall() if fetch else cur.rowcount


class PostgresStatsStore(StatsStore):
    """A short connection per statement, so idle connections closed by the host do not matter."""

    placeholder = "%s"

    def __init__(self, url: str):
        self._url = url
        super().__init__()

    def _execute(self, sql: str, params: tuple, fetch: bool):
        import psycopg

        with psycopg.connect(self._url, autocommit=True, connect_timeout=5) as conn:
            cur = conn.execute(sql, params)
            return cur.fetchall() if fetch else cur.rowcount


def open_store(url: str) -> StatsStore:
    if url.startswith(("postgres://", "postgresql://")):
        return PostgresStatsStore(url)
    if url.startswith("sqlite:///"):
        return SqliteStatsStore(url.removeprefix("sqlite:///"))
    raise ValueError("DATABASE_URL must start with postgresql:// or sqlite:///")
