"""
pipeline/scheduler.py
──────────────────────
CEO Scheduler: Sleep-mode system.
MEDPR stays idle and wakes only at scheduled windows.

Engagement tiers (from Brain scoring):
  100 → post 3x/day
   80 → post 2x/day
   70 → post 1x/day

All times are in the CEO's configured timezone.
"""

import time
import sched
import json
from datetime import datetime, date
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from pathlib import Path

from core.config import load_ceo_config, LOGS_DIR, log
from pipeline.pipeline import run_once


# ── Posting Windows by Tier ──────────────────────────────────────────

SCHEDULE_TIERS = {
    100: ["09:00", "15:00", "20:00"],
    80:  ["10:00", "19:00"],
    70:  ["11:00"],
}


def _get_tz(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, Exception):
        log(f"[Scheduler] Invalid timezone '{name}' — using UTC.")
        return ZoneInfo("UTC")


def _parse_hm(hm: str) -> tuple[int, int]:
    h, m = hm.split(":")
    return int(h), int(m)


def _seconds_until(hour: int, minute: int, tz: ZoneInfo) -> float:
    now  = datetime.now(tz)
    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    diff = (target - now).total_seconds()
    if diff < 0:
        diff += 86400  # next day
    return diff


def _status_line(ceo_config: dict) -> str:
    now = datetime.now()
    return (
        f"\n{'═'*60}\n"
        f"  MEDPR Status  |  {now.strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"  Region   : {ceo_config.get('region','any')}\n"
        f"  Keywords : {', '.join(ceo_config.get('keywords', []))}\n"
        f"  Tier     : {ceo_config.get('engagement_score', 70)} "
        f"({len(SCHEDULE_TIERS.get(ceo_config.get('engagement_score', 70), ['11:00']))}x/day)\n"
        f"  IG       : {'✓' if ceo_config.get('enable_ig') else '✗'}  "
        f"X : {'✓' if ceo_config.get('enable_x') else '✗'}  "
        f"TTS : {'✓' if ceo_config.get('enable_tts') else '✗'}\n"
        f"{'═'*60}"
    )


class CEOScheduler:
    def __init__(self, ceo_config: dict):
        self.cfg  = ceo_config
        self.tz   = _get_tz(ceo_config.get("timezone", "UTC"))
        self.score = ceo_config.get("engagement_score", 70)
        self.times = SCHEDULE_TIERS.get(self.score, SCHEDULE_TIERS[70])
        self._running = False

    def _fire(self):
        """Called at each scheduled posting window."""
        log(f"[Scheduler] ⏰ Wake event — running pipeline...")
        fresh_cfg = load_ceo_config()
        self.cfg.update(fresh_cfg)
        try:
            results = run_once(self.cfg)
            log(f"[Scheduler] Pipeline produced {len(results)} posts.")
        except Exception as e:
            log(f"[Scheduler] Pipeline error: {e}")

    def run_loop(self):
        """Blocking run loop. Wakes at configured posting times."""
        self._running = True
        log(_status_line(self.cfg))
        log(f"[Scheduler] Posting schedule: {self.times} ({self.tz})")
        log("[Scheduler] MEDPR is awake. Press Ctrl+C to stop.\n")

        while self._running:
            now  = datetime.now(self.tz)
            next_fire = None
            wait_sec  = 86400

            for t in self.times:
                h, m = _parse_hm(t)
                sec  = _seconds_until(h, m, self.tz)
                if sec < wait_sec:
                    wait_sec  = sec
                    next_fire = t

            log(f"[Scheduler] 💤 Sleeping {wait_sec/3600:.1f}h until {next_fire} ({self.tz})...")

            try:
                time.sleep(max(1, wait_sec))
            except KeyboardInterrupt:
                log("[Scheduler] Interrupted — shutting down.")
                self._running = False
                break

            if self._running:
                self._fire()

    def stop(self):
        self._running = False
