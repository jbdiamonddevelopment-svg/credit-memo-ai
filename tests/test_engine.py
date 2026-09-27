"""Sanity checks against figures reported in Apple's FY2025 10-K."""
import json
from pathlib import Path

from credit_engine import run

APPLE = json.loads((Path(__file__).parent.parent / "data/raw/CIK0000320193.json").read_text())


def test_apple_spread_matches_10k():
    p = run(APPLE)["spread"]["periods"][-1]
    assert p["fiscal_year"] == 2025
    assert p["revenue"] == 416_161_000_000
    assert p["ebitda"] == 133_050_000_000 + 11_698_000_000
    assert p["total_debt"] == 90_678_000_000 + 7_979_000_000  # term debt + commercial paper


def test_apple_is_top_grade():
    sc = run(APPLE)["analysis"]["scorecard"]
    assert sc["risk_rating"] == 1


def test_memo_has_all_sections():
    memo = run(APPLE)["memo"]["sections"]
    for key in ["request", "financial_performance", "risks", "recommendation", "covenants"]:
        assert memo[key]
