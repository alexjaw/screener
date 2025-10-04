"""pdf_parser.py

PDF parser for extracting financial data from annual reports.
This module provides methods to extract financial statements from PDF documents
using text extraction and pattern matching.

Designed specifically for SAAB's annual report format but can be adapted
for other Nordic companies.
"""

import re
import os
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass


@dataclass
class FinancialStatement:
    """Represents a financial statement section."""
    name: str
    page_start: int
    page_end: int
    content: str


class PDFFinancialParser:
    """Parser for extracting financial data from PDF annual reports."""
    
    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.text_content = ""
        self.pages = []
        self.financial_statements = {}
    
    def extract_text_from_pdf(self) -> str:
        """Extract text from PDF using available methods."""
        # Try different PDF libraries in order of preference
        try:
            import pdfplumber
            return self._extract_with_pdfplumber()
        except ImportError:
            try:
                import PyPDF2
                return self._extract_with_pypdf2()
            except ImportError:
                try:
                    import fitz  # PyMuPDF
                    return self._extract_with_pymupdf()
                except ImportError:
                    raise ImportError("No PDF library available. Install pdfplumber, PyPDF2, or PyMuPDF")
    
    def _extract_with_pdfplumber(self) -> str:
        """Extract text using pdfplumber (best for financial documents)."""
        import pdfplumber
        
        text_content = ""
        pages = []
        
        with pdfplumber.open(self.pdf_path) as pdf:
            for i, page in enumerate(pdf.pages):
                page_text = page.extract_text()
                if page_text:
                    text_content += f"\n--- PAGE {i+1} ---\n{page_text}\n"
                    pages.append(page_text)
        
        self.pages = pages
        self.text_content = text_content
        return text_content
    
    def _extract_with_pypdf2(self) -> str:
        """Extract text using PyPDF2 (fallback)."""
        import PyPDF2
        
        text_content = ""
        pages = []
        
        with open(self.pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for i, page in enumerate(pdf_reader.pages):
                page_text = page.extract_text()
                if page_text:
                    text_content += f"\n--- PAGE {i+1} ---\n{page_text}\n"
                    pages.append(page_text)
        
        self.pages = pages
        self.text_content = text_content
        return text_content
    
    def _extract_with_pymupdf(self) -> str:
        """Extract text using PyMuPDF (fallback)."""
        import fitz
        
        text_content = ""
        pages = []
        
        doc = fitz.open(self.pdf_path)
        for i in range(len(doc)):
            page = doc.load_page(i)
            page_text = page.get_text()
            if page_text:
                text_content += f"\n--- PAGE {i+1} ---\n{page_text}\n"
                pages.append(page_text)
        
        doc.close()
        self.pages = pages
        self.text_content = text_content
        return text_content
    
    def find_financial_statements(self) -> Dict[str, FinancialStatement]:
        """Find financial statement sections in the PDF."""
        statements = {}
        
        # Common financial statement patterns
        patterns = {
            'income_statement': [
                r'income statement',
                r'statement of income',
                r'profit and loss',
                r'consolidated income statement',
                r'statement of comprehensive income'
            ],
            'balance_sheet': [
                r'balance sheet',
                r'statement of financial position',
                r'consolidated balance sheet',
                r'statement of assets and liabilities'
            ],
            'cash_flow': [
                r'cash flow statement',
                r'statement of cash flows',
                r'consolidated cash flow',
                r'cash flow from operations'
            ]
        }
        
        # Search for each statement type
        for statement_type, pattern_list in patterns.items():
            for pattern in pattern_list:
                matches = re.finditer(pattern, self.text_content, re.IGNORECASE)
                for match in matches:
                    # Extract surrounding context
                    start_pos = max(0, match.start() - 500)
                    end_pos = min(len(self.text_content), match.end() + 2000)
                    content = self.text_content[start_pos:end_pos]
                    
                    statements[statement_type] = FinancialStatement(
                        name=statement_type,
                        page_start=self._get_page_number(match.start()),
                        page_end=self._get_page_number(match.end()),
                        content=content
                    )
                    break  # Take first match for each type
                if statement_type in statements:
                    break
        
        self.financial_statements = statements
        return statements
    
    def _get_page_number(self, position: int) -> int:
        """Get page number for a text position."""
        page_markers = [m.start() for m in re.finditer(r'--- PAGE \d+ ---', self.text_content)]
        
        for i, marker in enumerate(page_markers):
            if position < marker:
                return i
        return len(page_markers)
    
    def extract_financial_data(self) -> Dict[str, Any]:
        """Extract financial data from the PDF."""
        if not self.text_content:
            self.extract_text_from_pdf()
        
        if not self.financial_statements:
            self.find_financial_statements()
        
        financial_data = {}
        
        # Extract data from each statement type
        for statement_type, statement in self.financial_statements.items():
            if statement_type == 'income_statement':
                data = self._parse_income_statement(statement.content)
                financial_data.update(data)
            elif statement_type == 'balance_sheet':
                data = self._parse_balance_sheet(statement.content)
                financial_data.update(data)
            elif statement_type == 'cash_flow':
                data = self._parse_cash_flow_statement(statement.content)
                financial_data.update(data)
        
        return financial_data
    
    def _parse_income_statement(self, content: str) -> Dict[str, Any]:
        """Parse income statement data."""
        data = {}
        
        # Look for revenue/sales
        revenue_patterns = [
            r'revenue[:\s]+([\d,]+)',
            r'net sales[:\s]+([\d,]+)',
            r'turnover[:\s]+([\d,]+)',
            r'sales[:\s]+([\d,]+)'
        ]
        
        for pattern in revenue_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                # Take the largest value (likely the total)
                revenue_values = [self._parse_number(m) for m in matches]
                if revenue_values:
                    data['revenue'] = max(revenue_values)
                    break
        
        # Look for net income/profit
        income_patterns = [
            r'net income[:\s]+([\d,]+)',
            r'net profit[:\s]+([\d,]+)',
            r'profit for the year[:\s]+([\d,]+)',
            r'result for the year[:\s]+([\d,]+)'
        ]
        
        for pattern in income_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                income_values = [self._parse_number(m) for m in matches]
                if income_values:
                    data['net_income'] = max(income_values)
                    break
        
        return data
    
    def _parse_balance_sheet(self, content: str) -> Dict[str, Any]:
        """Parse balance sheet data."""
        data = {}
        
        # Look for total assets
        assets_patterns = [
            r'total assets[:\s]+([\d,]+)',
            r'total assets[:\s]+([\d,]+)',
            r'assets[:\s]+([\d,]+)'
        ]
        
        for pattern in assets_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                asset_values = [self._parse_number(m) for m in matches]
                if asset_values:
                    data['total_assets'] = max(asset_values)
                    break
        
        # Look for long-term debt
        debt_patterns = [
            r'long.?term debt[:\s]+([\d,]+)',
            r'non.?current liabilities[:\s]+([\d,]+)',
            r'long.?term liabilities[:\s]+([\d,]+)'
        ]
        
        for pattern in debt_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                debt_values = [self._parse_number(m) for m in matches]
                if debt_values:
                    data['long_term_debt'] = max(debt_values)
                    break
        
        return data
    
    def _parse_cash_flow_statement(self, content: str) -> Dict[str, Any]:
        """Parse cash flow statement data."""
        data = {}
        
        # Look for operating cash flow
        cfo_patterns = [
            r'cash flow from operations[:\s]+([\d,]+)',
            r'operating cash flow[:\s]+([\d,]+)',
            r'cash from operating activities[:\s]+([\d,]+)'
        ]
        
        for pattern in cfo_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                cfo_values = [self._parse_number(m) for m in matches]
                if cfo_values:
                    data['operating_cash_flow'] = max(cfo_values)
                    break
        
        return data
    
    def _parse_number(self, text: str) -> Optional[float]:
        """Parse number from text, handling various formats."""
        # Clean the text
        text = text.strip().replace(',', '').replace(' ', '')
        
        # Handle negative numbers
        if text.startswith('(') and text.endswith(')'):
            text = '-' + text[1:-1]
        
        # Extract numeric value
        try:
            return float(text)
        except ValueError:
            return None
    
    def get_financial_summary(self) -> Dict[str, Any]:
        """Get a summary of extracted financial data."""
        data = self.extract_financial_data()
        
        summary = {
            'source': self.pdf_path,
            'extracted_data': data,
            'statements_found': list(self.financial_statements.keys()),
            'total_pages': len(self.pages)
        }
        
        return summary


def parse_saab_annual_report(pdf_path: str) -> Dict[str, Any]:
    """Parse SAAB's annual report and extract financial data."""
    parser = PDFFinancialParser(pdf_path)
    return parser.get_financial_summary()


if __name__ == "__main__":
    # Test with SAAB's annual report
    pdf_path = "annual-reports/20250303-saab-publishes-its-2024-annual-and-sustainability-report-en-0-4999946.pdf"
    
    if os.path.exists(pdf_path):
        print("🔍 Parsing SAAB's 2024 Annual Report...")
        summary = parse_saab_annual_report(pdf_path)
        
        print(f"📄 Total pages: {summary['total_pages']}")
        print(f"📊 Statements found: {summary['statements_found']}")
        print(f"💰 Extracted data: {summary['extracted_data']}")
    else:
        print(f"❌ PDF not found: {pdf_path}")
