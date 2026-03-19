"""Async RSS fetcher — pulls all configured sources concurrently."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

import feedparser
import httpx

from .utils import CONFIG_DIR, load_yaml, load_user_config

logger = logging.getLogger(__name__)

_TIMEOUT = 10  # seconds per request


def _parse_published(entry: Any) -> datetime:
    if hasattr(entry, "published_parsed") and entry.published_parsed:
        try:
            return datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
        except Exception:
            pass
    if hasattr(entry, "updated_parsed") and entry.updated_parsed:
        try:
            return datetime(*entry.updated_parsed[:6], tzinfo=timezone.utc)
        except Exception:
            pass
    return datetime.now(timezone.utc)


def _should_include_source(source: dict, include_tags: list[str], exclude_tags: list[str]) -> bool:
    tags = source.get("tags", [])
    if include_tags and not any(t in tags for t in include_tags):
        return False
    if exclude_tags and any(t in tags for t in exclude_tags):
        return False
    return True


async def _fetch_one(client: httpx.AsyncClient, source: dict) -> list[dict]:
    url = source["url"]
    try:
        resp = await client.get(url, timeout=_TIMEOUT)
        resp.raise_for_status()
        feed = feedparser.parse(resp.text)
    except Exception as exc:
        logger.warning("Failed to fetch %s: %s", source["name"], exc)
        return []

    items = []
    for entry in feed.entries:
        raw_summary = getattr(entry, "summary", "") or ""
        # Strip HTML tags for arXiv-style summaries
        import re
        clean_summary = re.sub(r"<[^>]+>", " ", raw_summary).strip()

        items.append(
            {
                "title": getattr(entry, "title", "Untitled").strip(),
                "url": getattr(entry, "link", ""),
                "summary": clean_summary,
                "published": _parse_published(entry),
                "source_name": source["name"],
                "source_priority": source.get("priority", "medium"),
                "source_tags": source.get("tags", []),
            }
        )
    return items


async def fetch_all(sources: list[dict]) -> list[dict]:
    """Fetch all sources concurrently and return a flat list of raw items."""
    async with httpx.AsyncClient(
        follow_redirects=True,
        headers={"User-Agent": "ai-daily-digest/1.0 (github.com)"},
    ) as client:
        tasks = [_fetch_one(client, src) for src in sources]
        results = await asyncio.gather(*tasks)

    all_items: list[dict] = []
    for batch in results:
        all_items.extend(batch)
    return all_items


def load_sources_with_filter(user_cfg: dict) -> list[dict]:
    """Load sources.yaml and apply include/exclude tag filters from user config."""
    sources_data = load_yaml(CONFIG_DIR / "sources.yaml")
    sources = sources_data.get("sources", [])

    filt = user_cfg.get("filter", {})
    include_tags: list[str] = filt.get("include_tags") or []
    exclude_tags: list[str] = filt.get("exclude_tags") or []

    return [s for s in sources if _should_include_source(s, include_tags, exclude_tags)]
