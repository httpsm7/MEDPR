"""
integrations/x_publisher.py
─────────────────────────────
Post text + images to X (Twitter) via the API v2.
Uses OAuth 1.0a (API Key + Access Token).
Requires: pip install requests requests-oauthlib
"""

import requests
from core.config import X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_SECRET, log

TWITTER_V2 = "https://api.twitter.com/2"
TWITTER_V1 = "https://upload.twitter.com/1.1"


def _auth():
    try:
        from requests_oauthlib import OAuth1
    except ImportError:
        log("[X] requests_oauthlib not installed. Run: pip install requests-oauthlib")
        return None
    k, ks, t, ts = X_API_KEY(), X_API_SECRET(), X_ACCESS_TOKEN(), X_ACCESS_SECRET()
    if not all([k, ks, t, ts]):
        log("[X] Missing OAuth credentials.")
        return None
    return OAuth1(k, ks, t, ts)


def _upload_media(image_path: str, auth) -> str | None:
    try:
        with open(image_path, "rb") as f:
            r = requests.post(
                f"{TWITTER_V1}/media/upload.json",
                auth=auth,
                files={"media": f},
                timeout=60,
            )
        r.raise_for_status()
        media_id = r.json().get("media_id_string")
        log(f"[X] Media uploaded: {media_id}")
        return media_id
    except Exception as e:
        log(f"[X] Media upload error: {e}")
        return None


def post_tweet(text: str, image_path: str = None) -> str:
    """
    Post a tweet with optional image attachment.
    Returns tweet ID or empty string.
    """
    auth = _auth()
    if not auth:
        return ""

    payload = {"text": text[:280]}

    if image_path:
        media_id = _upload_media(image_path, auth)
        if media_id:
            payload["media"] = {"media_ids": [media_id]}

    try:
        r = requests.post(
            f"{TWITTER_V2}/tweets",
            auth=auth,
            json=payload,
            timeout=30,
        )
        r.raise_for_status()
        tweet_id = r.json().get("data", {}).get("id", "")
        if tweet_id:
            log(f"[X] ✅ Tweeted! id={tweet_id}")
        return tweet_id
    except Exception as e:
        log(f"[X] Post error: {e}")
        return ""
