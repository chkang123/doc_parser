from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from fastapi import UploadFile

from app.config import Settings


class FileTooLargeError(ValueError):
    """Raised when uploaded file exceeds configured size."""


@dataclass(slots=True)
class SavedUpload:
    filename: str
    extension: str
    input_path: Path


class StorageService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def ensure_directories(self) -> None:
        self._settings.data_dir.mkdir(parents=True, exist_ok=True)
        self._settings.uploads_dir.mkdir(parents=True, exist_ok=True)
        self._settings.jobs_dir.mkdir(parents=True, exist_ok=True)

    def make_job_dir(self, job_id: str) -> Path:
        job_dir = self._settings.jobs_dir / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        return job_dir

    async def save_upload(self, *, job_id: str, upload: UploadFile) -> SavedUpload:
        original_name = Path(upload.filename or "").name
        if not original_name:
            raise ValueError("파일 이름이 비어 있습니다.")

        extension = Path(original_name).suffix.lower()
        if extension not in self._settings.allowed_extensions:
            raise ValueError(f"지원하지 않는 파일 확장자입니다: {extension}")

        job_dir = self.make_job_dir(job_id)
        input_path = job_dir / f"input{extension}"
        total_size = 0
        max_size = self._settings.max_file_size_mb * 1024 * 1024

        with input_path.open("wb") as output:
            while True:
                chunk = await upload.read(1024 * 1024)
                if not chunk:
                    break
                total_size += len(chunk)
                if total_size > max_size:
                    output.close()
                    input_path.unlink(missing_ok=True)
                    raise FileTooLargeError(
                        f"업로드 최대 크기({self._settings.max_file_size_mb}MB)를 초과했습니다."
                    )
                output.write(chunk)

        await upload.close()
        return SavedUpload(
            filename=original_name,
            extension=extension,
            input_path=input_path,
        )

    def pdf_output_path(self, job_id: str) -> Path:
        return self.make_job_dir(job_id) / "converted.pdf"

    def markdown_output_path(self, job_id: str) -> Path:
        return self.make_job_dir(job_id) / "result.md"

    def read_markdown(self, path: Path) -> str:
        return path.read_text(encoding="utf-8")
