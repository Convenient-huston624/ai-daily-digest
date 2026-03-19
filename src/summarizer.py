"""LLM-powered summarization with multi-provider support."""
from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

_PROVIDERS: dict[str, dict] = {
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "key_env": "OPENAI_API_KEY",
    },
    "deepseek": {
        "base_url": "https://api.deepseek.com/v1",
        "key_env": "DEEPSEEK_API_KEY",
    },
    "anthropic": {
        "base_url": None,
        "key_env": "ANTHROPIC_API_KEY",
    },
}

_ITEM_SYSTEM_PROMPT = """你是一位 AI 领域资深研究员，负责为同行整理每日要闻。
请将用户提供的英文摘要用{language}写成一句话摘要（不超过{max_chars}字）。
要求：
1. 直接说出核心信息，不要说"该文章介绍了"之类的废话
2. 如果涉及模型发布，必须点出模型名称和关键数据指标
3. 如果是新模型，说明大小和主要能力
4. 如果是商业动态，说明金额/规模/战略意图"""

_OVERVIEW_SYSTEM_PROMPT = """你是一位 AI 领域资深研究员。
以下是今日 AI 领域的 {n} 条要闻摘要，请用 3-5 句话写一段执行摘要，
指出最重要的趋势或事件，以及对专业 AI 研究人员的影响。"""


def _build_client(provider: str) -> Any:
    cfg = _PROVIDERS.get(provider)
    if cfg is None:
        raise ValueError(f"Unknown provider: {provider!r}. Choose from {list(_PROVIDERS)}")

    api_key = os.getenv(cfg["key_env"], "")
    if not api_key:
        raise EnvironmentError(
            f"Environment variable {cfg['key_env']!r} is not set. "
            f"Add it to GitHub Secrets or your .env file."
        )

    if provider == "anthropic":
        import anthropic
        return anthropic.AsyncAnthropic(api_key=api_key)

    from openai import AsyncOpenAI
    return AsyncOpenAI(api_key=api_key, base_url=cfg["base_url"])


async def _summarize_one(client: Any, item: dict, user_cfg: dict) -> str:
    llm_cfg = user_cfg.get("llm", {})
    provider = llm_cfg.get("provider", "openai")
    model = llm_cfg.get("model", "gpt-4o-mini")
    language = "中文" if llm_cfg.get("summary_language", "zh") == "zh" else "English"
    max_chars = llm_cfg.get("max_summary_chars", 60)

    system_prompt = _ITEM_SYSTEM_PROMPT.format(language=language, max_chars=max_chars)
    user_prompt = f"标题: {item['title']}\n原文摘要: {item['summary'][:500]}"

    try:
        if provider == "anthropic":
            resp = await client.messages.create(
                model=model,
                max_tokens=200,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
            return resp.content[0].text.strip()
        else:
            resp = await client.chat.completions.create(
                model=model,
                max_tokens=200,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            return resp.choices[0].message.content.strip()
    except Exception as exc:
        logger.warning("LLM summarization failed for %r: %s", item["title"], exc)
        # Fallback: truncate original summary
        fallback = item.get("summary", item["title"])
        return fallback[:max_chars]


async def summarize_all(items: list[dict], user_cfg: dict) -> list[dict]:
    """Add a 'summary_zh' field to each item using the configured LLM."""
    provider = user_cfg.get("llm", {}).get("provider", "openai")
    client = _build_client(provider)

    tasks = [_summarize_one(client, item, user_cfg) for item in items]
    summaries = await asyncio.gather(*tasks)

    for item, summary in zip(items, summaries):
        item["summary_zh"] = summary

    return items


async def generate_overview(items: list[dict], user_cfg: dict) -> str:
    """Generate a global overview paragraph from the top items."""
    if not items:
        return ""

    provider = user_cfg.get("llm", {}).get("provider", "openai")
    model = user_cfg.get("llm", {}).get("model", "gpt-4o-mini")
    client = _build_client(provider)

    bullets = "\n".join(
        f"- {item['title']}: {item.get('summary_zh', item['summary'][:100])}"
        for item in items
    )
    system_prompt = _OVERVIEW_SYSTEM_PROMPT.format(n=len(items))
    user_prompt = bullets

    try:
        if provider == "anthropic":
            resp = await client.messages.create(
                model=model,
                max_tokens=400,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
            return resp.content[0].text.strip()
        else:
            resp = await client.chat.completions.create(
                model=model,
                max_tokens=400,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            return resp.choices[0].message.content.strip()
    except Exception as exc:
        logger.warning("Overview generation failed: %s", exc)
        return ""
