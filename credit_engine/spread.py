"""Turn raw XBRL facts into an annual financial spread (like a bank's spreading software)."""
from datetime import date

from .tags import DURATION_TAGS, INSTANT_TAGS


def _d(s: str) -> date:
    return date.fromisoformat(s)


def _annual_duration(facts: list) -> dict:
    """Map fiscal-year end date -> value for ~1-year periods, preferring the latest filing (restatements)."""
    out = {}
    for f in facts:
        if not f.get("start") or not (f.get("form") or "").startswith("10-K"):
            continue
        days = (_d(f["end"]) - _d(f["start"])).days
        if not 330 <= days <= 400:
            continue
        prev = out.get(f["end"])
        if prev is None or (f.get("filed") or "") >= prev[1]:
            out[f["end"]] = (f["val"], f.get("filed") or "")
    return {k: v[0] for k, v in out.items()}


def _instant(facts: list) -> dict:
    out = {}
    for f in facts:
        if f.get("start") or not (f.get("form") or "").startswith("10-K"):
            continue
        prev = out.get(f["end"])
        if prev is None or (f.get("filed") or "") >= prev[1]:
            out[f["end"]] = (f["val"], f.get("filed") or "")
    return {k: v[0] for k, v in out.items()}


def _pick(series_by_tag: dict, tags: list, end: str, tolerance_days: int = 0):
    """Return (value, tag) using the first tag with data for this period end."""
    for tag in tags:
        s = series_by_tag.get(tag)
        if not s:
            continue
        if end in s:
            return s[end], tag
        if tolerance_days:
            for k, v in s.items():
                if abs((_d(k) - _d(end)).days) <= tolerance_days:
                    return v, tag
    return None, None


def build_spread(company: dict, years: int = 4) -> dict:
    gaap = company["facts"]["us-gaap"]
    dur = {t: _annual_duration(v["units"]["USD"]) for t, v in gaap.items()}
    inst = {t: _instant(v["units"]["USD"]) for t, v in gaap.items()}

    # Fiscal year ends = periods where we have annual revenue or net income.
    ends = set()
    for tag in DURATION_TAGS["revenue"] + DURATION_TAGS["net_income"]:
        ends.update(dur.get(tag, {}).keys())
    ends = sorted(ends)[-years:]

    periods, sources = [], {}
    for end in ends:
        # Fiscal year label: calendar year it ends in, except Jan/early-Feb year-ends
        # (retailers), which call the year that just ended "fiscal <prior year>".
        fy = int(end[:4]) - 1 if end[5:7] == "01" or end[5:10] <= "02-07" and end[5:7] == "02" else int(end[:4])
        row = {"period_end": end, "fiscal_year": fy}
        for item, tags in DURATION_TAGS.items():
            val, tag = _pick(dur, tags, end, tolerance_days=7)
            row[item] = val
            if tag:
                sources.setdefault(item, set()).add(tag)
        for item, tags in INSTANT_TAGS.items():
            val, tag = _pick(inst, tags, end, tolerance_days=7)
            row[item] = val
            if tag:
                sources.setdefault(item, set()).add(tag)
                if item == "ltd_current":
                    row["_ltd_current_tag"] = tag
        _derive(row)
        periods.append(row)

    return {
        "company": {
            "name": company.get("entityName"),
            "cik": company.get("cik"),
            "ticker": (company.get("tickers") or [None])[0],
            "industry": company.get("sicDescription"),
            "sic": company.get("sic"),
            "fiscal_year_end": company.get("fiscalYearEnd"),
        },
        "periods": periods,
        "sources": {k: sorted(v) for k, v in sources.items()},
    }


def _nz(x):
    return x or 0


def _derive(r: dict) -> None:
    # Gross profit
    r["gross_profit"] = r["revenue"] - r["cogs"] if r.get("revenue") is not None and r.get("cogs") is not None else None
    # EBITDA = operating income + D&A (bank "simple EBITDA", no add-backs)
    # Fall back to pretax income + interest when operating income isn't tagged (e.g., Nike)
    if r.get("operating_income") is None and r.get("pretax_income") is not None:
        r["operating_income"] = r["pretax_income"] + _nz(r.get("interest_expense"))
        r["_ebit_proxy"] = True
    if r.get("operating_income") is not None:
        r["ebitda_reported"] = r["operating_income"] + _nz(r.get("depreciation_amortization"))
    else:
        r["ebitda_reported"] = None
    # Adjusted EBITDA adds back non-cash impairments (standard credit add-back)
    r["impairments"] = max(_nz(r.get("imp_goodwill_intangible")), _nz(r.get("imp_assets")),
                           _nz(r.get("imp_goodwill")) + _nz(r.get("imp_intangible")))
    r["ebitda"] = None if r["ebitda_reported"] is None else r["ebitda_reported"] + r["impairments"]
    # Total funded debt (excludes operating leases). Filers tag debt inconsistently, so take the
    # larger of (a) a reported total and (b) noncurrent + current portions.
    a = r.get("ltd_total")
    b = None
    if r.get("ltd_noncurrent") is not None or r.get("ltd_current") is not None:
        b = _nz(r.get("ltd_noncurrent")) + _nz(r.get("ltd_current"))
    debt = max([x for x in (a, b) if x is not None], default=0)
    # DebtCurrent already includes commercial paper/short-term borrowings; avoid double counting
    if not (r.get("_ltd_current_tag") == "DebtCurrent" and (b or 0) >= (a or 0)):
        debt += _nz(r.get("commercial_paper")) + _nz(r.get("short_term_borrowings"))
    r["total_debt"] = debt
    r["net_debt"] = r["total_debt"] - _nz(r.get("cash"))
    # FCF only when capex is reported; otherwise we'd overstate cash flow
    r["fcf"] = r["cfo"] - r["capex"] if r.get("cfo") is not None and r.get("capex") is not None else None
    r.pop("_ltd_current_tag", None)
