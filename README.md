# Underwriting Desk: AI-Assisted Credit Memos from SEC Filings

A Python credit engine that turns a public company's 10-K data into what a bank credit analyst produces:
a **financial spread**, **credit ratios**, a **risk rating scorecard**, a **stress test**, **covenant levels**
and a **drafted credit memo** (Word). An optional Claude layer rewrites the memo in analyst voice without changing any numbers.

Built by Jhose Bernhardt as a portfolio project connecting retail banking experience at TD Bank with credit analysis and AI.

## What it does

| Step | Credit-desk equivalent | Module |
|---|---|---|
| Pull audited annual data from SEC EDGAR XBRL | Collecting financial statements | `credit_engine/sec.py` |
| Map inconsistent US-GAAP tags to one layout | Spreading financials | `credit_engine/spread.py`, `tags.py` |
| Adjusted EBITDA (impairment add-backs), funded debt, FCF | Normalizing earnings and debt | `spread.py` |
| Leverage, coverage, FCF/debt, liquidity, margins | Ratio analysis | `analysis.py` |
| Weighted scorecard to an 8-point risk grade with policy overlays | Risk rating | `analysis.py` |
| Base / downside / severe cases, pro forma for new debt | Stress testing | `analysis.py` |
| Max leverage and min coverage covenants with headroom | Structuring | `analysis.py` |
| Strengths, risks, mitigants, recommendation | Credit memo | `memo.py` |
| Optional rewrite in analyst voice (numbers locked) | AI assist | `memo.refine_with_claude` |

## Quick start

```bash
pip install -r requirements.txt
export SEC_USER_AGENT="Your Name your.email@example.com"   # SEC requires a contact User-Agent

python cli.py --cik 320193 --docx        # Apple -> output/AAPL.json + output/AAPL_credit_memo.docx
python cli.py --export-web --docx        # every cached company -> web/companies.json

export ANTHROPIC_API_KEY=...             # optional
python cli.py --cik 320193 --docx --ai   # memo narrative rewritten by Claude
```

Look up any company's CIK at https://www.sec.gov/edgar/searchedgar/companysearch.

## Sample results (latest fiscal year)

| Company | Grade | Debt / EBITDA | Coverage | Decision |
|---|---|---|---|---|
| Apple | 1 Exceptional | 0.7x | n/a* | Approve |
| Delta, Dollar General, Nike, Target, Home Depot | 3 Good | 1.4x–2.2x | 9.7x–18.5x | Approve |
| Kraft Heinz, Verizon | 4 Satisfactory | 3.3x–3.8x | 5.9x–7.1x | Approve with conditions |
| Carnival, Starbucks | 5 Acceptable | 3.4x–3.8x | 5.4x–8.7x | Approve with conditions |
| Boeing | 7 Special Mention | 8.6x | 2.3x | Decline |
| AMC Entertainment | 8 Substandard | 11.5x | 0.7x | Decline |

*Apple no longer reports interest expense separately; the stress test assumes a 5.5% cost of debt.

## Methodology and known limits

- **EBITDA** = operating income + D&A + non-cash goodwill/intangible impairments. No other add-backs (no stock comp, restructuring), so it's more conservative than company-reported "Adjusted EBITDA."
- **Total debt** = the larger of reported long-term debt or (noncurrent + current portions), plus commercial paper and short-term borrowings. Operating leases are excluded, which understates leverage for retailers, restaurants and airlines.
- **Interest** falls back to cash interest paid when expense isn't tagged. **FCF** is left blank when capex isn't tagged (e.g., Verizon) rather than overstated.
- **Scorecard weights**: leverage 25%, coverage 20%, FCF/debt 15%, EBITDA margin 15%, current ratio 10%, scale 10%, EBITDA trend 5%. Negative equity triggers a one-notch downgrade; negative EBITDA floors the grade at Special Mention.
- The loan request (about 0.25x EBITDA), covenants and decision are **illustrative**. This is a learning project, not investment advice, a lending decision or an agency rating.

## Roadmap

- Operating-lease-adjusted leverage (lease liabilities from the balance sheet)
- Quarterly/TTM spreads from 10-Q data
- Industry peer comparison
- Small-business mode: upload a P&L and balance sheet (tax-return style) for commercial banking deals
