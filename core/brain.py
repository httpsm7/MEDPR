"""
core/brain.py
─────────────
The MEDPR Brain: single LLM interface.
Primary: Ollama (local, zero RAM overhead for API calls)
Fallback: Grok xAI API

The Brain executes tasks; the CEO governs strategy.
"""

import json
import re
import requests
from core.config import OLLAMA_HOST, OLLAMA_MODEL, GROK_KEY, log


# ── Ollama ────────────────────────────────────────────────────────────

def _ollama(messages: list[dict], temperature: float = 0.7) -> str:
    try:
        r = requests.post(
            f"{OLLAMA_HOST()}/api/chat",
            json={
                "model":   OLLAMA_MODEL(),
                "messages": messages,
                "stream":  False,
                "options": {"temperature": temperature, "num_predict": 1200},
            },
            timeout=120,
        )
        r.raise_for_status()
        return r.json()["message"]["content"].strip()
    except Exception as e:
        log(f"[Brain] Ollama error: {e}")
        return ""


# ── Grok (xAI) ───────────────────────────────────────────────────────

def _grok(messages: list[dict]) -> str:
    key = GROK_KEY()
    if not key:
        return ""
    try:
        r = requests.post(
            "https://api.x.ai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type":  "application/json",
            },
            json={
                "model":       "grok-3-mini",
                "messages":    messages,
                "max_tokens":  1200,
                "temperature": 0.7,
            },
            timeout=60,
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        log(f"[Brain] Grok error: {e}")
        return ""


# ── Public Interface ─────────────────────────────────────────────────

def think(messages: list[dict], temperature: float = 0.7) -> str:
    """Send messages to Brain. Tries Ollama first, then Grok."""
    result = _ollama(messages, temperature)
    if not result:
        log("[Brain] Ollama unavailable — falling back to Grok...")
        result = _grok(messages)
    return result


def think_json(messages: list[dict]) -> dict:
    """
    Ask the Brain for a JSON-only response.
    Strips markdown fences and parses safely.
    """
    raw = think(messages, temperature=0.5)
    raw = re.sub(r"```json|```", "", raw).strip()
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    log("[Brain] JSON parse failed — returning empty dict.")
    return {}


# ── Task Shortcuts ───────────────────────────────────────────────────

VERIFY_SYS = (
    "You are a news fact-checker. Given a news title and snippet, "
    "respond with ONLY valid JSON: {\"real\": true/false, \"reason\": \"one sentence\"}. "
    "Be strict. If the headline looks clickbait, sensational, or unverifiable — mark as false."
)

CAPTION_SYS = (
    "You are a social media journalist. Given a news story, produce ONLY valid JSON with keys: "
    "{\"caption\": \"<150-220 char caption>\", \"hashtags\": \"<20 hashtags as one string>\", "
    "\"hook\": \"<punchy 10-word opening>\", \"safe\": true/false}. "
    "'safe' is false if the content is violent, adult, or abusive."
)

SCORE_SYS = (
    "You are a social media analytics expert. Given an engagement summary (likes, shares, "
    "saves over last 3 days for a topic), score it 100, 80, or 70. "
    "Respond ONLY with JSON: {\"score\": 100, \"reason\": \"brief reason\"}. "
    "100=post 3x/day, 80=2x/day, 70=1x/day."
)


def verify_news(title: str, snippet: str) -> dict:
    msgs = [
        {"role": "system",  "content": VERIFY_SYS},
        {"role": "user",    "content": f"Title: {title}\nSnippet: {snippet}"},
    ]
    result = think_json(msgs)
    return result if "real" in result else {"real": True, "reason": "parse error — allowed"}


def generate_caption(title: str, summary: str, platform: str = "instagram") -> dict:
    msgs = [
        {"role": "system",  "content": CAPTION_SYS},
        {"role": "user",    "content": f"Platform: {platform}\nTitle: {title}\nSummary: {summary}"},
    ]
    result = think_json(msgs)
    return result if "caption" in result else {}


def score_engagement(topic: str, stats_summary: str) -> dict:
    msgs = [
        {"role": "system",  "content": SCORE_SYS},
        {"role": "user",    "content": f"Topic: {topic}\nStats: {stats_summary}"},
    ]
    result = think_json(msgs)
    return result if "score" in result else {"score": 70, "reason": "default"}
