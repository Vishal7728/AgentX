const button = document.getElementById("capture");
const status = document.getElementById("status");
const X_HOSTS = ["x.com", "www.x.com", "twitter.com", "www.twitter.com"];

async function getCaptureTarget(tabId) {
  const results = await chrome.scripting.executeScript({
    target: {tabId},
    func: () => {
      const post = document.querySelector("article");
      if (!post) throw new Error("No visible post card found. Open an individual post first.");
      const postRect = post.getBoundingClientRect();
      const media = [...post.querySelectorAll("img")]
        .filter(img => {
          const r = img.getBoundingClientRect();
          return img.complete && img.naturalWidth >= 120 && img.naturalHeight >= 90 &&
            (img.currentSrc || img.src).includes("pbs.twimg.com/media/") &&
            r.width > 0 && r.height > 0 && r.bottom > 0 && r.top < innerHeight &&
            r.right > 0 && r.left < innerWidth;
        })
        .sort((a,b) => {
          const ar = a.getBoundingClientRect(), br = b.getBoundingClientRect();
          return (br.width*br.height) - (ar.width*ar.height);
        })[0];
      const chosen = media || post;
      const r = chosen.getBoundingClientRect();
      const left = Math.max(0, r.left);
      const top = Math.max(0, r.top);
      const right = Math.min(innerWidth, r.right);
      const bottom = Math.min(innerHeight, r.bottom);
      if (right <= left || bottom <= top) throw new Error("Post media is outside the visible area. Bring it into view and try again.");
      const statusMatch = location.pathname.match(/\/status\/(\d+)/);
      const id = statusMatch ? statusMatch[1] : "post";
      return {
        x:left, y:top, width:right-left, height:bottom-top,
        viewportWidth:innerWidth, viewportHeight:innerHeight,
        postId:id, targetType:media ? "media_image" : "post_card"
      };
    }
  });
  return results[0].result;
}

async function cropViewport(dataUrl, box) {
  const image = new Image();
  image.src = dataUrl;
  await image.decode();
  const scaleX = image.naturalWidth / box.viewportWidth;
  const scaleY = image.naturalHeight / box.viewportHeight;
  const sx = Math.round(box.x * scaleX);
  const sy = Math.round(box.y * scaleY);
  const sw = Math.max(1, Math.round(box.width * scaleX));
  const sh = Math.max(1, Math.round(box.height * scaleY));
  const canvas = document.createElement("canvas");
  canvas.width = sw;
  canvas.height = sh;
  const ctx = canvas.getContext("2d");
  ctx.drawImage(image, sx, sy, sw, sh, 0, 0, sw, sh);
  return await new Promise(resolve => canvas.toBlob(resolve, "image/png"));
}

button.addEventListener("click", async () => {
  button.disabled = true;
  status.textContent = "Preparing post capture…";
  try {
    const [tab] = await chrome.tabs.query({active:true, currentWindow:true});
    if (!tab?.id || !tab.url) throw new Error("No active tab found.");
    const url = new URL(tab.url);
    if (!X_HOSTS.includes(url.hostname)) throw new Error("Open an X post in this tab first.");

    const box = await getCaptureTarget(tab.id);
    const viewport = await chrome.tabs.captureVisibleTab(tab.windowId, {format:"png"});
    const blob = await cropViewport(viewport, box);
    const bytes = await blob.arrayBuffer();
    const digestBytes = await crypto.subtle.digest("SHA-256", bytes);
    const digest = [...new Uint8Array(digestBytes)].map(v=>v.toString(16).padStart(2,"0")).join("");
    const key = `sha256:${digest}`;
    const prior = await chrome.storage.local.get(key);
    if (prior[key]) {
      status.textContent = "Duplicate detected. This screenshot is already in your archive.";
      return;
    }

    const objectUrl = URL.createObjectURL(blob);
    const safeId = box.postId.replace(/[^0-9A-Za-z_-]/g, "_");
    await chrome.downloads.download({
      url:objectUrl,
      filename:`AgentX-Captures/${safeId}/${digest.slice(0,16)}.png`,
      saveAs:false
    });
    await chrome.storage.local.set({[key]:{postId:box.postId, capturedAt:new Date().toISOString(), sha256:digest}});
    status.textContent = `Saved ${box.targetType} screenshot. Duplicate check passed.\nDownloads/AgentX-Captures/${safeId}/`;
    setTimeout(()=>URL.revokeObjectURL(objectUrl), 60000);
  } catch (error) {
    status.textContent = error.message || "Capture failed.";
  } finally {
    button.disabled = false;
  }
});
