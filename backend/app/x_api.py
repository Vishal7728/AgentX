import httpx
from .config import X_API_BASE, X_BEARER_TOKEN, HTTP_TIMEOUT_SECONDS

class XAPIError(Exception):
    pass

def _client():
    if not X_BEARER_TOKEN or X_BEARER_TOKEN == "replace_me":
        raise XAPIError("X_BEARER_TOKEN is not configured. Add an authorized bearer token to .env.")
    return httpx.Client(
        base_url=X_API_BASE,
        headers={"Authorization": f"Bearer {X_BEARER_TOKEN}"},
        timeout=HTTP_TIMEOUT_SECONDS,
        follow_redirects=True,
    )

def resolve_user(username: str) -> dict:
    with _client() as client:
        response = client.get(f"/users/by/username/{username}")
        if response.status_code >= 400:
            raise XAPIError(f"X user lookup failed ({response.status_code}): {response.text[:500]}")
        return response.json().get("data") or {}

def get_user_posts(user_id: str, pagination_token: str | None = None) -> dict:
    params = {
        "max_results": 100,
        "tweet.fields": "created_at,attachments",
        "expansions": "attachments.media_keys",
        "media.fields": "media_key,type,url,width,height,alt_text",
    }
    if pagination_token:
        params["pagination_token"] = pagination_token
    with _client() as client:
        response = client.get(f"/users/{user_id}/tweets", params=params)
        if response.status_code == 429:
            raise XAPIError("X API rate limit reached (429); respect the documented reset window.")
        if response.status_code >= 400:
            raise XAPIError(f"X timeline request failed ({response.status_code}): {response.text[:500]}")
        return response.json()
