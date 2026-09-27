from .analysis import analyze
from .memo import draft_memo, refine_with_claude, write_docx
from .spread import build_spread

__all__ = ["build_spread", "analyze", "draft_memo", "refine_with_claude", "write_docx", "run"]


def run(company: dict, years: int = 4, use_ai: bool = False) -> dict:
    spread = build_spread(company, years=years)
    analysis = analyze(spread)
    memo = draft_memo(spread, analysis)
    if use_ai:
        memo = refine_with_claude(memo)
    return {"spread": spread, "analysis": analysis, "memo": memo}
