"""SQLite-backed attribution store."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Iterator

from .models import Attribution, AttributionLabel


SCHEMA = """
CREATE TABLE IF NOT EXISTS attributions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file TEXT NOT NULL,
    start_line INTEGER NOT NULL,
    end_line INTEGER NOT NULL,
    label TEXT NOT NULL,
    confidence REAL NOT NULL,
    timestamp TEXT NOT NULL,
    source_hint TEXT,
    metadata TEXT DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_attributions_file ON attributions(file);
CREATE INDEX IF NOT EXISTS idx_attributions_timestamp ON attributions(timestamp);
"""


class Store:
    """Persistent attribution store using SQLite."""

    def __init__(self, db_path: Path | None = None):
        if db_path is None:
            db_path = Path.home() / ".codedna" / "attributions.db"
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with self._conn() as conn:
            conn.executescript(SCHEMA)

    @contextmanager
    def _conn(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def add(self, attr: Attribution) -> int:
        with self._conn() as conn:
            cur = conn.execute(
                """
                INSERT INTO attributions (file, start_line, end_line, label, confidence, timestamp, source_hint, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(attr.file),
                    attr.start_line,
                    attr.end_line,
                    attr.label.value,
                    attr.confidence,
                    attr.timestamp.isoformat(),
                    attr.source_hint,
                    attr.metadata,
                ),
            )
            return cur.lastrowid

    def add_batch(self, attrs: list[Attribution]) -> list[int]:
        with self._conn() as conn:
            cur = conn.executemany(
                """
                INSERT INTO attributions (file, start_line, end_line, label, confidence, timestamp, source_hint, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        str(a.file),
                        a.start_line,
                        a.end_line,
                        a.label.value,
                        a.confidence,
                        a.timestamp.isoformat(),
                        a.source_hint,
                        a.metadata,
                    )
                    for a in attrs
                ],
            )
            # SQLite doesn't return all lastrowids for executemany, so we fetch them
            first_id = cur.lastrowid
            return list(range(first_id - len(attrs) + 1, first_id + 1))

    def get_for_file(self, file: Path) -> list[Attribution]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM attributions WHERE file = ? ORDER BY start_line",
                (str(file),),
            ).fetchall()
            return [self._row_to_attr(row) for row in rows]

    def get_all(self) -> list[Attribution]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM attributions ORDER BY timestamp"
            ).fetchall()
            return [self._row_to_attr(row) for row in rows]

    def get_ratio(self, file: Path | None = None) -> tuple[int, int]:
        """Return (human_lines, ai_lines) for a file or globally."""
        with self._conn() as conn:
            if file:
                rows = conn.execute(
                    "SELECT label, start_line, end_line FROM attributions WHERE file = ?",
                    (str(file),),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT label, start_line, end_line FROM attributions"
                ).fetchall()

            human = 0
            ai = 0
            for row in rows:
                lines = row["end_line"] - row["start_line"] + 1
                label = AttributionLabel(row["label"])
                if label == AttributionLabel.HUMAN:
                    human += lines
                else:
                    ai += lines
            return (human, ai)

    def clear(self) -> None:
        with self._conn() as conn:
            conn.execute("DELETE FROM attributions")

    def _row_to_attr(self, row: sqlite3.Row) -> Attribution:
        import json
        return Attribution(
            file=Path(row["file"]),
            start_line=row["start_line"],
            end_line=row["end_line"],
            label=AttributionLabel(row["label"]),
            confidence=row["confidence"],
            timestamp=datetime.fromisoformat(row["timestamp"]),
            source_hint=row["source_hint"],
            metadata=json.loads(row["metadata"]) if row["metadata"] else {},
        )
