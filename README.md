# AgentX — X Image Archive Agent v1

Local Docker-based archiver for X profiles you own or are authorized to archive. Uses the official X API, not browser scraping.

See setup instructions and API limitations below. Requires an authorized X developer bearer token.

## Setup
1. Copy `.env.example` to `.env` and configure `X_BEARER_TOKEN`.
2. Run `docker compose up --build -d`.
3. Open http://localhost:8000.

Images are stored locally under `storage/archive/`. The app saves the photo rendition returned by the authorized API without recompression; it cannot guarantee original upload bytes unless X exposes them to your API tier.