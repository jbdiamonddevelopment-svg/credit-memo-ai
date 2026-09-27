"""XBRL tag map: each line item lists US-GAAP tags in priority order.

Companies tag the same concept differently, so the engine tries each tag
in order and uses the first one that has annual (10-K) data for a period.
"""

# Duration items (income statement / cash flow): measured over a fiscal year.
DURATION_TAGS = {
    "revenue": [
        "Revenues",
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "RevenueFromContractWithCustomerIncludingAssessedTax",
        "SalesRevenueNet",
        "RevenuesNetOfInterestExpense",
    ],
    "cogs": [
        "CostOfRevenue",
        "CostOfGoodsAndServicesSold",
        "CostOfGoodsSold",
        "CostOfGoodsAndServiceExcludingDepreciationDepletionAndAmortization",
    ],
    "operating_income": ["OperatingIncomeLoss"],
    "depreciation_amortization": [
        "DepreciationDepletionAndAmortization",
        "DepreciationAndAmortization",
        "DepreciationAmortizationAndAccretionNet",
        "Depreciation",
    ],
    "interest_expense": [
        "InterestExpense",
        "InterestExpenseNonoperating",
        "InterestExpenseDebt",
        "InterestAndDebtExpense",
        "InterestPaidNet",
    ],
    "pretax_income": [
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments",
    ],
    "net_income": ["NetIncomeLoss", "ProfitLoss"],
    "cfo": [
        "NetCashProvidedByUsedInOperatingActivities",
        "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations",
    ],
    "capex": [
        "PaymentsToAcquirePropertyPlantAndEquipment",
        "PaymentsToAcquireProductiveAssets",
    ],
    # Non-cash impairments - added back to get Adjusted EBITDA
    "imp_goodwill_intangible": ["GoodwillAndIntangibleAssetImpairment"],
    "imp_assets": ["AssetImpairmentCharges"],
    "imp_goodwill": ["GoodwillImpairmentLoss"],
    "imp_intangible": [
        "ImpairmentOfIntangibleAssetsExcludingGoodwill",
        "ImpairmentOfIntangibleAssetsIndefinitelivedExcludingGoodwill",
    ],
    "dividends": ["PaymentsOfDividends", "PaymentsOfDividendsCommonStock"],
    "buybacks": ["PaymentsForRepurchaseOfCommonStock"],
}

# Instant items (balance sheet): measured at fiscal year end.
INSTANT_TAGS = {
    "cash": [
        "CashAndCashEquivalentsAtCarryingValue",
        "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
        "Cash",
    ],
    "current_assets": ["AssetsCurrent"],
    "current_liabilities": ["LiabilitiesCurrent"],
    "total_assets": ["Assets"],
    "total_liabilities": ["Liabilities"],
    "equity": [
        "StockholdersEquity",
        "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
    ],
    # Debt pieces - combined in spread.total_debt()
    "ltd_total": ["LongTermDebt"],
    "ltd_noncurrent": [
        "LongTermDebtNoncurrent",
        "LongTermDebtAndCapitalLeaseObligations",
        "LongTermDebtAndCapitalLeaseObligationsNoncurrent" ,
        "LongTermDebtAndFinanceLeaseObligationsNoncurrent",
    ],
    "ltd_current": [
        "LongTermDebtCurrent",
        "LongTermDebtAndCapitalLeaseObligationsCurrent",
        "DebtCurrent",
    ],
    "commercial_paper": ["CommercialPaper"],
    "short_term_borrowings": ["ShortTermBorrowings"],
}

ALL_TAGS = sorted({t for d in (DURATION_TAGS, INSTANT_TAGS) for tags in d.values() for t in tags})
