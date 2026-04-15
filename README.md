# doc_parser

`doc_parser`는 문서 파일을 업로드 받아 Markdown으로 변환하는 FastAPI 서버입니다.

- 입력 형식: `pdf`, `doc`, `docx`, `ppt`, `pptx`, `xls`, `xlsx`
- 처리 파이프라인:
  - Office 문서 -> LibreOffice(`soffice --headless`)로 PDF 변환
  - PDF -> `marker`로 Markdown 추출
- 처리 모델: 비동기 잡 큐 (`job_id` 기반 상태 조회)

## 1) 로컬 실행

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env       # Windows PowerShell: Copy-Item .env.example .env
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## 2) Docker 실행

```bash
docker build -t doc-parser .
docker run --rm -p 8000:8000 -v doc_parser_data:/data --name doc-parser doc-parser
```

## 3) API

### Health check

```bash
curl http://localhost:8000/health
```

### 문서 파싱 요청

```bash
curl -X POST "http://localhost:8000/v1/jobs/parse" \
  -F "file=@/absolute/path/to/sample.docx"
```

응답 예시:

```json
{
  "job_id": "d7349c16ea7f4cb2b75796d2dfecb9a3",
  "status": "queued"
}
```

### 작업 상태 조회

```bash
curl "http://localhost:8000/v1/jobs/{job_id}"
```

응답 예시:

```json
{
  "job_id": "d7349c16ea7f4cb2b75796d2dfecb9a3",
  "filename": "sample.docx",
  "file_extension": ".docx",
  "status": "processing",
  "error_message": null,
  "created_at": "2026-04-15T10:00:00.000000+00:00",
  "updated_at": "2026-04-15T10:00:01.000000+00:00"
}
```

### 결과 조회

```bash
curl "http://localhost:8000/v1/jobs/{job_id}/result"
```

완료 시 응답 예시:

```json
{
  "job_id": "d7349c16ea7f4cb2b75796d2dfecb9a3",
  "status": "completed",
  "markdown": "# Parsed document\\n..."
}
```

## 4) 환경 변수

`.env.example`의 기본값:

- `DOC_PARSER_DATA_DIR`: 업로드/결과/DB 저장 루트 (기본 `/data`)
- `DOC_PARSER_MAX_FILE_SIZE_MB`: 업로드 최대 크기
- `DOC_PARSER_MARKER_TIMEOUT_SECONDS`: marker 처리 타임아웃
- `DOC_PARSER_SOFFICE_TIMEOUT_SECONDS`: Office PDF 변환 타임아웃
- `DOC_PARSER_WORKER_CONCURRENCY`: 워커 동시성

## 5) 운영 참고

- 장시간 처리/대용량 문서가 많아지면 in-process 큐 대신 외부 큐(Redis+RQ/Celery)로 분리 권장
- `data/`를 볼륨으로 마운트해 결과 및 잡 상태를 유지하세요
