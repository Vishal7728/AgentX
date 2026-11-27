# AgentX — Local X Screenshot Archive

AgentX is a local-first tool for capturing screenshots of image posts displayed in a
user-controlled browser. The local browser mode runs on the user's PC, uses a
persistent Chromium profile, and does not require an X API bearer token.

## Local browser capture (no X API token)

### Requirements

- Python 3.11+
- Chromium installed by Playwright

### Windows PowerShell

```powershell
git clone https://github.com/Vishal7728/AgentX.git
cd AgentX
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m playwright install chromium
$env:PYTHONPATH = "backend"
python -m app.browser_capture --url https://x.com/username
```

On macOS/Linux, create and activate a virtual environment, install requirements,
then run the same Playwright install and Python command.

AgentX opens a visible browser on this PC. Sign in yourself if required, then scroll
to a post you are authorized to archive. Press Enter in the terminal to capture
image elements from the first visible post; type `q` to exit. The browser session
is kept locally in `storage/browser-profile/`.

Screenshots and JSON integrity manifests are saved under
`storage/screenshots/`. The manifest records source page, capture time, dimensions
and SHA-256. Technical validation checks image load/visibility, dimensions,
decoding and aspect-ratio sanity only; no content or sensitivity classification
is performed.

**Important:** A browser screenshot is a rendered capture, not the original
uploaded image. X may resize, crop or transform what is displayed. AgentX does not
crawl timelines, auto-scroll, bypass login/CAPTCHA, evade rate limits or access
controls. Use automated browsing only where your authorization and the platform's
current terms permit it. If verification or login is required, complete it yourself.

## Optional local enhancement

The optional enhancement utility writes a separate derivative file. It must not
overwrite the source screenshot. Keep the untouched PNG as the archive master.

## Existing API/Docker pipeline

The repository also retains the earlier official-X-API pipeline (FastAPI, Celery,
Redis and PostgreSQL). That mode requires a valid X developer bearer token and
remains subject to X API access, billing and rate limits. It is separate from the
local browser screenshot mode.

## Local data and privacy

- Browser cookies and session data live in `storage/browser-profile/`.
- Captures live in `storage/screenshots/`.
- Keep `storage/` private; do not commit it or share browser session data.
- The Docker dashboard binds to localhost by default. Do not expose it publicly
  without authentication and appropriate security controls.

See [docs/manual-capture.md](docs/manual-capture.md) for capture details.
