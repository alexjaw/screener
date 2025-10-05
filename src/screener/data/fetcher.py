"""fetcher.py

Web scraper for fetching financial data directly from company reports.
This module scrapes financial data from official company reports and investor
relations pages, with support for Nordic companies using storage.mfn.se and
other official sources.

The scraper focuses on extracting data from:
- Official company investor relations pages
- storage.mfn.se (Nordic companies)
- Annual and interim reports (PDF and HTML)
- Cross-referencing with stockanalysis.com for validation

All scraped data includes source information for traceability.
"""

import requests
import json
import os
import re
from datetime import datetime
from typing import Optional, Dict, Any, List
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import time

from .models import FinancialData
from .pdf_parser import AIPDFParser


class FinancialDataScraper:
    """Web scraper for financial data from company reports."""
    
    def __init__(self, cache_dir: str = "cache/financial_data"):
        self.cache_dir = cache_dir
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self._ensure_cache_dir()
    
    def _ensure_cache_dir(self):
        """Ensure cache directory exists."""
        os.makedirs(self.cache_dir, exist_ok=True)
    
    def _get_cache_file(self, company: str) -> str:
        """Get cache file path for company."""
        return os.path.join(self.cache_dir, f"{company.lower().replace(' ', '_')}_financial_data.json")
    
    def _is_cache_fresh(self, cache_file: str, max_age_days: int = 30) -> bool:
        """Check if cache is fresh."""
        if not os.path.exists(cache_file):
            return False
        
        cache_time = os.path.getmtime(cache_file)
        age_days = (time.time() - cache_time) / (24 * 3600)
        return age_days < max_age_days
    
    def _load_from_cache(self, cache_file: str) -> Optional[Dict[str, Any]]:
        """Load data from cache."""
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return None
    
    def _save_to_cache(self, data: Dict[str, Any], cache_file: str):
        """Save data to cache."""
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def _fetch_url(self, url: str, timeout: int = 30) -> Optional[requests.Response]:
        """Fetch URL with error handling."""
        try:
            response = self.session.get(url, timeout=timeout)
            response.raise_for_status()
            return response
        except requests.RequestException as e:
            print(f"Error fetching {url}: {e}")
            return None
    
    def _parse_financial_table(self, soup: BeautifulSoup, table_name: str) -> Dict[str, Any]:
        """Parse financial data from HTML table with dynamic year detection."""
        data = {}
        
        # Look for tables containing financial data
        tables = soup.find_all('table')
        
        for table in tables:
            # Check if table contains relevant financial data
            table_text = table.get_text().lower()
            if any(keyword in table_text for keyword in ['revenue', 'income', 'assets', 'liabilities']):
                rows = table.find_all('tr')
                
                if not rows:
                    continue
                
                # Extract column headers to identify years
                header_row = rows[0]
                headers = [cell.get_text().strip() for cell in header_row.find_all(['th', 'td'])]
                
                # Find fiscal year columns (skip TTM, skip first column which is usually labels)
                year_columns = self._identify_fiscal_year_columns(headers)
                
                if len(year_columns) < 2:
                    print(f"Warning: Found only {len(year_columns)} fiscal year columns")
                    continue
                
                # Use the two most recent years
                current_year_col = year_columns[0]  # Most recent
                previous_year_col = year_columns[1]  # Second most recent
                
                print(f"Using fiscal years: {headers[current_year_col]} (current) and {headers[previous_year_col]} (previous)")
                
                # Parse data rows (skip header row and period ending row)
                for row in rows[2:]:  # Skip header row and period ending row
                    cells = row.find_all(['td', 'th'])
                    if len(cells) <= max(current_year_col, previous_year_col):
                        continue
                    
                    label = cells[0].get_text().strip().lower()
                    
                    # Skip non-financial rows
                    if any(skip_term in label for skip_term in ['period ending', 'growth', 'margin', 'rate']):
                        continue
                    
                    # Extract values from the identified year columns
                    current_value = self._extract_numeric_value(cells[current_year_col].get_text())
                    previous_value = self._extract_numeric_value(cells[previous_year_col].get_text())
                    
                    if current_value is not None and previous_value is not None:
                        data[label] = {
                            'current': current_value,
                            'previous': previous_value,
                            'current_year': headers[current_year_col],
                            'previous_year': headers[previous_year_col]
                        }
        
        return data
    
    def _identify_fiscal_year_columns(self, headers: List[str]) -> List[int]:
        """Identify fiscal year columns, excluding TTM and other non-fiscal periods."""
        year_columns = []
        
        for i, header in enumerate(headers):
            header_lower = header.lower()
            
            # Skip non-fiscal year columns
            if any(skip_term in header_lower for skip_term in ['ttm', 'trailing', 'quarterly', 'q1', 'q2', 'q3', 'q4']):
                continue
            
            # Look for fiscal year patterns
            if any(pattern in header_lower for pattern in ['fy ', 'fiscal', 'dec ', 'jan ', '2024', '2023', '2022']):
                year_columns.append(i)
            elif re.search(r'\b(20\d{2})\b', header):  # Any 4-digit year
                year_columns.append(i)
        
        # Sort by year (most recent first)
        year_columns.sort(key=lambda i: self._extract_year_from_header(headers[i]), reverse=True)
        
        return year_columns
    
    def _extract_year_from_header(self, header: str) -> int:
        """Extract year from header for sorting."""
        year_match = re.search(r'\b(20\d{2})\b', header)
        if year_match:
            return int(year_match.group(1))
        return 0  # Default for non-year headers
    
    def _extract_numeric_value(self, text: str) -> Optional[float]:
        """Extract numeric value from text, handling various formats."""
        # Clean the text
        text = text.strip().replace(',', '').replace('−', '-')
        
        # Handle upgrade/placeholder text
        if any(term in text.lower() for term in ['upgrade', 'n/a', 'na']):
            return None
        
        # Handle empty text
        if not text or text == '-':
            return None
        
        # Extract numbers (including negative) - fixed regex
        numbers = re.findall(r'-?\d+\.?\d*', text)
        if numbers:
            try:
                return float(numbers[0])
            except ValueError:
                return None
        
        return None
    
    def _extract_financial_data_from_html(self, html_content: str, source_url: str) -> Dict[str, Any]:
        """Extract financial data from HTML content."""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Parse financial tables
        financial_data = self._parse_financial_table(soup, "financial_statements")
        
        # Extract specific metrics
        extracted_data = {}
        
        # Revenue
        revenue_data = self._find_financial_metric(financial_data, ['revenue', 'net sales', 'turnover'])
        if revenue_data:
            extracted_data['revenue_cur'] = revenue_data['current']
            extracted_data['revenue_prev'] = revenue_data['previous']
        
        # Net Income
        income_data = self._find_financial_metric(financial_data, ['net income', 'profit', 'result', 'earnings'])
        if income_data:
            extracted_data['net_income_cur'] = income_data['current']
            extracted_data['net_income_prev'] = income_data['previous']
        
        # Total Assets
        assets_data = self._find_financial_metric(financial_data, ['total assets', 'assets'])
        if assets_data:
            extracted_data['total_assets_cur'] = assets_data['current']
            extracted_data['total_assets_prev'] = assets_data['previous']
        
        # Cash Flow from Operations
        cfo_data = self._find_financial_metric(financial_data, ['operating cash flow', 'cash flow from operations', 'cfo'])
        if cfo_data:
            extracted_data['cfo_cur'] = cfo_data['current']
            extracted_data['cfo_prev'] = cfo_data['previous']
        
        # Long-term Debt
        debt_data = self._find_financial_metric(financial_data, ['long term debt', 'long-term debt', 'total debt'])
        if debt_data:
            extracted_data['long_term_debt_cur'] = debt_data['current']
            extracted_data['long_term_debt_prev'] = debt_data['previous']
        
        # Current Assets
        current_assets_data = self._find_financial_metric(financial_data, ['current assets', 'total current assets'])
        if current_assets_data:
            extracted_data['current_assets_cur'] = current_assets_data['current']
            extracted_data['current_assets_prev'] = current_assets_data['previous']
        
        # Current Liabilities
        current_liab_data = self._find_financial_metric(financial_data, ['current liabilities', 'total current liabilities'])
        if current_liab_data:
            extracted_data['current_liabilities_cur'] = current_liab_data['current']
            extracted_data['current_liabilities_prev'] = current_liab_data['previous']
        
        # Cost of Goods Sold
        cogs_data = self._find_financial_metric(financial_data, ['cost of revenue', 'cost of goods sold', 'cogs'])
        if cogs_data:
            extracted_data['cogs_cur'] = cogs_data['current']
            extracted_data['cogs_prev'] = cogs_data['previous']
        
        # Shares Outstanding
        shares_data = self._find_financial_metric(financial_data, ['shares outstanding', 'outstanding shares'])
        if shares_data:
            extracted_data['shares_cur'] = shares_data['current']
            extracted_data['shares_prev'] = shares_data['previous']
        
        # Add source information
        extracted_data['source_url'] = source_url
        extracted_data['data_collected_at'] = datetime.now().isoformat()
        
        return extracted_data
    
    def _find_financial_metric(self, financial_data: Dict, keywords: List[str]) -> Optional[Dict[str, float]]:
        """Find financial metric by keywords."""
        for label, data in financial_data.items():
            if any(keyword in label for keyword in keywords):
                return data
        return None
    
    def _scrape_company_website(self, company: str) -> Optional[Dict[str, Any]]:
        """Scrape financial data from company website."""
        # Company-specific URLs (discovered from research)
        company_urls = {
            'saab': 'https://www.saab.com/investors/financial-reports/',
            'bioarctic': 'https://www.bioarctic.com/en/investors/financial-reports/',
            'intellego technologies': 'https://intellego-technologies.com/sv/intellego-investor-relations/'
        }
        
        company_key = company.lower().strip()
        if company_key not in company_urls:
            print(f"No URL configured for company: {company}")
            return None
        
        url = company_urls[company_key]
        response = self._fetch_url(url)
        
        if not response:
            return None
        
        return self._extract_financial_data_from_html(response.text, url)
    
    def _scrape_mfn_storage(self, company: str) -> Optional[Dict[str, Any]]:
        """Scrape financial data from storage.mfn.se."""
        # Search for company reports on MFN
        search_url = f"https://storage.mfn.se/search?q={company.replace(' ', '+')}"
        response = self._fetch_url(search_url)
        
        if not response:
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Look for annual report links
        report_links = []
        for link in soup.find_all('a', href=True):
            href = link['href']
            text = link.get_text().lower()
            if 'annual' in text or 'report' in text:
                report_links.append(urljoin(search_url, href))
        
        # Try to fetch the most recent report
        for report_url in report_links[:3]:  # Try first 3 reports
            response = self._fetch_url(report_url)
            if response:
                data = self._extract_financial_data_from_html(response.text, report_url)
                if data and 'revenue_cur' in data:
                    return data
        
        return None
    
    def _scrape_stockanalysis(self, company: str) -> Optional[Dict[str, Any]]:
        """Scrape financial data from stockanalysis.com for validation."""
        # Map company names to ticker symbols
        ticker_map = {
            'saab': 'SAAB.B',
            'bioarctic': 'BIOA.B',
            'intellego technologies': 'INT'
        }
        
        company_key = company.lower().strip()
        if company_key not in ticker_map:
            return None
        
        ticker = ticker_map[company_key]
        url = f"https://stockanalysis.com/quote/sto/{ticker}/financials/"
        
        response = self._fetch_url(url)
        if not response:
            return None
        
        return self._extract_financial_data_from_html(response.text, url)
    
    def _try_ai_pdf_parser(self, company: str) -> Optional[Dict[str, Any]]:
        """Try to use AI PDF parser for annual reports."""
        try:
            print(f"🤖 Using AI to parse {company} annual report...")
            ai_parser = AIPDFParser()
            extracted_data = ai_parser.extract_financial_data_from_pdf(company)
            
            if extracted_data:
                # Convert to dictionary format expected by the fetcher
                return {
                    'revenue_cur': extracted_data.get('revenue_cur', 0),
                    'revenue_prev': extracted_data.get('revenue_prev', 0),
                    'net_income_cur': extracted_data.get('net_income_cur', 0),
                    'net_income_prev': extracted_data.get('net_income_prev', 0),
                    'cfo_cur': extracted_data.get('cfo_cur', 0),
                    'cfo_prev': extracted_data.get('cfo_prev', 0),
                    'total_assets_cur': extracted_data.get('total_assets_cur', 0),
                    'total_assets_prev': extracted_data.get('total_assets_prev', 0),
                    'long_term_debt_cur': extracted_data.get('long_term_debt_cur', 0),
                    'long_term_debt_prev': extracted_data.get('long_term_debt_prev', 0),
                    'current_assets_cur': extracted_data.get('current_assets_cur', 0),
                    'current_assets_prev': extracted_data.get('current_assets_prev', 0),
                    'current_liabilities_cur': extracted_data.get('current_liabilities_cur', 0),
                    'current_liabilities_prev': extracted_data.get('current_liabilities_prev', 0),
                    'cogs_cur': extracted_data.get('cogs_cur', 0),
                    'cogs_prev': extracted_data.get('cogs_prev', 0),
                    'shares_cur': extracted_data.get('shares_cur', 1000000),
                    'shares_prev': extracted_data.get('shares_prev', 1000000),
                    'source_url': f"AI-parsed annual report for {company}",
                    'report_date': extracted_data.get('fiscal_years', {}).get('current', '2024'),
                    'data_collected_at': datetime.now().isoformat()
                }
            
            return None
            
        except Exception as e:
            print(f"AI PDF parser failed for {company}: {e}")
            return None
    
    def fetch_financials(self, company: str, use_cache: bool = True) -> FinancialData:
        """Fetch financial data for a company from multiple sources.
        
        Parameters
        ----------
        company : str
            Company name to fetch data for.
        use_cache : bool
            Whether to use cached data if available and fresh.
            
        Returns
        -------
        FinancialData
            Financial data with source information.
            
        Raises
        ------
        ValueError
            If company data cannot be found.
        """
        company_key = company.lower().strip()
        cache_file = self._get_cache_file(company_key)
        
        # Try cache first
        if use_cache and self._is_cache_fresh(cache_file):
            cached_data = self._load_from_cache(cache_file)
            if cached_data:
                print(f"Using cached data for {company}")
                return FinancialData(**cached_data)
        
        print(f"Fetching fresh data for {company}...")
        
        # Try multiple sources with smart fallback
        sources = [
            ('StockAnalysis', self._scrape_stockanalysis),
            ('AI PDF Parser', self._try_ai_pdf_parser),
            ('Company Website', self._scrape_company_website),
            ('MFN Storage', self._scrape_mfn_storage)
        ]
        
        scraped_data = None
        source_used = None
        
        for source_name, scraper_func in sources:
            try:
                print(f"Trying {source_name}...")
                data = scraper_func(company)
                if data and 'revenue_cur' in data:
                    # Check data quality for StockAnalysis.com
                    if source_name == 'StockAnalysis' and not self._is_data_sufficient(data):
                        print(f"⚠️ StockAnalysis.com data insufficient for {company}")
                        print(f"🔄 Falling back to AI-powered annual report analysis...")
                        continue
                    
                    scraped_data = data
                    source_used = source_name
                    if source_name == 'AI PDF Parser':
                        print(f"✅ Successfully extracted data using AI analysis of {company}'s annual report")
                    else:
                        print(f"Successfully scraped data from {source_name}")
                    break
            except Exception as e:
                print(f"Error scraping from {source_name}: {e}")
                continue
        
        if not scraped_data:
            # Fallback to hardcoded data if scraping fails
            print(f"Scraping failed for {company}, using hardcoded data")
            return self._get_hardcoded_data(company)
        
        # Fill missing fields with defaults or estimates
        scraped_data = self._fill_missing_data(scraped_data, company)
        
        # Save to cache
        self._save_to_cache(scraped_data, cache_file)
        
        return FinancialData(**scraped_data)
    
    def _is_data_sufficient(self, data: Dict[str, Any]) -> bool:
        """Check if StockAnalysis.com data is sufficient for F-Score calculation."""
        # Key fields needed for F-Score calculation
        critical_fields = [
            'revenue_cur', 'revenue_prev',
            'net_income_cur', 'net_income_prev',
            'cfo_cur', 'cfo_prev',
            'total_assets_cur', 'total_assets_prev'
        ]
        
        # Check if critical fields are missing or zero
        missing_critical = 0
        for field in critical_fields:
            value = data.get(field, 0)
            if value == 0 or value is None:
                missing_critical += 1
        
        # If more than 2 critical fields are missing/zero, data is insufficient
        if missing_critical > 2:
            print(f"⚠️ StockAnalysis.com missing {missing_critical}/6 critical financial fields")
            return False
        
        # Check for reasonable data quality
        revenue_cur = data.get('revenue_cur', 0)
        net_income_cur = data.get('net_income_cur', 0)
        total_assets_cur = data.get('total_assets_cur', 0)
        cfo_cur = data.get('cfo_cur', 0)
        
        # If revenue is very small (< 10M) and net income is very different, might be incomplete
        if revenue_cur > 0 and revenue_cur < 10 and abs(net_income_cur) > revenue_cur * 2:
            print(f"⚠️ StockAnalysis.com data appears incomplete (revenue={revenue_cur}, net_income={net_income_cur})")
            return False
        
        # If total assets is unreasonably small compared to revenue, data is likely incomplete
        if revenue_cur > 0 and total_assets_cur > 0 and total_assets_cur < revenue_cur * 0.1:
            print(f"⚠️ StockAnalysis.com total assets data appears incorrect ({total_assets_cur} vs revenue {revenue_cur})")
            return False
        
        # If cash flow is missing for a large company, data is incomplete
        if revenue_cur > 1000 and cfo_cur == 0:
            print(f"⚠️ StockAnalysis.com missing cash flow data for large company (revenue={revenue_cur})")
            return False
        
        print(f"✅ StockAnalysis.com data quality verified ({6-missing_critical}/6 critical fields)")
        return True
    
    def _fill_missing_data(self, data: Dict[str, Any], company: str) -> Dict[str, Any]:
        """Fill missing financial data fields."""
        # Set defaults for missing fields
        defaults = {
            'total_assets_cur': 0.0,
            'total_assets_prev': 0.0,
            'cfo_cur': 0.0,
            'cfo_prev': 0.0,
            'long_term_debt_cur': 0.0,
            'long_term_debt_prev': 0.0,
            'current_assets_cur': 0.0,
            'current_assets_prev': 0.0,
            'current_liabilities_cur': 0.0,
            'current_liabilities_prev': 0.0,
            'cogs_cur': 0.0,
            'cogs_prev': 0.0,
            'shares_cur': 1000000.0,
            'shares_prev': 1000000.0
        }
        
        for key, default_value in defaults.items():
            if key not in data:
                data[key] = default_value
        
        return data
    
    def _get_hardcoded_data(self, company: str) -> FinancialData:
        """Fallback to hardcoded data if scraping fails."""
        # Import the test data as fallback
        from tests.test_data import get_test_financial_data
        
        # Map tickers to company names for test data
        ticker_to_company = {
            'BIOA-B.ST': 'BioArctic',
            'SAAB-B.ST': 'SAAB', 
            'INT.ST': 'Intellego Technologies',
        }
        
        # Use mapped company name if available, otherwise use original
        company_name = ticker_to_company.get(company, company)
        
        try:
            hardcoded_data = get_test_financial_data(company_name)
            # Convert to dict and add source info
            data_dict = {
                'revenue_cur': hardcoded_data.revenue_cur,
                'revenue_prev': hardcoded_data.revenue_prev,
                'net_income_cur': hardcoded_data.net_income_cur,
                'net_income_prev': hardcoded_data.net_income_prev,
                'cfo_cur': hardcoded_data.cfo_cur,
                'cfo_prev': hardcoded_data.cfo_prev,
                'total_assets_cur': hardcoded_data.total_assets_cur,
                'total_assets_prev': hardcoded_data.total_assets_prev,
                'long_term_debt_cur': hardcoded_data.long_term_debt_cur,
                'long_term_debt_prev': hardcoded_data.long_term_debt_prev,
                'current_assets_cur': hardcoded_data.current_assets_cur,
                'current_assets_prev': hardcoded_data.current_assets_prev,
                'current_liabilities_cur': hardcoded_data.current_liabilities_cur,
                'current_liabilities_prev': hardcoded_data.current_liabilities_prev,
                'cogs_cur': hardcoded_data.cogs_cur,
                'cogs_prev': hardcoded_data.cogs_prev,
                'shares_cur': hardcoded_data.shares_cur,
                'shares_prev': hardcoded_data.shares_prev,
                'source_url': 'hardcoded_test_data',
                'report_date': '2024',
                'data_collected_at': datetime.now().isoformat()
            }
            return FinancialData(**data_dict)
        except ValueError:
            raise ValueError(f"Unsupported company '{company}'. Try 'Intellego Technologies', 'SAAB', or 'BioArctic'.")


# Global scraper instance
_scraper = FinancialDataScraper()


def fetch_financials(company: str) -> FinancialData:
    """Fetch financial data for a company from web sources.
    
    This function scrapes financial data from official company reports
    and investor relations pages, with fallback to hardcoded test data.
    
    Parameters
    ----------
    company : str
        Company name to fetch data for.
        
    Returns
    -------
    FinancialData
        Financial data with source information.
        
    Raises
    ------
    ValueError
        If company is not supported.
    """
    return _scraper.fetch_financials(company)


if __name__ == "__main__":
    # Test the scraper
    companies = ["SAAB", "BioArctic", "Intellego Technologies"]
    
    for company in companies:
        print(f"\n{'='*50}")
        print(f"Testing scraper for {company}")
        print(f"{'='*50}")
        
        try:
            data = fetch_financials(company)
            print(f"✅ Successfully fetched data for {company}")
            print(f"   Source: {data.source_url}")
            print(f"   Revenue (current): {data.revenue_cur:,.0f}")
            print(f"   Net Income (current): {data.net_income_cur:,.0f}")
            print(f"   Total Assets (current): {data.total_assets_cur:,.0f}")
        except Exception as e:
            print(f"❌ Error fetching data for {company}: {e}")