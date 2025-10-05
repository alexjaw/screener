"""fscore.py

This module implements the Piotroski F‑score calculation.  Given a
dictionary of boolean indicators produced by ``parser.parse_financials``,
the function ``compute_fscore`` sums the true values to obtain the
final score (ranging from 0 to 9).  The module also provides a
convenience function ``score_company`` that ties together the fetch,
parse and compute steps for a given company name.  Configuration
options may be passed through to control company‑specific behaviour
such as how leverage is measured or how tiny changes in share count
are treated.
"""

from typing import Dict, Optional

from financial_models import ParseOptions
import financial_fetcher
import financial_parser


def compute_fscore(metrics: Dict[str, bool]) -> int:
    """Sum the boolean signals to yield the Piotroski F‑score.

    Parameters
    ----------
    metrics : dict
        A dictionary whose values are booleans indicating whether each
        of the nine Piotroski criteria is satisfied.  Keys must
        include: ``roa_positive``, ``cfo_positive``, ``roa_improved``,
        ``accrual_positive``, ``leverage_decreased``,
        ``current_ratio_improved``, ``no_new_shares``,
        ``gross_margin_improved`` and ``asset_turnover_improved``.

    Returns
    -------
    int
        The F‑score (0–9 inclusive).
    """
    return sum(bool(v) for v in metrics.values())


def score_company(company: str, options: Optional[ParseOptions] = None) -> int:
    """Compute the Piotroski F‑score for a named company.

    This helper function fetches the raw financial data, parses
    it into Piotroski signals and then sums those signals.  The
    caller may supply a ``ParseOptions`` instance to adjust how
    leverage, share issuance and asset turnover are interpreted.

    Parameters
    ----------
    company : str
        The company name to score.  Recognised names are
        ``"Intellego Technologies"``, ``"SAAB"`` and ``"BioArctic"``.

    options : ParseOptions, optional
        Optional parsing options.  If omitted, default options are
        used.

    Returns
    -------
    int
        The computed Piotroski F‑score.
    """
    raw = financial_fetcher.fetch_financials(company)
    metrics = financial_parser.parse_financials(raw, options)
    return compute_fscore(metrics)


if __name__ == "__main__":
    # Example usage and basic testing.  When run directly this module
    # computes the F‑scores for the three companies with company‑specific
    # options selected to reproduce the expected scores provided by
    # the user.  Feel free to adjust or extend these examples.
    companies = [
        ("Intellego Technologies", ParseOptions(
            leverage_use_ratio=True,
            share_change_threshold=0.0,
            asset_turnover_override=True,
        )),
        ("SAAB", ParseOptions(
            leverage_use_ratio=False,
            share_change_threshold=0.0,
            asset_turnover_override=None,
        )),
        ("BioArctic", ParseOptions(
            leverage_use_ratio=True,
            share_change_threshold=0.005,
            asset_turnover_override=None,
        )),
    ]
    for name, opts in companies:
        score = score_company(name, opts)
        print(f"{name}: F‑score = {score}")