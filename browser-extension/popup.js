const button = document.getElementById("capture");
const status = document.getElementById("status");
const X_HOSTS = ["x.com","www.x.com","twitter.com","www.twitter.com"];

async function inspectPost(tabId) {
  const results = await chrome.scripting.executeScript({
    target:{tabId,frameIds:[0]},
    func:()=>{
      try {
        const match=location.pathname.match(/\/status\/(\d+)/);
        if(!match) return {ok:false,error:"Open an individual X post URL containing /status/ID."};
        const postId=match[1];
        const photoViewer=/\/photo\/\d+/.test(location.pathname);
        const articles=[...document.querySelectorAll("article")];
        const article=articles.find(a=>[...a.querySelectorAll('a[href*="/status/"]')].some(a=>{
          try{return new URL(a.href).pathname.includes("/status/"+postId)}catch{return false}
        })) || (articles.length===1?articles[0]:null);
        if(!article&&!photoViewer) return {ok:false,error:"Could not identify the target post card. Open its direct /status/ page."};
        // X /status/ID/photo/N uses a full-screen media viewer, not the normal tweetPhoto article layout.
        const scope=photoViewer?document:article;

        const candidates=[];
        const add=(el,src,nw,nh,alt,kind)=>{
          const r=el.getBoundingClientRect();
          const left=Math.max(0,r.left),top=Math.max(0,r.top);
          const right=Math.min(innerWidth,r.right),bottom=Math.min(innerHeight,r.bottom);
          if(r.width<70||r.height<60||right-left<60||bottom-top<50||
             r.bottom<=0||r.top>=innerHeight||r.right<=0||r.left>=innerWidth)return;
          candidates.push({el,x:left,y:top,width:right-left,height:bottom-top,
            viewportWidth:innerWidth,viewportHeight:innerHeight,
            naturalWidth:nw||Math.round(r.width),naturalHeight:nh||Math.round(r.height),
            alt:alt||"",source:src||"",kind});
        };

        // X photo grid: each [data-testid="tweetPhoto"] is an individual media tile.
        const tiles=[...scope.querySelectorAll('[data-testid="tweetPhoto"]')];
        for(const tile of tiles){
          const img=[...tile.querySelectorAll("img")].find(i=>i.complete&&i.naturalWidth>=100&&i.naturalHeight>=80);
          const bg=getComputedStyle(tile).backgroundImage||"";
          const src=img?(img.currentSrc||img.src||""):(bg.match(/url\(["']?(.*?)["']?\)/)?.[1]||"");
          const target=img||tile;
          const rect=target.getBoundingClientRect();
          if(img || src || rect.width>0) add(target,src,img?.naturalWidth,img?.naturalHeight,img?.alt,"tweetPhoto");
        }

        // Fallback for X layouts that expose media images without tweetPhoto wrappers.
        if(!candidates.length){
          const imgs=[...scope.querySelectorAll("img")];
          const mediaImgs=imgs.filter(img=>{
            const src=img.currentSrc||img.src||"";
            return src.includes("pbs.twimg.com/media/")&&img.complete&&
              img.naturalWidth>=100&&img.naturalHeight>=80;
          });
          for(const img of mediaImgs) add(img,img.currentSrc||img.src,img.naturalWidth,img.naturalHeight,img.alt,"media-img");
          // In the /photo/N lightbox, prefer the largest visible image if X changes its image host/markup.
          if(photoViewer&&!candidates.length){
            const visible=imgs.filter(img=>{
              const r=img.getBoundingClientRect();
              return img.complete&&img.naturalWidth>=300&&img.naturalHeight>=300&&
                r.width>=180&&r.height>=180&&r.bottom>0&&r.top<innerHeight&&r.right>0&&r.left<innerWidth;
            }).sort((a,b)=>{
              const ra=a.getBoundingClientRect(),rb=b.getBoundingClientRect();
              return (rb.width*rb.height)-(ra.width*ra.height);
            });
            if(visible.length){
              const img=visible[0];
              add(img,img.currentSrc||img.src,img.naturalWidth,img.naturalHeight,img.alt,"photo-viewer-largest-image");
            }
          }
        }

        // Remove duplicates by near-identical geometry; retain each distinct grid tile.
        const unique=[];
        for(const item of candidates){
          const duplicate=unique.some(u=>Math.abs(u.x-item.x)<3&&Math.abs(u.y-item.y)<3&&
            Math.abs(u.width-item.width)<4&&Math.abs(u.height-item.height)<4);
          if(!duplicate)unique.push(item);
        }
        const media=unique.map(({el,...data})=>data);
        return {ok:true,postId,pageUrl:location.href,media,
          detectedPhotoTiles:tiles.length,articleImageCount:scope.querySelectorAll("img").length,photoViewer};
      }catch(error){return {ok:false,error:"Page inspection failed: "+(error?.message||String(error))}}
    }
  });
  if(!Array.isArray(results)||!results.length)throw new Error("Chrome could not inspect the active X tab. Reload the post.");
  const payload=results[0]?.result;
  if(!payload||typeof payload!=="object")throw new Error("No page inspection result. Reload the individual X post.");
  if(!payload.ok)throw new Error(payload.error||"Could not identify the post.");
  if(!Array.isArray(payload.media)||!payload.media.length){
    throw new Error("Post detected, but X did not expose visible photo tiles. Open the post detail page, bring its images into view, wait for loading, and retry.");
  }
  return payload;
}

async function cropViewport(dataUrl,box){
  const image=new Image();image.src=dataUrl;await image.decode();
  const xs=image.naturalWidth/box.viewportWidth,ys=image.naturalHeight/box.viewportHeight;
  const sx=Math.max(0,Math.round(box.x*xs)),sy=Math.max(0,Math.round(box.y*ys));
  const sw=Math.min(image.naturalWidth-sx,Math.max(1,Math.round(box.width*xs)));
  const sh=Math.min(image.naturalHeight-sy,Math.max(1,Math.round(box.height*ys)));
  const canvas=document.createElement("canvas");canvas.width=sw;canvas.height=sh;
  canvas.getContext("2d").drawImage(image,sx,sy,sw,sh,0,0,sw,sh);
  return new Promise((resolve,reject)=>canvas.toBlob(b=>b?resolve(b):reject(new Error("PNG encoding failed.")),"image/png"));
}
function blobDataUrl(blob){
  return new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(reader.result);
    reader.onerror=()=>reject(new Error("Could not prepare download."));reader.readAsDataURL(blob)});
}
async function saveBlob(blob,filename){
  return chrome.downloads.download({url:await blobDataUrl(blob),filename,saveAs:false,conflictAction:"uniquify"});
}

button.addEventListener("click",async()=>{
  button.disabled=true;status.textContent="Detecting X photo tiles…";
  try{
    const [tab]=await chrome.tabs.query({active:true,currentWindow:true});
    if(!tab?.id||!tab.url)throw new Error("No active tab.");
    if(!X_HOSTS.includes(new URL(tab.url).hostname))throw new Error("Open an X post first.");
    const inspected=await inspectPost(tab.id);
    status.textContent=`Detected ${inspected.media.length} photo tile(s). Capturing each separately…`;
    const viewport=await chrome.tabs.captureVisibleTab(tab.windowId,{format:"png"});
    const safeId=inspected.postId.replace(/[^0-9A-Za-z_-]/g,"_");
    let saved=0,duplicates=0,failed=0;
    for(let i=0;i<inspected.media.length;i++){
      const item=inspected.media[i];
      try{
        const blob=await cropViewport(viewport,item);
        const digestBytes=await crypto.subtle.digest("SHA-256",await blob.arrayBuffer());
        const digest=[...new Uint8Array(digestBytes)].map(v=>v.toString(16).padStart(2,"0")).join("");
        const key="sha256:"+digest;
        if((await chrome.storage.local.get(key))[key]){duplicates++;continue;}
        const index=String(i+1).padStart(2,"0");
        const base=`AgentX-Captures/${safeId}/image-${index}-${digest.slice(0,12)}`;
        await saveBlob(blob,base+".png");
        const manifest={post_id:inspected.postId,source_page:inspected.pageUrl,captured_at:new Date().toISOString(),
          image_index:i+1,detected_images_in_view:inspected.media.length,
          screenshot_dimensions:[Math.round(item.width),Math.round(item.height)],
          source_natural_dimensions:[item.naturalWidth,item.naturalHeight],
          source_image_url:item.source,alt:item.alt,sha256:digest,capture_method:"user_initiated_visible_photo_tile_crop",
          note:"Rendered browser screenshot crop; not the original uploaded media bytes."};
        await saveBlob(new Blob([JSON.stringify(manifest,null,2)],{type:"application/json"}),base+".json");
        await chrome.storage.local.set({[key]:{postId:inspected.postId,capturedAt:manifest.captured_at,sha256:digest}});
        saved++;
      }catch(error){failed++;console.warn("AgentX tile capture failed:",error)}
    }
    status.textContent=`Post ${safeId}: ${saved} saved, ${duplicates} duplicate(s), ${failed} failed. Downloads/AgentX-Captures/${safeId}/`;
  }catch(error){status.textContent=error.message||"Capture failed."}
  finally{button.disabled=false}
});
