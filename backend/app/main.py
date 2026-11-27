import re
import uuid
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, HttpUrl
from sqlalchemy import select
from .db import init_db, SessionLocal
from .models import Job, Media
from .tasks import discover_profile, download_media
from .config import STORAGE_DIR

app = FastAPI(title="AgentX — X Image Archive", version="1.0.0")

class CreateJob(BaseModel):
    profile_url: HttpUrl

def extract_username(url: str) -> str:
    match = re.fullmatch(r"https?://(?:www\\.)?(?:x\\.com|twitter\\.com)/([A-Za-z0-9_]{1,15})/?", str(url))
    if not match:
        raise HTTPException(400, "Enter a profile URL such as https://x.com/username.")
    username = match.group(1)
    if username.lower() in {"home", "explore", "search", "settings", "i", "messages", "notifications"}:
        raise HTTPException(400, "URL is not a profile.")
    return username

@app.on_event("startup")
def startup():
    Path(STORAGE_DIR).mkdir(parents=True, exist_ok=True)
    init_db()

@app.get("/", response_class=HTMLResponse)
def dashboard():
    return HTMLResponse((Path(__file__).parent / "dashboard.html").read_text(encoding="utf-8"))

@app.get("/api/health")
def health():
    return {"ok": True, "service": "agentx-archive"}

@app.post("/api/jobs", status_code=202)
def create_job(body: CreateJob):
    username = extract_username(str(body.profile_url))
    job_id = str(uuid.uuid4())
    with SessionLocal() as db:
        db.add(Job(id=job_id, username=username, profile_url=str(body.profile_url), status="queued"))
        db.commit()
    discover_profile.delay(job_id)
    return {"job_id": job_id, "username": username, "status": "queued"}

def serialize(job):
    return {"job_id": job.id, "username": job.username, "profile_url": job.profile_url,
            "status": job.status, "total_posts": job.total_posts, "processed_posts": job.processed_posts,
            "total_media": job.total_media, "downloaded_media": job.downloaded_media,
            "failed_media": job.failed_media, "discovery_done": job.discovery_done,
            "error": job.error, "created_at": job.created_at.isoformat() if job.created_at else None}

@app.get("/api/jobs")
def list_jobs():
    with SessionLocal() as db:
        return [serialize(j) for j in db.scalars(select(Job).order_by(Job.created_at.desc()).limit(50)).all()]

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
        rows = db.scalars(select(Media).where(Media.job_id == job_id).order_by(Media.id.desc()).limit(500)).all()
        return [{"id": m.id, "post_id": m.post_id, "media_key": m.media_key, "status": m.status,
                 "path": m.file_path, "sha256": m.sha256, "width": m.width, "height": m.height, "error": m.error}
                for m in rows]
