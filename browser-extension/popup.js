const button = document.getElementById("capture");
const status = document.getElementById("status");
const X_HOSTS = ["x.com", "www.x.com", "twitter.com", "www.twitter.com"];

async function inspectPost(tabId) {
  const results = await chrome.scripting.executeScript({
    target: {tabId, frameIds:[0]},
    func: () => {
      try {
        const match = location.pathname.match(/\/status\/(\d+)/);
        if (!match) return {ok:false, error:"Open an individual X post URL containing /status/ID first."};
        const postId = match[1];
        const articles = [...document.querySelectorAll("article")];
        const article = articles.find(a =>
          [...a.querySelectorAll('a[href*="/status/"]')].some(a => {
            try { return new URL(a.href).pathname.includes("/status/" + postId); }
            catch { return false; }
          })
        ) || articles.find(a => {
          const r = a.getBoundingClientRect();
          return r.width > 0 && r.height > 0 && r.bottom > 0 && r.top < innerHeight;
        });
        if (!article) return {ok:false, error:"No visible post card found. Open the post detail page and wait for it to load."};

        const media = [];
        const seen = new Set();
        for (const img of [...article.querySelectorAll("img")]) {
          const src = img.currentSrc || img.src || "";
          const r = img.getBoundingClientRect();
          if (!src.includes("pbs.twimg.com/media/") || !img.complete ||
              img.naturalWidth < 120 || img.naturalHeight < 90 ||
              r.width < 80 || r.height < 60 || r.bottom <= 0 ||
              r.top >= innerHeight || r.right <= 0 || r.left >= innerWidth) continue;
          const key = src.split("?")[0] + "|" + Math.round(r.x) + "|" + Math.round(r.y);
          if (seen.has(key)) continue;
          seen.add(key);
          const left=Math.max(0,r.left), top=Math.max(0,r.top);
          const right=Math.min(innerWidth,r.right), bottom=Math.min(innerHeight,r.bottom);
          if (right<=left || bottom<=top) continue;
          media.push({x:left,y:top,width:right-left,height:bottom-top,
            viewportWidth:innerWidth,viewportHeight:innerHeight,
            naturalWidth:img.naturalWidth,naturalHeight:img.naturalHeight,
            alt:img.alt||"",source:src});
        }
        return {ok:true, postId, pageUrl:location.href, media,
          articleCount:articles.length, title:document.title};
      } catch (error) {
        return {ok:false,error:"Page inspection failed: " + (error?.message || String(error))};
      }
    }
  });
  if (!Array.isArray(results) || !results.length) {
    throw new Error("Chrome could not inspect the active X tab. Reload the post and try again.");
  }
  if (results[0]?.error) throw new Error("Chrome inspection error: " + (results[0].error.message || "unknown error"));
  const payload = results[0]?.result;
  if (!payload || typeof payload !== "object") {
    throw new Error("X page returned no inspection data. Check that this is an individual /status/ post, then reload it.");
  }
  if (!payload.ok) throw new Error(payload.error || "Could not identify the post.");
  if (!Array.isArray(payload.media) || payload.media.length === 0) {
    throw new Error("Post card found, but no loaded media images are visible. Scroll the post image(s) fully into view, wait for loading, then capture again.");
  }
  return payload;
}

async function cropViewport(dataUrl, box) {
  const image = new Image();
  image.src = dataUrl;
  await image.decode();
  const sxScale=image.naturalWidth/box.viewportWidth, syScale=image.naturalHeight/box.viewportHeight;
  const sx=Math.max(0,Math.round(box.x*sxScale)), sy=Math.max(0,Math.round(box.y*syScale));
  const sw=Math.min(image.naturalWidth-sx,Math.max(1,Math.round(box.width*sxScale)));
  const sh=Math.min(image.naturalHeight-sy,Math.max(1,Math.round(box.height*syScale)));
  const canvas=document.createElement("canvas"); canvas.width=sw; canvas.height=sh;
  canvas.getContext("2d").drawImage(image,sx,sy,sw,sh,0,0,sw,sh);
  return new Promise((resolve,reject)=>canvas.toBlob(b=>b?resolve(b):reject(new Error("Could not encode screenshot.")),"image/png"));
}

function blobDataUrl(blob) {
  return new Promise((resolve,reject)=>{
    const reader=new FileReader();
    reader.onload=()=>resolve(reader.result);
    reader.onerror=()=>reject(new Error("Could not prepare screenshot download."));
    reader.readAsDataURL(blob);
  });
}
async function saveBlob(blob,filename) {
  return chrome.downloads.download({url:await blobDataUrl(blob),filename,saveAs:false,conflictAction:"uniquify"});
}

button.addEventListener("click",async()=>{
  button.disabled=true; status.textContent="Inspecting the open post…";
  try {
    const [tab]=await chrome.tabs.query({active:true,currentWindow:true});
    if(!tab?.id||!tab.url) throw new Error("No active tab found.");
    const url=new URL(tab.url);
    if(!X_HOSTS.includes(url.hostname)) throw new Error("Open an X post in this tab first.");
    const inspected=await inspectPost(tab.id);
    status.textContent=`Found ${inspected.media.length} visible image(s). Saving separately…`;
    const viewport=await chrome.tabs.captureVisibleTab(tab.windowId,{format:"png"});
    const safeId=inspected.postId.replace(/[^0-9A-Za-z_-]/g,"_");
    let saved=0,duplicates=0,failed=0;
    for(let i=0;i<inspected.media.length;i++){
      const item=inspected.media[i];
      try{
        const blob=await cropViewport(viewport,item);
        const digestBytes=await crypto.subtle.digest("SHA-256",await blob.arrayBuffer());
        const digest=[...new Uint8Array(digestBytes)].map(v=>v.toString(16).padStart(2,"0")).join("");
        const key=`sha256:${digest}`;
        if((await chrome.storage.local.get(key))[key]){duplicates++;continue;}
        const index=String(i+1).padStart(2,"0");
        const base=`AgentX-Captures/${safeId}/image-${index}-${digest.slice(0,12)}`;
        await saveBlob(blob,`${base}.png`);
        const manifest={post_id:inspected.postId,source_page:inspected.pageUrl,
          captured_at:new Date().toISOString(),image_index:i+1,
          detected_images_in_view:inspected.media.length,
          screenshot_dimensions:[Math.round(item.width),Math.round(item.height)],
          source_natural_dimensions:[item.naturalWidth,item.naturalHeight],
          source_image_url:item.source,alt:item.alt,sha256:digest,
          capture_method:"user_initiated_individual_visible_image_crop",
          note:"Rendered browser screenshot crop; not original uploaded media bytes."};
        await saveBlob(new Blob([JSON.stringify(manifest,null,2)],{type:"application/json"}),`${base}.json`);
        await chrome.storage.local.set({[key]:{postId:inspected.postId,capturedAt:manifest.captured_at,sha256:digest}});
        saved++;
      }catch(error){failed++;console.warn("AgentX image capture failed:",error);}
    }
    status.textContent=`Post ${safeId}: ${saved} saved, ${duplicates} duplicate(s), ${failed} failed. Downloads/AgentX-Captures/${safeId}/`;
  }catch(error){status.textContent=error.message||"Capture failed.";}
  finally{button.disabled=false;}
});
