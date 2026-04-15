from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, File, HTTPException, Request, UploadFile, status

from app.schemas import (
    JobResultResponse,
    JobStatus,
    JobStatusResponse,
    ParseJobCreateResponse,
)
from app.services.storage import FileTooLargeError
from app.state import AppState

router = APIRouter(prefix="/v1/jobs", tags=["jobs"])


def _state(request: Request) -> AppState:
    return request.app.state.services


@router.post(
    "/parse",
    response_model=ParseJobCreateResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def parse_document(request: Request, file: UploadFile = File(...)) -> ParseJobCreateResponse:
    services = _state(request)
    job_id = uuid4().hex

    try:
        saved = await services.storage.save_upload(job_id=job_id, upload=file)
    except FileTooLargeError as exc:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    services.job_store.create_job(
        job_id=job_id,
        filename=saved.filename,
        file_extension=saved.extension,
        input_path=saved.input_path,
    )
    await services.worker.enqueue(job_id)
    return ParseJobCreateResponse(job_id=job_id, status=JobStatus.queued)


@router.get("/{job_id}", response_model=JobStatusResponse)
def get_job_status(job_id: str, request: Request) -> JobStatusResponse:
    services = _state(request)
    job = services.job_store.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="작업을 찾을 수 없습니다.")

    return JobStatusResponse(
        job_id=job["job_id"],
        filename=job["filename"],
        file_extension=job["file_extension"],
        status=JobStatus(job["status"]),
        error_message=job["error_message"],
        created_at=job["created_at"],
        updated_at=job["updated_at"],
    )


@router.get("/{job_id}/result", response_model=JobResultResponse)
def get_job_result(job_id: str, request: Request) -> JobResultResponse:
    services = _state(request)
    job = services.job_store.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="작업을 찾을 수 없습니다.")

    current_status = JobStatus(job["status"])
    if current_status == JobStatus.failed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=job["error_message"] or "문서 파싱 작업이 실패했습니다.",
        )
    if current_status != JobStatus.completed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="아직 결과가 준비되지 않았습니다.",
        )

    markdown_path = job["markdown_path"]
    if not markdown_path:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="결과 Markdown 경로를 찾을 수 없습니다.",
        )

    result_path = Path(markdown_path)
    if not result_path.exists():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="결과 Markdown 파일을 찾을 수 없습니다.",
        )

    markdown = services.storage.read_markdown(result_path)
    return JobResultResponse(job_id=job_id, status=current_status, markdown=markdown)
