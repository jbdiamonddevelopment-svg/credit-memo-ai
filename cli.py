"""Command line: python cli.py --cik 320193 [--ai] [--docx]

Examples
    export SEC_USER_AGENT="Your Name your@email.com"
    python cli.py --cik 320193 --docx          # Apple
    python cli.py --file data/raw/CIK0000320193.json --docx
    python cli.py --export-web                 # all cached companies -> web/companies.json
"""
import argparse
import json
from pathlib import Path

from credit_engine import run, write_docx
from credit_engine.memo import mult, money
from credit_engine.sec import DATA_DIR, fetch_company, load_company

OUT = Path(__file__).parent / "output"


def one(company: dict, args) -> dict:
    result = run(company, years=args.years, use_ai=args.ai)
    c = result["spread"]["company"]
    sc = result["analysis"]["scorecard"]
    r = result["analysis"]["ratios"][-1]
    print(f"{c['name']:<40} rating {sc['risk_rating']} {sc['risk_label']:<16} "
          f"Debt/EBITDA {mult(r['debt_to_ebitda']):>6}  Coverage {mult(r['interest_coverage']):>7}  "
          f"-> {result['analysis']['facility']['decision']}")
    OUT.mkdir(exist_ok=True)
    slug = (c["ticker"] or str(c["cik"])).upper()
    (OUT / f"{slug}.json").write_text(json.dumps(result, indent=2, default=str))
    if args.docx:
        write_docx(result["memo"], result["spread"], result["analysis"], str(OUT / f"{slug}_credit_memo.docx"))
    return result


def main():
    ap = argparse.ArgumentParser(description="Credit memo generator from SEC filings")
    ap.add_argument("--cik", type=int)
    ap.add_argument("--file")
    ap.add_argument("--years", type=int, default=4)
    ap.add_argument("--ai", action="store_true", help="Refine narrative with Claude (needs ANTHROPIC_API_KEY)")
    ap.add_argument("--docx", action="store_true")
    ap.add_argument("--export-web", action="store_true", help="Run all cached companies and write web/companies.json")
    args = ap.parse_args()

    if args.export_web:
        results = [one(load_company(f), args) for f in sorted(DATA_DIR.glob("CIK*.json"))]
        web = Path(__file__).parent / "web"
        web.mkdir(exist_ok=True)
        (web / "companies.json").write_text(json.dumps(results, default=str))
        print(f"Wrote {len(results)} companies to web/companies.json")
        return
    company = load_company(args.file) if args.file else fetch_company(args.cik)
    one(company, args)


if __name__ == "__main__":
    main()
