from __future__ import annotations

import json
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any


class SessionMemory:
    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=15)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        return conn

    def _init_db(self) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    history_json TEXT NOT NULL,
                    last_image_prompt TEXT NOT NULL DEFAULT '',
                    last_image_attachment_id TEXT NOT NULL DEFAULT '',
                    updated_at INTEGER NOT NULL
                )
                """
            )
            columns = {row[1] for row in conn.execute("PRAGMA table_info(sessions)").fetchall()}
            if "last_image_attachment_id" not in columns:
                conn.execute(
                    "ALTER TABLE sessions ADD COLUMN last_image_attachment_id TEXT NOT NULL DEFAULT ''"
                )

    def load(self, session_id: str) -> dict[str, Any] | None:
        with self._lock, self._connect() as conn:
            row = conn.execute(
                "SELECT history_json, last_image_prompt, last_image_attachment_id, updated_at FROM sessions WHERE session_id = ?",
                (session_id,),
            ).fetchone()
        if not row:
            return None
        try:
            history = json.loads(row[0])
        except json.JSONDecodeError:
            return None
        if not isinstance(history, list):
            return None
        return {
            "history": history,
            "last_image_prompt": row[1] or "",
            "last_image_attachment_id": row[2] or "",
            "updated_at": int(row[3]),
        }

    def save(
        self,
        session_id: str,
        history: list[dict[str, Any]],
        last_image_prompt: str = "",
        last_image_attachment_id: str = "",
    ) -> None:
        payload = json.dumps(history, ensure_ascii=False, separators=(",", ":"))
        now = int(time.time())
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO sessions(
                    session_id, history_json, last_image_prompt, last_image_attachment_id, updated_at
                )
                VALUES(?, ?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    history_json=excluded.history_json,
                    last_image_prompt=excluded.last_image_prompt,
                    last_image_attachment_id=excluded.last_image_attachment_id,
                    updated_at=excluded.updated_at
                """,
                (session_id, payload, last_image_prompt, last_image_attachment_id, now),
            )

    def delete(self, session_id: str) -> bool:
        with self._lock, self._connect() as conn:
            cur = conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
            return cur.rowcount > 0

    def list_recent(self, limit: int = 20) -> list[dict[str, Any]]:
        limit = max(1, min(int(limit), 100))
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                "SELECT session_id, updated_at FROM sessions ORDER BY updated_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [{"session_id": sid, "updated_at": int(updated)} for sid, updated in rows]
