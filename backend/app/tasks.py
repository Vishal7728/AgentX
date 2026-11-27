import hashlib
import mimetypes
import os
import re
from datetime import datetime, timezone
from pathlib import Path
import httpx
from PIL import Image
from celery import shared_task
from sqlalchemy import select, func
from .db import SessionLocal
from .models import Job, Post, Media
from .x_api import resolve_user, get_user_posts
from .config import STORAGE_DIR, MAX_DOWNLOAD_BYTES, HTTP_TIMEOUT_SECONDS

def _job_status(job_id):
    with SessionLocal() as db:
        job = db.get(Job, job_id)
        return job.status if job else "missing"

def _finalize(job_id):
    with SessionLocal() as db:
        job = db.get(Job, job_id)
        if not job or not job.discovery_done or job.status == "paused":
            return
        pending = db.scalar(select(func.count()).select_from(Media).where(
            Media.job_id == job_id, Media.status.in_(["pending", "downloading"])
        )) or 0
        failed = db.scalar(select(func.count()).select_from(Media).where(
            Media.job_id == job_id, Media.status == "failed"
        )) or 0
        job.failed_media = failed
        if pending == 0:
            job.status = "completed" if failed == 0 else "completed_with_errors"
        db.commit()

@shared_task(bind=True, max_retries=5, default_retry_delay=30)
def discover_profile(self, job_id):
    with SessionLocal() as db:
        job = db.get(Job, job_id)
        if not job or job.discovery_done or job.status == "paused":
            return
        job.status, username = "discovering", job.username
        db.commit()
    try:
        user = resolve_user(username)
        if not user or not user.get("id"):
            raise RuntimeError("X API did not return a user ID. Check the username and API access.")
        with SessionLocal() as db:
            job = db.get(Job, job_id)
            job.x_user_id = str(user["id"])
            db.commit()
        while True:
            if _job_status(job_id) == "paused":
                return
            with SessionLocal() as db:
                job = db.get(Job, job_id)
                token, user_id = job.pagination_token, job.x_user_id
            payload = get_user_posts(user_id, token)
            posts = payload.get("data") or []
            photos = {
                item["media_key"]: item
                for item in payload.get("includes", {}).get("media", [])
                if item.get("type") == "photo"
            }
            queued_media_ids = []
            with SessionLocal() as db:
                job = db.get(Job, job_id)
                for post in posts:
                    post_id = str(post["id"])
                    keys = [k for k in post.get("attachments", {}).get("media_keys", []) if k in photos]
                    exists = db.scalar(select(Post.id).where(Post.job_id == job_id, Post.post_id == post_id))
                    if exists:
                        continue
                    db.add(Post(job_id=job_id, post_id=post_id,
                                created_at_x=post.get("created_at"),
                                post_url=f"https://x.com/{username}/status/{post_id}",
                                has_images=bool(keys)))
                    job.total_posts += 1
                    job.processed_posts += 1
                    for key in keys:
                        item = photos[key]
                        row = Media(job_id=job_id, post_id=post_id, media_key=key,
                                    source_url=item.get("url"), width=item.get("width"), height=item.get("height"),
                                    status="pending" if item.get("url") else "unavailable",
                                    error=None if item.get("url") else "No photo URL returned by API.")
                        db.add(row)
                        job.total_media += 1
                        if item.get("url"):
                            db.flush()
                            queued_media_ids.append(row.id)
                job.pagination_token = payload.get("meta", {}).get("next_token")
                db.commit()
            for media_id in queued_media_ids:
                download_media.delay(media_id)
            if not payload.get("meta", {}).get("next_token"):
                break
        with SessionLocal() as db:
            job = db.get(Job, job_id)
            job.discovery_done, job.status = True, "processing"
            db.commit()
        _finalize(job_id)
    except Exception as exc:
        with SessionLocal() as db:
            job = db.get(Job, job_id)
            if job:
                job.status, job.error = "error", str(exc)[:2000]
                db.commit()
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=min(300, 15 * (2 ** self.request.retries)))
        raise

@shared_task(bind=True, max_retries=5, default_retry_delay=20)
def download_media(self, media_id):
    with SessionLocal() as db:
        media = db.get(Media, media_id)
        if not media or media.status in ("completed", "unavailable"):
            return
        job = db.get(Job, media.job_id)
        if not job or job.status == "paused":
            return
        media.status = "downloading"
        source, post_id, key, job_id, username = media.source_url, media.post_id, media.media_key, media.job_id, job.username
        folder_mode, archive_name = job.folder_mode, job.archive_name
        db.commit()
    temp = None
    try:
        if not source:
            raise ValueError("Missing authorized media URL.")
        digest, size = hashlib.sha256(), 0
        tmp_dir = Path(STORAGE_DIR) / "tmp"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        temp = tmp_dir / f"{media_id}.part"
        with httpx.stream("GET", source, timeout=HTTP_TIMEOUT_SECONDS, follow_redirects=True) as response:
            response.raise_for_status()
            mime = response.headers.get("content-type", "").split(";")[0].lower()
            if not mime.startswith("image/"):
                raise ValueError(f"Expected image MIME type; got {mime or 'unknown'}.")
            with temp.open("wb") as out:
                for chunk in response.iter_bytes(131072):
                    size += len(chunk)
                    if size > MAX_DOWNLOAD_BYTES:
                        raise ValueError("Image exceeds MAX_DOWNLOAD_BYTES.")
                    digest.update(chunk)
                    out.write(chunk)
        with Image.open(temp) as image:
            image.verify()
        with Image.open(temp) as image:
            width, height, fmt = image.width, image.height, (image.format or "img").lower()
        ext = mimetypes.guess_extension(mime) or f".{fmt}"
        if ext == ".jpe":
            ext = ".jpg"
        with SessionLocal() as db:
            post = db.scalar(select(Post).where(Post.job_id == job_id, Post.post_id == post_id))
            created = post.created_at_x if post else None
        try:
            dt = datetime.fromisoformat(created.replace("Z", "+00:00")) if created else datetime.now(timezone.utc)
        except ValueError:
            dt = datetime.now(timezone.utc)
        safe_archive = re.sub(r"[^A-Za-z0-9_-]", "_", archive_name)
        base = Path(STORAGE_DIR) / "archive" / safe_archive / username
        if folder_mode == "post":
            folder = base / f"{dt.year:04d}" / f"{dt.month:02d}" / post_id
        else:
            folder = base / "images"
        folder.mkdir(parents=True, exist_ok=True)
        safe_key = re.sub(r"[^A-Za-z0-9_-]", "_", key)
        target = folder / f"{post_id}_{safe_key}{ext}"
        os.replace(temp, target)
        with SessionLocal() as db:
            media = db.get(Media, media_id)
            media.status, media.file_path = "completed", str(target)
            media.file_size, media.sha256, media.mime_type = size, digest.hexdigest(), mime
            media.width, media.height, media.error = width, height, None
            db.get(Job, job_id).downloaded_media += 1
            db.commit()
        _finalize(job_id)
    except Exception as exc:
        if temp and temp.exists():
            temp.unlink(missing_ok=True)
        with SessionLocal() as db:
            media = db.get(Media, media_id)
            if media:
                media.status = "failed" if self.request.retries >= self.max_retries else "pending"
                media.error = str(exc)[:1000]
                db.commit()
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=min(300, 15 * (2 ** self.request.retries)))
        _finalize(job_id)
        raise
