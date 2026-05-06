import os
from groq import Groq

_client = None


def _get_client() -> Groq:
    global _client
    if _client is None:
        _client = Groq(api_key=os.environ["GROQ_API_KEY"])
    return _client


SYSTEM_PROMPT = """You are a supply chain security analyst. Your job is to triage incoming news items.

For each item you receive, respond with a JSON object containing:
- "relevant": true/false — is this genuinely relevant to supply chain security?
- "summary": one sentence (max 25 words) explaining what happened
- "severity": "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | "INFO" — only for vulnerabilities/incidents, otherwise null
- "tags": list of up to 3 tags from: [vulnerability, malicious-package, dependency-confusion, typosquatting, build-system, ci-cd, sbom, signing, tool-release, ai-release, incident, research, advisory]

Supply chain security includes: dependency vulnerabilities, malicious packages, CI/CD attacks, build system compromises, SBOM, software signing, typosquatting, dependency confusion, and related tooling.

Respond ONLY with valid JSON. No markdown, no explanation."""


def triage_item(item: dict) -> dict:
    """Run LLM triage on a single item. Returns enriched item dict."""
    prompt = f"Title: {item['title']}\nSource: {item['source_name']}\nContent: {item.get('raw_content', '')[:500]}"

    try:
        response = _get_client().chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            max_tokens=200,
        )
        import json
        result = json.loads(response.choices[0].message.content)
        item["relevant"] = result.get("relevant", True)
        item["summary"] = result.get("summary") or item.get("summary")
        item["severity"] = item.get("severity") or result.get("severity")
        item["tags"] = result.get("tags", [])
    except Exception as e:
        print(f"[Triage] LLM call failed for '{item['title']}': {e}")
        item["relevant"] = True
        item["summary"] = item["title"]
        item["tags"] = []

    return item


def triage_batch(items: list[dict]) -> list[dict]:
    """Triage a list of items, filtering irrelevant ones out."""
    results = []
    for item in items:
        triaged = triage_item(item)
        if triaged.get("relevant", True):
            results.append(triaged)
    return results
