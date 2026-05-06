import time
from storage.database import insert_item, make_hash, is_duplicate
from processing.triage import triage_item

TRIAGE_DELAY_SECONDS = 1.5


def process_items(raw_items: list[dict]) -> list[dict]:
    """Dedup, triage, and store incoming items. Returns newly inserted items."""
    new_items = []

    for item in raw_items:
        content_hash = make_hash(item["title"], item["source_url"])
        if is_duplicate(content_hash):
            continue

        triaged = triage_item(item)

        if not triaged.get("relevant", True):
            continue

        row_id = insert_item(triaged)
        if row_id:
            triaged["id"] = row_id
            new_items.append(triaged)

        time.sleep(TRIAGE_DELAY_SECONDS)

    return new_items
