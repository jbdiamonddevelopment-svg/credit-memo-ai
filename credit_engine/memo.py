"""Draft a credit memo from the spread and analysis.

The first draft is rule-based (deterministic, auditable). If ANTHROPIC_API_KEY is set,
`refine_with_claude` rewrites the narrative in analyst voice without changing any numbers.
"""
import json
import os


def money(x, digits=1):
    if x is None:
        return "n/a"
    a = abs(x)
    s = f"${a/1e9:,.{digits}f}B" if a >= 1e9 else f"${a/1e6:,.{digits}f}M" if a >= 1e6 else f"${a:,.0f}"
    return f"({s})" if x < 0 else s


def pct(x, digits=1):
    return "n/a" if x is None else f"{x*100:.{digits}f}%"


def mult(x, digits=1):
    return "n/a" if x is None else f"{x:.{digits}f}x"


def draft_memo(spread: dict, analysis: dict) -> dict:
    c = spread["company"]
    p = spread["periods"][-1]
    first = spread["periods"][0]
    r = analysis["ratios"][-1]
    sc = analysis["scorecard"]
    fac = analysis["facility"]
    stress = analysis["stress"]
    fy = p["fiscal_year"]
    n_years = len(spread["periods"])

    strengths, risks = [], []
    # --- strengths / risks rules ---
    if (p.get("revenue") or 0) > 10e9:
        strengths.append(f"Significant scale with {money(p['revenue'])} of FY{fy} revenue, supporting market position and access to capital markets.")
    if r["ebitda_margin"] is not None and r["ebitda_margin"] > 0.20:
        strengths.append(f"Strong profitability: EBITDA margin of {pct(r['ebitda_margin'])}.")
    elif r["ebitda_margin"] is not None and r["ebitda_margin"] < 0.08:
        risks.append(f"Thin EBITDA margin of {pct(r['ebitda_margin'])} leaves little room to absorb cost pressure.")
    if r["debt_to_ebitda"] is not None:
        if r["debt_to_ebitda"] < 2:
            strengths.append(f"Conservative leverage at {mult(r['debt_to_ebitda'])} total debt / EBITDA.")
        elif r["debt_to_ebitda"] > 4:
            risks.append(f"Elevated leverage at {mult(r['debt_to_ebitda'])} total debt / EBITDA.")
    elif p.get("ebitda") is not None and p["ebitda"] <= 0:
        risks.append("Negative EBITDA: the company is not currently generating operating cash earnings to service debt.")
    if r["interest_coverage"] is not None:
        if r["interest_coverage"] > 8:
            strengths.append(f"Ample debt service capacity with EBITDA covering interest {mult(r['interest_coverage'])}.")
        elif r["interest_coverage"] < 3:
            risks.append(f"Weak interest coverage of {mult(r['interest_coverage'])}.")
    if p.get("fcf") is not None:
        if p["fcf"] > 0:
            strengths.append(f"Positive free cash flow of {money(p['fcf'])} (CFO less capex).")
        else:
            risks.append(f"Negative free cash flow of {money(p['fcf'])}; the business relies on liquidity or external funding.")
    if r["current_ratio"] is not None and r["current_ratio"] < 1.0:
        risks.append(f"Current ratio below 1.0x ({mult(r['current_ratio'],2)}); monitor working capital and revolver availability.")
    if r["negative_equity"]:
        risks.append("Negative shareholders' equity (often from share buybacks or accumulated losses); balance-sheet cushion for creditors is limited.")
    if r["revenue_growth"] is not None:
        if r["revenue_growth"] < -0.03:
            risks.append(f"Revenue declined {pct(-r['revenue_growth'])} year over year.")
        elif r["revenue_growth"] > 0.05:
            strengths.append(f"Revenue grew {pct(r['revenue_growth'])} year over year.")
    down = stress[1]
    if down["coverage"] is not None and down["coverage"] < 2:
        risks.append(f"Under the downside case (EBITDA -20%, rates +200bp) coverage falls to {mult(down['coverage'])}.")
    elif down["coverage"] is not None:
        strengths.append(f"Resilient under stress: downside-case coverage remains {mult(down['coverage'])}.")

    mitigants = []
    if r["negative_equity"] and p.get("fcf") and p["fcf"] > 0:
        mitigants.append("Negative equity is mitigated by consistent free cash flow; repayment relies on cash flow, not balance-sheet liquidation value.")
    if any("leverage" in x.lower() for x in risks):
        mitigants.append("Leverage covenant with ~30% cushion and a requirement to direct excess cash flow to debt reduction if leverage exceeds the covenant level.")
    if any("coverage" in x.lower() for x in risks):
        mitigants.append("Minimum interest coverage covenant tested quarterly; consider an interest-rate hedge for floating-rate exposure.")
    if any("current ratio" in x.lower() for x in risks):
        mitigants.append("Low current ratio is typical for retailers and restaurants with fast inventory turnover and supplier financing; confirm committed revolver availability.")
    if not mitigants:
        mitigants.append("Standard annual review, financial reporting and compliance certificate requirements.")

    growth_txt = ""
    if first.get("revenue") and p.get("revenue") and n_years > 1:
        cagr = (p["revenue"] / first["revenue"]) ** (1 / (n_years - 1)) - 1
        growth_txt = f" Revenue moved from {money(first['revenue'])} in FY{first['fiscal_year']} to {money(p['revenue'])} in FY{fy} ({pct(cagr)} CAGR)."

    sections = {
        "request": (
            f"Illustrative request: a {money(fac['amount'],2)} {fac['type'].lower()} with a {fac['tenor_years']}-year tenor "
            f"to {c['name'].rstrip('.')}. The amount is sized at roughly 0.25x FY{fy} EBITDA for demonstration purposes."
        ),
        "borrower_overview": (
            f"{c['name']} ({c['ticker'] or 'n/a'}) operates in {(c.get('industry') or 'n/a').lower()} (SIC {c.get('sic') or 'n/a'}). "
            f"This analysis uses audited annual figures from the company's 10-K filings via SEC EDGAR XBRL data.{growth_txt}"
        ),
        "financial_performance": (
            (f"Reported EBITDA of {money(p.get('ebitda_reported'))} is adjusted for {money(p.get('impairments'))} of non-cash impairment charges. "
             if (p.get('impairments') or 0) > 0 else "")
            + f"FY{fy} revenue was {money(p.get('revenue'))} with adjusted EBITDA of {money(p.get('ebitda'))} ({pct(r['ebitda_margin'])} margin) "
            f"and net income of {money(p.get('net_income'))}. Operating cash flow was {money(p.get('cfo'))} and capital expenditures were "
            f"{money(p.get('capex'))}, producing free cash flow of {money(p.get('fcf'))}."
        ),
        "leverage_and_coverage": (
            f"Total funded debt was {money(p['total_debt'])} against cash of {money(p.get('cash'))} (net debt {money(p['net_debt'])}). "
            f"Leverage is {mult(r['debt_to_ebitda'])} total and {mult(r['net_debt_to_ebitda'])} net of cash; interest coverage (EBITDA / interest) is "
            + (f"{mult(r['interest_coverage'])}. " if r['interest_coverage'] is not None else "n/a (interest expense not separately disclosed in the 10-K; stress test assumes a 5.5% cost of debt). ")
            + f"Pro forma for the request, leverage is {mult(fac['pro_forma'][0]['leverage'])} and coverage "
            f"{mult(fac['pro_forma'][0]['coverage'])}."
        ),
        "liquidity": (
            f"Current assets of {money(p.get('current_assets'))} versus current liabilities of {money(p.get('current_liabilities'))} "
            f"(current ratio {mult(r['current_ratio'],2)}). Shareholders' equity was {money(p.get('equity'))}."
        ),
        "stress_test": " ".join(
            f"{s['scenario']} (EBITDA {pct(s['ebitda_change'],0)}, rates +{s['rate_change']*10000:.0f}bp): leverage {mult(s['leverage'])}, coverage {mult(s['coverage'])}."
            for s in fac["pro_forma"]
        ),
        "strengths": strengths or ["No material strengths identified by the rule set."],
        "risks": risks or ["No material risks flagged by the rule set; confirm with qualitative review."],
        "mitigants": mitigants,
        "risk_rating": (
            f"Indicative risk rating {sc['risk_rating']} ({sc['risk_label']}), roughly equivalent to {sc['implied_equivalent']}, "
            f"based on a weighted scorecard score of {sc['weighted_score']}/10."
            + (" Overlays applied: " + "; ".join(sc["overlays"]) + "." if sc["overlays"] else "")
        ),
        "recommendation": f"{fac['decision']}. {fac['rationale']}",
        "covenants": [f"{cv['name']}: {cv['level']:.2f}{cv['unit']}" for cv in fac["covenants"]],
    }
    return {"title": f"Credit Memo - {c['name']}", "as_of_fiscal_year": fy, "sections": sections, "ai_refined": False}


def refine_with_claude(memo: dict, model: str = "claude-sonnet-4-5") -> dict:
    """Optional: rewrite narrative sections in analyst voice. Numbers must not change."""
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return memo
    import anthropic  # pip install anthropic

    client = anthropic.Anthropic(api_key=key)
    prompt = (
        "You are a senior commercial credit analyst. Rewrite the narrative fields of this credit memo JSON in concise, "
        "professional bank credit-memo voice. Do NOT change, add or remove any numbers, ratings or the decision. "
        "Keep the same JSON keys and list lengths. Return only JSON.\n\n" + json.dumps(memo["sections"])
    )
    msg = client.messages.create(model=model, max_tokens=4000, messages=[{"role": "user", "content": prompt}])
    text = msg.content[0].text.strip().strip("`")
    if text.startswith("json"):
        text = text[4:]
    try:
        memo = {**memo, "sections": json.loads(text), "ai_refined": True}
    except json.JSONDecodeError:
        pass
    return memo


SECTION_TITLES = [
    ("request", "1. Request"),
    ("borrower_overview", "2. Borrower Overview"),
    ("financial_performance", "3. Financial Performance"),
    ("leverage_and_coverage", "4. Leverage & Debt Service Coverage"),
    ("liquidity", "5. Liquidity & Capital Structure"),
    ("stress_test", "6. Stress Test (Pro Forma)"),
    ("strengths", "7. Key Strengths"),
    ("risks", "8. Key Risks"),
    ("mitigants", "9. Mitigants"),
    ("risk_rating", "10. Risk Rating"),
    ("covenants", "11. Proposed Financial Covenants"),
    ("recommendation", "12. Recommendation"),
]


def write_docx(memo: dict, spread: dict, analysis: dict, path: str) -> None:
    from docx import Document
    from docx.shared import Pt

    doc = Document()
    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(10.5)
    doc.add_heading(memo["title"], level=0)
    doc.add_paragraph(
        f"Fiscal year analyzed: FY{memo['as_of_fiscal_year']}  |  Source: SEC EDGAR 10-K XBRL  |  "
        "Portfolio project - illustrative analysis, not a lending decision."
    ).italic = True

    # Spread table
    doc.add_heading("Financial Spread", level=1)
    periods = spread["periods"]
    rows = [("Revenue", "revenue"), ("Gross profit", "gross_profit"), ("Reported EBITDA", "ebitda_reported"),
            ("Impairment add-backs", "impairments"), ("Adjusted EBITDA", "ebitda"), ("Net income", "net_income"),
            ("Operating cash flow", "cfo"), ("Capex", "capex"), ("Free cash flow", "fcf"), ("Cash", "cash"),
            ("Total debt", "total_debt"), ("Shareholders' equity", "equity")]
    t = doc.add_table(rows=1, cols=len(periods) + 1)
    t.style = "Light Grid Accent 1"
    t.rows[0].cells[0].text = "($)"
    for i, p in enumerate(periods):
        t.rows[0].cells[i + 1].text = f"FY{p['fiscal_year']}"
    for label, key in rows:
        cells = t.add_row().cells
        cells[0].text = label
        for i, p in enumerate(periods):
            cells[i + 1].text = money(p.get(key))
    ratio_rows = [("EBITDA margin", "ebitda_margin", pct), ("Debt / EBITDA", "debt_to_ebitda", mult),
                  ("EBITDA / Interest", "interest_coverage", mult), ("FCF / Debt", "fcf_to_debt", pct),
                  ("Current ratio", "current_ratio", lambda x: mult(x, 2))]
    for label, key, f in ratio_rows:
        cells = t.add_row().cells
        cells[0].text = label
        for i, rr in enumerate(analysis["ratios"]):
            cells[i + 1].text = f(rr.get(key))

    for key, title in SECTION_TITLES:
        doc.add_heading(title, level=1)
        val = memo["sections"][key]
        if isinstance(val, list):
            for item in val:
                doc.add_paragraph(item, style="List Bullet")
        else:
            doc.add_paragraph(val)

    doc.add_heading("Risk Rating Scorecard", level=1)
    st = doc.add_table(rows=1, cols=4)
    st.style = "Light Grid Accent 1"
    for i, h in enumerate(["Factor", "Weight", "Value", "Score (0-10)"]):
        st.rows[0].cells[i].text = h
    for f in analysis["scorecard"]["factors"]:
        cells = st.add_row().cells
        cells[0].text = f["factor"]
        cells[1].text = f"{f['weight']*100:.0f}%"
        v = f["value"]
        cells[2].text = money(v) if f["format"] == "$" else pct(v) if f["format"] == "%" else mult(v)
        cells[3].text = "n/a" if f["score"] is None else str(f["score"])
    doc.save(path)
