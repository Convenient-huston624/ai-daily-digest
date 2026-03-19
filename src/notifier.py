"""WeChat notification via Server酱 (ftqq.com)."""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone

import httpx

from .utils import format_time_delta, get_beijing_time

logger = logging.getLogger(__name__)

_SERVERCHAN_API = "https://sctapi.ftqq.com/{key}.send"
_MAX_DESP_BYTES = 32 * 1024  # 32 KB Server酱 limit
_BATCH_SIZE = 10              # split into two messages if items > this


def _score_to_stars(score: float, thresholds: dict) -> str:
    if score >= thresholds.get("critical", 15):
        return "🔥🔥🔥"
    if score >= thresholds.get("high", 8):
        return "⭐⭐"
    return "⭐"


def _render_item(item: dict, index: int, display_cfg: dict, thresholds: dict) -> str:
    stars = _score_to_stars(item.get("score", 0), thresholds)
    lines = [f"**{index}. {item['title']}**"]

    summary = item.get("summary_zh") or item.get("summary", "")
    if summary:
        lines.append(summary)

    meta_parts = []
    if display_cfg.get("show_stars", True):
        meta_parts.append(stars)
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
    items: list[dict],
    overview: str,
    display_cfg: dict,
    thresholds: dict,
    part_label: str = "",
) -> str:
    sections: list[str] = []

    if overview and not part_label:
        sections.append(f"## 📋 今日概述\n\n{overview}\n\n---")

    # Group items by source priority tier
    critical_items = [i for i in items if i.get("source_priority") == "critical" or i.get("score", 0) >= thresholds.get("critical", 15)]
    high_items = [i for i in items if i not in critical_items and i.get("score", 0) >= thresholds.get("high", 8)]
    normal_items = [i for i in items if i not in critical_items and i not in high_items]

    counter = 1

    if critical_items:
        sections.append("## 🔥🔥🔥 重大突破")
        for item in critical_items:
            sections.append(_render_item(item, counter, display_cfg, thresholds))
            counter += 1
        sections.append("---")

    if high_items:
        sections.append("## ⭐⭐ 值得关注")
        for item in high_items:
            sections.append(_render_item(item, counter, display_cfg, thresholds))
            counter += 1
        sections.append("---")

    if normal_items:
        sections.append("## ⭐ 业界动态")
        for item in normal_items:
            sections.append(_render_item(item, counter, display_cfg, thresholds))
            counter += 1
        sections.append("---")

    now_str = get_beijing_time().strftime("%Y-%m-%d %H:%M")
    sections.append(f"*由 AI Daily Digest 自动生成 · {now_str}*")

    return "\n\n".join(sections)


async def send_wechat(
    items: list[dict],
    overview: str,
    schedule: dict,
    user_cfg: dict,
) -> None:
    key = os.getenv("SERVERCHAN_KEY", "")
    if not key:
        logger.error("SERVERCHAN_KEY is not set — skipping WeChat notification.")
        return

    display_cfg = user_cfg.get("display", {})
    thresholds = display_cfg.get("tier_thresholds", {"critical": 15, "high": 8})
    label = schedule.get("label", "📰 AI 日报")
    beijing_now = get_beijing_time()
    title = f"{label} · {beijing_now.strftime('%Y-%m-%d')} 共{len(items)}条"

    url = _SERVERCHAN_API.format(key=key)

    async with httpx.AsyncClient(timeout=15) as client:
        if len(items) <= _BATCH_SIZE:
            desp = _build_desp(items, overview, display_cfg, thresholds)
            await _post_message(client, url, title, desp)
        else:
            # Split into two messages: first half + second half
            first = items[: _BATCH_SIZE]
            second = items[_BATCH_SIZE:]

            desp1 = _build_desp(first, overview, display_cfg, thresholds)
            desp2 = _build_desp(second, "", display_cfg, thresholds, part_label="(下)")

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
