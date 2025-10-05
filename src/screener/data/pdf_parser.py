"""ai_pdf_parser.py

AI-powered PDF parser for extracting financial data from annual reports.
Uses OpenAI's API to intelligently parse PDF documents and extract
structured financial data.

This approach is much more reliable than traditional text extraction
and can handle complex layouts, tables, and various document formats.
"""

import os
import json
import requests
from pathlib import Path
import base64
import tempfile
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from dotenv import load_dotenv
import openai
import fitz  # PyMuPDF

# Load environment variables
load_dotenv()


from .models import FinancialData


class AIPDFParser:
    """AI-powered PDF parser for financial documents."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the AI parser."""
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OpenAI API key not found. Set OPENAI_API_KEY environment variable.")
        
        self.client = openai.OpenAI(api_key=self.api_key)
        
        # Load annual report URLs and setup directories
        self.annual_report_urls = self._load_annual_report_urls()
        self.annual_reports_dir = Path("annual-reports")
        self.annual_reports_dir.mkdir(exist_ok=True)
    
    def _load_annual_report_urls(self) -> Dict[str, Any]:
        """Load annual report URLs from configuration file."""
        try:
            with open("annual_report_urls.json", "r") as f:
                return json.load(f)
        except FileNotFoundError:
            print("⚠️ annual_report_urls.json not found, using fallback URLs")
            return {
                "annual_report_urls": {
                    "SAAB": {
                        "annual_report_2024": {
                            "download_url": "https://www.saab.com/globalassets/corporate/investor-relations/annual-reports/2025/20250303-saab-publishes-its-2024-annual-and-sustainability-report-en-0-4999946.pdf",
                            "filename": "saab-2024-annual-report.pdf"
                        }
                    }
                }
            }
    
    def _download_annual_report(self, company: str, year: int = 2024) -> Optional[str]:
        """Download annual report for a company if not already present."""
        # Try different company name variations
        company_variations = [
            company,
            company.upper(),
            company.lower(),
            company.replace(" ", ""),
            company.replace(" ", "_"),
            company.replace(" ", "-")
        ]
        
        # Check if we have URL for this company
        report_info = None
        for variation in company_variations:
            if variation in self.annual_report_urls.get("annual_report_urls", {}):
                report_info = self.annual_report_urls["annual_report_urls"][variation].get(f"annual_report_{year}")
                if report_info:
                    break
        
        if not report_info:
            print(f"❌ No annual report URL found for {company}")
            return None
        
        filename = report_info["filename"]
        download_url = report_info["download_url"]
        file_path = self.annual_reports_dir / filename
        
        # Check if file already exists
        if file_path.exists():
            print(f"📁 Using existing annual report: {filename}")
            return str(file_path)
        
        # Download the report
        print(f"📥 Downloading annual report for {company}...")
        try:
            response = requests.get(download_url, timeout=30)
            response.raise_for_status()
            
            # Check if we got HTML instead of PDF
            content_type = response.headers.get('content-type', '').lower()
            if 'html' in content_type:
                print(f"📄 Got HTML page, searching for PDF download link...")
                # Try to find PDF download link in HTML
                pdf_url = self._extract_pdf_url_from_html(response.text, download_url)
                if pdf_url:
                    print(f"🔗 Found PDF URL: {pdf_url}")
                    # Download the actual PDF
                    pdf_response = requests.get(pdf_url, timeout=30)
                    pdf_response.raise_for_status()
                    response = pdf_response
                else:
                    print(f"❌ Could not find PDF download link in HTML")
                    return None
            
            # Check file size
            max_size = self.annual_report_urls.get("download_settings", {}).get("max_file_size_mb", 50) * 1024 * 1024
            if len(response.content) > max_size:
                print(f"❌ File too large: {len(response.content) / 1024 / 1024:.1f}MB")
                return None
            
            # Save the file
            with open(file_path, "wb") as f:
                f.write(response.content)
            
            print(f"✅ Downloaded: {filename} ({len(response.content) / 1024 / 1024:.1f}MB)")
            return str(file_path)
            
        except Exception as e:
            print(f"❌ Failed to download annual report for {company}: {e}")
            return None
    
    def _extract_pdf_url_from_html(self, html_content: str, base_url: str) -> Optional[str]:
        """Extract PDF download URL from HTML content."""
        import re
        from urllib.parse import urljoin
        
        # Look for PDF links in various patterns, prioritizing annual reports
        pdf_patterns = [
            r'href=["\']([^"\']*annual[^"\']*2024[^"\']*\.pdf[^"\']*)["\']',
            r'href=["\']([^"\']*annual[^"\']*report[^"\']*\.pdf[^"\']*)["\']',
            r'href=["\']([^"\']*2024[^"\']*annual[^"\']*\.pdf[^"\']*)["\']',
            r'href=["\']([^"\']*annual[^"\']*\.pdf[^"\']*)["\']',
            r'href=["\']([^"\']*report[^"\']*2024[^"\']*\.pdf[^"\']*)["\']',
            r'href=["\']([^"\']*\.pdf[^"\']*)["\']'
        ]
        
        for pattern in pdf_patterns:
            matches = re.findall(pattern, html_content, re.IGNORECASE)
            for match in matches:
                # Convert relative URLs to absolute
                pdf_url = urljoin(base_url, match)
                
                # Skip non-annual report PDFs
                if any(skip_word in pdf_url.lower() for skip_word in ['transparency', 'disclosure', 'interim', 'quarterly', 'q1', 'q2', 'q3', 'q4']):
                    continue
                
                # Check if it looks like an annual report
                if any(keyword in pdf_url.lower() for keyword in ['annual', 'report', '2024']):
                    return pdf_url
        
        return None
    
    def find_table_of_contents(self, pdf_path: str) -> Dict[str, int]:
        """Find Table of Contents and extract page numbers for financial sections."""
        doc = fitz.open(pdf_path)
        toc_pages = []
        
        # Look for Table of Contents in first 50 pages (some reports have TOC later)
        for page_num in range(min(50, len(doc))):
            page = doc.load_page(page_num)
            text = page.get_text().lower()
            
            if any(keyword in text for keyword in [
                'table of contents', 'contents', 'index', 'overview', 'financial statements'
            ]):
                toc_pages.append(page_num)
                print(f"📑 Found Table of Contents on page {page_num + 1}")
        
        # Also look for financial statements TOC in the middle of the document
        for page_num in range(100, min(200, len(doc))):
            page = doc.load_page(page_num)
            text = page.get_text().lower()
            
            if 'financial statements' in text and 'income statement' in text:
                toc_pages.append(page_num)
                print(f"📑 Found Financial Statements TOC on page {page_num + 1}")
        
        if not toc_pages:
            print("❌ No Table of Contents found")
            doc.close()
            return {}
        
        # Extract financial section page numbers from TOC
        financial_sections = {}
        
        for toc_page_num in toc_pages:
            page = doc.load_page(toc_page_num)
            text = page.get_text()
            
            # Look for financial statement sections
            financial_keywords = [
                'statement of cash flows',
                'cash flows',
                'income statement',
                'statement of financial position',
                'balance sheet',
                'statement of comprehensive income',
                'statement of changes in equity',
                'financial statements'
            ]
            
            lines = text.split('\n')
            for line in lines:
                line_lower = line.lower().strip()
                
                # Check if line contains financial keywords
                for keyword in financial_keywords:
                    if keyword in line_lower:
                        # Extract page number from the line
                        page_num = self._extract_page_number(line)
                        if page_num:
                            section_name = keyword.replace('consolidated ', '').replace('statement of ', '')
                            financial_sections[section_name] = page_num
                            print(f"📊 Found '{section_name}' on page {page_num}")
        
        doc.close()
        return financial_sections
    
    def _extract_page_number(self, line: str) -> Optional[int]:
        """Extract page number from a TOC line."""
        import re
        
        # Look for page numbers at the end of the line
        # Common patterns: "...page 123", "...123", "...p. 123"
        patterns = [
            r'page\s+(\d+)',
            r'p\.\s*(\d+)',
            r'(\d+)\s*$',  # Number at end of line
            r'\.\s*(\d+)\s*$'  # Number after dot at end
        ]
        
        for pattern in patterns:
            match = re.search(pattern, line.strip(), re.IGNORECASE)
            if match:
                try:
                    return int(match.group(1))
                except ValueError:
                    continue
        
        return None
    
    def find_financial_statement_pages(self, pdf_path: str) -> List[int]:
        """Find pages containing financial statements using AI-powered TOC analysis."""
        print("🔍 Using AI to find financial statements via Table of Contents...")
        
        # Use AI to find and parse the Table of Contents
        financial_sections = self._ai_find_financial_sections(pdf_path)
        
        if financial_sections:
            # Use AI-found sections to get specific pages
            financial_pages = []
            for section_name, page_num in financial_sections.items():
                # Include a few pages around the main section
                for offset in range(-1, 3):  # Include page before and 2 pages after
                    adjusted_page = page_num - 1 + offset  # Convert to 0-indexed
                    if 0 <= adjusted_page < len(fitz.open(pdf_path)):
                        financial_pages.append(adjusted_page)
            
            # Remove duplicates and sort
            financial_pages = sorted(list(set(financial_pages)))
            print(f"📊 Found {len(financial_pages)} pages via AI TOC analysis")
            return financial_pages
        
        # Fallback to keyword search if AI method fails
        print("🔄 AI TOC method failed, falling back to keyword search...")
        return self._find_financial_pages_by_keywords(pdf_path)
    
    def _ai_find_financial_sections(self, pdf_path: str) -> Dict[str, int]:
        """Use AI to find financial sections in the Table of Contents."""
        doc = fitz.open(pdf_path)
        
        # Extract text from first 50 pages (where TOC usually is)
        toc_text = ""
        for page_num in range(min(50, len(doc))):
            page = doc.load_page(page_num)
            toc_text += f"\n=== PAGE {page_num + 1} ===\n{page.get_text()}\n"
        
        # Also check around page 100-200 for financial statements TOC
        for page_num in range(100, min(200, len(doc))):
            page = doc.load_page(page_num)
            text = page.get_text()
            if len(text) > 100 and any(keyword in text.lower() for keyword in ['financial', 'statement', 'income', 'balance', 'cash flow']):
                toc_text += f"\n=== PAGE {page_num + 1} ===\n{text}\n"
        
        doc.close()
        
        # Use AI to analyze the TOC and find financial sections
        prompt = f"""
You are analyzing a Table of Contents from an annual report to find financial statement sections.

Below is the extracted text from the Table of Contents pages:

{toc_text[:4000]}  # Limit to avoid token limits

Please identify the page numbers for these financial statement sections:
1. Income Statement (or Profit & Loss Statement)
2. Balance Sheet (or Statement of Financial Position) 
3. Cash Flow Statement (or Statement of Cash Flows)
4. Statement of Comprehensive Income
5. Statement of Changes in Equity

Return ONLY a JSON object with this exact structure:
{{
    "income_statement": <page_number>,
    "balance_sheet": <page_number>,
    "cash_flow_statement": <page_number>,
    "comprehensive_income": <page_number>,
    "changes_in_equity": <page_number>
}}

IMPORTANT INSTRUCTIONS:
- Look for the ACTUAL page numbers where the financial statements are located, NOT the Table of Contents page
- If you see "Income Statement, Consolidated ..............................................149", the page number is 149, not the TOC page
- Look for patterns like "Statement Name ..............................................PageNumber"
- Focus on the main consolidated statements, not parent company statements
- If a section is not found, use null for that field

Return ONLY the JSON object, no additional text.
"""
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500,
                temperature=0.1
            )
            
            # Parse the AI response
            response_text = response.choices[0].message.content
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start != -1 and json_end != -1:
                json_str = response_text[json_start:json_end]
                import json
                data = json.loads(json_str)
                
                # Convert to our format
                financial_sections = {}
                if data.get('income_statement'):
                    financial_sections['income statement'] = data['income_statement']
                if data.get('balance_sheet'):
                    financial_sections['balance sheet'] = data['balance_sheet']
                if data.get('cash_flow_statement'):
                    financial_sections['cash flow statement'] = data['cash_flow_statement']
                if data.get('comprehensive_income'):
                    financial_sections['comprehensive income'] = data['comprehensive_income']
                if data.get('changes_in_equity'):
                    financial_sections['changes in equity'] = data['changes_in_equity']
                
                print(f"🤖 AI found financial sections: {financial_sections}")
                return financial_sections
            
        except Exception as e:
            print(f"❌ AI TOC analysis failed: {e}")
        
        return {}
    
    def _find_financial_pages_by_keywords(self, pdf_path: str) -> List[int]:
        """Fallback method: Find pages using keyword search."""
        doc = fitz.open(pdf_path)
        financial_pages = []
        
        # Keywords to look for in financial statements
        financial_keywords = [
            "consolidated statement of cash flows", "cash flow from operating activities",
            "income statement", "profit and loss", "consolidated income",
            "balance sheet", "statement of financial position", "consolidated balance",
            "cash flow", "statement of cash flows", "consolidated cash flow",
            "financial statements", "notes to the financial statements"
        ]
        
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            text = page.get_text().lower()
            
            # Check if page contains financial statement keywords
            if any(keyword in text for keyword in financial_keywords):
                financial_pages.append(page_num)
                print(f"📄 Found financial content on page {page_num + 1}")
        
        doc.close()
        return financial_pages
    
    def extract_pages_to_pdf(self, pdf_path: str, page_numbers: List[int]) -> str:
        """Extract specific pages to a new PDF file."""
        doc = fitz.open(pdf_path)
        new_doc = fitz.open()
        
        for page_num in page_numbers:
            new_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)
        
        # Create temporary file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
        new_doc.save(temp_file.name)
        new_doc.close()
        doc.close()
        
        return temp_file.name
    
    def extract_text_from_pages(self, pdf_path: str, page_numbers: List[int]) -> str:
        """Extract text from specific pages."""
        doc = fitz.open(pdf_path)
        text_content = []
        
        for page_num in page_numbers:
            page = doc.load_page(page_num)
            text = page.get_text()
            text_content.append(f"=== PAGE {page_num + 1} ===\n{text}\n")
        
        doc.close()
        return "\n".join(text_content)
    
    def extract_financial_data_from_pdf(self, company_name: str, year: int = 2024) -> Dict[str, Any]:
        """Extract financial data from a company's annual report PDF."""
        # First try to download the annual report
        pdf_path = self._download_annual_report(company_name, year)
        if not pdf_path:
            print(f"❌ Could not obtain annual report for {company_name}")
            return {}
        
        return self._extract_financial_data_from_pdf_file(pdf_path, company_name)
    
    def _extract_financial_data_from_pdf_file(self, pdf_path: str, company_name: str = "SAAB") -> Dict[str, Any]:
        """Extract financial data from PDF using AI text analysis."""
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        print(f"🤖 Using AI to parse {company_name} annual report...")
        
        # Find pages with financial statements
        print("🔍 Searching for financial statement pages...")
        financial_pages = self.find_financial_statement_pages(pdf_path)
        
        if not financial_pages:
            print("❌ No financial statement pages found")
            return {}
        
        print(f"📊 Found {len(financial_pages)} pages with financial content")
        
        # Extract text from financial pages
        print("📄 Extracting text from financial pages...")
        print(f"🎯 Using {len(financial_pages)} pages found via Table of Contents")
        financial_text = self.extract_text_from_pages(pdf_path, financial_pages[:15])  # Limit to 15 pages
        
        # Auto-detect report type based on filename or content
        report_type = "annual"  # Default
        if any(keyword in pdf_path.lower() for keyword in ['q1', 'q2', 'q3', 'q4', 'quarterly', 'interim']):
            report_type = "quarterly"
        
        # Create the prompt for financial data extraction
        prompt = self._create_financial_extraction_prompt(company_name, financial_text, report_type)
        
        try:
            # Call OpenAI API with the extracted text
            response = self.client.chat.completions.create(
                model="gpt-4o",  # Use GPT-4
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=2000,
                temperature=0.1  # Low temperature for consistent extraction
            )
            
            # Parse the response
            extracted_data = self._parse_ai_response(response.choices[0].message.content)
            return extracted_data
            
        except Exception as e:
            print(f"❌ Error calling OpenAI API: {e}")
            return {}
    
    def _create_financial_extraction_prompt(self, company_name: str, financial_text: str, report_type: str = "annual", current_year: int = None, previous_year: int = None) -> str:
        """Create a detailed prompt for financial data extraction."""
        
        # Auto-detect years if not provided
        if current_year is None or previous_year is None:
            # Try to extract years from the financial text
            import re
            years = re.findall(r'\b(20\d{2})\b', financial_text)
            if len(years) >= 2:
                years = sorted(set(years), reverse=True)  # Most recent first
                current_year = int(years[0])
                previous_year = int(years[1])
            else:
                # Fallback to current year
                from datetime import datetime
                current_year = datetime.now().year
                previous_year = current_year - 1
        
        if report_type == "quarterly":
            period_description = f"TWO MOST RECENT PERIODS (current period and same period previous year)"
            period_examples = f"e.g., Q2 {current_year} vs Q2 {previous_year}, or 6 months {current_year} vs 6 months {previous_year}"
        else:
            period_description = f"TWO MOST RECENT FISCAL YEARS (current year and previous year)"
            period_examples = f"e.g., {current_year} vs {previous_year}"
        
        return f"""
You are a financial analyst extracting data from {company_name}'s {report_type} report.

Below is the extracted text from the financial statements section of the {report_type} report:

{financial_text}

Please extract the following financial metrics for the {period_description} ({period_examples}):

**INCOME STATEMENT:**
- Revenue/Net Sales/Turnover (current year and previous year)
- Net Income/Profit for the year (current year and previous year)
- Cost of Goods Sold/Cost of Revenue (current year and previous year)

**BALANCE SHEET:**
- Total Assets (current year and previous year)
- Long-term Debt/Non-current liabilities (current year and previous year)
- Current Assets (current year and previous year)
- Current Liabilities (current year and previous year)

**CASH FLOW STATEMENT:**
- Cash Flow from Operating Activities (from Consolidated Statement of Cash Flows, NOT summary sections)

**OTHER:**
- Shares Outstanding (current year and previous year)

**IMPORTANT INSTRUCTIONS:**
1. Look for the most recent period data ({period_examples})
2. Extract actual numbers, not percentages or ratios
3. Note the units (millions, thousands, etc.)
4. If data is not available, use 0
5. Return ONLY a JSON object with this exact structure:

{{
    "revenue_cur": <number>,
    "revenue_prev": <number>,
    "net_income_cur": <number>,
    "net_income_prev": <number>,
    "cfo_cur": <number>,
    "cfo_prev": <number>,
    "total_assets_cur": <number>,
    "total_assets_prev": <number>,
    "long_term_debt_cur": <number>,
    "long_term_debt_prev": <number>,
    "current_assets_cur": <number>,
    "current_assets_prev": <number>,
    "current_liabilities_cur": <number>,
    "current_liabilities_prev": <number>,
    "cogs_cur": <number>,
    "cogs_prev": <number>,
    "shares_cur": <number>,
    "shares_prev": <number>,
    "units": "<millions/thousands/actual>",
    "fiscal_years": {{
        "current": "{current_year}",
        "previous": "{previous_year}"
    }},
    "confidence": "<high/medium/low>",
    "notes": "<any important observations>"
}}

6. If you cannot find specific data, explain what you found instead
7. Focus on consolidated financial statements, not individual segments
8. Look for audited financial statements, not preliminary or interim reports
9. For cash flow, use "Cash flow from operating activities" from Consolidated Statement of Cash Flows
10. AVOID summary sections or executive summaries - use the actual financial statements
11. For quarterly reports, look for interim financial statements or quarterly results
12. If this is a quarterly report, compare current quarter with same quarter previous year

Return ONLY the JSON object, no additional text.
"""
    
    def _parse_ai_response(self, response_text: str) -> Dict[str, Any]:
        """Parse the AI response and extract JSON data."""
        try:
            # Try to find JSON in the response
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start != -1 and json_end != -1:
                json_str = response_text[json_start:json_end]
                data = json.loads(json_str)
                
                # Add metadata
                data['source'] = 'ai_pdf_parser'
                data['extraction_method'] = 'openai_gpt4_vision'
                
                return data
            else:
                print("❌ No JSON found in AI response")
                print(f"Response: {response_text[:500]}...")
                return {}
                
        except json.JSONDecodeError as e:
            print(f"❌ Error parsing JSON: {e}")
            print(f"Response: {response_text[:500]}...")
            return {}
        except Exception as e:
            print(f"❌ Error parsing response: {e}")
            return {}
    
    def convert_to_financial_data(self, extracted_data: Dict[str, Any], pdf_path: str) -> FinancialData:
        """Convert extracted data to FinancialData dataclass."""
        from datetime import datetime
        
        # Handle missing values
        defaults = {
            'revenue_cur': 0.0,
            'revenue_prev': 0.0,
            'net_income_cur': 0.0,
            'net_income_prev': 0.0,
            'cfo_cur': 0.0,
            'cfo_prev': 0.0,
            'total_assets_cur': 0.0,
            'total_assets_prev': 0.0,
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
        
        # Fill in extracted data
        for key, default_value in defaults.items():
            if key not in extracted_data:
                extracted_data[key] = default_value
        
        # Add source information
        extracted_data['source_url'] = pdf_path
        extracted_data['report_date'] = extracted_data.get('fiscal_years', {}).get('current', '2024')
        extracted_data['data_collected_at'] = datetime.now().isoformat()
        
        # Remove extra fields that aren't part of FinancialData
        financial_data_fields = {
            'revenue_cur', 'revenue_prev', 'net_income_cur', 'net_income_prev',
            'cfo_cur', 'cfo_prev', 'total_assets_cur', 'total_assets_prev',
            'long_term_debt_cur', 'long_term_debt_prev', 'current_assets_cur',
            'current_assets_prev', 'current_liabilities_cur', 'current_liabilities_prev',
            'cogs_cur', 'cogs_prev', 'shares_cur', 'shares_prev',
            'source_url', 'report_date', 'data_collected_at'
        }
        
        # Filter to only include FinancialData fields
        filtered_data = {k: v for k, v in extracted_data.items() if k in financial_data_fields}
        
        return FinancialData(**filtered_data)


def parse_saab_annual_report_ai(pdf_path: str) -> FinancialData:
    """Parse SAAB's annual report using AI."""
    parser = AIPDFParser()
    
    # Extract data using AI
    extracted_data = parser.extract_financial_data_from_pdf(pdf_path, "SAAB")
    
    if not extracted_data:
        raise ValueError("Failed to extract financial data from PDF")
    
    # Convert to FinancialData object
    return parser.convert_to_financial_data(extracted_data, pdf_path)


if __name__ == "__main__":
    # Test with SAAB's annual report
    pdf_path = "annual-reports/20250303-saab-publishes-its-2024-annual-and-sustainability-report-en-0-4999946.pdf"
    
    if os.path.exists(pdf_path):
        print("🤖 Testing AI PDF Parser with SAAB's 2024 Annual Report...")
        
        try:
            financial_data = parse_saab_annual_report_ai(pdf_path)
            
            print("\n✅ Successfully extracted financial data:")
            print(f"📊 Revenue (current): {financial_data.revenue_cur:,.0f}")
            print(f"📊 Revenue (previous): {financial_data.revenue_prev:,.0f}")
            print(f"💰 Net Income (current): {financial_data.net_income_cur:,.0f}")
            print(f"💰 Net Income (previous): {financial_data.net_income_prev:,.0f}")
            print(f"🏦 Total Assets (current): {financial_data.total_assets_cur:,.0f}")
            print(f"🏦 Total Assets (previous): {financial_data.total_assets_prev:,.0f}")
            print(f"💸 Operating Cash Flow (current): {financial_data.cfo_cur:,.0f}")
            print(f"💸 Operating Cash Flow (previous): {financial_data.cfo_prev:,.0f}")
            print(f"📅 Report Date: {financial_data.report_date}")
            print(f"🔗 Source: {financial_data.source_url}")
            
        except Exception as e:
            print(f"❌ Error: {e}")
    else:
        print(f"❌ PDF not found: {pdf_path}")
        print("Make sure to set your OpenAI API key in a .env file:")
        print("OPENAI_API_KEY=your_api_key_here")
