"""
integrations/pexels.py
───────────────────────
Fetch and download free stock images from Pexels.
"""

import os
import requests
from pathlib import Path
from core.config import PEXELS_KEY, IMAGES_DIR, log


def search(query: str, count: int = 4) -> list[str]:
    """
    Search Pexels for `query`, download `count` images.
    Returns list of local file paths.
    """
    key = PEXELS_KEY()
    if not key:
        log("[Pexels] No API key — skipping image fetch.")
        return []

    try:
        r = requests.get(
            "https://api.pexels.com/v1/search",
            headers={"Authorization": key},
            params={"query": query, "per_page": count, "orientation": "portrait"},
            timeout=20,
        )
        r.raise_for_status()
        photos = r.json().get("photos", [])
        log(f"[Pexels] Found {len(photos)} photos for '{query}'")
    except Exception as e:
        log(f"[Pexels] Search error: {e}")
        return []

    paths = []
    for i, photo in enumerate(photos):
        url  = photo.get("src", {}).get("large2x") or photo.get("src", {}).get("original")
        if not url:
            continue
        ext  = url.split("?")[0].rsplit(".", 1)[-1] or "jpg"
        safe = query.replace(" ", "_")[:30]
        dest = IMAGES_DIR / f"pexels_{safe}_{i}.{ext}"
        if dest.exists():
            paths.append(str(dest))
            continue
        try:
            img = requests.get(url, timeout=30)
            img.raise_for_status()
            dest.write_bytes(img.content)
            paths.append(str(dest))
            log(f"[Pexels] Downloaded: {dest.name}")
        except Exception as e:
            log(f"[Pexels] Download error: {e}")

    return paths
