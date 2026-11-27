import re
import uuid
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, HttpUrl, Field
from sqlalchemy import select, text
from .db import init_db, SessionLocal, engine
from .models import Job, Media
from .tasks import discover_profile, download_media
from .config import STORAGE_DIR, X_BEARER_TOKEN, REDIS_URL
import redis

app = FastAPI(title="AgentX — X Image Archive", version="1.1.0")

class CreateJob(BaseModel):
    profile_url: HttpUrl
    folder_mode: str = "post"
    archive_name: str = Field(default="X Archive", min_length=1, max_length=80)

def extract_username(url: str) -> str:
    match = re.fullmatch(r"https?://(?:www\.)?(?:x\.com|twitter\.com)/([A-Za-z0-9_]{1,15})/?", str(url))
    if not match:
        raise HTTPException(400, "Enter a profile URL such as https://x.com/username.")
    username = match.group(1)
    if username.lower() in {"home", "explore", "search", "settings", "i", "messages", "notifications"}:
        raise HTTPException(400, "URL is not a profile.")
    return username

def safe_folder_name(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9 _-]", "", value).strip()
    value = re.sub(r"\s+", "_", value)[:80]
    if not value:
        raise HTTPException(400, "Archive folder name must contain letters or numbers.")
    return value

@app.on_event("startup")
def startup():
    Path(STORAGE_DIR).mkdir(parents=True, exist_ok=True)
    init_db()

@app.get("/", response_class=HTMLResponse)
def dashboard():
    return HTMLResponse((Path(__file__).parent / "dashboard.html").read_text(encoding="utf-8"))

@app.get("/api/health")
def health():
    checks = {"database": False, "redis": False, "x_token_configured": bool(X_BEARER_TOKEN and X_BEARER_TOKEN != "replace_me")}
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        checks["database"] = True
    except Exception:
        pass
    try:
        redis.Redis.from_url(REDIS_URL, socket_connect_timeout=2).ping()
        checks["redis"] = True
    except Exception:
        pass
    checks["ok"] = checks["database"] and checks["redis"]
    return checks

@app.post("/api/jobs", status_code=202)
def create_job(body: CreateJob):
    username = extract_username(str(body.profile_url))
    if body.folder_mode not in {"post", "profile"}:
        raise HTTPException(400, "folder_mode must be 'post' or 'profile'.")
    archive_name = safe_folder_name(body.archive_name)
    job_id = str(uuid.uuid4())
    with SessionLocal() as db:
        db.add(Job(id=job_id, username=username, profile_url=str(body.profile_url),
                   status="queued", folder_mode=body.folder_mode, archive_name=archive_name))
        db.commit()
    try:
        discover_profile.delay(job_id)
    except Exception as exc:
        with SessionLocal() as db:
            job = db.get(Job, job_id)
            job.status, job.error = "error", f"Could not enqueue discovery worker: {exc}"
            db.commit()
        raise HTTPException(503, "Job saved but worker queue is unavailable. Check Redis and worker logs.")
    return {"job_id": job_id, "username": username, "status": "queued",
            "folder_mode": body.folder_mode, "archive_name": archive_name}

def serialize(job):
    return {"job_id": job.id, "username": job.username, "profile_url": job.profile_url,
            "status": job.status, "folder_mode": job.folder_mode, "archive_name": job.archive_name,
            "total_posts": job.total_posts, "processed_posts": job.processed_posts,
            "total_media": job.total_media, "downloaded_media": job.downloaded_media,
            "failed_media": job.failed_media, "discovery_done": job.discovery_done,
            "error": job.error, "created_at": job.created_at.isoformat() if job.created_at else None}

@app.get("/api/jobs")
def list_jobs():
    with SessionLocal() as db:
        return [serialize(j) for j in db.scalars(select(Job).order_by(Job.created_at.desc()).limit(100)).all()]

@app.get("/api/jobs/{job_id}")
def get_job(job_id: str):
    with SessionLocal() as db:
        job = db.get(Job, job_id)
        if not job:
            raise HTTPException(404, "Job not found")
        return serialize(job)

@app.post("/api/jobs/{job_id}/pause")
def pause_job(job_id: str):
    with SessionLocal() as db:
        job = db.get(Job, job_id)
        if not job:
            raise HTTPException(404, "Job not found")
        job.status = "paused"
        db.commit()
        return serialize(job)

@app.post("/api/jobs/{job_id}/resume")
def resume_job(job_id: str):
    with SessionLocal() as db:
        job = db.get(Job, job_id)
        if not job:
            raise HTTPException(404, "Job not found")
        if job.status != "paused":
            raise HTTPException(409, "Only paused jobs can be resumed.")
        job.status, job.error = "queued", None
        db.commit()
        pending = db.scalars(select(Media.id).where(Media.job_id == job_id, Media.status.in_(["pending", "failed"]))).all()
        discovery_done = job.discovery_done
    if not discovery_done:
        discover_profile.delay(job_id)
    for media_id in pending:
        download_media.delay(media_id)
    return {"job_id": job_id, "status": "resumed", "queued_downloads": len(pending)}

@app.get("/api/jobs/{job_id}/media")
def list_media(job_id: str):
    with SessionLocal() as db:
        if not db.get(Job, job_id):
            raise HTTPException(404, "Job not found")
        rows = db.scalars(select(Media).where(Media.job_id == job_id).order_by(Media.id.desc()).limit(500)).all()
        return [{"id": m.id, "post_id": m.post_id, "media_key": m.media_key, "status": m.status,
                 "path": m.file_path, "sha256": m.sha256, "width": m.width, "height": m.height, "error": m.error}
                for m in rows]
