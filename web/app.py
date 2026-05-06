from flask import Flask, render_template, request, jsonify
from storage.database import get_all_items, get_recent_items, get_count_since

app = Flask(__name__)

CATEGORIES = {
    "": "All",
    "supply_chain_news": "Supply Chain News",
    "tool_release": "Tool Releases",
    "ai_release": "AI / LLM",
}

SEVERITY_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4, None: 5}


@app.route("/")
def index():
    category = request.args.get("category", "")
    page = int(request.args.get("page", 1))
    result = get_all_items(page=page, per_page=50, category=category or None)
    items = result["items"]
    items.sort(key=lambda x: SEVERITY_ORDER.get(x.get("severity"), 5))
    total_pages = max(1, (result["total"] + 49) // 50)
    return render_template(
        "index.html",
        items=items,
        categories=CATEGORIES,
        active_category=category,
        page=page,
        total_pages=total_pages,
        total=result["total"],
    )


@app.route("/api/items")
def api_items():
    category = request.args.get("category")
    page = int(request.args.get("page", 1))
    result = get_all_items(page=page, per_page=50, category=category)
    return jsonify(result)


@app.route("/api/recent")
def api_recent():
    hours = int(request.args.get("hours", 24))
    return jsonify(get_recent_items(hours=hours))


@app.route("/api/unread-count")
def api_unread_count():
    since = request.args.get("since", "1970-01-01T00:00:00")
    return jsonify({"count": get_count_since(since)})
