#!/usr/bin/env python3
"""
medpr.py
─────────
MEDPR — Media Engine for Daily Post Rendering
CLI entry point. The CEO interface.

Usage:
  python3 medpr.py            → Interactive setup + start scheduler
  python3 medpr.py --run-now  → Run pipeline once immediately
  python3 medpr.py --dry-run  → Test pipeline without posting
  python3 medpr.py --status   → Show current config and status
  python3 medpr.py --setup    → Re-run interactive setup only
"""

import sys
import json
import os
import argparse
from pathlib import Path
from datetime import datetime

# ── Ensure project root is on the path ──────────────────────────────
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from core.config import (
    load_ceo_config, save_ceo_config, ENV_FILE, log, BASE_DIR
)


# ── Banner ───────────────────────────────────────────────────────────

BANNER = r"""
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║   ███╗   ███╗███████╗██████╗ ██████╗ ██████╗                 ║
║   ████╗ ████║██╔════╝██╔══██╗██╔══██╗██╔══██╗                ║
║   ██╔████╔██║█████╗  ██║  ██║██████╔╝██████╔╝                ║
║   ██║╚██╔╝██║██╔══╝  ██║  ██║██╔═══╝ ██╔══██╗                ║
║   ██║ ╚═╝ ██║███████╗██████╔╝██║     ██║  ██║                ║
║   ╚═╝     ╚═╝╚══════╝╚═════╝ ╚═╝     ╚═╝  ╚═╝                ║
║                                                               ║
║   Media Engine for Daily Post Rendering                       ║
║   Powered by: Ollama / Grok · Pexels · ElevenLabs            ║
║   Platforms:  Instagram · X (Twitter)                         ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
"""


# ── CEO Setup Wizard ─────────────────────────────────────────────────

def _ask(prompt: str, default: str = "", secret: bool = False) -> str:
    if default:
        prompt = f"{prompt} [{default}]: "
    else:
        prompt = f"{prompt}: "
    try:
        if secret:
            import getpass
            val = getpass.getpass(prompt)
        else:
            val = input(prompt).strip()
        return val if val else default
    except (KeyboardInterrupt, EOFError):
        return default


def _ask_bool(prompt: str, default: bool = False) -> bool:
    d = "Y/n" if default else "y/N"
    val = input(f"{prompt} [{d}]: ").strip().lower()
    if not val:
        return default
    return val in ("y", "yes", "1", "true")


def setup_wizard() -> dict:
    """Interactive CEO setup. Returns ceo_config dict."""
    print(BANNER)
    print("=" * 63)
    print("  CEO SETUP — Provide your directives and API keys")
    print("=" * 63)
    print()

    cfg = load_ceo_config()

    # ── Content Targeting ────────────────────────────────────────────
    print("\n── CONTENT TARGETING ──────────────────────────────────────")
    cfg["region"]   = _ask("Target region / city", cfg.get("region", ""))
    raw_kw          = _ask("Keywords (comma-separated)", ", ".join(cfg.get("keywords", [])))
    cfg["keywords"] = [k.strip() for k in raw_kw.split(",") if k.strip()]
    cfg["category"] = _ask("News category (general/technology/business/science)", cfg.get("category", "general"))
    cfg["language"] = _ask("Language code (en/hi/es...)", cfg.get("language", "en"))
    cfg["timezone"] = _ask("Your timezone (e.g. Asia/Kolkata)", cfg.get("timezone", "UTC"))

    # ── Engagement Score ─────────────────────────────────────────────
    print("\n── POSTING SCHEDULE ────────────────────────────────────────")
    print("  Engagement tier: 100=3x/day  80=2x/day  70=1x/day")
    tier_raw = _ask("Engagement tier", str(cfg.get("engagement_score", 70)))
    try:
        tier = int(tier_raw)
        cfg["engagement_score"] = tier if tier in (100, 80, 70) else 70
    except ValueError:
        cfg["engagement_score"] = 70
    cfg["max_posts_per_run"] = int(_ask("Max posts per pipeline run", str(cfg.get("max_posts_per_run", 3))))

    # ── Platforms ────────────────────────────────────────────────────
    print("\n── PLATFORMS ───────────────────────────────────────────────")
    cfg["enable_ig"]  = _ask_bool("Post to Instagram?", cfg.get("enable_ig", True))
    cfg["enable_x"]   = _ask_bool("Post to X (Twitter)?", cfg.get("enable_x", True))
    cfg["enable_tts"] = _ask_bool("Generate voiceovers (ElevenLabs)?", cfg.get("enable_tts", False))
    cfg["remove_background"] = _ask_bool("Remove image backgrounds (remove.bg)?", cfg.get("remove_background", False))

    # ── API Keys ─────────────────────────────────────────────────────
    print("\n── API KEYS (leave blank to skip / keep existing) ──────────")

    env_entries = {}
    apis = [
        ("NEWSAPI_KEY",           "NewsAPI key",            True),
        ("GNEWS_KEY",             "GNews API key",          True),
        ("PEXELS_KEY",            "Pexels API key",         True),
        ("ELEVENLABS_KEY",        "ElevenLabs API key",     True),
        ("REMOVEBG_KEY",          "remove.bg API key",      True),
        ("CLOUDINARY_CLOUD_NAME", "Cloudinary cloud name",  False),
        ("CLOUDINARY_API_KEY",    "Cloudinary API key",     True),
        ("CLOUDINARY_API_SECRET", "Cloudinary API secret",  True),
        ("GROK_API_KEY",          "Grok (xAI) API key",     True),
        ("OLLAMA_HOST",           "Ollama host URL",         False),
        ("OLLAMA_MODEL",          "Ollama model name",       False),
        ("IG_USER_ID",            "Instagram user ID",       False),
        ("IG_ACCESS_TOKEN",       "Instagram access token",  True),
        ("X_API_KEY",             "X API key",               True),
        ("X_API_SECRET",          "X API secret",            True),
        ("X_ACCESS_TOKEN",        "X access token",          True),
        ("X_ACCESS_SECRET",       "X access token secret",   True),
    ]

    existing_env = {}
    if ENV_FILE.exists():
        with open(ENV_FILE) as f:
            for line in f:
                line = line.strip()
                if line and "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    existing_env[k.strip()] = v.strip()

    for env_key, label, is_secret in apis:
        current = existing_env.get(env_key, os.environ.get(env_key, ""))
        display = "*" * min(len(current), 8) if (is_secret and current) else current
        hint    = f" (current: {display})" if display else ""
        val     = _ask(f"{label}{hint}", secret=is_secret)
        if val:
            env_entries[env_key] = val
        elif current:
            env_entries[env_key] = current

    # ── Write .env ───────────────────────────────────────────────────
    lines = [f"# MEDPR .env — generated {datetime.now().isoformat()}\n"]
    for k, v in env_entries.items():
        lines.append(f"{k}={v}\n")
    ENV_FILE.write_text("".join(lines))
    os.chmod(ENV_FILE, 0o600)
    print(f"\n✅ API keys saved to {ENV_FILE} (mode 600)\n")

    save_ceo_config(cfg)
    print("✅ CEO config saved.\n")
    return cfg


# ── Status Printer ───────────────────────────────────────────────────

def print_status():
    cfg = load_ceo_config()
    if not cfg:
        print("No config found. Run: python3 medpr.py --setup")
        return

    env = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                env[k.strip()] = bool(v.strip())

    print(BANNER)
    print("── CEO CONFIG ──────────────────────────────────────────────")
    for k, v in cfg.items():
        print(f"  {k:<25}: {v}")
    print("\n── API KEYS SET ────────────────────────────────────────────")
    for k in ["NEWSAPI_KEY","GNEWS_KEY","PEXELS_KEY","ELEVENLABS_KEY",
              "REMOVEBG_KEY","CLOUDINARY_CLOUD_NAME","GROK_API_KEY",
              "OLLAMA_HOST","IG_USER_ID","IG_ACCESS_TOKEN","X_API_KEY"]:
        v = env.get(k, False)
        print(f"  {k:<30}: {'✓' if v else '✗ (not set)'}")


# ── CLI Entry ────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="MEDPR — Media Engine for Daily Post Rendering"
    )
    parser.add_argument("--run-now",  action="store_true", help="Run pipeline once immediately")
    parser.add_argument("--dry-run",  action="store_true", help="Run pipeline without posting")
    parser.add_argument("--status",   action="store_true", help="Show status and exit")
    parser.add_argument("--setup",    action="store_true", help="Run setup wizard only")
    args = parser.parse_args()

    if args.status:
        print_status()
        return

    if args.setup:
        setup_wizard()
        return

    # Load or create config
    cfg = load_ceo_config()
    if not cfg:
        print(BANNER)
        print("No config found. Starting CEO setup wizard...")
        cfg = setup_wizard()

    if args.dry_run:
        print(BANNER)
        log("[CEO] DRY RUN — no posts will be published.")
        from pipeline.pipeline import run_once
        results = run_once(cfg, dry_run=True)
        log(f"[CEO] Dry run complete. {len(results)} items processed.")
        for r in results:
            print(f"\n  Title     : {r['title'][:70]}")
            print(f"  IG caption: {r['ig_caption'][:120]}")
            print(f"  X  caption: {r['x_caption'][:120]}")
            print(f"  Image     : {r['image_path']}")
        return

    if args.run_now:
        print(BANNER)
        log("[CEO] Running pipeline now...")
        from pipeline.pipeline import run_once
        results = run_once(cfg)
        log(f"[CEO] Done. {len(results)} posts processed.")
        return

    # Normal: start scheduler
    print(BANNER)
    log("[CEO] Starting MEDPR scheduler...")
    from pipeline.scheduler import CEOScheduler
    try:
        scheduler = CEOScheduler(cfg)
        scheduler.run_loop()
    except KeyboardInterrupt:
        log("[CEO] Shutdown by user.")


if __name__ == "__main__":
    main()
