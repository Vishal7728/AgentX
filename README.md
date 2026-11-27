# AgentX — Local X Screenshot Archive

AgentX is a local-first tool for saving screenshots of X posts that the user
opens and selects in a visible local Chromium browser.

## Windows setup

From the repository root, activate the virtual environment, install dependencies
and Chromium:

```bat
.venv\Scripts\activate
pip install -r requirements.txt
python -m playwright install chromium
```

## Manual capture (no X API token or API credits required)

Run from the repository root in Command Prompt:

```bat
set PYTHONPATH=backend
python -m app.browser_capture --url https://x.com/username --manual
```

Replace `username` with the profile you are authorized to view and archive.
A visible Chromium window opens using a persistent local browser profile. Sign in
yourself if X requests it. Navigate manually to an individual post. Return to the
Command Prompt and press Enter to capture the currently open post; type `q` and
press Enter to finish. Repeat for each post you choose.

This mode does not use the X API, enumerate profile posts, auto-scroll, or
automatically navigate from one post to another. It only captures eligible,
visible X media images in the currently open post after your explicit Enter
keypress. It does not bypass login, CAPTCHA, access controls or platform rules.

## Output

- Screenshots: `storage/screenshots/<post-id>/image-XX.png`
- JSON sidecars: source page, capture time, dimensions, SHA-256 and alt text
- Persistent browser session: `storage/browser-profile/`

Screenshots represent rendered pixels, not original uploaded bytes. Optional
enhancement must create a separate derivative and never overwrite the master
screenshot. Keep `.env`, `storage/browser-profile/` and `storage/screenshots/`
private.

## API-based mode

The older API-discovery mode remains available separately and requires an X
developer bearer token with appropriate endpoint access and credits. HTTP 402
(credits depleted) stops discovery. Browser capture is not an API billing
workaround.
