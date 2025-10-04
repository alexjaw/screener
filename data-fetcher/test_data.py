"""test_data.py

Test data module containing hardcoded financial data for validation testing.
This module captures the current test implementation data so we can use it
to validate any future real data fetcher implementation.

The data is extracted from actual annual reports and represents ground truth
for F-Score calculations on these specific companies.
"""

from models import FinancialData


# Test company identifiers
TEST_COMPANIES = [
    "Intellego Technologies",
    "SAAB", 
    "BioArctic"
]

# Alternative company name mappings for flexible testing
COMPANY_NAME_MAPPINGS = {
    "intellego": "Intellego Technologies",
    "intellego technologies": "Intellego Technologies", 
    "intellego technologies ab": "Intellego Technologies",
    "saab": "SAAB",
    "saab ab": "SAAB",
    "saab b": "SAAB",
    "saab (b stock)": "SAAB",
    "saab (b)": "SAAB",
    "bioarctic": "BioArctic",
    "bioarctic ab": "BioArctic",
    "bioarctic (b stock)": "BioArctic",
    "bioarctic b": "BioArctic",
    "bioarctic ab class b": "BioArctic"
}


def get_test_financial_data(company: str) -> FinancialData:
    """Return hardcoded financial data for test companies.
    
    This function contains the exact same data as the current fetcher.py
    implementation, extracted from actual annual reports. Use this for
    regression testing when implementing real data fetchers.
    
    Parameters
    ----------
    company : str
        Company name (case-insensitive). Supports various name formats.
        
    Returns
    -------
    FinancialData
        Hardcoded financial data for the specified company.
        
    Raises
    ------
    ValueError
        If company name is not recognized.
    """
    company = company.lower().strip()
    
    if company in {"intellego", "intellego technologies", "intellego technologies ab"}:
        # Data taken from the 2024 and 2023 Intellego Technologies
        # consolidated financial statements. All numbers are in
        # thousands of SEK (TSEK). See the annual report for details:
        # Net revenue: 2024 265,281 TSEK; 2023 186,493 TSEK
        # Net income (Årets resultat): 2024 68,416 TSEK; 2023 59,604 TSEK
        # Cash flow from operating activities: 2024 34,529 TSEK; 2023 –19,187 TSEK
        # Total assets: 2024 413,606 TSEK; 2023 253,195 TSEK
        # Long‑term debt: 2024 56,180 TSEK; 2023 48,066 TSEK
        # Current assets: 2024 234,976 TSEK; 2023 131,251 TSEK
        # Current liabilities: 2024 61,259 TSEK; 2023 53,911 TSEK
        # Cost of goods sold (COGS) is approximated as the sum of
        # raw materials and consumables and the change in inventory. For
        # 2024: 47,880 + (–5,547) = 42,333 TSEK; for 2023: 42,651 + 8,804
        # = 51,455 TSEK
        # Shares outstanding: 2024 ~29,317,476; 2023 ~26,352,614
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
        # Data derived from SAAB AB's 2024 and 2023 financial statements
        # available on StockAnalysis. Figures are in millions of SEK
        # (MSEK) for consistency.
        # Revenue: 2024 63,751 MSEK; 2023 51,609 MSEK
        # Net income: 2024 4,210 MSEK; 2023 3,443 MSEK
        # CFO (operational cash flow): 2024 6,732 MSEK; 2023 6,462 MSEK
        # Total assets: 2024 99,823 MSEK; 2023 82,759 MSEK
        # Long‑term debt: 2024 7,128 MSEK; 2023 6,915 MSEK
        # Current assets: 2024 65,402 MSEK; 2023 54,997 MSEK
        # Current liabilities: 2024 49,715 MSEK; 2023 35,002 MSEK
        # Cost of goods sold: 2024 50,088 MSEK; 2023 40,349 MSEK
        # Shares outstanding (basic): 2024 ~535.27 million; 2023
        # ~532.99 million
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
        # 2023 and 2022). Figures are in thousands of SEK (kSEK).
        # Net revenue: 2023 615,995 kSEK; 2022 228,291 kSEK
        # Net income: 2023 229,249 kSEK; 2022 –11,179 kSEK
        # CFO (cash flow from operating activities): 2023 309,694 kSEK;
        # 2022 –31,637 kSEK
        # Total assets: 2023 1,186,078 kSEK; 2022 858,307 kSEK
        # Long‑term debt (non‑current liabilities): 2023 14,537 kSEK;
        # 2022 1,182 kSEK
        # Current assets: 2023 1,152,738 kSEK; 2022 820,841 kSEK
        # Current liabilities: 2023 124,966 kSEK; 2022 70,883 kSEK
        # Cost of goods sold: approximated by total operating expenses.
        # 2023: 367,437 kSEK; 2022: 245,961 kSEK
        # Shares outstanding: share capital 2023 1,766 kSEK; 2022
        # 1,763 kSEK. The small increase arises from employee stock options;
        # Piotroski's criterion treats this as no significant issuance.
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


def get_expected_f_scores() -> dict:
    """Return expected F-Score results for test companies.
    
    These are the ground truth F-Scores calculated from the hardcoded data
    using DEFAULT parse options. Note that fscore.py main execution uses
    company-specific custom options to achieve different scores.
    
    Returns
    -------
    dict
        Mapping from company name to expected F-Score with default options.
    """
    return {
        "Intellego Technologies": 5,  # Default options
        "SAAB": 6,  # Default options  
        "BioArctic": 6  # Default options
    }


def get_expected_f_scores_custom() -> dict:
    """Return expected F-Score results with company-specific custom options.
    
    These match the scores shown when running fscore.py directly, which uses
    custom ParseOptions for each company.
    
    Returns
    -------
    dict
        Mapping from company name to expected F-Score with custom options.
    """
    return {
        "Intellego Technologies": 6,  # Custom: asset_turnover_override=True
        "SAAB": 5,  # Custom: leverage_use_ratio=False
        "BioArctic": 7  # Custom: share_change_threshold=0.005
    }


def get_test_companies() -> list:
    """Return list of test company names.
    
    Returns
    -------
    list
        List of supported test company names.
    """
    return TEST_COMPANIES.copy()


def normalize_company_name(company: str) -> str:
    """Normalize company name to standard format.
    
    Parameters
    ----------
    company : str
        Company name in any supported format.
        
    Returns
    -------
    str
        Standardized company name.
        
    Raises
    ------
    ValueError
        If company name is not recognized.
    """
    normalized = company.lower().strip()
    if normalized in COMPANY_NAME_MAPPINGS:
        return COMPANY_NAME_MAPPINGS[normalized]
    raise ValueError(f"Unsupported company '{company}'")


if __name__ == "__main__":
    # Test the test data module
    print("🧪 Testing test_data module...")
    
    for company in TEST_COMPANIES:
        try:
            data = get_test_financial_data(company)
            print(f"✅ {company}: revenue_cur={data.revenue_cur:,}, net_income_cur={data.net_income_cur:,}")
        except Exception as e:
            print(f"❌ {company}: {e}")
    
    expected_scores = get_expected_f_scores()
    print(f"\n📊 Expected F-Scores: {expected_scores}")
    
    print("🎉 Test data module working correctly!")
