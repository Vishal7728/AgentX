# AgentX local browser screenshot capture

## Purpose

This mode uses the user's own PC and a visible Chromium browser. It does not use
an X API bearer token and does not download image URLs from X. It saves screenshots
of image elements rendered in the browser. A screenshot is not the original upload
and cannot recover pixels that X does not render.

## Setup (Windows PowerShell)

1. Install Python 3.11+.
2. From the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m playwright install chromium
```

3. Launch AgentX's local capture browser with the profile URL:

```powershell
$env:PYTHONPATH = "backend"
python -m app.browser_capture --url https://x.com/username
```

On macOS/Linux, activate the virtual environment and run the same Python command.
The browser profile is stored under `storage/browser-profile/`, so a user can sign
in once and reuse the local session. Keep this directory private.

## Capture workflow

- AgentX opens the submitted X URL in a visible browser on this PC.
- The user signs in or completes any verification directly with X.
- The user scrolls to the post they want to capture.
- Press Enter in the AgentX terminal to capture images in the first visible post.
- Type `q` to close the browser.

AgentX does not automate timeline traversal, auto-scroll, solve CAPTCHA, bypass
login, access controls, or rate limits. Use browser automation only where the
platform's current terms and your authorization permit it.

## Local output and integrity

Screenshots are saved to `storage/screenshots/<post-id-or-time>/`. Each PNG has
a JSON sidecar containing source page, capture time, browser natural dimensions,
screenshot dimensions and SHA-256. The capture is rejected if the PNG cannot be
decoded or its aspect ratio differs substantially from the browser-reported image.

The screenshot is a rendered browser capture, not the original uploaded image.
X may resize, crop, transform or omit pixels before rendering. Review captures
before relying on them. The persistent browser profile contains login cookies:
never commit it, share it, or store it in a public/synced folder.

## Technical validation only

No subject-matter or sensitivity classification is performed. Validation is limited
to image load state, visibility, dimensions, PNG decoding, aspect-ratio sanity and
cryptographic hash generation.

## Optional enhancement

If the local enhancement utility is used, it must write a separate derivative.
It must never overwrite the source screenshot. The untouched PNG remains the archive
master.
