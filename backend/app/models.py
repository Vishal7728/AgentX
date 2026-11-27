from sqlalchemy import String, Integer, BigInteger, Boolean, DateTime, Text, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from .db import Base

class Job(Base):
    __tablename__ = "jobs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    username: Mapped[str] = mapped_column(String(64), index=True)
    x_user_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    profile_url: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="queued", index=True)
    pagination_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    discovery_done: Mapped[bool] = mapped_column(Boolean, default=False)
    total_posts: Mapped[int] = mapped_column(Integer, default=0)
    processed_posts: Mapped[int] = mapped_column(Integer, default=0)
    total_media: Mapped[int] = mapped_column(Integer, default=0)
    downloaded_media: Mapped[int] = mapped_column(Integer, default=0)
    failed_media: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class Post(Base):
    __tablename__ = "posts"
    __table_args__ = (UniqueConstraint("job_id", "post_id", name="uq_job_post"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    post_id: Mapped[str] = mapped_column(String(32), index=True)
    created_at_x: Mapped[str | None] = mapped_column(String(40), nullable=True)
    post_url: Mapped[str] = mapped_column(Text)
    has_images: Mapped[bool] = mapped_column(Boolean, default=False)

class Media(Base):
    __tablename__ = "media"
    __table_args__ = (UniqueConstraint("job_id", "post_id", "media_key", name="uq_job_post_media"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    post_id: Mapped[str] = mapped_column(String(32), index=True)
    media_key: Mapped[str] = mapped_column(String(128))
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(24), default="pending", index=True)
    file_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_size: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
