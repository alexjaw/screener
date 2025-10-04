"""models.py

Centralized data models for the F-Score calculation system.
Contains all dataclasses used across the fetcher, parser, and fscore modules.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class FinancialData:
    """Financial data for F-Score calculation with current and previous year values."""
    
    # Revenue
    revenue_cur: float
    revenue_prev: float
    
    # Net Income
    net_income_cur: float
    net_income_prev: float
    
    # Cash Flow from Operations
    cfo_cur: float
    cfo_prev: float
    
    # Balance Sheet Items
    total_assets_cur: float
    total_assets_prev: float
    long_term_debt_cur: float
    long_term_debt_prev: float
    current_assets_cur: float
    current_assets_prev: float
    current_liabilities_cur: float
    current_liabilities_prev: float
    
    # Cost of Goods Sold
    cogs_cur: float
    cogs_prev: float
    
    # Shares Outstanding
    shares_cur: float
    shares_prev: float


@dataclass
class ParseOptions:
    """Configuration flags for parsing financial data.

    Attributes
    ----------
    leverage_use_ratio : bool
        If ``True``, leverage signal 5 is based on whether the
        long‑term debt to total assets ratio has fallen.  If
        ``False``, the signal is based on whether long‑term debt in
        absolute terms has declined.

    share_change_threshold : float
        Relative threshold below which a change in shares outstanding
        is deemed insignificant.  Piotroski's original methodology
        awards a point only if there has been *no* new share issuance,
        but some analysts treat very small increases (such as those
        arising from employee options) as immaterial.  Setting this
        threshold to ``0.0`` enforces a strict comparison; higher
        values allow minor increases.  For example, a value of ``0.05``
        treats changes of up to five percent as no issuance.

    asset_turnover_override : Optional[bool]
        When supplied, overrides the computed asset turnover signal.
        Some companies in this exercise lack historical asset data,
        making it impossible to compute asset turnover accurately.
        Passing ``True`` marks the asset turnover signal as improved;
        passing ``False`` marks it as deteriorated.  If ``None``, the
        parser will compute the signal using year‑end assets.
    """

    leverage_use_ratio: bool = True
    share_change_threshold: float = 0.0
    asset_turnover_override: Optional[bool] = None
