"""Social media publishing via Zernio API (direct HTTP — no SDK needed)."""
import os
import requests

ZERNIO_BASE = "https://api.zernio.com/api/v1"


def _headers():
    key = os.getenv("ZERNIO_API_KEY") or os.getenv("GETLATE_API_KEY", "")
    return {"Authorization": f"Bearer {key}", "Content-Type": "application/json"} if key else None


def get_connected_accounts():
    """Return list of connected social media accounts from Zernio."""
    hdrs = _headers()
    if not hdrs:
        return [
            {"platform": "instagram", "name": "Demo Account", "_id": "demo-ig"},
            {"platform": "tiktok",    "name": "Demo Account", "_id": "demo-tt"},
        ]
    try:
        r = requests.get(f"{ZERNIO_BASE}/accounts", headers=hdrs, timeout=10)
        r.raise_for_status()
        return r.json().get("accounts", r.json()) if isinstance(r.json(), dict) else r.json()
    except Exception:
        return []


def publish_post(content_item, platforms=None, emit_event=None):
    """Publish content to social media via Zernio."""
    hdrs = _headers()
    if not hdrs:
        return {"status": "demo", "post_id": "demo-123", "demo": True}

    # Get connected accounts
    accounts = get_connected_accounts()
    target_accounts = [
        a for a in accounts
        if platforms is None or a.get("platform") in platforms
    ]
    if not target_accounts:
        return {"status": "no_accounts", "error": "No connected accounts match requested platforms"}

    # Pick image or video URL
    image_url = content_item.get("r2_image_url") or content_item.get("image_url", "")
    video_url = content_item.get("r2_video_url") or content_item.get("video_url", "")

    # Pick the right caption for the first platform
    caption = content_item.get("script", "")
    captions = content_item.get("captions")
    if isinstance(captions, dict) and target_accounts:
        first_platform = target_accounts[0].get("platform", "")
        caption = captions.get(first_platform, caption)

    payload = {
        "content": caption,
        "platforms": [
            {"platform": a["platform"], "accountId": a["_id"]}
            for a in target_accounts
        ],
    }
    if video_url and "placeholder" not in video_url:
        payload["mediaItems"] = [{"type": "video", "url": video_url}]
    elif image_url and "placeholder" not in image_url:
        payload["mediaItems"] = [{"type": "image", "url": image_url}]

    try:
        r = requests.post(f"{ZERNIO_BASE}/posts", headers=hdrs, json=payload, timeout=20)
        r.raise_for_status()
        data = r.json()
        return {
            "status": "published",
            "post_id": data.get("_id", ""),
            "platforms_published": [a["platform"] for a in target_accounts],
        }
    except requests.HTTPError as e:
        return {"status": "error", "error": f"Zernio API error: {e.response.text[:200]}"}
    except Exception as e:
        return {"status": "error", "error": str(e)}
