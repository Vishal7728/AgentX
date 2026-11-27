const button = document.getElementById("capture");
const status = document.getElementById("status");

button.addEventListener("click", async () => {
  button.disabled = true;
  status.textContent = "Capturing visible tab…";
  try {
    const [tab] = await chrome.tabs.query({active: true, currentWindow: true});
    if (!tab || !tab.url) throw new Error("No active browser tab found.");
    const url = new URL(tab.url);
    if (!["x.com", "www.x.com", "twitter.com", "www.twitter.com"].includes(url.hostname)) {
      throw new Error("Open the X post in this tab before capturing.");
    }
    const dataUrl = await chrome.tabs.captureVisibleTab(tab.windowId, {format: "png"});
    const stamp = new Date().toISOString().replace(/[:.]/g, "-");
    const match = url.pathname.match(/\/status\/(\d+)/);
    const postPart = match ? match[1] : "x-page";
    await chrome.downloads.download({
      url: dataUrl,
      filename: `AgentX-Captures/${postPart}-${stamp}.png`,
      saveAs: false
    });
    status.textContent = "Screenshot saved to Downloads/AgentX-Captures.";
  } catch (error) {
    status.textContent = error.message || "Capture failed.";
  } finally {
    button.disabled = false;
  }
});
