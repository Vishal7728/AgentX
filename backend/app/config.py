import os

X_BEARER_TOKEN = os.getenv("X_BEARER_TOKEN", "")
X_API_BASE = os.getenv("X_API_BASE", "https://api.x.com/2").rstrip("/")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://archive:archive@db:5432/archive")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
STORAGE_DIR = os.getenv("STORAGE_DIR", "/data")
MAX_DOWNLOAD_BYTES = int(os.getenv("MAX_DOWNLOAD_BYTES", "25000000"))
HTTP_TIMEOUT_SECONDS = float(os.getenv("HTTP_TIMEOUT_SECONDS", "30"))
