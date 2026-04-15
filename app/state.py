from dataclasses import dataclass

from app.config import Settings
from app.services.converter import OfficeToPdfConverter
from app.services.job_store import JobStore
from app.services.marker_service import MarkerService
from app.services.storage import StorageService
from app.services.worker import ParseWorker


@dataclass(slots=True)
class AppState:
    settings: Settings
    job_store: JobStore
    storage: StorageService
    office_converter: OfficeToPdfConverter
    marker_service: MarkerService
    worker: ParseWorker
