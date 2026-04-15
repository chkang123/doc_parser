from __future__ import annotations

import sqlite3
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.schemas import JobStatus


class JobStore:
    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._lock = threading.Lock()
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._db_path, check_same_thread=False)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    job_id TEXT PRIMARY KEY,
                    filename TEXT NOT NULL,
                    file_extension TEXT NOT NULL,
                    status TEXT NOT NULL,
                    input_path TEXT NOT NULL,
                    pdf_path TEXT,
                    markdown_path TEXT,
                    error_message TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def create_job(
        self,
        *,
        job_id: str,
        filename: str,
        file_extension: str,
        input_path: Path,
    ) -> None:
        now = datetime.now(UTC).isoformat()
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO jobs (
                    job_id, filename, file_extension, status, input_path,
                    pdf_path, markdown_path, error_message, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, NULL, NULL, NULL, ?, ?)
                """,
                (
                    job_id,
                    filename,
                    file_extension,
                    JobStatus.queued.value,
                    str(input_path),
                    now,
                    now,
                ),
            )
            conn.commit()

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        with self._lock, self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM jobs WHERE job_id = ?",
                (job_id,),
            ).fetchone()
            if row is None:
                return None
            return dict(row)

    def set_processing(self, job_id: str) -> None:
        self._update_job(
            job_id,
            status=JobStatus.processing.value,
            error_message=None,
        )

    def set_completed(self, job_id: str, *, pdf_path: Path, markdown_path: Path) -> None:
        self._update_job(
            job_id,
            status=JobStatus.completed.value,
            pdf_path=str(pdf_path),
            markdown_path=str(markdown_path),
            error_message=None,
        )

    def set_failed(self, job_id: str, *, error_message: str) -> None:
        self._update_job(
            job_id,
            status=JobStatus.failed.value,
            error_message=error_message[:2000],
        )

    def _update_job(
        self,
        job_id: str,
        *,
        status: str,
        error_message: str | None = None,
        pdf_path: str | None = None,
        markdown_path: str | None = None,
    ) -> None:
        now = datetime.now(UTC).isoformat()
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                UPDATE jobs
                SET status = ?,
                    error_message = ?,
                    pdf_path = COALESCE(?, pdf_path),
                    markdown_path = COALESCE(?, markdown_path),
                    updated_at = ?
                WHERE job_id = ?
                """,
                (status, error_message, pdf_path, markdown_path, now, job_id),
            )
            conn.commit()
