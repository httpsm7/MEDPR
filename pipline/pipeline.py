"""
pipeline/pipeline.py
─────────────────────
MEDPR Content Pipeline
Signal → Filter → Interpret → Package → Publish → Log

Steps:
  1. Fetch news
  2. Verify & filter (Brain)
  3. Generate caption & hashtags (Brain)
  4. Fetch image (Pexels)
  5. [Optional] Remove background
  6. [Optional] Generate voice (ElevenLabs)
  7. Upload to Cloudinary
  8. Post to Instagram + X
  9. Mark used, log result
"""

import json
import time
from datetime import datetime
from pathlib import Path

from core.config import (
    POSTS_DIR, IMAGES_DIR, log,
    load_ceo_config,
)
from core import brain
from integrations import news, pexels, elevenlabs
from integrations.removebg import remove_background
from integrations.cloudinary_client import upload as cdn_upload
from integrations.instagram import publish_image
from integrations.x_publisher import post_tweet


def _build_caption(article: dict, caption_data: dict, platform: str) -> str:
    hook    = caption_data.get("hook", "")
    caption = caption_data.get("caption", article["title"])
    tags    = caption_data.get("hashtags", "")
    if platform == "instagram":
        return f"{hook}\n\n{caption}\n\n{tags}"
    else:  # X — tight limit
        base = f"{hook} {caption}"
        return base[:250] + " " + tags[:25] if len(base) < 230 else base[:260]


def run_once(ceo_config: dict, dry_run: bool = False) -> list[dict]:
    """
    Execute one full pipeline cycle.
    Returns list of post result dicts.
    """
    keywords   = ceo_config.get("keywords", [])
    category   = ceo_config.get("category", "general")
    language   = ceo_config.get("language", "en")
    region     = ceo_config.get("region", "")
    tts_style  = ceo_config.get("tts_style", "professional")
    enable_tts = ceo_config.get("enable_tts", False)
    enable_x   = ceo_config.get("enable_x", True)
    enable_ig  = ceo_config.get("enable_ig", True)
    max_posts  = ceo_config.get("max_posts_per_run", 3)
    removebg   = ceo_config.get("remove_background", False)

    results = []

    # ── Step 1: Fetch News ──────────────────────────────────────────
    log("═══ [Pipeline] Step 1: Fetching news...")
    if region:
        keywords = [region] + keywords
    articles = news.fetch(keywords=keywords, category=category, language=language)

    # Also load unprocessed from previous runs
    unprocessed = news.load_unused()
    # Merge (new first, then old unprocessed not in new)
    new_ids = {a["id"] for a in articles}
    all_articles = articles + [a for a in unprocessed if a["id"] not in new_ids]
    all_articles = all_articles[:20]  # cap at 20

    log(f"[Pipeline] {len(all_articles)} articles to evaluate")

    posted_count = 0

    for article in all_articles:
        if posted_count >= max_posts:
            break

        title   = article["title"]
        snippet = article.get("description", "")

        # ── Step 2: Verify ──────────────────────────────────────────
        log(f"[Pipeline] Step 2: Verifying — '{title[:60]}...'")
        verify = brain.verify_news(title, snippet)
        if not verify.get("real", True):
            log(f"[Pipeline] ❌ Rejected (fake): {verify.get('reason','')}")
            news.mark_used(article["id"])
            continue

        # ── Step 3: Generate Captions ───────────────────────────────
        log("[Pipeline] Step 3: Generating caption...")
        ig_data  = brain.generate_caption(title, snippet, "instagram")
        x_data   = brain.generate_caption(title, snippet, "twitter")

        if not ig_data.get("caption"):
            log("[Pipeline] ⚠ Caption generation failed — skipping.")
            continue

        # Safety check
        if not ig_data.get("safe", True):
            log("[Pipeline] ❌ Content flagged unsafe — skipping.")
            news.mark_used(article["id"])
            continue

        ig_caption = _build_caption(article, ig_data, "instagram")
        x_caption  = _build_caption(article, x_data,  "x")

        # ── Step 4: Fetch Image ─────────────────────────────────────
        log("[Pipeline] Step 4: Fetching image from Pexels...")
        query       = (keywords[0] if keywords else category) + " news"
        image_paths = pexels.search(query, count=1)
        image_path  = image_paths[0] if image_paths else None

        # ── Step 5: Remove Background (optional) ───────────────────
        if image_path and removebg:
            log("[Pipeline] Step 5: Removing background...")
            image_path = remove_background(image_path)

        # ── Step 6: TTS (optional) ──────────────────────────────────
        audio_path = ""
        if enable_tts and ig_data.get("hook"):
            log("[Pipeline] Step 6: Generating voiceover...")
            text_for_tts = ig_data["hook"] + ". " + ig_data.get("caption", "")
            audio_path = elevenlabs.generate(
                text_for_tts,
                style=tts_style,
                filename=f"voice_{article['id']}",
            )

        # ── Step 7: Upload to CDN ───────────────────────────────────
        cdn_url = ""
        if image_path and not dry_run:
            log("[Pipeline] Step 7: Uploading to Cloudinary...")
            cdn_url = cdn_upload(image_path, folder="MEDPR")

        # ── Step 8: Publish ─────────────────────────────────────────
        ig_media_id = ""
        x_tweet_id  = ""

        if not dry_run:
            if enable_ig and cdn_url:
                log("[Pipeline] Step 8a: Publishing to Instagram...")
                ig_media_id = publish_image(cdn_url, ig_caption)

            if enable_x:
                log("[Pipeline] Step 8b: Posting to X...")
                x_tweet_id = post_tweet(x_caption, image_path)

        # ── Step 9: Log Result ──────────────────────────────────────
        result = {
            "article_id":   article["id"],
            "title":        title,
            "ig_caption":   ig_caption,
            "x_caption":    x_caption,
            "image_path":   image_path or "",
            "audio_path":   audio_path,
            "cdn_url":      cdn_url,
            "ig_media_id":  ig_media_id,
            "x_tweet_id":   x_tweet_id,
            "posted_at":    datetime.now().isoformat(),
            "dry_run":      dry_run,
        }

        post_file = POSTS_DIR / f"post_{article['id']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        post_file.write_text(json.dumps(result, indent=2, ensure_ascii=False))

        news.mark_used(article["id"])
        results.append(result)
        posted_count += 1

        log(f"[Pipeline] ✅ Done [{posted_count}/{max_posts}]: '{title[:60]}'")

        if posted_count < max_posts:
            time.sleep(5)  # Be polite to APIs

    log(f"[Pipeline] Cycle complete. {posted_count} posts processed.")
    return results
