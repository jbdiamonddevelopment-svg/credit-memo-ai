"""Credit ratios, stress testing, risk rating scorecard and an illustrative facility request."""
import math


def _div(a, b):
    if a is None or b is None or b == 0:
        return None
    return a / b


def compute_ratios(spread: dict) -> list:
    out = []
    prev = None
    for p in spread["periods"]:
        r = {"fiscal_year": p["fiscal_year"], "period_end": p["period_end"]}
        r["revenue_growth"] = _div(p["revenue"] - prev["revenue"], abs(prev["revenue"])) if prev and p.get("revenue") and prev.get("revenue") else None
        r["gross_margin"] = _div(p.get("gross_profit"), p.get("revenue"))
        r["ebitda_margin"] = _div(p.get("ebitda"), p.get("revenue"))
        r["net_margin"] = _div(p.get("net_income"), p.get("revenue"))
        ebitda = p.get("ebitda")
        r["debt_to_ebitda"] = _div(p["total_debt"], ebitda) if ebitda and ebitda > 0 else None
        r["net_debt_to_ebitda"] = _div(p["net_debt"], ebitda) if ebitda and ebitda > 0 else None
        r["interest_coverage"] = _div(ebitda, p.get("interest_expense"))
        r["capex_adj_coverage"] = _div((ebitda or 0) - (p.get("capex") or 0), p.get("interest_expense")) if ebitda is not None else None
        r["fcf_to_debt"] = _div(p.get("fcf"), p["total_debt"]) if p["total_debt"] else None
        r["current_ratio"] = _div(p.get("current_assets"), p.get("current_liabilities"))
        eq = p.get("equity")
        r["debt_to_equity"] = _div(p["total_debt"], eq) if eq and eq > 0 else None
        r["debt_to_capital"] = _div(p["total_debt"], p["total_debt"] + eq) if eq is not None and (p["total_debt"] + eq) > 0 else None
        r["roa"] = _div(p.get("net_income"), p.get("total_assets"))
        r["negative_equity"] = eq is not None and eq < 0
        out.append(r)
        prev = p
    return out


# ---------- Scorecard ----------

def _band(x, cuts, higher_is_better=True):
    """cuts: thresholds for scores 10,8,6,4,2 (else 0)."""
    if x is None:
        return None
    scores = [10, 8, 6, 4, 2]
    for c, s in zip(cuts, scores):
        if (x > c) if higher_is_better else (x < c):
            return s
    return 0


RATINGS = [
    (8.5, 1, "Exceptional", "AA / Aa"),
    (7.5, 2, "Strong", "A"),
    (6.5, 3, "Good", "BBB+ / BBB"),
    (5.5, 4, "Satisfactory", "BBB-"),
    (4.5, 5, "Acceptable", "BB"),
    (3.5, 6, "Watch", "B+"),
    (2.5, 7, "Special Mention", "B / B-"),
    (-1, 8, "Substandard", "CCC"),
]


def scorecard(spread: dict, ratios: list) -> dict:
    p, r = spread["periods"][-1], ratios[-1]
    first = spread["periods"][0]
    no_debt = (p["total_debt"] or 0) <= 0.05 * max(p.get("ebitda") or 1, 1)
    ebitda = p.get("ebitda")

    factors = []

    def add(name, weight, score, value, fmt):
        factors.append({"factor": name, "weight": weight, "score": score, "value": value, "format": fmt})

    lev = 10 if no_debt else (0 if not ebitda or ebitda <= 0 else _band(r["debt_to_ebitda"], [1, 2, 3, 4, 5.5], higher_is_better=False))
    add("Leverage (Debt / EBITDA)", 0.25, lev, r["debt_to_ebitda"], "x")
    cov = 10 if no_debt else _band(r["interest_coverage"], [15, 8, 5, 3, 1.5])
    add("Interest coverage (EBITDA / Interest)", 0.20, cov, r["interest_coverage"], "x")
    fcf = 10 if no_debt else _band(r["fcf_to_debt"], [0.5, 0.25, 0.15, 0.08, 0.0])
    add("Cash flow (FCF / Debt)", 0.15, fcf, r["fcf_to_debt"], "%")
    add("Profitability (EBITDA margin)", 0.15, _band(r["ebitda_margin"], [0.30, 0.20, 0.12, 0.07, 0.0]), r["ebitda_margin"], "%")
    add("Liquidity (Current ratio)", 0.10, _band(r["current_ratio"], [2.0, 1.5, 1.1, 0.9, 0.7]), r["current_ratio"], "x")
    add("Scale (Revenue)", 0.10, _band(p.get("revenue"), [50e9, 10e9, 2e9, 500e6, 100e6]), p.get("revenue"), "$")
    growth = None
    if first.get("ebitda") and ebitda is not None and first["ebitda"] > 0 and len(spread["periods"]) > 1:
        growth = (ebitda / first["ebitda"]) ** (1 / (len(spread["periods"]) - 1)) - 1 if ebitda > 0 else -1
    add("Trend (EBITDA CAGR)", 0.05, _band(growth, [0.10, 0.05, 0.0, -0.05, -0.10]), growth, "%")

    scored = [f for f in factors if f["score"] is not None]
    total_w = sum(f["weight"] for f in scored)
    weighted = sum(f["weight"] * f["score"] for f in scored) / total_w if total_w else 0
    # Negative equity is an automatic one-notch penalty (common bank policy overlay)
    overlay = []
    if r["negative_equity"]:
        overlay.append("Negative shareholders' equity: 1-notch downgrade overlay")
    if ebitda is not None and ebitda <= 0:
        overlay.append("Negative EBITDA: rating floored at Special Mention")

    rating = next(x for x in RATINGS if weighted >= x[0])
    grade = rating[1] + (1 if r["negative_equity"] else 0)
    if ebitda is not None and ebitda <= 0:
        grade = max(grade, 7)
    grade = min(grade, 8)
    final = next(x for x in RATINGS if x[1] == grade)
    return {
        "factors": factors,
        "weighted_score": round(weighted, 2),
        "overlays": overlay,
        "risk_rating": grade,
        "risk_label": final[2],
        "implied_equivalent": final[3],
    }


# ---------- Stress test ----------

SCENARIOS = [
    ("Base case", 0.0, 0.0),
    ("Downside", -0.20, 0.02),
    ("Severe downside", -0.35, 0.03),
]


def implied_rate(p: dict) -> float:
    rate = _div(p.get("interest_expense"), p["total_debt"]) if p["total_debt"] else None
    if rate is None or not 0.005 < rate < 0.20:
        rate = 0.055
    return rate


def stress_test(spread: dict, extra_debt: float = 0.0) -> list:
    p = spread["periods"][-1]
    debt = p["total_debt"] + extra_debt
    base_rate = implied_rate(p)
    rows = []
    for name, ebitda_shock, rate_shock in SCENARIOS:
        ebitda = (p.get("ebitda") or 0) * (1 + ebitda_shock)
        interest = debt * (base_rate + rate_shock)
        rows.append({
            "scenario": name,
            "ebitda_change": ebitda_shock,
            "rate_change": rate_shock,
            "ebitda": ebitda,
            "interest": interest,
            "leverage": _div(debt, ebitda) if ebitda > 0 else None,
            "coverage": _div(ebitda, interest) if interest else None,
        })
    return rows


# ---------- Illustrative facility + recommendation ----------

def _nice(x):
    if x <= 0:
        return 0
    mag = 10 ** math.floor(math.log10(x))
    return round(x / mag * 2) / 2 * mag


def propose_facility(spread: dict, score: dict) -> dict:
    p = spread["periods"][-1]
    ebitda = p.get("ebitda") or 0
    size = _nice(0.25 * ebitda) if ebitda > 0 else _nice(0.03 * (p.get("revenue") or 0))
    pf = stress_test(spread, extra_debt=size)
    base = pf[0]
    grade = score["risk_rating"]
    lev = base["leverage"]
    cov = base["coverage"]

    covenants = []
    if lev is not None:
        covenants.append({"name": "Maximum Total Leverage (Debt / EBITDA)",
                          "level": math.ceil(max(lev * 1.30, lev + 0.5) * 4) / 4, "unit": "x"})
    if cov is not None:
        # Market-style minimum coverage: ~50% cushion to base case, capped at 3.0x, floored at 1.25x
        covenants.append({"name": "Minimum Interest Coverage (EBITDA / Interest)",
                          "level": max(1.25, min(3.0, math.floor(cov * 0.50 * 4) / 4)), "unit": "x"})

    if grade <= 4 and (lev is None or lev < 3.5):
        decision = "Approve"
        rationale = "Pro forma leverage and coverage remain comfortably within policy, and repayment capacity holds under the downside case."
    elif grade <= 6:
        decision = "Approve with conditions"
        rationale = "Credit profile is acceptable but leaves less cushion; approval conditioned on financial covenants with ~30% headroom, quarterly compliance reporting and annual review."
    else:
        decision = "Decline / refer to Special Assets"
        rationale = "Leverage, coverage or earnings stability fall outside policy; incremental exposure is not supported without additional collateral or sponsor support."
    return {
        "type": "Senior unsecured term loan",
        "amount": size,
        "tenor_years": 5,
        "pro_forma": pf,
        "covenants": covenants,
        "decision": decision,
        "rationale": rationale,
    }


def analyze(spread: dict) -> dict:
    ratios = compute_ratios(spread)
    score = scorecard(spread, ratios)
    return {
        "ratios": ratios,
        "scorecard": score,
        "stress": stress_test(spread),
        "facility": propose_facility(spread, score),
    }
