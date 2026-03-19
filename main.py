"""Entry point — run a single digest cycle for the given schedule index."""
from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("main")

# Ensure project root is on the path when invoked directly
sys.path.insert(0, str(Path(__file__).parent))

from src.fetcher import fetch_all, load_sources_with_filter
from src.filter import filter_and_score
from src.notifier import send_wechat
from src.summarizer import generate_overview, summarize_all
from src.utils import load_user_config, save_archive


async def run(schedule_index: int) -> None:
    user_cfg = load_user_config()
    schedules = user_cfg.get("schedule", [])

    if schedule_index >= len(schedules):
        logger.error(
            "schedule_index %d out of range (only %d schedules defined)",
            schedule_index,
            len(schedules),
        )
        sys.exit(1)

    schedule = schedules[schedule_index]
    if not schedule.get("enabled", True):
        logger.info("Schedule index %d (%s) is disabled — exiting.", schedule_index, schedule.get("label"))
        return

    lookback_hours: int = schedule.get("lookback_hours", 24)
    logger.info(
        "Running digest: %s  (lookback=%dh)",
        schedule.get("label", ""),
        lookback_hours,
    )

    # 1. Load sources with tag filters applied
    sources = load_sources_with_filter(user_cfg)
    logger.info("Loaded %d sources after tag filtering", len(sources))

    # 2. Fetch all RSS feeds concurrently
    raw_items = await fetch_all(sources)
    logger.info("Fetched %d raw items", len(raw_items))

    # 3. Filter, deduplicate, score and rank
    filtered = filter_and_score(raw_items, user_cfg, lookback_hours=lookback_hours)
    logger.info("After filtering: %d items", len(filtered))

    if not filtered:
        logger.info("No items to send — exiting cleanly.")
        return

    # 4. LLM summarization
    items = await summarize_all(filtered, user_cfg)

    overview = ""
    if user_cfg.get("llm", {}).get("generate_overview", True):
        overview = await generate_overview(items, user_cfg)

    # 5. Archive to markdown
    save_archive(items, overview, schedule.get("label", "AI Digest"))

    # 6. Send WeChat notification
    await send_wechat(items, overview, schedule, user_cfg)

    logger.info("Done ✅")


def main() -> None:
    parser = argparse.ArgumentParser(description="AI Daily Digest runner")
    parser.add_argument(
        "--schedule-index",
        type=int,
        default=0,
        help="Index into user_config.yaml schedule list (0-based)",
    )
    args = parser.parse_args()
    asyncio.run(run(args.schedule_index))


if __name__ == "__main__":
    main()
