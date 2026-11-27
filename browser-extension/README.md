# AgentX Chrome extension — visible-tab capture

This extension captures only the visible browser viewport after the user clicks
its toolbar button. It does not read page contents, enumerate posts, scroll,
navigate, access cookies, or automate login.

## Install in Chrome

1. Open `chrome://extensions`.
2. Turn on **Developer mode**.
3. Select **Load unpacked**.
4. Choose the repository's `browser-extension` folder.
5. Open an individual X post in your normal Chrome session.
6. Click the AgentX extension icon, then **Capture visible tab**.

Screenshots are saved under `Downloads/AgentX-Captures/`. The extension uses
Chrome's `activeTab` permission and the user-initiated visible-tab capture API.
It does not access or transfer your X credentials or browser cookies.

The output is a screenshot of the entire visible tab viewport, not an extracted
original image file. Make sure the post/media is visible before capture.
