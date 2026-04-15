from __future__ import annotations

import asyncio
from pathlib import Path

from app.schemas import JobStatus
from app.services.converter import OfficeToPdfConverter
from app.services.job_store import JobStore
from app.services.marker_service import MarkerService
from app.services.storage import StorageService


class ParseWorker:
    def __init__(
        self,
        *,
        job_store: JobStore,
        storage: StorageService,
        office_converter: OfficeToPdfConverter,
        marker_service: MarkerService,
        concurrency: int = 1,
    ) -> None:
        self._job_store = job_store
        self._storage = storage
        self._office_converter = office_converter
        self._marker_service = marker_service
        self._queue: asyncio.Queue[str] = asyncio.Queue()
        self._tasks: list[asyncio.Task[None]] = []
        self._concurrency = max(1, concurrency)

    async def start(self) -> None:
        if self._tasks:
            return
        for _ in range(self._concurrency):
            self._tasks.append(asyncio.create_task(self._run_loop()))

    async def stop(self) -> None:
        for task in self._tasks:
            task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()

    async def enqueue(self, job_id: str) -> None:
        await self._queue.put(job_id)

    async def _run_loop(self) -> None:
        while True:
            job_id = await self._queue.get()
            try:
                await self._process_job(job_id)
            finally:
                self._queue.task_done()

    async def _process_job(self, job_id: str) -> None:
        job = self._job_store.get_job(job_id)
        if job is None:
            return

        self._job_store.set_processing(job_id)
        try:
            source_path = Path(job["input_path"])
            source_ext = source_path.suffix.lower()
            pdf_path = source_path

            if OfficeToPdfConverter.is_office_extension(source_ext):
                pdf_path = await asyncio.to_thread(
                    self._office_converter.convert_to_pdf,
                    source_path,
                    self._storage.pdf_output_path(job_id),
                )
            elif source_ext != ".pdf":
                raise RuntimeError(f"지원하지 않는 파일 형식입니다: {source_ext}")

            markdown_path = self._storage.markdown_output_path(job_id)
            await asyncio.to_thread(
                self._marker_service.convert_pdf_to_markdown,
                pdf_path,
                markdown_path,
            )
            self._job_store.set_completed(
                job_id,
                pdf_path=pdf_path,
                markdown_path=markdown_path,
            )
        except Exception as exc:
            self._job_store.set_failed(job_id, error_message=str(exc))

    def queue_size(self) -> int:
        return self._queue.qsize()

    def is_running(self) -> bool:
        return any(task and not task.done() for task in self._tasks)

    def status(self, job_id: str) -> JobStatus | None:
        job = self._job_store.get_job(job_id)
        if job is None:
            return None
        return JobStatus(job["status"])
