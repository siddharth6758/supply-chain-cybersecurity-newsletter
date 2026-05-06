import re
import yaml
from flask import Flask, render_template, request, jsonify, abort
from storage.database import get_all_items, get_recent_items, get_count_since, get_topic_data, get_topic_items


def slugify(name: str) -> str:
    return re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')

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


@app.route("/hot-topics")
def hot_topics():
    with open("config/hot_topics.yaml") as f:
        config = yaml.safe_load(f)

    topics = []
    for t in config["topics"]:
        data = get_topic_data(t["keywords"])
        topics.append({
            "name":      t["name"],
            "type":      t["type"],
            "label":     t.get("label", ""),
            "slug":      slugify(t["name"]),
            "count_24h": data["count_24h"],
            "count_7d":  data["count_7d"],
            "latest":    data["latest"],
        })

    topics.sort(key=lambda t: (-t["count_24h"], -t["count_7d"]))
    active_24h = sum(1 for t in topics if t["count_24h"] > 0)
    return render_template("hot_topics.html", topics=topics, active_24h=active_24h)


@app.route("/topics/<slug>")
def topic_detail(slug):
    with open("config/hot_topics.yaml") as f:
        config = yaml.safe_load(f)

    topic_cfg = next((t for t in config["topics"] if slugify(t["name"]) == slug), None)
    if not topic_cfg:
        abort(404)

    page = int(request.args.get("page", 1))
    result = get_topic_items(topic_cfg["keywords"], page=page, per_page=50)
    total_pages = max(1, (result["total"] + 49) // 50)

    return render_template(
        "topic_detail.html",
        topic={
            "name":  topic_cfg["name"],
            "type":  topic_cfg["type"],
            "label": topic_cfg.get("label", ""),
            "slug":  slug,
        },
        items=result["items"],
        total=result["total"],
        page=page,
        total_pages=total_pages,
    )


@app.route("/api/unread-count")
def api_unread_count():
    since = request.args.get("since", "1970-01-01T00:00:00")
    return jsonify({"count": get_count_since(since)})
