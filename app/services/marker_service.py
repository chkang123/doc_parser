from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from app.config import Settings


class MarkerService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._converter: Any = None
        self._pdf_converter_cls: Any = None
        self._create_model_dict: Any = None
        self._text_from_rendered: Any = None
        self._python_api_available = False
        self._load_python_api()

    def _load_python_api(self) -> None:
        try:
            from marker.converters.pdf import PdfConverter
            from marker.models import create_model_dict
            from marker.output import text_from_rendered
        except Exception:
            self._python_api_available = False
            return

        self._pdf_converter_cls = PdfConverter
        self._create_model_dict = create_model_dict
        self._text_from_rendered = text_from_rendered
        self._python_api_available = True

    def convert_pdf_to_markdown(self, pdf_path: Path, markdown_path: Path) -> Path:
        markdown_path.parent.mkdir(parents=True, exist_ok=True)
        markdown_text = ""

        if self._python_api_available:
            try:
                markdown_text = self._convert_with_python_api(pdf_path)
            except RuntimeError:
                # 환경/버전 차이를 고려해 CLI 경로를 폴백으로 유지한다.
                markdown_text = self._convert_with_cli(pdf_path, markdown_path.parent)
        else:
            markdown_text = self._convert_with_cli(pdf_path, markdown_path.parent)

        if not markdown_text.strip():
            raise RuntimeError("marker 결과가 비어 있습니다.")

        markdown_path.write_text(markdown_text, encoding="utf-8")
        return markdown_path

    def _convert_with_python_api(self, pdf_path: Path) -> str:
        try:
            if self._converter is None:
                self._converter = self._pdf_converter_cls(
                    artifact_dict=self._create_model_dict()
                )
            rendered = self._converter(str(pdf_path))
            markdown, _, _ = self._text_from_rendered(rendered)
        except Exception as exc:
            raise RuntimeError(f"marker Python API 변환 실패: {exc}") from exc
        return markdown or ""

    def _convert_with_cli(self, pdf_path: Path, output_dir: Path) -> str:
        command = [
            "marker_single",
            str(pdf_path),
            "--output_dir",
            str(output_dir),
            "--output_format",
            "markdown",
        ]
        try:
            subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=True,
                timeout=self._settings.marker_timeout_seconds,
            )
        except FileNotFoundError as exc:
            raise RuntimeError(
                "marker 라이브러리를 찾지 못했습니다. `marker-pdf` 설치를 확인하세요."
            ) from exc
        except subprocess.CalledProcessError as exc:
            detail = (exc.stderr or exc.stdout or "unknown error").strip()
            raise RuntimeError(f"marker CLI 변환 실패: {detail}") from exc
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError("marker 변환 시간이 초과되었습니다.") from exc

        # marker 실행 결과에서 생성된 최신 markdown 파일을 읽는다.
        markdown_candidates = sorted(
            output_dir.rglob("*.md"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        if not markdown_candidates:
            raise RuntimeError("marker 결과 Markdown 파일을 찾지 못했습니다.")
        return markdown_candidates[0].read_text(encoding="utf-8")
