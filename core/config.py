"""
core/config.py
──────────────
MEDPR Central Configuration
Loads API keys from .env (never hard-coded).
All directories are created on first import.
"""

import os
import json
from pathlib import Path
from datetime import datetime

BASE_DIR      = Path(__file__).parent.parent
WORKSPACE_DIR = BASE_DIR / "workspace"
ENV_FILE      = BASE_DIR / ".env"

# ── Workspace Subdirs ────────────────────────────────────────────────
NEWS_DIR    = WORKSPACE_DIR / "NewsContext"
IMAGES_DIR  = WORKSPACE_DIR / "Images"
VOICES_DIR  = WORKSPACE_DIR / "Voices"
VIDEOS_DIR  = WORKSPACE_DIR / "Videos"
POSTS_DIR   = WORKSPACE_DIR / "Posts"
LOGS_DIR    = WORKSPACE_DIR / "Logs"

for d in [NEWS_DIR, IMAGES_DIR, VOICES_DIR, VIDEOS_DIR, POSTS_DIR, LOGS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ── Load .env ────────────────────────────────────────────────────────
def _load_env():
    if ENV_FILE.exists():
        with open(ENV_FILE) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())

_load_env()

def get(key: str, default: str = "") -> str:
    return os.environ.get(key, default)

# ── API Keys (read-only helpers) ─────────────────────────────────────
NEWSAPI_KEY         = lambda: get("NEWSAPI_KEY")
GNEWS_KEY           = lambda: get("GNEWS_KEY")
PEXELS_KEY          = lambda: get("PEXELS_KEY")
REMOVEBG_KEY        = lambda: get("REMOVEBG_KEY")
CLOUDINARY_NAME     = lambda: get("CLOUDINARY_CLOUD_NAME")
CLOUDINARY_API_KEY  = lambda: get("CLOUDINARY_API_KEY")
CLOUDINARY_SECRET   = lambda: get("CLOUDINARY_API_SECRET")
ELEVENLABS_KEY      = lambda: get("ELEVENLABS_KEY")
GROK_KEY            = lambda: get("GROK_API_KEY")
OLLAMA_HOST         = lambda: get("OLLAMA_HOST", "http://127.0.0.1:11434")
OLLAMA_MODEL        = lambda: get("OLLAMA_MODEL", "mistral")
IG_USER_ID          = lambda: get("IG_USER_ID")
IG_ACCESS_TOKEN     = lambda: get("IG_ACCESS_TOKEN")
X_API_KEY           = lambda: get("X_API_KEY")
X_API_SECRET        = lambda: get("X_API_SECRET")
X_ACCESS_TOKEN      = lambda: get("X_ACCESS_TOKEN")
X_ACCESS_SECRET     = lambda: get("X_ACCESS_SECRET")

# ── Runtime Settings ─────────────────────────────────────────────────
CEO_CONFIG_FILE = BASE_DIR / "ceo_config.json"

def load_ceo_config() -> dict:
    if CEO_CONFIG_FILE.exists():
        with open(CEO_CONFIG_FILE) as f:
            return json.load(f)
    return {}

def save_ceo_config(data: dict):
    with open(CEO_CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=2)

# ── Daily Log ────────────────────────────────────────────────────────
def daily_log_path() -> Path:
    return LOGS_DIR / f"report_{datetime.now().strftime('%Y-%m-%d')}.txt"

def log(msg: str):
    ts  = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(daily_log_path(), "a") as f:
        f.write(line + "\n")
