"""Filter, deduplicate, score and rank news items."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from .utils import (
    CONFIG_DIR,
    load_seen_urls,
    load_yaml,
    save_seen_urls,
)

logger = logging.getLogger(__name__)

_SOURCE_WEIGHT = {"critical": 1.0, "high": 0.8, "medium": 0.5}


def _keyword_score(item: dict, kw_cfg: dict) -> float:
    text = (item["title"] + " " + item["summary"][:200]).lower()
    score = 0.0
    for kw in kw_cfg.get("critical", []):
        if kw.lower() in text:
            score += 10
    for kw in kw_cfg.get("high", []):
        if kw.lower() in text:
            score += 5
    for kw in kw_cfg.get("medium", []):
        if kw.lower() in text:
            score += 2
    return score


def _recency_bonus(published: datetime) -> float:
    now = datetime.now(timezone.utc)
    if published.tzinfo is None:
        published = published.replace(tzinfo=timezone.utc)
    diff_hours = (now - published).total_seconds() / 3600
    if diff_hours < 3:
        return 5
    if diff_hours < 6:
        return 3
    if diff_hours < 12:
        return 1
    return 0


def _personal_bonus(item: dict, interests: list[str]) -> float:
    text = (item["title"] + " " + item["summary"][:200]).lower()
    bonus = 0.0
    for phrase in interests:
        if phrase.lower() in text:
            bonus += 8
    return bonus


def _compute_score(item: dict, kw_cfg: dict, user_cfg: dict) -> float:
    kw_score = _keyword_score(item, kw_cfg)
    src_weight = _SOURCE_WEIGHT.get(item.get("source_priority", "medium"), 0.5)
    recency = _recency_bonus(item["published"])
    personal = _personal_bonus(item, user_cfg.get("personal_interests") or [])
    return kw_score * src_weight + recency + personal


def filter_and_score(
    raw_items: list[dict],
    user_cfg: dict,
    lookback_hours: int,
) -> list[dict]:
    """
    Apply all filter stages and return top-N scored items.
    Also persists newly seen URLs to disk.
    """
    kw_cfg = load_yaml(CONFIG_DIR / "keywords.yaml").get("keywords", {})
    filt_cfg = user_cfg.get("filter", {})
    block_kws: list[str] = [k.lower() for k in (filt_cfg.get("block_keywords") or [])]
    min_score: float = filt_cfg.get("min_score", 0)
    max_items: int = filt_cfg.get("max_items", 12)

    cutoff = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
    seen_urls = load_seen_urls()

    filtered: list[dict] = []
    for item in raw_items:
        published = item["published"]
        if published.tzinfo is None:
            published = published.replace(tzinfo=timezone.utc)

        # Time window filter
        if published < cutoff:
            continue

        # Dedup
        if item["url"] in seen_urls:
            continue

        # Block-keyword filter
        text_lower = (item["title"] + " " + item["summary"]).lower()
        if any(bk in text_lower for bk in block_kws):
            logger.debug("Blocked by keyword: %s", item["title"])
            continue

        score = _compute_score(item, kw_cfg, user_cfg)
        if score < min_score:
            continue

        item["score"] = score
        filtered.append(item)

    # Sort descending by score
    filtered.sort(key=lambda x: x["score"], reverse=True)
    top = filtered[:max_items]

    # Persist seen URLs for dedup in future runs
    save_seen_urls([item["url"] for item in top])

    return top
