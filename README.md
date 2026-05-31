# MEDPR — Media Engine for Daily Post Rendering

> A lightweight, sleep-mode content factory for 1 Instagram + 1 X account.  
> Built from Spidergram's DNA — without the RAM overhead.

---

## Architecture

```
CEO (You / CLI)
    └── Brain (Ollama local / Grok API)
          ├── News Fetcher     (NewsAPI → GNews fallback)
          ├── Verifier         (fake-news filter)
          ├── Caption Engine   (caption + hashtags + safety check)
          ├── Image Selector   (Pexels)
          ├── BG Remover       (remove.bg, optional)
          ├── TTS Engine       (ElevenLabs → pyttsx3 fallback)
          ├── CDN Uploader     (Cloudinary)
          ├── IG Publisher     (Instagram Graph API)
          └── X Publisher      (Twitter API v2)
```

## Workspace Structure

```
workspace/
├── NewsContext/   ← Raw fetched articles (JSON)
├── Images/        ← Downloaded & edited images
├── Voices/        ← ElevenLabs MP3 voiceovers
├── Videos/        ← Reels (future)
├── Posts/         ← Final post data per article
└── Logs/          ← Daily reports (report_YYYY-MM-DD.txt)
```

## Quick Start

```bash
# 1. Install deps
pip install -r requirements.txt

# 2. First-time setup (CEO wizard)
python3 medpr.py

# 3. Test without posting
python3 medpr.py --dry-run

# 4. Post right now
python3 medpr.py --run-now

# 5. Start scheduler (runs continuously at posting windows)
python3 medpr.py

# 6. Check status
python3 medpr.py --status
```

## Posting Schedule (Engagement Tiers)

| Tier | Posts/Day | Times              |
|------|-----------|--------------------|
| 100  | 3         | 09:00 · 15:00 · 20:00 |
| 80   | 2         | 10:00 · 19:00      |
| 70   | 1         | 11:00              |

Set your tier during `--setup`.

## Kali Linux / Systemd Autostart

```ini
# /etc/systemd/system/medpr.service
[Unit]
Description=MEDPR Content Engine
After=network.target

[Service]
Type=simple
User=kali
WorkingDirectory=/path/to/MEDPR
ExecStart=/usr/bin/python3 medpr.py
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable medpr
sudo systemctl start medpr
sudo journalctl -u medpr -f
```

## API Keys Required

| Service       | Purpose                    | Free Tier?   |
|---------------|----------------------------|--------------|
| NewsAPI       | News fetch (primary)       | ✓ 100/day    |
| GNews         | News fetch (fallback)      | ✓ 100/day    |
| Pexels        | Stock images               | ✓ 200/hr     |
| remove.bg     | Background removal         | ✓ 50/month   |
| Cloudinary    | CDN / image hosting        | ✓ 25GB       |
| ElevenLabs    | Text-to-speech             | ✓ 10k chars  |
| Grok (xAI)    | Brain fallback LLM         | Paid          |
| Ollama        | Brain primary LLM (local)  | Free (local) |
| Instagram     | IG Graph API               | Free (token) |
| X / Twitter   | Twitter API v2             | Basic $100/mo|

## vs Spidergram

| Feature           | Spidergram       | MEDPR            |
|-------------------|------------------|------------------|
| Architecture      | Multi-agent      | Single-brain     |
| RAM usage         | High             | Minimal          |
| Interface         | Web dashboard    | Terminal CLI     |
| Accounts          | Multi-account    | 1 IG + 1 X       |
| Sleep mode        | No               | Yes              |
| Self-modifying    | Yes              | Planned          |

---

Built as a lean, auditable alternative to Spidergram.
