import requests
import yaml
from datetime import datetime, timedelta

CONFIG_PATH = "config/sources.yaml"
REQUEST_TIMEOUT = 15


def _load_sources() -> dict:
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


def _fetch_osv() -> list[dict]:
    """Fetch vulnerabilities from OSV.dev for a watchlist of high-value packages."""
    sources = _load_sources()
    packages_cfg = sources.get("apis", {}).get("osv", {}).get("packages", {})
    base_url = sources["apis"]["osv"]["base_url"]
    items = []

    for ecosystem, packages in packages_cfg.items():
        for package_name in packages:
            try:
                resp = requests.post(
                    f"{base_url}/query",
                    json={"package": {"name": package_name, "ecosystem": ecosystem}},
                    timeout=REQUEST_TIMEOUT,
                )
                resp.raise_for_status()
                for vuln in resp.json().get("vulns", [])[:5]:
                    vuln_id = vuln.get("id", "")
                    summary = vuln.get("summary", "")
                    modified = vuln.get("modified", "")
                    aliases = vuln.get("aliases", [])
                    cve = next((a for a in aliases if a.startswith("CVE-")), vuln_id)

                    items.append({
                        "title": f"[{ecosystem}/{package_name}] {cve}: {summary}",
                        "source_url": f"https://osv.dev/vulnerability/{vuln_id}",
                        "source_name": f"OSV.dev ({ecosystem})",
                        "category": "supply_chain_news",
                        "published_at": modified,
                        "raw_content": summary,
                    })
            except Exception as e:
                print(f"[OSV] Failed for {ecosystem}/{package_name}: {e}")

    return items


def _fetch_cisa_kev() -> list[dict]:
    """Fetch CISA Known Exploited Vulnerabilities."""
    sources = _load_sources()
    url = sources["apis"]["cisa_kev"]["url"]
    items = []

    try:
        resp = requests.get(url, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        cutoff = (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%d")

        for vuln in data.get("vulnerabilities", []):
            date_added = vuln.get("dateAdded", "")
            if date_added < cutoff:
                continue
            cve_id = vuln.get("cveID", "")
            name = vuln.get("vulnerabilityName", "")
            vendor = vuln.get("vendorProject", "")
            product = vuln.get("product", "")

            items.append({
                "title": f"[CISA KEV] {cve_id}: {name} — {vendor} {product}",
                "source_url": f"https://www.cisa.gov/known-exploited-vulnerabilities-catalog",
                "source_name": "CISA KEV",
                "category": "supply_chain_news",
                "published_at": date_added,
                "raw_content": vuln.get("shortDescription", ""),
            })
    except Exception as e:
        print(f"[CISA KEV] Failed: {e}")

    return items


def _fetch_nvd() -> list[dict]:
    """Fetch NVD CVEs matching supply chain keywords."""
    sources = _load_sources()
    base_url = sources["apis"]["nvd"]["base_url"]
    keywords = sources["apis"]["nvd"]["keywords"]
    items = []

    pub_start = (datetime.utcnow() - timedelta(days=3)).strftime("%Y-%m-%dT00:00:00.000")
    pub_end = datetime.utcnow().strftime("%Y-%m-%dT23:59:59.999")

    for keyword in keywords[:3]:
        try:
            resp = requests.get(
                base_url,
                params={
                    "keywordSearch": keyword,
                    "pubStartDate": pub_start,
                    "pubEndDate": pub_end,
                    "resultsPerPage": 10,
                },
                timeout=REQUEST_TIMEOUT,
            )
            resp.raise_for_status()
            for vuln in resp.json().get("vulnerabilities", []):
                cve = vuln.get("cve", {})
                cve_id = cve.get("id", "")
                descs = cve.get("descriptions", [])
                desc = next((d["value"] for d in descs if d["lang"] == "en"), "")
                published = cve.get("published", "")
                metrics = cve.get("metrics", {})
                severity = None
                cvss_v3 = metrics.get("cvssMetricV31") or metrics.get("cvssMetricV30")
                if cvss_v3:
                    severity = cvss_v3[0].get("cvssData", {}).get("baseSeverity")

                items.append({
                    "title": f"[NVD] {cve_id}: {desc[:120]}",
                    "source_url": f"https://nvd.nist.gov/vuln/detail/{cve_id}",
                    "source_name": "NVD",
                    "category": "supply_chain_news",
                    "published_at": published,
                    "raw_content": desc,
                    "severity": severity,
                })
        except Exception as e:
            print(f"[NVD] Failed for '{keyword}': {e}")

    return items


def poll_apis() -> list[dict]:
    items = []
    items.extend(_fetch_osv())
    items.extend(_fetch_cisa_kev())
    items.extend(_fetch_nvd())
    return items
