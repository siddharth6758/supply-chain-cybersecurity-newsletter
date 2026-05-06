import os
import threading
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

load_dotenv()

from storage.database import init_db
from ingestion.rss_poller import poll_rss
from ingestion.api_poller import poll_apis
from processing.pipeline import process_items
from delivery.digest import send_digest
from web.app import app

POLL_INTERVAL = int(os.environ.get("POLL_INTERVAL_MINUTES", 5))
DIGEST_TIME = os.environ.get("DIGEST_TIME", "08:00")


def run_poll_cycle():
    print("[Scheduler] Starting poll cycle...")
    raw = poll_rss() + poll_apis()
    print(f"[Scheduler] Fetched {len(raw)} raw items")
    new_items = process_items(raw)
    print(f"[Scheduler] {len(new_items)} new items after dedup + triage")
    if new_items:
        print(f"[Scheduler] {len(new_items)} new items stored")


def start_scheduler():
    scheduler = BackgroundScheduler()

    scheduler.add_job(
        run_poll_cycle,
        "interval",
        minutes=POLL_INTERVAL,
        id="poll_cycle",
        max_instances=1,
    )

    digest_hour, digest_minute = DIGEST_TIME.split(":")
    scheduler.add_job(
        send_digest,
        CronTrigger(hour=int(digest_hour), minute=int(digest_minute)),
        id="daily_digest",
    )

    scheduler.start()
    print(f"[Scheduler] Polling every {POLL_INTERVAL}m | Digest at {DIGEST_TIME} UTC")
    return scheduler


if __name__ == "__main__":
    init_db()
    print("[Init] Database ready")

    # Run one poll cycle immediately on startup
    threading.Thread(target=run_poll_cycle, daemon=True).start()

    scheduler = start_scheduler()

    print(f"[Web] Dashboard at http://0.0.0.0:5000")
    app.run(host="0.0.0.0", port=5000, use_reloader=False)
