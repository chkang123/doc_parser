from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel


class JobStatus(StrEnum):
    queued = "queued"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class ParseJobCreateResponse(BaseModel):
    job_id: str
    status: JobStatus


class JobStatusResponse(BaseModel):
    job_id: str
    filename: str
    file_extension: str
    status: JobStatus
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime


class JobResultResponse(BaseModel):
    job_id: str
    status: JobStatus
    markdown: str
