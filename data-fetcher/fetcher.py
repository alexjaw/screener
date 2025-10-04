"""fetcher.py

This module provides a simple interface for obtaining the financial data
required to compute Piotroski F‑scores.  In a real‑world setting one
would implement network requests, web scraping or API calls inside
``fetch_financials`` to download a company's financial statements
directly from its investor relations site or from a financial data
provider.  However, the execution environment for this exercise has
no outbound internet access, so ``fetch_financials`` instead returns
hard‑coded values extracted from the companies' 2023–2024 annual
reports.  These values are expressed in either thousands (kSEK) or
millions (MSEK) depending on how the underlying documents report
figures.  Since Piotroski F‑scores rely only on relative changes and
signs, using a consistent unit within each company suffices.

The top‑level function ``fetch_financials`` accepts a company name and
returns a dictionary containing current and previous year figures for
revenue, net income, cash flow from operations (CFO), total assets,
long‑term debt, current assets, current liabilities, cost of goods
sold (used to compute gross margin), and the number of shares
outstanding.  The dictionary keys follow a consistent naming scheme:

``<metric>_cur`` – the value for the most recent fiscal year.
``<metric>_prev`` – the value for the prior fiscal year.

See parser.py and fscore.py for downstream processing.
"""

from models import FinancialData


def fetch_financials(company: str) -> FinancialData:
    """Return raw financial data for the specified company.

    Parameters
    ----------
    company : str
        The name of the company.  Valid values are
        ``"Intellego Technologies"``, ``"SAAB"``, and ``"BioArctic"``.

    Returns
    -------
    FinancialData
        A dataclass containing financial metrics for both the current and
        previous fiscal years.  Fields are suffixed with ``_cur`` or
        ``_prev`` to denote the year.

    Raises
    ------
    ValueError
        If the company name is not recognised.
    """

    company = company.lower().strip()

    if company in {"intellego", "intellego technologies", "intellego technologies ab"}:
        # Data taken from the 2024 and 2023 Intellego Technologies
        # consolidated financial statements.  All numbers are in
        # thousands of SEK (TSEK).  See the annual report for details:
        # Net revenue: 2024 265,281 TSEK; 2023 186,493 TSEK【676334621722664†L296-L303】.
        # Net income (Årets resultat): 2024 68,416 TSEK; 2023 59,604 TSEK【676334621722664†L310-L315】.
        # Cash flow from operating activities: 2024 34,529 TSEK; 2023 –19,187 TSEK【676334621722664†L430-L446】.
        # Total assets: 2024 413,606 TSEK; 2023 253,195 TSEK【676334621722664†L350-L352】.
        # Long‑term debt: 2024 56,180 TSEK; 2023 48,066 TSEK【676334621722664†L368-L374】.
        # Current assets: 2024 234,976 TSEK; 2023 131,251 TSEK【676334621722664†L344-L351】.
        # Current liabilities: 2024 61,259 TSEK; 2023 53,911 TSEK【676334621722664†L375-L382】.
        # Cost of goods sold (COGS) is approximated as the sum of
        # raw materials and consumables and the change in inventory.  For
        # 2024: 47,880 + (–5,547) = 42,333 TSEK; for 2023: 42,651 + 8,804
        # = 51,455 TSEK【676334621722664†L296-L303】.
        # Shares outstanding: 2024 ~29,317,476; 2023 ~26,352,614 (note
        # 18 of the report)【676334621722664†L350-L352】 (the exact share
        # count is not critical; only the direction of change matters).
        return FinancialData(
            revenue_cur=265_281,
            revenue_prev=186_493,
            net_income_cur=68_416,
            net_income_prev=59_604,
            cfo_cur=34_529,
            cfo_prev=-19_187,
            total_assets_cur=413_606,
            total_assets_prev=253_195,
            long_term_debt_cur=56_180,
            long_term_debt_prev=48_066,
            current_assets_cur=234_976,
            current_assets_prev=131_251,
            current_liabilities_cur=61_259,
            current_liabilities_prev=53_911,
            cogs_cur=42_333,
            cogs_prev=51_455,
            shares_cur=29_317_476,
            shares_prev=26_352_614,
        )

    if company in {"saab", "saab ab", "saab b", "saab (b stock)", "saab (b)"}:
        # Data derived from SAAB AB’s 2024 and 2023 financial statements
        # available on StockAnalysis.  Figures are in millions of SEK
        # (MSEK) for consistency.  Citation details:
        # Revenue: 2024 63,751 MSEK; 2023 51,609 MSEK【597396822729309†L117-L137】.
        # Net income: 2024 4,210 MSEK; 2023 3,443 MSEK【597396822729309†L165-L183】.
        # CFO (operational cash flow): 2024 6,732 MSEK; 2023 6,462 MSEK【904360004523542†L183-L187】.
        # Total assets: 2024 99,823 MSEK; 2023 82,759 MSEK【106043114209427†L279-L353】.
        # Long‑term debt: 2024 7,128 MSEK; 2023 6,915 MSEK【106043114209427†L279-L353】.
        # Current assets: 2024 65,402 MSEK; 2023 54,997 MSEK【106043114209427†L279-L353】.
        # Current liabilities: 2024 49,715 MSEK; 2023 35,002 MSEK【106043114209427†L279-L353】.
        # Cost of goods sold: 2024 50,088 MSEK; 2023 40,349 MSEK
        # (cost of revenue on the income statement)【597396822729309†L117-L137】.
        # Shares outstanding (basic): 2024 ~535.27 million; 2023
        # ~532.99 million【106043114209427†L279-L353】.
        return FinancialData(
            revenue_cur=63_751,
            revenue_prev=51_609,
            net_income_cur=4_210,
            net_income_prev=3_443,
            cfo_cur=6_732,
            cfo_prev=6_462,
            total_assets_cur=99_823,
            total_assets_prev=82_759,
            long_term_debt_cur=7_128,
            long_term_debt_prev=6_915,
            current_assets_cur=65_402,
            current_assets_prev=54_997,
            current_liabilities_cur=49_715,
            current_liabilities_prev=35_002,
            cogs_cur=50_088,
            cogs_prev=40_349,
            shares_cur=535.27,
            shares_prev=532.99,
        )

    if company in {"bioarctic", "bioarctic ab", "bioarctic (b stock)", "bioarctic b", "bioarctic ab class b"}:
        # Data taken from the BioArctic AB 2023 annual report (covering
        # 2023 and 2022).  Figures are in thousands of SEK (kSEK).
        # Net revenue: 2023 615,995 kSEK; 2022 228,291 kSEK【944835775721943†L4650-L4658】.
        # Net income: 2023 229,249 kSEK; 2022 –11,179 kSEK【944835775721943†L4701-L4709】.
        # CFO (cash flow from operating activities): 2023 309,694 kSEK;
        # 2022 –31,637 kSEK【944835775721943†L5008-L5024】.
        # Total assets: 2023 1,186,078 kSEK; 2022 858,307 kSEK【944835775721943†L4812-L4815】.
        # Long‑term debt (non‑current liabilities): 2023 14,537 kSEK;
        # 2022 1,182 kSEK【944835775721943†L4832-L4843】.
        # Current assets: 2023 1,152,738 kSEK; 2022 820,841 kSEK【944835775721943†L4809-L4811】.
        # Current liabilities: 2023 124,966 kSEK; 2022 70,883 kSEK【944835775721943†L4862-L4864】.
        # Cost of goods sold: approximated by total operating expenses.
        # 2023: 367,437 kSEK; 2022: 245,961 kSEK【944835775721943†L4665-L4688】.
        # Shares outstanding: share capital 2023 1,766 kSEK; 2022
        # 1,763 kSEK【944835775721943†L4816-L4831】.  The small
        # increase arises from employee stock options; Piotroski’s
        # criterion treats this as no significant issuance.
        return FinancialData(
            revenue_cur=615_995,
            revenue_prev=228_291,
            net_income_cur=229_249,
            net_income_prev=-11_179,
            cfo_cur=309_694,
            cfo_prev=-31_637,
            total_assets_cur=1_186_078,
            total_assets_prev=858_307,
            long_term_debt_cur=14_537,
            long_term_debt_prev=1_182,
            current_assets_cur=1_152_738,
            current_assets_prev=820_841,
            current_liabilities_cur=124_966,
            current_liabilities_prev=70_883,
            cogs_cur=367_437,
            cogs_prev=245_961,
            shares_cur=1_766,  # share capital as a proxy for shares outstanding
            shares_prev=1_763,
        )

    raise ValueError(
        f"Unsupported company '{company}'. Try 'Intellego Technologies', 'SAAB', or 'BioArctic'."
    )