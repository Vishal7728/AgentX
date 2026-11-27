const button = document.getElementById("capture");
const status = document.getElementById("status");
const X_HOSTS = ["x.com", "www.x.com", "twitter.com", "www.twitter.com"];

async function inspectPost(tabId) {
  const results = await chrome.scripting.executeScript({
    target: {tabId},
    func: () => {
      const match = location.pathname.match(/\/status\/(\d+)/);
      if (!match) throw new Error("Open an individual X post URL containing /status/ID first.");
      const postId = match[1];
      const articles = [...document.querySelectorAll("article")];
      const article = articles.find(a =>
        [...a.querySelectorAll('a[href*="/status/"]')].some(a => a.href.includes("/status/" + postId))
      ) || (articles.length === 1 ? articles[0] : null);
      if (!article) throw new Error("Could not identify the post card for this URL. Open the post directly, not the profile timeline.");

      const seen = new Set();
      const images = [...article.querySelectorAll("img")];
      const media = [];
      for (const img of images) {
        const src = img.currentSrc || img.src || "";
        const r = img.getBoundingClientRect();
        if (!src.includes("pbs.twimg.com/media/") ||
            !img.complete || img.naturalWidth < 120 || img.naturalHeight < 90 ||
            r.width < 80 || r.height < 60 ||
            r.bottom <= 0 || r.top >= innerHeight || r.right <= 0 || r.left >= innerWidth) continue;
        const key = src.split("?")[0] + "|" + Math.round(r.x) + "|" + Math.round(r.y);
        if (seen.has(key)) continue;
        seen.add(key);
        const left = Math.max(0, r.left), top = Math.max(0, r.top);
        const right = Math.min(innerWidth, r.right), bottom = Math.min(innerHeight, r.bottom);
        if (right <= left || bottom <= top) continue;
        media.push({
          x:left, y:top, width:right-left, height:bottom-top,
          viewportWidth:innerWidth, viewportHeight:innerHeight,
          naturalWidth:img.naturalWidth, naturalHeight:img.naturalHeight,
          alt:img.alt || "", source:src
        });
      }
      if (!media.length) throw new Error("No loaded X post images are visible. Bring the image grid fully into view and try again.");
      return {postId, pageUrl:location.href, media};
    }
  });
  if (!Array.isArray(results) || results.length === 0) {
    throw new Error("Chrome could not inspect this tab. Reload the X post and try again.");
  }
  const payload = results[0]?.result;
  if (!payload || typeof payload !== "object") {
    throw new Error("X page did not return post details. Make sure the post is fully loaded, then reload the tab and try again.");
  }
  if (!Array.isArray(payload.media)) {
    throw new Error("Post image detection did not complete. Reload the X post and try again.");
  }
  return payload;
}

async function cropViewport(dataUrl, box) {
  const image = new Image();
  image.src = dataUrl;
  await image.decode();
  const sxScale = image.naturalWidth / box.viewportWidth;
  const syScale = image.naturalHeight / box.viewportHeight;
  const sx = Math.max(0, Math.round(box.x * sxScale));
  const sy = Math.max(0, Math.round(box.y * syScale));
  const sw = Math.min(image.naturalWidth - sx, Math.max(1, Math.round(box.width * sxScale)));
  const sh = Math.min(image.naturalHeight - sy, Math.max(1, Math.round(box.height * syScale)));
  const canvas = document.createElement("canvas");
  canvas.width = sw; canvas.height = sh;
  canvas.getContext("2d").drawImage(image, sx, sy, sw, sh, 0, 0, sw, sh);
  return await new Promise((resolve, reject) => canvas.toBlob(blob => blob ? resolve(blob) : reject(new Error("Could not encode screenshot.")), "image/png"));
}

function blobDataUrl(blob) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = () => reject(new Error("Could not prepare screenshot download."));
    reader.readAsDataURL(blob);
  });
}

async function saveBlob(blob, filename) {
  const url = await blobDataUrl(blob);
  return chrome.downloads.download({url, filename, saveAs:false, conflictAction:"uniquify"});
}

button.addEventListener("click", async () => {
  button.disabled = true;
  status.textContent = "Inspecting the open post…";
  try {
    const [tab] = await chrome.tabs.query({active:true, currentWindow:true});
    if (!tab?.id || !tab.url) throw new Error("No active tab found.");
    const url = new URL(tab.url);
    if (!X_HOSTS.includes(url.hostname)) throw new Error("Open an X post in this tab first.");

    const inspected = await inspectPost(tab.id);
    if (!inspected || !Array.isArray(inspected.media) || inspected.media.length === 0) {
      throw new Error("No eligible post images found. Open the post directly, wait for its images to load, and try again.");
    }
    status.textContent = `Found ${inspected.media.length} visible image(s). Capturing individually…`;
    const viewport = await chrome.tabs.captureVisibleTab(tab.windowId, {format:"png"});
    const safeId = inspected.postId.replace(/[^0-9A-Za-z_-]/g, "_");
    let saved = 0, duplicates = 0, failed = 0;

    for (let i = 0; i < inspected.media.length; i++) {
      const item = inspected.media[i];
      try {
        const blob = await cropViewport(viewport, item);
        const digestBytes = await crypto.subtle.digest("SHA-256", await blob.arrayBuffer());
        const digest = [...new Uint8Array(digestBytes)].map(v=>v.toString(16).padStart(2,"0")).join("");
        const key = `sha256:${digest}`;
        const existing = await chrome.storage.local.get(key);
        if (existing[key]) { duplicates++; continue; }

        const index = String(i+1).padStart(2,"0");
        const base = `AgentX-Captures/${safeId}/image-${index}-${digest.slice(0,12)}`;
        await saveBlob(blob, `${base}.png`);
        const manifest = {
          post_id: inspected.postId,
          source_page: inspected.pageUrl,
          captured_at: new Date().toISOString(),
          image_index: i+1,
          detected_images_in_view: inspected.media.length,
          screenshot_dimensions: [Math.round(item.width), Math.round(item.height)],
          source_natural_dimensions: [item.naturalWidth, item.naturalHeight],
          source_image_url: item.source,
          alt: item.alt,
          sha256: digest,
          capture_method: "user_initiated_individual_visible_image_crop",
          note: "Rendered browser screenshot crop; not the original uploaded media bytes."
        };
        await saveBlob(new Blob([JSON.stringify(manifest,null,2)], {type:"application/json"}), `${base}.json`);
        await chrome.storage.local.set({[key]:{postId:inspected.postId, capturedAt:manifest.captured_at, sha256:digest}});
        saved++;
      } catch (error) {
        failed++;
        console.warn("AgentX image capture failed:", error);
      }
    }
    status.textContent = `Post ${safeId}: ${saved} saved, ${duplicates} duplicate(s), ${failed} failed. Check Downloads/AgentX-Captures/${safeId}/`;
  } catch (error) {
    status.textContent = error.message || "Capture failed.";
  } finally {
    button.disabled = false;
  }
});
