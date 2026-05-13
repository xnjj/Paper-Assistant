from __future__ import annotations

import json
from datetime import datetime

from app_backend.db.connection import DatabaseManager


class ConfigRepository:
    """应用配置仓储。

    配置写入数据库，避免直接修改 Python 源文件。
    """

    def __init__(self, db_manager: DatabaseManager) -> None:
        self.db_manager = db_manager

    def set_value(self, key: str, value: str) -> None:
        """写入一个配置键值。"""
        now = datetime.now().isoformat(timespec="seconds")
        value_json = json.dumps({"value": value}, ensure_ascii=False)
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

    def get_value(self, key: str) -> str | None:
        """读取一个配置键值，不存在则返回 None。"""
        with self.db_manager.get_connection() as connection:
            row = connection.execute("SELECT value_json FROM app_config WHERE key = ?", (key,)).fetchone()
            if row is None:
                return None
            return json.loads(row["value_json"]).get("value")
