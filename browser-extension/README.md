# AgentX Chrome extension — user-triggered post-media capture

The extension captures the largest visible X media image inside the currently
open post card. If no eligible media image is found, it captures the visible
post card instead. The user must click the extension button for every capture.

## Install or update

1. Pull the latest repository changes.
2. Open `chrome://extensions`.
3. If AgentX is already loaded unpacked, click **Reload** on its extension card.
   Otherwise enable **Developer mode**, choose **Load unpacked**, and select
   this `browser-extension` folder.
4. Open an individual X post in your normal Chrome session.
5. Click the AgentX extension icon, then **Capture post media**.

## Output and duplicate handling

Files are saved under `Downloads/AgentX-Captures/<post-id>/` using a SHA-256
prefix as the filename. A local Chrome extension storage record prevents
capturing identical screenshot bytes again. Chrome's download manager handles
the actual file save.

The extension uses `activeTab`, `scripting`, `downloads`, and `storage`.
It reads only the currently visible post card geometry and eligible image
element geometry after the user clicks capture. It does not read cookies,
credentials, messages, or profile timelines; it does not scroll or navigate.

The output is a screenshot crop of rendered browser pixels, not the original
uploaded media bytes. For posts with multiple images, the largest visible media
image is selected; capture each additional image by bringing it into view and
using the button again. Keep your local archive private.
