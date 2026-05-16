from __future__ import annotations

import json
from datetime import datetime

from app_backend.db.connection import DatabaseManager


class ConfigRepository:
    """Persistence helper for app-level configuration entries."""

    def __init__(self, db_manager: DatabaseManager) -> None:
        self.db_manager = db_manager

    def set_value(self, key: str, value: str) -> None:
        """Persist one simple string value under a config key."""
        self.set_json_value(key, {"value": value})

    def set_json_value(self, key: str, value: object) -> None:
        """Persist one JSON-serializable value under a config key."""
        now = datetime.now().isoformat(timespec="seconds")
        value_json = json.dumps(value, ensure_ascii=False)
        with self.db_manager.get_connection() as connection:
            connection.execute(
                """
                INSERT INTO app_config(key, value_json, updated_at)
                VALUES(?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value_json=excluded.value_json,
                    updated_at=excluded.updated_at
                """,
                (key, value_json, now),
            )

    def set_many_json_values(self, values: dict[str, object]) -> None:
        """Persist multiple JSON values in one transaction."""
        if not values:
            return

        now = datetime.now().isoformat(timespec="seconds")
        with self.db_manager.get_connection() as connection:
            for key, value in values.items():
                connection.execute(
                    """
                    INSERT INTO app_config(key, value_json, updated_at)
                    VALUES(?, ?, ?)
                    ON CONFLICT(key) DO UPDATE SET
                        value_json=excluded.value_json,
                        updated_at=excluded.updated_at
                    """,
                    (key, json.dumps(value, ensure_ascii=False), now),
                )

    def get_value(self, key: str) -> str | None:
        """Load one simple string value by key."""
        payload = self.get_json_value(key)
        if isinstance(payload, dict):
            value = payload.get("value")
            return str(value) if value is not None else None
        return None

    def get_json_value(self, key: str) -> object | None:
        """Load one raw JSON payload by key."""
        with self.db_manager.get_connection() as connection:
            row = connection.execute("SELECT value_json FROM app_config WHERE key = ?", (key,)).fetchone()
            if row is None:
                return None
            return json.loads(row["value_json"])

    def get_many_json_values(self, keys: list[str]) -> dict[str, object]:
        """Load multiple raw JSON payloads by exact key."""
        if not keys:
            return {}

        placeholders = ", ".join("?" for _ in keys)
        with self.db_manager.get_connection() as connection:
            rows = connection.execute(
                f"SELECT key, value_json FROM app_config WHERE key IN ({placeholders})",
                keys,
            ).fetchall()
        return {str(row["key"]): json.loads(row["value_json"]) for row in rows}
