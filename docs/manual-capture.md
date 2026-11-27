# Manual local-browser screenshot capture

## What this mode does

AgentX opens an X profile in a visible Chromium browser on your PC. You manually
navigate to an individual post, then explicitly trigger a screenshot from the
Command Prompt. It does not require an X API bearer token or API credits.

This is a screenshot archive, not an original-media downloader. The browser
captures rendered pixels that are visible in the currently open post. X may
resize, crop or transform the displayed media.

## Run on Windows

From the repository root, with the virtual environment activated:

```bat
set PYTHONPATH=backend
python -m app.browser_capture --url https://x.com/username --manual
```

Replace `username` with the profile you are authorized to view and archive.
Sign in yourself in the browser if required. Open one individual post at a time.
Return to the Command Prompt and press Enter to capture the current post. Type
`q` and press Enter to close the browser and finish.

## Scope and limitations

- No X API calls, API token, or API credits are used in manual mode.
- AgentX does not enumerate profile posts, auto-scroll, or automatically move
  between posts. The user chooses each post and initiates each capture.
- Only visible, loaded image elements served from X's media host and meeting
  basic technical dimensions are considered.
- The tool does not bypass login, CAPTCHA, access controls, rate limits or
  platform restrictions. Only use it for content you are authorized to access
  and archive, consistent with X's current terms and applicable law.

## Local output and privacy

Screenshots are stored in `storage/screenshots/<post-id>/` with JSON sidecars
containing source URL, capture timestamp, dimensions, SHA-256 and alt text.
Persistent browser cookies/session data are stored in
`storage/browser-profile/`. Keep these folders private and do not commit them.

## Optional enhancement

Any enhancement must write a separate derivative and must never overwrite the
original screenshot. Keep the untouched PNG as the archive master.
