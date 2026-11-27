"""API-discovered, local-browser screenshot archive.

X API is used only to enumerate posts the configured bearer token can access.
A visible Chromium session on this PC opens each discovered post and screenshots
rendered image elements. This mode is gated by an explicit platform-permission
confirmation. It never calls undocumented endpoints or bypasses access controls.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import time
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


def load_local_env() -> None:
    env_file = ROOT / ".env"
    if not env_file.exists():
        return
    for raw in env_file.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]", "_", value)[:80] or "capture"


def validate_profile_url(value: str) -> tuple[str, str]:
    parsed = urlparse(value)
    if parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS:
        raise ValueError("Only an https://x.com or https://twitter.com URL is accepted.")
    parts = [p for p in parsed.path.split("/") if p]
    if len(parts) != 1 or not re.fullmatch(r"[A-Za-z0-9_]{1,15}", parts[0]):
        raise ValueError("Enter a profile URL such as https://x.com/username.")
    if parts[0].lower() in {"home", "explore", "search", "settings", "i", "messages", "notifications"}:
        raise ValueError("The URL does not identify a profile.")
    return parts[0], f"https://x.com/{parts[0]}"


def discover_posts(username: str, max_posts: int | None) -> list[dict]:
    # Import after loading .env so the API module sees the local bearer token.
    from app.x_api import resolve_user, get_user_posts

    user = resolve_user(username)
    if not user or not user.get("id"):
        raise RuntimeError("X API did not return a user ID for this profile.")
    user_id = str(user["id"])
    posts: list[dict] = []
    token = None
    seen: set[str] = set()
    while True:
        page = get_user_posts(user_id, token)
        for item in page.get("data") or []:
            post_id = str(item.get("id") or "")
            if not post_id or post_id in seen:
                continue
            seen.add(post_id)
            posts.append({
                "id": post_id,
                "url": f"https://x.com/{username}/status/{post_id}",
                "created_at": item.get("created_at"),
            })
            if max_posts and len(posts) >= max_posts:
                return posts
        token = (page.get("meta") or {}).get("next_token")
        if not token:
            break
        # Conservative pacing between documented API page requests.
        time.sleep(2.0)
    return posts


def capture_visible_post(page, output: Path, post: dict) -> int:
    page.goto(post["url"], wait_until="domcontentloaded", timeout=60000)
    try:
        page.locator("article").first.wait_for(state="visible", timeout=15000)
    except Exception:
        print(f"  SKIP {post['id']}: no visible post article (login/visibility/access may be required).")
        return 0

    article = page.locator("article").first
    images = article.locator("img")
    candidates = []
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

    if not candidates:
        print(f"  NO IMAGE {post['id']}")
        return 0

    folder = output / safe_name(post["id"])
    folder.mkdir(parents=True, exist_ok=True)
    saved = 0
    for index, (img, info) in enumerate(candidates, start=1):
        target = folder / f"image-{index:02d}.png"
        if target.exists() and target.with_suffix(".json").exists():
            print(f"  EXISTS {post['id']} image {index}")
            continue
        try:
            img.screenshot(path=str(target), animations="disabled", timeout=12000)
            with Image.open(target) as shot:
                shot.load()
                sw, sh = shot.size
            if (sw < 1 or sh < 1 or
                    abs((sw / sh) - (info["w"] / info["h"])) > 0.08):
                target.unlink(missing_ok=True)
                print(f"  REJECTED {post['id']} image {index}: boundary check failed")
                continue
            digest = hashlib.sha256(target.read_bytes()).hexdigest()
            metadata = {
                "source_page": post["url"],
                "captured_at": datetime.now(timezone.utc).isoformat(),
                "capture_method": "visible_img_element_screenshot",
                "browser_natural_dimensions": [info["w"], info["h"]],
                "screenshot_dimensions": [sw, sh],
                "sha256": digest,
                "alt": info["alt"],
                "note": "Rendered screenshot, not the original uploaded file.",
            }
            target.with_suffix(".json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
            saved += 1
        except Exception as exc:
            target.unlink(missing_ok=True)
            print(f"  FAILED {post['id']} image {index}: {exc}")
    print(f"  SAVED {post['id']}: {saved}/{len(candidates)} screenshot(s)")
    return saved


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Discover accessible X posts via API and screenshot them in local Chromium."
    )
    parser.add_argument("--url", required=True, help="X profile URL")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--max-posts", type=int, default=0, help="Optional test limit; 0 means all API-accessible posts")
    parser.add_argument("--confirm-platform-permission", action="store_true",
                        help="Confirm you are authorized and X's current terms permit this automated browser workflow.")
    args = parser.parse_args()

    if not args.confirm_platform_permission:
        parser.error("Before automation, review X's current terms and pass --confirm-platform-permission only if this activity is permitted.")
    if args.max_posts < 0:
        parser.error("--max-posts cannot be negative.")

    try:
        username, profile_url = validate_profile_url(args.url)
    except ValueError as exc:
        parser.error(str(exc))

    load_local_env()
    if not os.environ.get("X_BEARER_TOKEN") or os.environ.get("X_BEARER_TOKEN") == "replace_me":
        parser.error("Set X_BEARER_TOKEN in the repository .env file first.")

    output = Path(args.output).expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    max_posts = args.max_posts or None

    print(f"Discovering posts for @{username} through the configured X API token…")
    posts = discover_posts(username, max_posts)
    print(f"Discovered {len(posts)} API-accessible posts.")
    if not posts:
        print("No posts were returned by the API.")
        return

    with sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(
            str(PROFILE_DIR), headless=False,
            viewport={"width": 1440, "height": 1000},
            device_scale_factor=1, accept_downloads=False,
        )
        page = context.pages[0] if context.pages else context.new_page()
        try:
            page.goto(profile_url, wait_until="domcontentloaded", timeout=60000)
            print("\nLocal browser opened. Sign in yourself if required.")
            print("If login/CAPTCHA/access confirmation appears, complete it yourself in the browser.")
            input("When the profile is ready, press Enter here to begin automatic post capture… ")
            total = 0
            for index, post in enumerate(posts, start=1):
                print(f"[{index}/{len(posts)}] {post['url']}")
                total += capture_visible_post(page, output, post)
                # Deliberate pacing; this is not a rate-limit workaround.
                time.sleep(2.5)
            print(f"\nFinished. Captured {total} verified screenshot(s) from {len(posts)} API-accessible posts.")
            print(f"Local archive: {output}")
        finally:
            context.close()


if __name__ == "__main__":
    load_local_env()
    main()
