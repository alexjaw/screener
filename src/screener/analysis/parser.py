"""parser.py

This module transforms raw financial statement data into the intermediate
metrics required for computing a Piotroski F‑score.  It exposes a
single function, ``parse_financials``, which accepts the raw data
returned by ``fetcher.fetch_financials`` and derives ratios and
comparative indicators.  The caller can supply optional flags to
control how certain criteria are evaluated for a given company (for
example, whether to compute the leverage signal using a ratio or
absolute change, or whether to treat small increases in share count as
insignificant).

Piotroski’s nine signals break down into three groups:

* **Profitability:**
    1. Positive return on assets (ROA).
    2. Positive cash flow from operations (CFO).
    3. Improvement in ROA relative to the previous year.
    4. Positive accruals (CFO exceeds net income).

* **Leverage, Liquidity & Funding:**
    5. Reduction in leverage (long‑term debt) relative to total assets,
       or, optionally, a decrease in the absolute level of long‑term debt.
    6. Improvement in the current ratio (current assets divided by
       current liabilities).
    7. No new shares issued.

* **Operating Efficiency:**
    8. Improvement in gross margin.
    9. Improvement in asset turnover.

The returned ``metrics`` dictionary contains boolean flags for each
criterion as well as the underlying ratios used to compute them.  The
fscore.py module will convert these booleans into the integer score.
"""

from dataclasses import dataclass
from typing import Dict, Optional

from ..data.models import FinancialData, ParseOptions


def parse_financials(raw: FinancialData, options: Optional[ParseOptions] = None) -> Dict[str, bool]:
    """Derive Piotroski F‑score metrics from raw financial data.

    Parameters
    ----------
    raw : FinancialData
        A FinancialData dataclass containing financial data as returned by
        ``fetcher.fetch_financials``.  Contains fields for current and
        previous year values: revenue, net_income, cfo, total_assets,
        long_term_debt, current_assets, current_liabilities, cogs, and shares.

    options : ParseOptions, optional
        Optional configuration controlling how certain signals are
        computed.  See ``ParseOptions`` for details.

    Returns
    -------
    Dict[str, bool]
        A mapping from the name of each F‑score signal to a boolean
        indicating whether the criterion is satisfied.  The keys are:
        ``roa_positive``, ``cfo_positive``, ``roa_improved``,
        ``accrual_positive``, ``leverage_decreased``,
        ``current_ratio_improved``, ``no_new_shares``,
        ``gross_margin_improved`` and ``asset_turnover_improved``.
    """

    if options is None:
        options = ParseOptions()

    # Helper function to avoid division by zero.
    def safe_div(numerator: float, denominator: float) -> float:
        return numerator / denominator if denominator != 0 else 0.0

    # 1. Return on assets (ROA) positivity and change
    roa_cur = safe_div(raw.net_income_cur, raw.total_assets_cur)
    roa_prev = safe_div(raw.net_income_prev, raw.total_assets_prev)
    roa_positive = roa_cur > 0
    roa_improved = roa_cur > roa_prev

    # 2. Cash flow from operations positivity and accrual quality
    cfo_positive = raw.cfo_cur > 0
    accrual_positive = raw.cfo_cur > raw.net_income_cur

    # 5. Leverage change: ratio vs absolute decline
    if options.leverage_use_ratio:
        # Compare the long‑term debt to total assets ratios
        ratio_cur = safe_div(raw.long_term_debt_cur, raw.total_assets_cur)
        ratio_prev = safe_div(raw.long_term_debt_prev, raw.total_assets_prev)
        leverage_decreased = ratio_cur < ratio_prev
    else:
        # Compare absolute long‑term debt levels
        leverage_decreased = raw.long_term_debt_cur < raw.long_term_debt_prev

    # 6. Current ratio improvement
    current_ratio_cur = safe_div(raw.current_assets_cur, raw.current_liabilities_cur)
    current_ratio_prev = safe_div(raw.current_assets_prev, raw.current_liabilities_prev)
    current_ratio_improved = current_ratio_cur > current_ratio_prev

    # 7. Shares issuance check
    share_delta = raw.shares_cur - raw.shares_prev
    # Use relative threshold to decide whether the change is material
    share_change_ratio = safe_div(abs(share_delta), raw.shares_prev)
    no_new_shares = share_delta <= 0 or share_change_ratio <= options.share_change_threshold

    # 8. Gross margin change
    gross_margin_cur = safe_div(raw.revenue_cur - raw.cogs_cur, raw.revenue_cur)
    gross_margin_prev = safe_div(raw.revenue_prev - raw.cogs_prev, raw.revenue_prev)
    gross_margin_improved = gross_margin_cur > gross_margin_prev

    # 9. Asset turnover change
    if options.asset_turnover_override is not None:
        asset_turnover_improved = bool(options.asset_turnover_override)
    else:
        asset_turnover_cur = safe_div(raw.revenue_cur, raw.total_assets_cur)
        asset_turnover_prev = safe_div(raw.revenue_prev, raw.total_assets_prev)
        asset_turnover_improved = asset_turnover_cur > asset_turnover_prev

    return {
        "roa_positive": roa_positive,
        "cfo_positive": cfo_positive,
        "roa_improved": roa_improved,
        "accrual_positive": accrual_positive,
        "leverage_decreased": leverage_decreased,
        "current_ratio_improved": current_ratio_improved,
        "no_new_shares": no_new_shares,
        "gross_margin_improved": gross_margin_improved,
        "asset_turnover_improved": asset_turnover_improved,
    }