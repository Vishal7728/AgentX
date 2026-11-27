# AgentX manual browser capture (local-first)

## What this mode does

This companion launches a visible Chromium browser with a persistent local profile.
You sign in yourself, navigate to a post yourself, and explicitly press Enter in the
terminal to capture image elements from the first visible post. It does not crawl
profiles, auto-scroll, open posts, or enumerate a timeline.

This is a **screenshot archive**, not an original-media downloader. A screenshot
cannot restore source pixels, may be affected by display scaling/cropping, and must
not be labelled as the original upload. The companion records browser-reported
natural dimensions, screenshot dimensions, source page, capture time, and SHA-256.
It rejects screenshots that fail basic dimension/aspect-ratio checks. Review every
capture before relying on it.

Only use this with content and accounts you are authorized to access and archive,
and only where the platform permits the activity. Do not use it to bypass API
credits, access controls, rate limits, or platform restrictions. If automated
browser capture is not permitted for the account/content, do not use this mode.

## Setup (Windows PowerShell)

1. Install Python 3.11+.
2. From the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m playwright install chromium
```

3. Start the visible browser:

```powershell
$env:PYTHONPATH = "backend"
python -m app.browser_capture --url https://x.com/
```

4. Sign in in the opened browser if required. Navigate manually to the authorized post.
5. Return to the terminal and press Enter to capture visible image elements. Type `q`
   to close the browser.

Files are written to `storage/screenshots/<post-id-or-time>/`. Each PNG has a
sidecar JSON manifest. The persistent browser profile is in
`storage/browser-profile/`; keep it private and never commit it. Sign out in the
browser when finished.

## Full-image capture design

- Detect loaded image elements in the first visible post.
- Read natural dimensions and visible bounding box before capture.
- Capture the image element itself, not the entire viewport.
- Validate the saved PNG and compare aspect ratios to detect obvious clipping.
- Save a SHA-256 digest and dimensions in a sidecar manifest.
- Never upscale or overwrite the capture. Enhancement should be a separate,
  optional derivative pipeline, preserving the screenshot byte-for-byte.

## Limitations

A web page can display a resized or transformed rendition. Element screenshots are
not proof of original upload quality. Multi-image posts are captured as separate
visible image elements; image carousels or hidden slides must be navigated by the
user and captured separately. This companion intentionally does not automate
timeline browsing.
