import feedparser
import yaml
from datetime import datetime
from email.utils import parsedate_to_datetime

CONFIG_PATH = "config/sources.yaml"

CATEGORY_MAP = {
    "supply_chain_news": "supply_chain_news",
    "tool_releases": "tool_release",
    "ai_releases": "ai_release",
}


def _load_sources() -> dict:
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


def _parse_published(entry) -> str | None:
    for attr in ("published", "updated"):
        raw = getattr(entry, attr, None)
        if raw:
            try:
                return parsedate_to_datetime(raw).isoformat()
            except Exception:
                return raw
    return None


def _entry_to_item(entry, source_name: str, category: str) -> dict:
    link = entry.get("link") or ""
    title = entry.get("title", "Untitled").strip()
    return {
        "title": title,
        "source_url": link,
        "source_name": source_name,
        "category": category,
        "published_at": _parse_published(entry),
        "raw_content": entry.get("summary", ""),
    }


def poll_rss() -> list[dict]:
    sources = _load_sources()
    items = []

    for section, category in CATEGORY_MAP.items():
        feeds = sources.get("rss_feeds", {}).get(section, [])
        for feed_cfg in feeds:
            name = feed_cfg["name"]
            url = feed_cfg["url"]
            try:
                parsed = feedparser.parse(url)
                for entry in parsed.entries:
                    item = _entry_to_item(entry, name, category)
                    if item["source_url"]:
                        items.append(item)
            except Exception as e:
                print(f"[RSS] Failed to fetch {name}: {e}")

    return items
