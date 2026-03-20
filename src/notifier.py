"""WeChat notification via Server酱 (ftqq.com)."""
from __future__ import annotations

import logging
import os

import httpx

from .utils import format_time_delta, get_beijing_time

logger = logging.getLogger(__name__)

_SERVERCHAN_API = "https://sctapi.ftqq.com/{key}.send"
_MAX_DESP_BYTES = 32 * 1024  # 32 KB Server酱 limit
_BATCH_SIZE = 10              # split into two messages if total items exceed this

# Fixed order for rendering tracks
_TRACK_ORDER = ["industry", "impact_papers", "domain_papers"]
_TRACK_DEFAULTS = {
    "industry":      "📰 业界动态",
    "impact_papers": "🔬 影响力论文",
    "domain_papers": "🎯 细分领域",
}


def _render_item(item: dict, index: int, display_cfg: dict) -> str:
    lines = [f"**{index}. {item['title']}**"]

    summary = item.get("summary_zh") or item.get("summary", "")
    if summary:
        lines.append(summary)

    meta_parts = []
    if display_cfg.get("show_source", True):
        meta_parts.append(f"📰 {item.get('source_name', '')}")
    if display_cfg.get("show_time", True):
        meta_parts.append(f"🕐 {format_time_delta(item['published'])}")
    if display_cfg.get("show_links", True) and item.get("url"):
        meta_parts.append(f"🔗 [原文]({item['url']})")

    if meta_parts:
        lines.append("  ".join(meta_parts))

    return "\n".join(lines)


def _build_desp(
    tracks: dict[str, list[dict]],
    overview: str,
    display_cfg: dict,
    tracks_cfg: dict,
    include_overview: bool = True,
) -> str:
    sections: list[str] = []

    if overview and include_overview:
        sections.append(f"## 📋 今日概述\n\n{overview}\n\n---")

    counter = 1
    for track_key in _TRACK_ORDER:
        items = tracks.get(track_key, [])
        if not items:
            continue
        label = tracks_cfg.get(track_key, {}).get("label", _TRACK_DEFAULTS[track_key])
        sections.append(f"## {label}")
        for item in items:
            sections.append(_render_item(item, counter, display_cfg))
            counter += 1
        sections.append("---")

    now_str = get_beijing_time().strftime("%Y-%m-%d %H:%M")
    sections.append(f"*由 AI Daily Digest 自动生成 · {now_str}*")

    return "\n\n".join(sections)


async def send_wechat(
    tracks: dict[str, list[dict]],
    overview: str,
    schedule: dict,
    user_cfg: dict,
) -> None:
    key = os.getenv("SERVERCHAN_KEY", "")
    if not key:
        logger.error("SERVERCHAN_KEY is not set — skipping WeChat notification.")
        return

    display_cfg = user_cfg.get("display", {})
    tracks_cfg = user_cfg.get("tracks", {})
    label = schedule.get("label", "📰 AI 日报")
    beijing_now = get_beijing_time()
    total = sum(len(v) for v in tracks.values())
    title = f"{label} · {beijing_now.strftime('%Y-%m-%d')} 共{total}条"

    url = _SERVERCHAN_API.format(key=key)

    async with httpx.AsyncClient(timeout=15) as client:
        if total <= _BATCH_SIZE:
            desp = _build_desp(tracks, overview, display_cfg, tracks_cfg)
            await _post_message(client, url, title, desp)
        else:
            # First message: overview + industry news
            # Second message: both paper tracks
            first_tracks = {"industry": tracks.get("industry", [])}
            second_tracks = {
                "impact_papers": tracks.get("impact_papers", []),
                "domain_papers": tracks.get("domain_papers", []),
            }
            desp1 = _build_desp(first_tracks, overview, display_cfg, tracks_cfg)
            desp2 = _build_desp(second_tracks, "", display_cfg, tracks_cfg, include_overview=False)
            await _post_message(client, url, title + "（上）", desp1)
            await _post_message(client, url, title + "（下）", desp2)


async def _post_message(client: httpx.AsyncClient, url: str, title: str, desp: str) -> None:
    # Truncate title to 32 chars (Server酱 limit)
    title = title[:32]
    # Truncate desp if over 32 KB
    desp_bytes = desp.encode("utf-8")
    if len(desp_bytes) > _MAX_DESP_BYTES:
        desp = desp_bytes[:_MAX_DESP_BYTES].decode("utf-8", errors="ignore")

    try:
        resp = await client.post(url, data={"title": title, "desp": desp})
        data = resp.json()
        if data.get("code") == 0:
            logger.info("WeChat message sent: %s", title)
        else:
            logger.warning("Server酱 returned error: %s", data)
    except Exception as exc:
        logger.error("Failed to send WeChat message: %s", exc)
