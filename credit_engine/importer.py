"""Convert the compact browser-export format into the engine's companyfacts shape."""
import json
from pathlib import Path


def from_compact(o: dict) -> dict:
    facts = {}
    for tag, rows in o["f"].items():
        if tag.startswith("_"):
            continue
        facts[tag] = {"units": {"USD": [
            {"start": r[0] or None, "end": r[1], "val": r[2], "form": "10-K", "filed": ""} for r in rows
        ]}}
    return {"cik": o["c"], "entityName": o["n"], "tickers": o.get("t", []), "sic": o.get("s"),
            "sicDescription": o.get("sd"), "fiscalYearEnd": o.get("fy"), "facts": {"us-gaap": facts}}


def _year_before(end: str) -> str:
    from datetime import date, timedelta
    return (date.fromisoformat(end) - timedelta(days=364)).isoformat()


def import_batches(src_dir: Path, dest_dir: Path) -> int:
    imp_path = src_dir / "impairments.json"
    impairments = json.loads(imp_path.read_text()) if imp_path.exists() else {}
    n = 0
    for f in sorted(src_dir.glob("batch*.json")):
        for o in json.loads(f.read_text()):
            data = from_compact(o)
            for tag, rows in impairments.get(str(o["c"]), {}).items():
                data["facts"]["us-gaap"][tag] = {"units": {"USD": [
                    {"start": _year_before(e), "end": e, "val": v, "form": "10-K", "filed": ""} for e, v in rows]}}
            (dest_dir / f"CIK{o['c']:010d}.json").write_text(json.dumps(data))
            n += 1
    return n
