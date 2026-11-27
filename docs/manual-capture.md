# AgentX automatic local-browser screenshot archive

## What this mode does

AgentX uses the configured X API bearer token to discover the posts returned by
the authorized user-timeline endpoint. It then opens each discovered post URL in
a visible Chromium browser running on the user's PC and captures rendered X media
images from the post. Screenshots are stored locally with JSON manifests and
SHA-256 checksums.

This is a screenshot archive, not an original-media downloader. The browser can
only capture pixels X actually renders; screenshots are not the original uploaded
bytes and may be resized or transformed.

## Requirements

- Python 3.11+
- An X developer bearer token with sufficient current API access and credits for
  user lookup and user-post timeline endpoints
- Chromium installed through Playwright
- Authorization to archive the account/content, and confirmation that the
  automated browser activity is permitted under X's current terms

## Setup (Windows PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m playwright install chromium
Copy-Item .env.example .env
notepad .env
```

Set `X_BEARER_TOKEN` in `.env`. Do not commit or share this file.

## Run an automatic archive

From the repository root:

```powershell
$env:PYTHONPATH = "backend"
python -m app.browser_capture --url https://x.com/username --confirm-platform-permission
```

Optional small test run:

```powershell
python -m app.browser_capture --url https://x.com/username --max-posts 10 --confirm-platform-permission
```

AgentX will:
1. Resolve the profile using the official API.
2. Fetch timeline pages using API pagination and collect returned post IDs.
3. Open a persistent, visible Chromium browser on this PC.
4. Ask for one-time user readiness confirmation after any required login.
5. Visit each API-discovered post URL sequentially.
6. Capture visible image elements served from X's media host.
7. Validate PNG decoding, dimensions and aspect-ratio sanity.
8. Save SHA-256 and metadata sidecars in `storage/screenshots/<post-id>/`.

The user does not need to scroll or confirm every post. The browser profile is
stored in `storage/browser-profile/` and should be kept private. The user may
need to sign in or complete verification directly in the browser.

## API and platform limits

The runner only processes posts returned by the configured official API endpoint.
It cannot promise every historical post: results depend on API tier, credits,
timeline endpoint behavior, account visibility and the token's permissions. If
the API returns HTTP 402 (credits depleted), discovery stops; browser automation
is not used to evade API billing or access restrictions.

The browser runner does not call undocumented endpoints, scrape hidden APIs,
bypass login, solve CAPTCHA, evade rate limits or continue through access denials.
It is gated behind an explicit confirmation flag because local execution does not
remove the platform's terms or restrictions. If X does not permit the automated
browser traversal for the intended use, do not run it; use a permitted manual or
official export workflow instead.

## Local output and privacy

Screenshots are saved to `storage/screenshots/`; each PNG has a JSON sidecar with
source URL, capture timestamp, natural and screenshot dimensions, alt text and
SHA-256. Browser cookies/session data are stored under
`storage/browser-profile/`. Keep both folders private and never commit them.

No content or sensitivity classification is performed. Checks are technical only:
X media-host image source, loaded/visible state, dimensions, PNG decoding,
aspect-ratio sanity and SHA-256.

## Optional enhancement

The optional local enhancement utility must write a separate derivative and must
never overwrite the source screenshot. Keep the untouched PNG as the archive master.
