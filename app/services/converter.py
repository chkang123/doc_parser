from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from app.config import Settings

OFFICE_EXTENSIONS = {".doc", ".docx", ".ppt", ".pptx", ".xls", ".xlsx"}


class OfficeToPdfConverter:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    @staticmethod
    def is_office_extension(extension: str) -> bool:
        return extension.lower() in OFFICE_EXTENSIONS

    def convert_to_pdf(self, source_path: Path, target_pdf_path: Path) -> Path:
        source_ext = source_path.suffix.lower()
        if source_ext not in OFFICE_EXTENSIONS:
            raise ValueError(f"Office 문서가 아닙니다: {source_ext}")

        target_pdf_path.parent.mkdir(parents=True, exist_ok=True)
        outdir = target_pdf_path.parent

        command = [
            "soffice",
            "--headless",
            "--convert-to",
            "pdf",
            "--outdir",
            str(outdir),
            str(source_path),
        ]
        try:
            subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=True,
                timeout=self._settings.soffice_timeout_seconds,
            )
        except FileNotFoundError as exc:
            raise RuntimeError(
                "LibreOffice(soffice)를 찾지 못했습니다. Docker 이미지에 libreoffice를 설치하세요."
            ) from exc
        except subprocess.CalledProcessError as exc:
            detail = (exc.stderr or exc.stdout or "unknown error").strip()
            raise RuntimeError(f"Office->PDF 변환 실패: {detail}") from exc
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError("Office->PDF 변환 시간이 초과되었습니다.") from exc

        converted_path = outdir / f"{source_path.stem}.pdf"
        if not converted_path.exists():
            raise RuntimeError("변환된 PDF 파일을 찾을 수 없습니다.")

        if converted_path.resolve() != target_pdf_path.resolve():
            shutil.move(str(converted_path), str(target_pdf_path))

        return target_pdf_path
