# Architecture

- FastAPI: local dashboard and job API.
- PostgreSQL: durable jobs, posts, media metadata and checkpoints.
- Redis: Celery broker/backend.
- Celery worker: paginated profile discovery and concurrent photo downloads.
- Local bind mount: image files under storage/archive.

The orchestration is deterministic Python code. Workers are queue consumers, not independent LLM instances. This keeps repetitive work efficient and auditable.

## Reliability model
- Persist pagination token after each successfully committed page.
- Unique constraints prevent duplicate post/media rows within a job.
- Temporary failures use Celery retries with exponential delay.
- SHA-256 and image decoding verify downloaded files.
- Pause is cooperative and may allow an in-flight request to finish.

## Media quality
The program saves the exact bytes returned by the authorized media URL without resizing or recompression. It does not alter undocumented URL parameters to force an original rendition. Original-upload quality is only possible if X exposes that rendition to the API credentials.
