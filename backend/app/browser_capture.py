"""User-controlled screenshot capture companion.

Opens a persistent, visible browser. The user signs in and navigates manually.
Press Enter in this terminal to capture image elements from the currently visible
X post; 'q' exits. No profile crawling, scrolling, or automatic post traversal.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = ROOT / "storage" / "screenshots"
PROFILE_DIR = ROOT / "storage" / "browser-profile"
ALLOWED_HOSTS = {"x.com", "www.x.com", "twitter.com", "www.twitter.com"}

def safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]", "_", value)[:80] or "capture"

def main() -> None:
    parser = argparse.ArgumentParser(description="Capture user-selected, visible X post images.")
    parser.add_argument("--url", default="https://x.com/", help="Page to open; user navigates manually.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()
    parsed = urlparse(args.url)
    if parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS:
        parser.error("Only an https://x.com or https://twitter.com URL is accepted.")
    out = Path(args.output).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            str(PROFILE_DIR), headless=False, viewport={"width": 1440, "height": 1000},
            device_scale_factor=1, accept_downloads=False,
        )
        page = context.pages[0] if context.pages else context.new_page()
        page.goto(args.url, wait_until="domcontentloaded")
        print("\nAgentX manual capture browser is ready.")
        print("Sign in if needed, then navigate yourself to a post you are authorized to archive.")
        print("Press Enter here to capture image(s) in the first visible post; type q to exit.\n")
        try:
            while True:
                command = input("AgentX > ").strip().lower()
                if command in {"q", "quit", "exit"}:
                    break
                articles = page.locator("article")
                if articles.count() == 0:
                    print("No post/article is visible. Navigate to a post and try again.")
                    continue
                article = articles.first
                if not article.is_visible():
                    print("The first post is not visible. Scroll manually and retry.")
                    continue
                images = article.locator("img")
                candidates = []
                for index in range(images.count()):
                    img = images.nth(index)
                    try:
                        info = img.evaluate("""el => {
                          const r=el.getBoundingClientRect();
                          return {w:el.naturalWidth,h:el.naturalHeight,complete:el.complete,
                            visible:r.width>0&&r.height>0&&r.bottom>0&&r.top<innerHeight&&r.right>0&&r.left<innerWidth,
                            alt:el.alt||''};
                        }""")
                        if info["complete"] and info["visible"] and info["w"] >= 160 and info["h"] >= 100:
                            candidates.append((img, info))
                    except Exception:
                        continue
                if not candidates:
                    print("No fully loaded, visible image was detected in this post.")
                    continue
                post_url = page.url
                post_id_match = re.search(r"/status/(\d+)", post_url)
                post_id = post_id_match.group(1) if post_id_match else datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
                folder = out / safe_name(post_id)
                folder.mkdir(parents=True, exist_ok=True)
                saved = 0
                for index, (img, info) in enumerate(candidates, start=1):
                    target = folder / f"image-{index:02d}.png"
                    try:
                        img.scroll_into_view_if_needed(timeout=3000)
                        img.screenshot(path=str(target), animations="disabled", timeout=10000)
                        with Image.open(target) as shot:
                            shot.load()
                            sw, sh = shot.size
                        if sw < 1 or sh < 1 or abs((sw / sh) - (info["w"] / info["h"])) > 0.08:
                            target.unlink(missing_ok=True)
                            print(f"Skipped image {index}: screenshot dimensions failed boundary check.")
                            continue
                        digest = hashlib.sha256(target.read_bytes()).hexdigest()
                        meta = {
                            "source_page": post_url, "captured_at": datetime.now(timezone.utc).isoformat(),
                            "capture_method": "visible_img_element_screenshot",
                            "browser_natural_dimensions": [info["w"], info["h"]],
                            "screenshot_dimensions": [sw, sh], "sha256": digest,
                            "alt": info["alt"], "note": "Screenshot is not the original uploaded file.",
                        }
                        target.with_suffix(".json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
                        saved += 1
                    except Exception as exc:
                        target.unlink(missing_ok=True)
                        print(f"Image {index} failed verification: {exc}")
                print(f"Saved {saved}/{len(candidates)} verified image screenshot(s) to {folder}")
        finally:
            context.close()

if __name__ == "__main__":
    main()
