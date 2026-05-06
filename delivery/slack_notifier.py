import os
import requests

SEVERITY_EMOJI = {
    "CRITICAL": ":rotating_light:",
    "HIGH": ":red_circle:",
    "MEDIUM": ":large_yellow_circle:",
    "LOW": ":large_green_circle:",
    "INFO": ":information_source:",
}

CATEGORY_EMOJI = {
    "supply_chain_news": ":link:",
    "tool_release": ":wrench:",
    "ai_release": ":robot_face:",
}


def _webhook_url() -> str | None:
    return os.environ.get("SLACK_WEBHOOK_URL")


def send_alert(item: dict) -> bool:
    url = _webhook_url()
    if not url:
        return False

    sev = item.get("severity")
    cat = item.get("category", "")
    emoji = SEVERITY_EMOJI.get(sev, CATEGORY_EMOJI.get(cat, ":newspaper:"))
    sev_text = f" | *{sev}*" if sev else ""

    payload = {
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"{emoji} *<{item['source_url']}|{item['title']}>*{sev_text}",
                },
            },
            {
                "type": "context",
                "elements": [
                    {"type": "mrkdwn", "text": f"_{item.get('summary', '')}_"},
                    {"type": "mrkdwn", "text": f"Source: *{item['source_name']}*"},
                ],
            },
        ]
    }

    try:
        resp = requests.post(url, json=payload, timeout=10)
        return resp.status_code == 200
    except Exception as e:
        print(f"[Slack] Failed to send alert: {e}")
        return False


def send_batch_alerts(items: list[dict]):
    for item in items:
        send_alert(item)
