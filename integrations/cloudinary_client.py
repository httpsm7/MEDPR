"""
integrations/cloudinary_client.py
───────────────────────────────────
Upload images/videos to Cloudinary.
Returns the public CDN URL for use with Instagram/X.
"""

import requests
import hashlib
import time
from core.config import CLOUDINARY_NAME, CLOUDINARY_API_KEY, CLOUDINARY_SECRET, log


def _sign(params: dict, api_secret: str) -> str:
    """Generate Cloudinary upload signature."""
    sorted_params = "&".join(
        f"{k}={v}" for k, v in sorted(params.items()) if k not in ("file", "api_key")
    )
    to_sign = sorted_params + api_secret
    return hashlib.sha256(to_sign.encode()).hexdigest()


def upload(file_path: str, folder: str = "MEDPR", resource_type: str = "image") -> str:
    """
    Upload a local file to Cloudinary under `folder`.
    Returns the secure CDN URL or empty string on failure.
    """
    cloud = CLOUDINARY_NAME()
    key   = CLOUDINARY_API_KEY()
    sec   = CLOUDINARY_SECRET()

    if not all([cloud, key, sec]):
        log("[Cloudinary] Missing credentials — skipping upload.")
        return ""

    ts     = str(int(time.time()))
    params = {"folder": folder, "timestamp": ts}
    sig    = _sign(params, sec)

    try:
        with open(file_path, "rb") as f:
            r = requests.post(
                f"https://api.cloudinary.com/v1_1/{cloud}/{resource_type}/upload",
                data={**params, "api_key": key, "signature": sig},
                files={"file": f},
                timeout=120,
            )
        r.raise_for_status()
        url = r.json().get("secure_url", "")
        log(f"[Cloudinary] Uploaded → {url}")
        return url
    except Exception as e:
        log(f"[Cloudinary] Upload error: {e}")
        return ""
