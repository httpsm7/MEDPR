"""
integrations/removebg.py
─────────────────────────
Remove image backgrounds via remove.bg API.
Falls back gracefully if key is missing.
"""

import requests
from pathlib import Path
from core.config import REMOVEBG_KEY, IMAGES_DIR, log


def remove_background(image_path: str) -> str:
    """
    Send image to remove.bg, save result as *_nobg.png.
    Returns path to cleaned image, or original path on failure.
    """
    key = REMOVEBG_KEY()
    if not key:
        log("[RemoveBG] No API key — skipping background removal.")
        return image_path

    src  = Path(image_path)
    dest = IMAGES_DIR / f"{src.stem}_nobg.png"
    if dest.exists():
        return str(dest)

    try:
        with open(image_path, "rb") as f:
            r = requests.post(
                "https://api.remove.bg/v1.0/removebg",
                headers={"X-Api-Key": key},
                files={"image_file": f},
                data={"size": "auto"},
                timeout=60,
            )
        if r.ok:
            dest.write_bytes(r.content)
            log(f"[RemoveBG] Background removed → {dest.name}")
            return str(dest)
        else:
            log(f"[RemoveBG] API error {r.status_code}: {r.text[:120]}")
            return image_path
    except Exception as e:
        log(f"[RemoveBG] Exception: {e}")
        return image_path
