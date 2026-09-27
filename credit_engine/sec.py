"""Fetch and cache SEC EDGAR XBRL data (free, no API key).

SEC asks every client to send a descriptive User-Agent with contact info.
Set it with the SEC_USER_AGENT environment variable, e.g.
    export SEC_USER_AGENT="Your Name your.email@example.com"
"""
import json
import os
import urllib.request
from pathlib import Path

from .tags import ALL_TAGS

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
BASE = "https://data.sec.gov"


def _get(url: str) -> dict:
    ua = os.environ.get("SEC_USER_AGENT")
    if not ua:
        raise RuntimeError("Set SEC_USER_AGENT to 'Your Name your@email' before fetching from SEC.")
    req = urllib.request.Request(url, headers={"User-Agent": ua, "Accept-Encoding": "identity"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def compact(companyfacts: dict, submissions: dict | None = None) -> dict:
    """Keep only the tags the engine uses (a full companyfacts file can be 5+ MB)."""
    gaap = companyfacts.get("facts", {}).get("us-gaap", {})
    kept = {}
    for tag in ALL_TAGS:
        units = gaap.get(tag, {}).get("units", {})
        usd = units.get("USD")
        if usd:
            kept[tag] = {"units": {"USD": [
                {k: f.get(k) for k in ("start", "end", "val", "fy", "fp", "form", "filed", "frame")}
                for f in usd if (f.get("form") or "").startswith("10-K")
            ]}}
    sub = submissions or {}
    return {
        "cik": int(companyfacts.get("cik", 0)),
        "entityName": companyfacts.get("entityName"),
        "tickers": sub.get("tickers", []),
        "sic": sub.get("sic"),
        "sicDescription": sub.get("sicDescription"),
        "fiscalYearEnd": sub.get("fiscalYearEnd"),
        "facts": {"us-gaap": kept},
    }


def fetch_company(cik: int, refresh: bool = False) -> dict:
    """Return compacted company data, using the local cache when present."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = DATA_DIR / f"CIK{cik:010d}.json"
    if path.exists() and not refresh:
        return json.loads(path.read_text())
    facts = _get(f"{BASE}/api/xbrl/companyfacts/CIK{cik:010d}.json")
    subs = _get(f"{BASE}/submissions/CIK{cik:010d}.json")
    data = compact(facts, subs)
    path.write_text(json.dumps(data))
    return data


def load_company(path: str | Path) -> dict:
    return json.loads(Path(path).read_text())
