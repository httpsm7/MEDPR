"""
integrations/news.py
─────────────────────
Fetch news from NewsAPI (primary) → GNews (fallback).
Saves raw JSON to workspace/NewsContext/.
"""

import json
import hashlib
import requests
from datetime import datetime
from pathlib import Path
from core.config import NEWSAPI_KEY, GNEWS_KEY, NEWS_DIR, log


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:12]


def _save(article: dict, source_name: str) -> dict | None:
    title = (article.get("title") or "").strip()
    if not title or title == "[Removed]":
        return None

    article_id = _sha256(title)
    fpath      = NEWS_DIR / f"{article_id}.json"
    if fpath.exists():
        return None  # deduplicated

    data = {
        "id":          article_id,
        "title":       title,
        "description": article.get("description") or "",
        "url":         article.get("url", ""),
        "source":      source_name,
        "published":   article.get("publishedAt") or article.get("publishedAt") or datetime.now().isoformat(),
        "fetched_at":  datetime.now().isoformat(),
        "used":        False,
    }
    fpath.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    return data


def _from_newsapi(keywords: list[str], category: str, language: str) -> list[dict]:
    key = NEWSAPI_KEY()
    if not key:
        return []
    try:
        params = {
            "apiKey":   key,
            "language": language,
            "pageSize": 20,
        }
        q = " OR ".join(keywords) if keywords else ""
        if q:
            params["q"] = q
        else:
            params["category"] = category

        r = requests.get("https://newsapi.org/v2/top-headlines", params=params, timeout=20)
        r.raise_for_status()
        articles = r.json().get("articles", [])
        log(f"[NewsAPI] Retrieved {len(articles)} articles")
        return articles
    except Exception as e:
        log(f"[NewsAPI] Error: {e}")
        return []


def _from_gnews(keywords: list[str], language: str) -> list[dict]:
    key = GNEWS_KEY()
    if not key:
        return []
    try:
        q = " ".join(keywords) if keywords else "news"
        r = requests.get(
            "https://gnews.io/api/v4/search",
            params={"q": q, "lang": language, "max": 20, "apikey": key},
            timeout=20,
        )
        r.raise_for_status()
        raw = r.json().get("articles", [])
        # Normalize GNews shape to NewsAPI shape
        for a in raw:
            a.setdefault("source", {})["name"] = a.get("source", {}).get("name", "GNews")
            a["publishedAt"] = a.get("publishedAt", "")
        log(f"[GNews] Retrieved {len(raw)} articles")
        return raw
    except Exception as e:
        log(f"[GNews] Error: {e}")
        return []


def fetch(
    keywords: list[str] = None,
    category: str = "general",
    language: str = "en",
) -> list[dict]:
    """
    Fetch fresh news. Returns list of new (non-duplicate) article dicts.
    NewsAPI first; GNews fallback.
    """
    keywords = keywords or []
    raw      = _from_newsapi(keywords, category, language)

    if not raw:
        log("[News] NewsAPI empty — trying GNews...")
        raw = _from_gnews(keywords, language)

    saved = []
    for art in raw:
        src  = art.get("source", {}).get("name", "Unknown")
        item = _save(art, src)
        if item:
            saved.append(item)

    log(f"[News] {len(saved)} new articles saved to NewsContext/")
    return saved


def load_unused() -> list[dict]:
    """Load all unprocessed articles from workspace."""
    items = []
    for f in sorted(NEWS_DIR.glob("*.json"), reverse=True):
        try:
            data = json.loads(f.read_text())
            if not data.get("used"):
                items.append(data)
        except Exception:
            pass
    return items


def mark_used(article_id: str):
    fpath = NEWS_DIR / f"{article_id}.json"
    if fpath.exists():
        data = json.loads(fpath.read_text())
        data["used"] = True
        fpath.write_text(json.dumps(data, indent=2))
