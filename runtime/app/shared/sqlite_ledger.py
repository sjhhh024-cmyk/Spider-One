from __future__ import annotations

import json
import sqlite3
from datetime import datetime, UTC
from pathlib import Path
from typing import Any

from runtime.app.shared.task_models import CrawlTask
from runtime.app.shared.task_status import TaskStatus, ensure_transition
from runtime.app.shared.task_types import TaskType


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


class SQLiteTaskLedger:
    def __init__(self, db_path: Path) -> None:
        self._db_path = Path(db_path)

    def initialize(self) -> None:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        schema_path = Path(__file__).with_name("sqlite_schema.sql")
        schema_sql = schema_path.read_text(encoding="utf-8")

        with self._connect() as connection:
            connection.executescript(schema_sql)

    def create_job(
        self,
        *,
        job_id: str,
        project_code: str,
        site_code: str,
        entity_type: str,
        request_text: str,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO crawl_job (
                    job_id,
                    project_code,
                    site_code,
                    entity_type,
                    request_text,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    job_id,
                    project_code,
                    site_code,
                    entity_type,
                    request_text,
                    utc_now_iso(),
                ),
            )

    def create_task(self, task: CrawlTask) -> None:
        timestamp = utc_now_iso()

        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO crawl_task (
                    task_id,
                    job_id,
                    parent_task_id,
                    project_code,
                    site_code,
                    task_type,
                    status,
                    payload_json,
                    created_at,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task.task_id,
                    task.job_id,
                    task.parent_task_id,
                    task.project_code,
                    task.site_code,
                    task.task_type.value,
                    task.status.value,
                    json.dumps(task.payload, ensure_ascii=True, sort_keys=True),
                    timestamp,
                    timestamp,
                ),
            )

    def update_task_status(self, task_id: str, next_status: TaskStatus) -> None:
        current_status = self._get_task_status(task_id)
        ensure_transition(current_status, next_status)

        with self._connect() as connection:
            connection.execute(
                """
                UPDATE crawl_task
                SET status = ?, updated_at = ?
                WHERE task_id = ?
                """,
                (next_status.value, utc_now_iso(), task_id),
            )

    def upsert_checkpoint(
        self,
        task_id: str,
        checkpoint_key: str,
        checkpoint_value: str,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO crawl_task_checkpoint (
                    task_id,
                    checkpoint_key,
                    checkpoint_value,
                    updated_at
                ) VALUES (?, ?, ?, ?)
                ON CONFLICT(task_id, checkpoint_key) DO UPDATE SET
                    checkpoint_value = excluded.checkpoint_value,
                    updated_at = excluded.updated_at
                """,
                (task_id, checkpoint_key, checkpoint_value, utc_now_iso()),
            )

    def log_attempt(
        self,
        *,
        task_id: str,
        worker_type: str,
        outcome_status: str,
        error_message: str | None,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO crawl_task_attempt (
                    task_id,
                    worker_type,
                    outcome_status,
                    error_message,
                    created_at
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (task_id, worker_type, outcome_status, error_message, utc_now_iso()),
            )

    def get_unfinished_tasks(self) -> list[CrawlTask]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    task_id,
                    job_id,
                    parent_task_id,
                    project_code,
                    site_code,
                    task_type,
                    status,
                    payload_json
                FROM crawl_task
                WHERE status NOT IN (?, ?, ?)
                ORDER BY created_at ASC, task_id ASC
                """,
                (
                    TaskStatus.DONE.value,
                    TaskStatus.FAILED.value,
                    TaskStatus.CANCELLED.value,
                ),
            ).fetchall()

        return [self._row_to_task(row) for row in rows]

    def get_task_checkpoints(self, task_id: str) -> dict[str, str]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT checkpoint_key, checkpoint_value
                FROM crawl_task_checkpoint
                WHERE task_id = ?
                ORDER BY checkpoint_key ASC
                """,
                (task_id,),
            ).fetchall()

        return {row["checkpoint_key"]: row["checkpoint_value"] for row in rows}

    def get_attempts(self, task_id: str) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT attempt_id, worker_type, outcome_status, error_message, created_at
                FROM crawl_task_attempt
                WHERE task_id = ?
                ORDER BY attempt_id ASC
                """,
                (task_id,),
            ).fetchall()

        return [dict(row) for row in rows]

    def _get_task_status(self, task_id: str) -> TaskStatus:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT status FROM crawl_task WHERE task_id = ?",
                (task_id,),
            ).fetchone()

        if row is None:
            raise KeyError(f"task not found: {task_id}")

        return TaskStatus(row["status"])

    def _row_to_task(self, row: sqlite3.Row) -> CrawlTask:
        return CrawlTask(
            task_id=row["task_id"],
            job_id=row["job_id"],
            project_code=row["project_code"],
            site_code=row["site_code"],
            task_type=TaskType(row["task_type"]),
            status=TaskStatus(row["status"]),
            payload=json.loads(row["payload_json"]),
            parent_task_id=row["parent_task_id"],
        )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._db_path)
        connection.row_factory = sqlite3.Row
        return connection
