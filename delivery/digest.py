import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from storage.database import get_recent_items, log_digest

CATEGORY_LABELS = {
    "supply_chain_news": "Supply Chain News",
    "tool_release": "Tool Releases",
    "ai_release": "AI / LLM Releases",
}


def _build_html(items: list[dict], date_str: str) -> str:
    by_category: dict[str, list] = {}
    for item in items:
        by_category.setdefault(item["category"], []).append(item)

    rows = ""
    for cat_key, label in CATEGORY_LABELS.items():
        cat_items = by_category.get(cat_key, [])
        if not cat_items:
            continue
        rows += f'<h2 style="color:#58a6ff;border-bottom:1px solid #30363d;padding-bottom:8px;margin-top:28px">{label} ({len(cat_items)})</h2>'
        for item in cat_items:
            sev_badge = ""
            if item.get("severity"):
                colors = {"CRITICAL": "#f85149", "HIGH": "#d29922", "MEDIUM": "#e3b341", "LOW": "#3fb950"}
                color = colors.get(item["severity"], "#8b949e")
                sev_badge = f'<span style="background:{color}22;color:{color};padding:2px 8px;border-radius:10px;font-size:11px;font-weight:bold;margin-left:8px">{item["severity"]}</span>'
            rows += f"""
            <div style="background:#161b22;border:1px solid #30363d;border-radius:8px;padding:14px 16px;margin-bottom:12px">
              <a href="{item['source_url']}" style="color:#e6edf3;text-decoration:none;font-weight:600;font-size:14px">{item['title']}</a>{sev_badge}
              <p style="color:#8b949e;font-size:13px;margin:6px 0 0">{item.get('summary','')}</p>
              <p style="color:#58a6ff;font-size:12px;margin:6px 0 0">{item['source_name']}</p>
            </div>"""

    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"></head>
<body style="background:#0d1117;color:#e6edf3;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;max-width:680px;margin:0 auto;padding:24px">
  <h1 style="color:#e6edf3;font-size:20px">Supply Chain Security Digest<br>
    <span style="color:#8b949e;font-size:14px;font-weight:normal">{date_str} &mdash; {len(items)} items</span>
  </h1>
  {rows}
  <p style="color:#8b949e;font-size:12px;margin-top:32px;border-top:1px solid #30363d;padding-top:16px">
    Supply Chain Security Tracker &mdash; Triam Security
  </p>
</body></html>"""


def send_digest():
    recipient = os.environ.get("DIGEST_EMAIL")
    gmail_user = os.environ.get("GMAIL_USER")
    gmail_pass = os.environ.get("GMAIL_APP_PASSWORD")

    items = get_recent_items(hours=24)
    if not items:
        print("[Digest] No items in last 24h, skipping.")
        return

    date_str = datetime.utcnow().strftime("%B %d, %Y")
    html = _build_html(items, date_str)

    if recipient and gmail_user and gmail_pass:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"Supply Chain Security Digest — {date_str}"
        msg["From"] = gmail_user
        msg["To"] = recipient
        msg.attach(MIMEText(html, "html"))
        try:
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(gmail_user, gmail_pass)
                server.sendmail(gmail_user, recipient, msg.as_string())
            print(f"[Digest] Sent to {recipient} ({len(items)} items)")
        except Exception as e:
            print(f"[Digest] Email failed: {e}")
    else:
        print(f"[Digest] Email not configured. Would have sent {len(items)} items.")

    log_digest(len(items))
