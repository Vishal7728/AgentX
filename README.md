# AgentX — Local X Screenshot Archive

AgentX is a local-first archive tool. It uses an authorized X API bearer token to
discover API-accessible profile posts, then opens those post URLs in a visible
Chromium browser on the user's PC and captures rendered X media screenshots.

## Requirements

- Python 3.11+
- X developer bearer token with access/credits for user lookup and user timeline
- Playwright Chromium
- Authorization to archive the account/content and permission for the automated
  browser workflow under X's current terms

## Windows PowerShell quick start

```powershell
git clone https://github.com/Vishal7728/AgentX.git
cd AgentX
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m playwright install chromium
Copy-Item .env.example .env
notepad .env
```

Set `X_BEARER_TOKEN` in `.env`, then run:

```powershell
$env:PYTHONPATH = "backend"
python -m app.browser_capture --url https://x.com/username --confirm-platform-permission
```

For a small test first:

```powershell
python -m app.browser_capture --url https://x.com/username --max-posts 10 --confirm-platform-permission
```

AgentX discovers posts using API pagination, opens a visible local Chromium
session, and visits each discovered post automatically. If login or verification
is required, complete it yourself in the browser and press Enter once to start
the run. It then processes the discovered posts without requiring manual scrolling
or per-post confirmation.

## What gets saved

- Screenshots: `storage/screenshots/<post-id>/image-XX.png`
- Sidecar metadata: source URL, capture time, natural/screenshot dimensions and SHA-256
- Persistent browser session: `storage/browser-profile/`

A screenshot is a rendered browser capture, not the original uploaded file. X may
resize, crop or transform the pixels it renders. Optional enhancement must create
a separate derivative and never overwrite the screenshot.

## API and platform limitations

Only posts returned by the configured official X API timeline endpoint are
processed. Historical coverage and access depend on API tier, available credits,
endpoint behavior, account visibility and token permissions. HTTP 402 (credits
depleted) stops API discovery; browser automation is not an API billing workaround.

The browser runner does not call undocumented endpoints, bypass login/CAPTCHA,
evade rate limits or defeat access controls. Local execution does not exempt
automation from X's terms. Run automated browser traversal only if the activity is
permitted for your account and use case. If not, use an allowed manual or official
export workflow instead.

No subject-matter or sensitivity filter is applied. Validation is technical only:
media-host source, loaded/visible state, dimensions, PNG decoding, aspect ratio
and SHA-256.

## Existing Docker dashboard

The repository retains the earlier FastAPI/Celery/Redis/PostgreSQL API-download
dashboard. That service is separate from the local Playwright runner. The
Playwright browser runner should be run directly on the user's PC so it can open
a visible desktop browser; the Docker API container cannot automatically control
the host desktop browser.

Keep `.env`, `storage/browser-profile/` and `storage/screenshots/` private.
See [docs/manual-capture.md](docs/manual-capture.md) for full details.
