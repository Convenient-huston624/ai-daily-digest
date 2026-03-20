"""Shared utility helpers."""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).parent.parent
CONFIG_DIR = ROOT / "config"
DATA_DIR = ROOT / "data"
ARCHIVE_DIR = ROOT / "archive"
SEEN_URLS_FILE = DATA_DIR / "seen_urls.json"

# Keep seen-URL records for this many days before pruning
_SEEN_URL_TTL_DAYS = 7


def load_yaml(path: str | Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_user_config() -> dict:
    cfg = load_yaml(CONFIG_DIR / "user_config.yaml")
    _validate_user_config(cfg)
    return cfg


def _validate_user_config(cfg: dict) -> None:
    assert "schedule" in cfg, "user_config.yaml missing 'schedule' section"
    assert "llm" in cfg, "user_config.yaml missing 'llm' section"


def get_enabled_schedules(cfg: dict) -> list[dict]:
    return [s for s in cfg.get("schedule", []) if s.get("enabled", True)]


def get_beijing_time() -> datetime:
    beijing_tz = timezone(timedelta(hours=8))
    return datetime.now(beijing_tz)


def format_time_delta(dt: datetime) -> str:
    now = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    diff = now - dt
    total_seconds = diff.total_seconds()
    if total_seconds < 0:
        return "刚刚"
    hours = total_seconds / 3600
    if hours < 1:
        return "刚刚"
    if hours < 24:
        return f"{int(hours)}小时前"
    return "昨天"


def load_seen_urls() -> set[str]:
    if not SEEN_URLS_FILE.exists():
        return set()
    try:
        data = json.loads(SEEN_URLS_FILE.read_text(encoding="utf-8"))
        return {entry["url"] for entry in data.get("urls", [])}
    except (json.JSONDecodeError, KeyError):
        return set()


def save_seen_urls(new_urls: list[str]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    existing: list[dict] = []
    if SEEN_URLS_FILE.exists():
        try:
            data = json.loads(SEEN_URLS_FILE.read_text(encoding="utf-8"))
            existing = data.get("urls", [])
        except (json.JSONDecodeError, KeyError):
            existing = []

    cutoff = (datetime.now(timezone.utc) - timedelta(days=_SEEN_URL_TTL_DAYS)).date().isoformat()
    pruned = [e for e in existing if e.get("date", "") >= cutoff]

    existing_url_set = {e["url"] for e in pruned}
    today = datetime.now(timezone.utc).date().isoformat()
    for url in new_urls:
        if url not in existing_url_set:
            pruned.append({"url": url, "date": today})

    SEEN_URLS_FILE.write_text(
        json.dumps({"urls": pruned}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


_TRACK_ORDER = ["industry", "impact_papers", "domain_papers"]
_TRACK_DEFAULTS = {
    "industry":      "📰 业界动态",
    "impact_papers": "🔬 影响力论文",
    "domain_papers": "🎯 细分领域",
}


def save_archive(tracks: dict[str, list[dict]], overview: str, label: str, user_cfg: dict) -> str:
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    now = get_beijing_time()
    filename = now.strftime("%Y-%m-%d_%H%M") + ".md"
    path = ARCHIVE_DIR / filename

    tracks_cfg = user_cfg.get("tracks", {})
    lines = [f"# {label} — {now.strftime('%Y-%m-%d %H:%M')}\n\n"]
    if overview:
        lines.append(f"## 📋 今日概述\n\n{overview}\n\n---\n\n")

    counter = 1
    for track_key in _TRACK_ORDER:
        items = tracks.get(track_key, [])
        if not items:
            continue
        section_label = tracks_cfg.get(track_key, {}).get("label", _TRACK_DEFAULTS[track_key])
        lines.append(f"## {section_label}\n\n")
        for item in items:
            lines.append(f"### {counter}. {item['title']}\n\n")
            lines.append(f"**来源**: {item.get('source_name', '')}  \n")
            lines.append(f"**时间**: {format_time_delta(item['published'])}  \n")
            lines.append(f"**链接**: {item['url']}  \n\n")
            if item.get("summary_zh"):
                lines.append(f"{item['summary_zh']}\n\n")
            counter += 1

    path.write_text("".join(lines), encoding="utf-8")
    return str(path)
