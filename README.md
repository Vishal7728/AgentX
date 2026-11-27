# AgentX — X Image Archive Agent v1

A local Docker application for archiving image posts from X profiles you own or are authorized to archive. It uses the official X API and does not automate the X website or use undocumented scraping endpoints.

## Features

- Accepts an X profile URL and resolves it through the X API.
- Paginates the user-posts timeline using API pagination tokens.
- Selects photo attachments and excludes video-only media.
- Queues downloads through Celery and Redis.
- Saves downloaded image bytes locally without resizing or recompression.
- Verifies image readability, dimensions and SHA-256 checksums.
- Stores job, post and media metadata in PostgreSQL.
- Provides a local dashboard with job status, pause and resume controls.

## Requirements

- Docker Desktop (Windows/macOS) or Docker Engine + Docker Compose (Linux).
- An X developer app and bearer token with access to user lookup and user-post timeline endpoints.

## Quick start

1. Clone this repository:
   ```bash
   git clone https://github.com/Vishal7728/AgentX.git
   cd AgentX
   ```
2. Create your local environment file:
   - Windows PowerShell: `Copy-Item .env.example .env`
   - macOS/Linux: `cp .env.example .env`
3. Edit `.env` and set `X_BEARER_TOKEN=YOUR_ACTUAL_BEARER_TOKEN`.
4. Build and start services:
   ```bash
   docker compose up --build -d
   ```
5. Open http://localhost:8000 and enter an authorized profile URL such as `https://x.com/your_account`.

API documentation: http://localhost:8000/docs

## Services

| Service | Purpose |
|---|---|
| FastAPI | Dashboard and job API |
| Celery | Background task execution |
| Redis | Celery broker and result backend |
| PostgreSQL | Persistent jobs, posts and media metadata |
| Local storage | Downloaded images under `storage/archive/` |

## Useful commands

```bash
docker compose logs -f api worker
docker compose ps
docker compose down
```

`docker compose down -v` also removes the PostgreSQL and Redis volumes (destructive to job state). Downloaded files in the local `storage/` bind mount remain unless deleted separately.

## API and original-quality limitations

Endpoint access, historical depth, media fields, rate limits and pricing depend on your X developer access tier and current X documentation. The app can only archive posts and media made available to the configured credentials.

The downloader saves the bytes returned by the authorized photo media URL without resizing or recompression. It does not construct undocumented URL parameters to force an original rendition. If X only exposes a transformed rendition or does not expose a media URL for your access tier, the app cannot guarantee retrieval of the original upload bytes.

Respect X's developer terms, automation rules, rate limits, retention requirements and applicable image rights. Do not redistribute downloaded images without the necessary rights.

## Local security

- The dashboard port is bound to `127.0.0.1` by default and is not exposed to your LAN.
- Keep `.env` private; never commit it or share the bearer token.
- Default PostgreSQL credentials are for local development only.
- Do not expose the application publicly without authentication, TLS, CSRF protection and a reverse proxy.

## MVP limitations

- One profile per archive job.
- Bearer-token authentication only; OAuth user-context flow is not implemented.
- API access determines which historical posts and image renditions are available.
- Pause is cooperative; an in-flight HTTP request may finish.
- The dashboard is a local development UI without login.
- Tables are created at startup; use Alembic migrations before production.
- Test with a small authorized profile before running a large archive.
