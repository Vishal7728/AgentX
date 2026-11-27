"""Local, visible-browser screenshot capture for user-authorized X pages.

This tool opens the supplied profile/post URL in a persistent Chromium session.
The user remains in control of scrolling and explicitly confirms each capture.
It does not call the X API, crawl timelines, auto-scroll, or bypass login/CAPTCHA.
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
MIN_WIDTH, MIN_HEIGHT = 160, 100


def safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]", "_", value)[:80] or "capture"


def validate_url(value: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS:
        raise ValueError("Only an https://x.com or https://twitter.com URL is accepted.")
    return value


def visible_image_candidates(article):
    candidates = []
    images = article.locator("img")
    for index in range(images.count()):
        img = images.nth(index)
        try:
            info = img.evaluate("""el => {
              const r = el.getBoundingClientRect();
              return {w:el.naturalWidth,h:el.naturalHeight,complete:el.complete,
                visible:r.width>0&&r.height>0&&r.bottom>0&&r.top<innerHeight&&r.right>0&&r.left<innerWidth,
                alt:el.alt||''};
            }""")
            if (info["complete"] and info["visible"] and
                    info["w"] >= MIN_WIDTH and info["h"] >= MIN_HEIGHT):
                candidates.append((img, info))
        except Exception:
            continue
    return candidates


def capture_article(page, output: Path) -> int:
    articles = page.locator("article")
    if articles.count() == 0:
        print("No post is visible. Scroll to a post in the browser and retry.")
        return 0
    article = articles.first
    if not article.is_visible():
        print("The first post is not visible. Scroll manually and retry.")
        return 0

    candidates = visible_image_candidates(article)
    if not candidates:
        print("No fully loaded, visible image was detected in this post.")
        return 0

    post_url = page.url
    match = re.search(r"/status/(\d+)", post_url)
    post_id = match.group(1) if match else datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    folder = output / safe_name(post_id)
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
            if (sw < 1 or sh < 1 or
                    abs((sw / sh) - (info["w"] / info["h"])) > 0.08):
                target.unlink(missing_ok=True)
                print(f"Skipped image {index}: screenshot boundary check failed.")
                continue
            digest = hashlib.sha256(target.read_bytes()).hexdigest()
            metadata = {
                "source_page": post_url,
                "captured_at": datetime.now(timezone.utc).isoformat(),
                "capture_method": "visible_img_element_screenshot",
                "browser_natural_dimensions": [info["w"], info["h"]],
                "screenshot_dimensions": [sw, sh],
                "sha256": digest,
                "alt": info["alt"],
                "note": "Screenshot is not the original uploaded file.",
            }
            target.with_suffix(".json").write_text(
                json.dumps(metadata, indent=2), encoding="utf-8"
            )
            saved += 1
        except Exception as exc:
            target.unlink(missing_ok=True)
            print(f"Image {index} failed verification: {exc}")
    print(f"Saved {saved}/{len(candidates)} verified screenshot(s): {folder}")
    return saved


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Open X locally and capture user-selected visible post images."
    )
    parser.add_argument("--url", required=True, help="X profile or post URL to open")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()

    try:
        url = validate_url(args.url)
    except ValueError as exc:
        parser.error(str(exc))

    output = Path(args.output).expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(
            str(PROFILE_DIR),
            headless=False,
            viewport={"width": 1440, "height": 1000},
            device_scale_factor=1,
            accept_downloads=False,
        )
        page = context.pages[0] if context.pages else context.new_page()
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            print("\nAgentX local browser is ready.")
            print("Sign in yourself if X asks. Complete any verification yourself.")
            print("Scroll manually to a post you are authorized to archive.")
            print("Press Enter here to screenshot the first visible post; type q to exit.\n")
            while True:
                command = input("AgentX > ").strip().lower()
                if command in {"q", "quit", "exit"}:
                    break
                capture_article(page, output)
        finally:
            context.close()


if __name__ == "__main__":
    main()
