"""
integrations/instagram.py
──────────────────────────
Post images/reels to Instagram via the Graph API.
Requires IG_USER_ID + IG_ACCESS_TOKEN with publish permissions.
"""

import time
import requests
from core.config import IG_USER_ID, IG_ACCESS_TOKEN, log

GRAPH = "https://graph.facebook.com/v19.0"


def _post(endpoint: str, **kwargs) -> dict:
    try:
        r = requests.post(f"{GRAPH}/{endpoint}", **kwargs, timeout=60)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        log(f"[Instagram] Error on {endpoint}: {e}")
        return {}


def publish_image(image_url: str, caption: str) -> str:
    """
    Publish a single image post. Returns media ID or empty string.
    image_url must be publicly accessible (use Cloudinary CDN URL).
    """
    uid   = IG_USER_ID()
    token = IG_ACCESS_TOKEN()
    if not uid or not token:
        log("[Instagram] Missing credentials — skipping publish.")
        return ""

    # Step 1: Create media container
    container = _post(
        f"{uid}/media",
        params={
            "image_url":    image_url,
            "caption":      caption,
            "access_token": token,
        },
    )
    container_id = container.get("id")
    if not container_id:
        log("[Instagram] Failed to create container.")
        return ""

    # Step 2: Wait for container to be ready
    time.sleep(5)

    # Step 3: Publish the container
    result = _post(
        f"{uid}/media_publish",
        params={
            "creation_id":  container_id,
            "access_token": token,
        },
    )
    media_id = result.get("id", "")
    if media_id:
        log(f"[Instagram] ✅ Published! media_id={media_id}")
    else:
        log("[Instagram] ❌ Publish returned no media_id.")
    return media_id


def publish_reel(video_url: str, caption: str) -> str:
    """
    Publish a Reel. video_url must be a publicly accessible MP4 (use Cloudinary).
    Returns media ID or empty string.
    """
    uid   = IG_USER_ID()
    token = IG_ACCESS_TOKEN()
    if not uid or not token:
        log("[Instagram] Missing credentials — skipping reel.")
        return ""

    container = _post(
        f"{uid}/media",
        params={
            "media_type":   "REELS",
            "video_url":    video_url,
            "caption":      caption,
            "access_token": token,
        },
    )
    container_id = container.get("id")
    if not container_id:
        log("[Instagram] Reel container creation failed.")
        return ""

    log("[Instagram] Waiting for video processing (30s)...")
    time.sleep(30)

    result = _post(
        f"{uid}/media_publish",
        params={"creation_id": container_id, "access_token": token},
    )
    media_id = result.get("id", "")
    if media_id:
        log(f"[Instagram] ✅ Reel published! media_id={media_id}")
    return media_id
