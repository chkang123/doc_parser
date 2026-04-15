from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import get_settings
from app.routes import health_router, jobs_router
from app.services.converter import OfficeToPdfConverter
from app.services.job_store import JobStore
from app.services.marker_service import MarkerService
from app.services.storage import StorageService
from app.services.worker import ParseWorker
from app.state import AppState


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    storage = StorageService(settings)
    storage.ensure_directories()
    job_store = JobStore(settings.db_path)
    office_converter = OfficeToPdfConverter(settings)
    marker_service = MarkerService(settings)
    worker = ParseWorker(
        job_store=job_store,
        storage=storage,
        office_converter=office_converter,
        marker_service=marker_service,
        concurrency=settings.worker_concurrency,
    )

    services = AppState(
        settings=settings,
        job_store=job_store,
        storage=storage,
        office_converter=office_converter,
        marker_service=marker_service,
        worker=worker,
    )
    await services.worker.start()
    app.state.services = services
    try:
        yield
    finally:
        await services.worker.stop()


app = FastAPI(
    title="doc_parser API",
    description="Upload documents and extract Markdown using marker.",
    version="0.1.0",
    lifespan=lifespan,
)
app.include_router(health_router)
app.include_router(jobs_router)
