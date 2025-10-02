#!/usr/bin/env python3
"""
Piotroski F-Score Calculator

Calculates Piotroski F-Score (0-9) for financial strength assessment.
Can be run standalone or imported for use with momentum screener.

Standalone usage:
    python fscore.py tickers.csv --output scores.csv
    
Integrated usage:
    from fscore import calculate_f_score
    f_score = calculate_f_score("VOLV-B.ST")
"""

from __future__ import annotations
import pandas as pd
import numpy as np
import yfinance as yf
from typing import Optional, Dict, Any
import argparse
import sys
from dataclasses import dataclass
import os
import json
import time as time_module

@dataclass
class FScoreData:
    """Financial data required for F-Score calculation"""
    net_income: float
    operating_cash_flow: float
    roa: float
    gross_margin: float
    asset_turnover: float
    debt_to_equity: float
    current_ratio: float
    shares_outstanding: float
    leverage_ratio: float

# Cache configuration
FSCORE_CACHE_DIR = "cache"
FSCORE_CACHE_DAYS = 7  # Refresh cache if data is older than 7 days

def ensure_fscore_cache_dir():
    """Create F-Score cache directory if it doesn't exist."""
    if not os.path.exists(FSCORE_CACHE_DIR):
        os.makedirs(FSCORE_CACHE_DIR)

def get_fscore_cache_file(ticker: str) -> str:
    """Get the cache file path for a ticker's F-Score data."""
    ensure_fscore_cache_dir()
    return os.path.join(FSCORE_CACHE_DIR, f"fscore_{ticker.replace('.', '_').replace('-', '_')}.json")

def is_fscore_cache_fresh(cache_file: str) -> bool:
    """Check if F-Score cache file is fresh enough."""
    if not os.path.exists(cache_file):
        return False
    
    # Check if file is less than FSCORE_CACHE_DAYS old
    file_age = time_module.time() - os.path.getmtime(cache_file)
    return file_age < (FSCORE_CACHE_DAYS * 24 * 3600)

def save_fscore_to_cache(ticker: str, data: Optional[FScoreData], prev_data: Optional[FScoreData], f_score_result: Dict[str, Any]):
    """Save F-Score calculation results to cache."""
    cache_file = get_fscore_cache_file(ticker)
    
    cache_data = {
        'ticker': ticker,
        'calculated_at': time_module.time(),
        'data': data.__dict__ if data else None,
        'prev_data': prev_data.__dict__ if prev_data else None,
        'f_score_result': f_score_result
    }
    
    try:
        with open(cache_file, 'w') as f:
            json.dump(cache_data, f, indent=2)
    except Exception as e:
        print(f"Warning: Could not save F-Score cache for {ticker}: {e}")

def load_fscore_from_cache(ticker: str) -> Optional[Dict[str, Any]]:
    """Load F-Score calculation results from cache."""
    cache_file = get_fscore_cache_file(ticker)
    
    if not is_fscore_cache_fresh(cache_file):
        return None
    
    try:
        with open(cache_file, 'r') as f:
            cache_data = json.load(f)
        return cache_data
    except Exception as e:
        print(f"Warning: Could not load F-Score cache for {ticker}: {e}")
        return None

def fetch_financial_data(ticker: str, use_cache: bool = True) -> Optional[FScoreData]:
    """
    Fetch financial data required for F-Score calculation using yfinance.
    
    Args:
        ticker: Stock symbol (e.g., "VOLV-B.ST")
        
    Returns:
        FScoreData object or None if insufficient data
    """
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        # Extract financial metrics
        annual_reports = stock.financials
        balance_sheet = stock.balance_sheet
        cash_flow = stock.cashflow
        
        # Get latest annual data (most recent year)
        if annual_reports.empty or balance_sheet.empty or cash_flow.empty:
            print(f"Warning: Insufficient financial data for {ticker}")
            return None
            
        # Get most recent year's data
        latest_year = annual_reports.columns[0]
        
        try:
            # Extract key metrics (try multiple field names)
            net_income = (
                annual_reports.loc['Net Earnings', latest_year] if 'Net Earnings' in annual_reports.index else (
                    annual_reports.loc['Net Income', latest_year] if 'Net Income' in annual_reports.index else 0
                )
            )
            total_revenue = (
                annual_reports.loc['Total Revenue', latest_year] if 'Total Revenue' in annual_reports.index else (
                    annual_reports.loc['Revenue', latest_year] if 'Revenue' in annual_reports.index else 1
                )
            )
            cost_of_revenue = (
                annual_reports.loc['Cost Of Goods Sold', latest_year] if 'Cost Of Goods Sold' in annual_reports.index else (
                    annual_reports.loc['Cost of Revenue', latest_year] if 'Cost of Revenue' in annual_reports.index else (
                        annual_reports.loc['Total Cost Of Revenue', latest_year] if 'Total Cost Of Revenue' in annual_reports.index else 0
                    )
                )
            )
            
            # Balance sheet items (try multiple field names)
            total_assets = (
                balance_sheet.loc['Total Assets', latest_year] if 'Total Assets' in balance_sheet.index else 1
            )
            long_term_debt = (
                balance_sheet.loc['Long Term Debt', latest_year] if 'Long Term Debt' in balance_sheet.index else 0
            )
            current_debt = (
                balance_sheet.loc['Current Debt', latest_year] if 'Current Debt' in balance_sheet.index else 0
            )
            current_assets = (
                balance_sheet.loc['Current Assets', latest_year] if 'Current Assets' in balance_sheet.index else 0
            )
            current_liabilities = (
                balance_sheet.loc['Current Liabilities', latest_year] if 'Current Liabilities' in balance_sheet.index else 1
            )
            stockholders_equity = (
                balance_sheet.loc['Stockholders Equity', latest_year] if 'Stockholders Equity' in balance_sheet.index else (
                    balance_sheet.loc['Total Stockholder Equity', latest_year] if 'Total Stockholder Equity' in balance_sheet.index else 1
                )
            )
            
            # Cash flow (try multiple field names)
            operating_cash_flow = (
                cash_flow.loc['Total Cash From Operating Activities', latest_year] if 'Total Cash From Operating Activities' in cash_flow.index else (
                    cash_flow.loc['Operating Cash Flow', latest_year] if 'Operating Cash Flow' in cash_flow.index else (
                        cash_flow.loc['Net Cash Flow', latest_year] if 'Net Cash Flow' in cash_flow.index else (
                            cash_flow.loc['Cash From Operating Activities', latest_year] if 'Cash From Operating Activities' in cash_flow.index else 0
                        )
                    )
                )
            )
            
            # Shares outstanding
            shares_outstanding = info.get('sharesOutstanding', 1)
            
            # Calculate ratios
            roa = net_income / total_assets if total_assets != 0 else 0
            gross_margin = (total_revenue - cost_of_revenue) / total_revenue if total_revenue != 0 else 0
            asset_turnover = total_revenue / total_assets if total_assets != 0 else 0
            debt_to_equity = (long_term_debt + current_debt) / stockholders_equity if stockholders_equity != 0 else 0
            current_ratio = current_assets / current_liabilities if current_liabilities != 0 else 0
            leverage_ratio = long_term_debt / stockholders_equity if stockholders_equity != 0 else 0
            
            return FScoreData(
                net_income=net_income,
                operating_cash_flow=operating_cash_flow,
                roa=roa,
                gross_margin=gross_margin,
                asset_turnover=asset_turnover,
                debt_to_equity=debt_to_equity,
                current_ratio=current_ratio,
                shares_outstanding=shares_outstanding,
                leverage_ratio=leverage_ratio
            )
            
        except (KeyError, IndexError) as e:
            print(f"Warning: Error extracting financial data for {ticker}: {e}")
            return None
            
    except Exception as e:
        print(f"Warning: Could not fetch financial data for {ticker}: {e}")
        return None

def fetch_financial_data_previous_year(ticker: str) -> Optional[FScoreData]:
    """
    Fetch financial data from previous year for trend analysis.
    
    Args:
        ticker: Stock symbol
        
    Returns:
        FScoreData object or None if insufficient data
    """
    try:
        stock = yf.Ticker(ticker)
        
        annual_reports = stock.financials
        balance_sheet = stock.balance_sheet
        cash_flow = stock.cashflow
        
        if annual_reports.empty or len(annual_reports.columns) < 2:
            return None
            
        # Get second most recent year
        previous_year = annual_reports.columns[1]
        
        try:
            # Use same logic as current year for previous year
            net_income = (
                annual_reports.loc['Net Earnings', previous_year] if 'Net Earnings' in annual_reports.index else (
                    annual_reports.loc['Net Income', previous_year] if 'Net Income' in annual_reports.index else 0
                )
            )
            total_revenue = (
                annual_reports.loc['Total Revenue', previous_year] if 'Total Revenue' in annual_reports.index else (
                    annual_reports.loc['Revenue', previous_year] if 'Revenue' in annual_reports.index else 1
                )
            )
            cost_of_revenue = (
                annual_reports.loc['Cost Of Goods Sold', previous_year] if 'Cost Of Goods Sold' in annual_reports.index else (
                    annual_reports.loc['Cost of Revenue', previous_year] if 'Cost of Revenue' in annual_reports.index else (
                        annual_reports.loc['Total Cost Of Revenue', previous_year] if 'Total Cost Of Revenue' in annual_reports.index else 0
                    )
                )
            )
            
            total_assets = balance_sheet.loc['Total Assets', previous_year] if 'Total Assets' in balance_sheet.index else 1
            long_term_debt = balance_sheet.loc['Long Term Debt', previous_year] if 'Long Term Debt' in balance_sheet.index else 0
            current_debt = balance_sheet.loc['Current Debt', previous_year] if 'Current Debt' in balance_sheet.index else 0
            current_assets = balance_sheet.loc['Current Assets', previous_year] if 'Current Assets' in balance_sheet.index else 0
            current_liabilities = balance_sheet.loc['Current Liabilities', previous_year] if 'Current Liabilities' in balance_sheet.index else 1
            stockholders_equity = (
                balance_sheet.loc['Stockholders Equity', previous_year] if 'Stockholders Equity' in balance_sheet.index else (
                    balance_sheet.loc['Total Stockholder Equity', previous_year] if 'Total Stockholder Equity' in balance_sheet.index else 1
                )
            )
            
            operating_cash_flow = (
                cash_flow.loc['Total Cash From Operating Activities', previous_year] if 'Total Cash From Operating Activities' in cash_flow.index else (
                    cash_flow.loc['Operating Cash Flow', previous_year] if 'Operating Cash Flow' in cash_flow.index else (
                        cash_flow.loc['Net Cash Flow', previous_year] if 'Net Cash Flow' in cash_flow.index else (
                            cash_flow.loc['Cash From Operating Activities', previous_year] if 'Cash From Operating Activities' in cash_flow.index else 0
                        )
                    )
                )
            )
            
            # Calculate ratios
            roa = net_income / total_assets if total_assets != 0 else 0
            gross_margin = (total_revenue - cost_of_revenue) / total_revenue if total_revenue != 0 else 0
            asset_turnover = total_revenue / total_assets if total_assets != 0 else 0
            debt_to_equity = (long_term_debt + current_debt) / stockholders_equity if stockholders_equity != 0 else 0
            current_ratio = current_assets / current_liabilities if current_liabilities != 0 else 0
            leverage_ratio = long_term_debt / stockholders_equity if stockholders_equity != 0 else 0
            
            return FScoreData(
                net_income=net_income,
                operating_cash_flow=operating_cash_flow,
                roa=roa,
                gross_margin=gross_margin,
                asset_turnover=asset_turnover,
                debt_to_equity=debt_to_equity,
                current_ratio=current_ratio,
                shares_outstanding=1,  # Not used for comparison
                leverage_ratio=leverage_ratio
            )
            
        except (KeyError, IndexError):
            return None
            
    except Exception:
        return None

def calculate_piotroski_f_score(data: FScoreData, prev_data: Optional[FScoreData] = None) -> Dict[str, Any]:
    """
    Calculate Piotroski F-Score based on financial data.
    
    Args:
        data: Current year financial data
        prev_data: Previous year data (optional, for trend analysis)
        
    Returns:
        Dictionary with score breakdown and total F-Score
    """
    score = 0
    breakdown = {}
    
    # Profitability Tests (4 tests)
    breakdown['roa_positive'] = 1 if data.roa > 0 else 0
    score += breakdown['roa_positive']
    
    breakdown['ocf_positive'] = 1 if data.operating_cash_flow > 0 else 0
    score += breakdown['ocf_positive']
    
    breakdown['net_income_positive'] = 1 if data.net_income > 0 else 0
    score += breakdown['net_income_positive']
    
    breakdown['ocf_greater_ni'] = 1 if data.operating_cash_flow > data.net_income else 0
    score += breakdown['ocf_greater_ni']
    
    # Leverage & Liquidity Tests (3 tests)
    if prev_data is not None:
        breakdown['decreasing_leverage'] = 1 if data.debt_to_equity < prev_data.debt_to_equity else 0
        breakdown['increasing_current_ratio'] = 1 if data.current_ratio > prev_data.current_ratio else 0
        breakdown['no_share_dilution'] = 1 if data.shares_outstanding <= prev_data.shares_outstanding else 0
        
        score += breakdown['decreasing_leverage']
        score += breakdown['increasing_current_ratio']
        score += breakdown['no_share_dilution']
    else:
        # Without previous year data, give neutral scores
        breakdown['decreasing_leverage'] = 0
        breakdown['increasing_current_ratio'] = 0
        breakdown['no_share_dilution'] = 0
    
    # Operating Efficiency Tests (2 tests)
    if prev_data is not None:
        breakdown['higher_gross_margin'] = 1 if data.gross_margin > prev_data.gross_margin else 0
        breakdown['higher_asset_turnover'] = 1 if data.asset_turnover > prev_data.asset_turnover else 0
        
        score += breakdown['higher_gross_margin']
        score += breakdown['higher_asset_turnover']
    else:
        breakdown['higher_gross_margin'] = 0
        breakdown['higher_asset_turnover'] = 0
    
    breakdown['total_f_score'] = score
    
    return breakdown

def calculate_f_score(ticker: str, use_cache: bool = True) -> Dict[str, Any]:
    """
    Calculate F-Score for a single ticker with caching support.
    
    Args:
        ticker: Stock symbol
        use_cache: Whether to use cached results if available
        
    Returns:
        Dictionary with F-Score and breakdown
    """
    # Try to load from cache first
    if use_cache:
        cached_result = load_fscore_from_cache(ticker)
        if cached_result is not None:
            print(f"Loaded F-Score from cache: {ticker}")
            return cached_result['f_score_result']
    
    print(f"Calculating F-Score for {ticker}...")
    
    # Fetch current and previous year data
    data = fetch_financial_data(ticker, use_cache=False)  # No cache for individual fetch
    prev_data = fetch_financial_data_previous_year(ticker)
    
    if data is None:
        result = {'total_f_score': 0, 'error': 'insufficient_data'}
    else:
        # Calculate F-Score
        result = calculate_piotroski_f_score(data, prev_data)
    
    result['ticker'] = ticker
    result['has_previous_year'] = prev_data is not None
    
    # Save to cache
    if use_cache:
        save_fscore_to_cache(ticker, data, prev_data, result)
    
    return result

def load_tickers_from_csv(filepath: str) -> list[str]:
    """Load ticker symbols from CSV file (same as screeer.py)"""
    try:
        df = pd.read_csv(filepath)
        
        if 'ticker' in df.columns:
            tickers = df['ticker'].dropna().tolist()
        else:
            tickers = df.iloc[:, 0].dropna().tolist()
        
        tickers = [str(t).strip() for t in tickers if str(t).strip()]
        return tickers
        
    except Exception as e:
        raise ValueError(f"Error reading ticker file {filepath}: {e}")

def print_detailed_f_score_report(result: Dict[str, Any]):
    """Print detailed F-Score report for a single ticker"""
    ticker = result['ticker']
    f_score = result['total_f_score']
    
    print(f"\n📊 Detailed F-Score Analysis: {ticker}")
    print("=" * 60)
    print(f"Overall F-Score: {f_score}/9 ({'Strong' if f_score >= 7 else 'Medium' if f_score >= 5 else 'Weak'})")
    
    # Profitability Analysis
    print(f"\n💰 PROFITABILITY TESTS (4/9 points)")
    print("-" * 40)
    print(f"✓ ROA Positive:         {result.get('roa_positive', 0)} {'✓' if result.get('roa_positive', 0) else '✗'}")
    print(f"✓ Operating CF Positive: {result.get('ocf_positive', 0)} {'✓' if result.get('ocf_positive', 0) else '✗'}")
    print(f"✓ Net Income Positive:  {result.get('net_income_positive', 0)} {'✓' if result.get('net_income_positive', 0) else '✗'}")
    print(f"✓ OCF > Net Income:     {result.get('ocf_greater_ni', 0)} {'✓' if result.get('ocf_greater_ni', 0) else '✗'}")
    
    # Leverage & Liquidity Analysis  
    print(f"\n💵 LEVERAGE & LIQUIDITY TESTS (3/9 points)")
    print("-" * 40)
    print(f"✓ Decreasing Leverage:   {result.get('decreasing_leverage', 0)} {'✓' if result.get('decreasing_leverage', 0) else '✗'}")
    print(f"✓ Increasing Current Ratio: {result.get('increasing_current_ratio', 0)} {'✓' if result.get('increasing_current_ratio', 0) else '✗'}")
    print(f"✓ No Share Dilution:     {result.get('no_share_dilution', 0)} {'✓' if result.get('no_share_dilution', 0) else '✗'}")
    
    # Operating Efficiency Analysis
    print(f"\n⚙️  OPERATING EFFICIENCY TESTS (2/9 points)")
    print("-" * 40)
    print(f"✓ Higher Gross Margin:   {result.get('higher_gross_margin', 0)} {'✓' if result.get('higher_gross_margin', 0) else '✗'}")
    print(f"✓ Higher Asset Turnover: {result.get('higher_asset_turnover', 0)} {'✓' if result.get('higher_asset_turnover', 0) else '✗'}")
    
    # Summary and Interpretation
    print(f"\n📈 INTERPRETATION")
    print("-" * 40)
    if f_score >= 8:
        print("🎯 EXCELLENT: Strong fundamentals across all areas")
    elif f_score >= 6:
        print("👍 GOOD: Strong fundamentals with some weaknesses")
    elif f_score >= 4:
        print("⚠️  AVERAGE: Mixed fundamentals, requires caution")
    elif f_score >= 2:
        print("⚠️  WEAK: Significant fundamental weaknesses")
    else:
        print("❌ POOR: Multiple fundamental red flags")
    
    # Previous year data availability note
    if result.get('has_previous_year'):
        print(f"\n📊 Data includes previous year comparison for trend analysis")
    else:
        print(f"\n⚠️  Previous year data not available - some tests defaulted to 0")

def print_enhanced_detailed_report(ticker: str, detailed: bool = False):
    """Print enhanced detailed F-Score report with actual financial numbers"""
    
    print(f"🔍 Enhanced F-Score Analysis for {ticker}")
    print("=" * 80)
    
    # Fetch raw financial data
    stock = yf.Ticker(ticker)
    info = stock.info
    financials = stock.financials
    balance_sheet = stock.balance_sheet
    cash_flow = stock.cashflow
    
    print(f"📊 Company: {info.get('longName', ticker)}")
    print(f"📊 Market Cap: {info.get('marketCap', 0):,.0f}")
    print(f"📊 Currency: {info.get('currency', 'N/A')}")
    
    # Get most recent year's data
    if len(financials.columns) < 2:
        print("❌ Error: Insufficient historical data - need at least 2 years")
        return None
        
    latest_year = financials.columns[0]
    prev_year = financials.columns[1]
    
    print(f"\n📅 Analysis Period: {latest_year.year} (vs {prev_year.year})")
    
    # Extract key metrics
    def safe_extract(df, field, year, default=0):
        """Safely extract financial data with multiple field name attempts"""
        field_variations = [field, field.replace(' ', ''), field.replace('Total ', '')]
        
        for variation in field_variations:
            if variation in df.index:
                try:
                    return df.loc[variation, year]
                except:
                    continue
        return default
    
    # Income Statement Data
    print(f"\n📈 INCOME STATEMENT DATA")
    print("-" * 60)
    
    # Current Year
    net_income_curr = (
        safe_extract(financials, 'Net Income', latest_year) or 
        safe_extract(financials, 'Net Earnings', latest_year) or 
        0
    )
    revenue_curr = safe_extract(financials, 'Total Revenue', latest_year)
    cost_of_revenue_curr = (
        safe_extract(financials, 'Cost Of Goods Sold', latest_year) or
        safe_extract(financials, 'Cost of Revenue', latest_year) or
        0
    )
    
    print(f"Current Year ({latest_year.year}):")
    print(f"  Revenue: {revenue_curr:,.0f}")
    print(f"  Cost of Revenue: {cost_of_revenue_curr:,.0f}")
    print(f"  Net Income: {net_income_curr:,.0f}")
    
    # Previous Year  
    net_income_prev = (
        safe_extract(financials, 'Net Income', prev_year) or 
        safe_extract(financials, 'Net Earnings', prev_year) or 
        0
    )
    revenue_prev = safe_extract(financials, 'Total Revenue', prev_year)
    cost_of_revenue_prev = (
        safe_extract(financials, 'Cost Of Goods Sold', prev_year) or
        safe_extract(financials, 'Cost of Revenue', prev_year) or
        0
    )
    
    print(f"Previous Year ({prev_year.year}):")
    print(f"  Revenue: {revenue_prev:,.0f}")
    print(f"  Cost of Revenue: {cost_of_revenue_prev:,.0f}")
    print(f"  Net Income: {net_income_prev:,.0f}")
    
    # Balance Sheet Data
    print(f"\n📊 BALANCE SHEET DATA")
    print("-" * 60)
    
    # Current Year
    total_assets_curr = safe_extract(balance_sheet, 'Total Assets', latest_year)
    stockholders_equity_curr = (
        safe_extract(balance_sheet, 'Stockholders Equity', latest_year) or
        safe_extract(balance_sheet, 'Total Stockholder Equity', latest_year) or
        1
    )
    long_term_debt_curr = safe_extract(balance_sheet, 'Long Term Debt', latest_year)
    current_debt_curr = safe_extract(balance_sheet, 'Current Debt', latest_year)
    current_assets_curr = safe_extract(balance_sheet, 'Current Assets', latest_year)
    current_liabilities_curr = safe_extract(balance_sheet, 'Current Liabilities', latest_year)
    shares_curr = info.get('sharesOutstanding', 0)
    
    print(f"Current Year ({latest_year.year}):")
    print(f"  Total Assets: {total_assets_curr:,.0f}")
    print(f"  Stockholders Equity: {stockholders_equity_curr:,.0f}")
    print(f"  Current Assets: {current_assets_curr:,.0f}")
    print(f"  Current Liabilities: {current_liabilities_curr:,.0f}")
    print(f"  Long Term Debt: {long_term_debt_curr:,.0f}")
    print(f"  Current Debt: {current_debt_curr:,.0f}")
    print(f"  Shares Outstanding: {shares_curr:,.0f}")
    
    # Previous Year
    total_assets_prev = safe_extract(balance_sheet, 'Total Assets', prev_year) or 1
    stockholders_equity_prev = (
        safe_extract(balance_sheet, 'Stockholders Equity', prev_year) or
        safe_extract(balance_sheet, 'Total Stockholder Equity', prev_year) or
        1
    )
    long_term_debt_prev = safe_extract(balance_sheet, 'Long Term Debt', prev_year)
    current_debt_prev = safe_extract(balance_sheet, 'Current Debt', prev_year)
    current_assets_prev = safe_extract(balance_sheet, 'Current Assets', prev_year)
    current_liabilities_prev = safe_extract(balance_sheet, 'Current Liabilities', prev_year)
    shares_prev = shares_curr  # Assume same for simplicity

    print(f"Previous Year ({prev_year.year}):")
    print(f"  Total Assets: {total_assets_prev:,.0f}")
    print(f"  Stockholders Equity: {stockholders_equity_prev:,.0f}")
    print(f"  Current Assets: {current_assets_prev:,.0f}")
    print(f"  Current Liabilities: {current_liabilities_prev:,.0f}")
    print(f"  Long Term Debt: {long_term_debt_prev:,.0f}")
    print(f"  Current Debt: {current_debt_prev:,.0f}")
    
    # Cash Flow Data
    print(f"\n💰 CASH FLOW DATA")
    print("-" * 60)
    
    # Current Year
    ocf_curr = (
        safe_extract(cash_flow, 'Operating Cash Flow', latest_year) or
        safe_extract(cash_flow, 'Total Cash From Operating Activities', latest_year) or
        0
    )
    
    # Previous Year
    ocf_prev = (
        safe_extract(cash_flow, 'Operating Cash Flow', prev_year) or
        safe_extract(cash_flow, 'Total Cash From Operating Activities', prev_year) or
        0
    )
    
    print(f"Current Year ({latest_year.year}):")
    print(f"  Operating Cash Flow: {ocf_curr:,.0f}")
    print(f"Previous Year ({prev_year.year}):")
    print(f"  Operating Cash Flow: {ocf_prev:,.0f}")
    
    # Calculate Ratios
    print(f"\n📊 CALCULATED RATIOS")
    print("-" * 60)
    
    roa_curr = (net_income_curr / total_assets_curr) if total_assets_curr != 0 else 0
    gross_margin_curr = ((revenue_curr - cost_of_revenue_curr) / revenue_curr) if revenue_curr != 0 else 0
    asset_turnover_curr = (revenue_curr / total_assets_curr) if total_assets_curr != 0 else 0
    debt_to_equity_curr = ((long_term_debt_curr + current_debt_curr) / stockholders_equity_curr) if stockholders_equity_curr != 0 else 0
    current_ratio_curr = (current_assets_curr / current_liabilities_curr) if current_liabilities_curr != 0 else 0
    
    roa_prev = (net_income_prev / total_assets_prev) if total_assets_prev != 0 else 0
    gross_margin_prev = ((revenue_prev - cost_of_revenue_prev) / revenue_prev) if revenue_prev != 0 else 0
    asset_turnover_prev = (revenue_prev / total_assets_prev) if total_assets_prev != 0 else 0
    debt_to_equity_prev = ((long_term_debt_prev + current_debt_prev) / stockholders_equity_prev) if stockholders_equity_prev != 0 else 0
    current_ratio_prev = (current_assets_prev / current_liabilities_prev) if current_liabilities_prev != 0 else 0
    
    print(f"Current Year:")
    print(f"  ROA: {roa_curr:.4f}")
    print(f"  Gross Margin: {gross_margin_curr:.1%}")
    print(f"  Asset Turnover: {asset_turnover_curr:.2f}")
    print(f"  Debt to Equity: {debt_to_equity_curr:.4f}")
    print(f"  Current Ratio: {current_ratio_curr:.2f}")
    
    print(f"Previous Year:")
    print(f"  ROA: {roa_prev:.4f}")
    print(f"  Gross Margin: {gross_margin_prev:.1%}")
    print(f"  Asset Turnover: {asset_turnover_prev:.2f}")
    print(f"  Debt to Equity: {debt_to_equity_prev:.4f}")
    print(f"  Current Ratio: {current_ratio_prev:.2f}")
    
    # Calculate F-Score Tests
    print(f"\n🎯 PIOTROSKI F-SCORE TESTS")
    print("=" * 60)
    
    print(f"\n💰 PROFITABILITY TESTS (4/9 points)")
    print("-" * 40)
    
    # Test 1: ROA
    test1_roa = 1 if roa_curr > 0 else 0
    print(f"1. ROA Positive:         {test1_roa} {'✓' if test1_roa else '✗'}")
    print(f"   Result: ROA = {roa_curr:.4f} {'> 0' if roa_curr > 0 else '< 0'}")
    
    # Test 2: Operating Cash Flow
    test2_ocf = 1 if ocf_curr > 0 else 0
    print(f"2. CFPS Positive:        {test2_ocf} {'✓' if test2_ocf else '✗'}")
    print(f"   Result: OCF = {ocf_curr:,.0f} {'> 0' if ocf_curr > 0 else '< 0'}")
    
    # Test 3: Change in ROA
    test3_roa_change = 1 if roa_curr > roa_prev else 0
    print(f'3. Positive ΔROA:        {test3_roa_change} {"✓" if test3_roa_change else "✗"}')
    print(f"   Result: ΔROA = {roa_curr:.4f} - {roa_prev:.4f} = {roa_curr - roa_prev:.4f}")
    print(f"   Current ROA: {roa_curr:.4f}, Previous ROA: {roa_prev:.4f}")
    
    # Test 4: Cash quality
    test4_cash_quality = 1 if ocf_curr > net_income_curr else 0
    print(f"4. CFO > Net Income:    {test4_cash_quality} {'✓' if test4_cash_quality else '✗'}")
    print(f"   Result: OCF = {ocf_curr:,.0f}, Net Income = {net_income_curr:,.0f}")
    print(f"   Cash Quality: {'High' if test4_cash_quality else 'Low'}")
    
    print(f"\n💵 LEVERAGE & LIQUIDITY TESTS (3/9 points)")
    print("-" * 40)
    
    # Test 5: Decrease in Long-term debt
    test5_leverage = 1 if debt_to_equity_curr < debt_to_equity_prev else 0
    print(f"5. Decreasing Leverage: {test5_leverage} {'✓' if test5_leverage else '✗'}")
    print(f"   Result: D/E = {debt_to_equity_curr:.4f} {'<' if debt_to_equity_curr < debt_to_equity_prev else '>'} {debt_to_equity_prev:.4f}")
    print(f"   Current D/E: {debt_to_equity_curr:.4f}, Previous D/E: {debt_to_equity_prev:.4f}")
    
    # Test 6: Current Ratio Improvement
    test6_current_ratio = 1 if current_ratio_curr > current_ratio_prev else 0
    print(f"6. Higher Current Ratio:{test6_current_ratio} {'✓' if test6_current_ratio else '✗'}")
    print(f"   Result: Current Ratio = {current_ratio_curr:.2f} {'>' if current_ratio_curr > current_ratio_prev else '<'} {current_ratio_prev:.2f}")
    print(f"   Current: {current_ratio_curr:.2f}, Previous: {current_ratio_prev:.2f}")
    
    # Test 7: No Share Dilution
    test7_shares = 1 if shares_curr <= shares_prev else 0
    print(f"7. No Share Dilution:   {test7_shares} {'✓' if test7_shares else '✗'}")
    print(f"   Result: Shares = {shares_curr:,.0f} {'<=' if shares_curr <= shares_prev else '>'} {shares_prev:,.0f}")
    
    print(f"\n⚙️  OPERATING EFFICIENCY (2/9 points)")
    print("-" * 40)
    
    # Test 8: Higher Gross Margin
    test8_gross_margin = 1 if gross_margin_curr > gross_margin_prev else 0
    print(f"8. Higher Gross Margin: {test8_gross_margin} {'✓' if test8_gross_margin else '✗'}")
    print(f"   Result: GM = {gross_margin_curr:.1%} {'>' if gross_margin_curr > gross_margin_prev else '<'} {gross_margin_prev:.1%}")
    
    # Test 9: Higher Asset Turnover
    test9_asset_turnover = 1 if asset_turnover_curr > asset_turnover_prev else 0
    print(f"9. Higher Asset Turnover:{test9_asset_turnover} {'✓' if test9_asset_turnover else '✗'}")
    print(f"   Result: AT = {asset_turnover_curr:.2f} {'>' if asset_turnover_curr > asset_turnover_prev else '<'} {asset_turnover_prev:.2f}")
    
    # Calculate Total F-Score
    total_score = (test1_roa + test2_ocf + test3_roa_change + test4_cash_quality + 
                   test5_leverage + test6_current_ratio + test7_shares + 
                   test8_gross_margin + test9_asset_turnover)
    
    print(f"\n🏆 TOTAL F-SCORE: {total_score}/9")
    print("=" * 60)
    
    print(f"Score breakdown:")
    print(f"  Profitability: {test1_roa + test2_ocf + test3_roa_change + test4_cash_quality}/4")
    print(f"  Leverage/Liquidity: {test5_leverage + test6_current_ratio + test7_shares}/3")
    print(f"  Operating Efficiency: {test8_gross_margin + test9_asset_turnover}/2")
    
    print(f"\nInterpretation:")
    if total_score >= 8:
        print("🎯 EXCELLENT: Strong fundamentals across all areas")
    elif total_score >= 6:
        print("👍 GOOD: Strong fundamentals with minor weaknesses")
    elif total_score >= 4:
        print("⚠️  AVERAGE: Mixed fundamentals, requires caution")
    elif total_score >= 2:
        print("🚨 WEAK: Significant fundamental red flags")
    else:
        print("💀 POOR: Multiple severe fundamental problems")
    
    return {
        'ticker': ticker,
        'f_score': total_score,
        'tests': {
            1: test1_roa, 2: test2_ocf, 3: test3_roa_change, 4: test4_cash_quality,
            5: test5_leverage, 6: test6_current_ratio, 7: test7_shares,
            8: test8_gross_margin, 9: test9_asset_turnover
        }
    }

def main():
    """Main function for standalone F-Score calculation"""
    parser = argparse.ArgumentParser(description="Piotroski F-Score Calculator")
    parser.add_argument("input", help="Ticker symbol (e.g., 'VOLV-B.ST') or CSV file containing tickers")
    parser.add_argument("--output", default=None, help="Output CSV file (only used with ticker file input)")
    parser.add_argument("--verbose", action="store_true", help="Show detailed breakdown for each ticker")
    parser.add_argument("--no-cache", action="store_true", help="Disable caching (always fetch fresh data)")
    parser.add_argument("--detailed", action="store_true", help="Show detailed analysis (only for single ticker)")
    
    args = parser.parse_args()
    
    # Determine if input is a single ticker or a file
    input_path = args.input
    
    # Check if file exists - if not, treat as single ticker
    if not os.path.exists(input_path):
        # Treat as single ticker
        ticker = input_path.upper()
        print(f"Analyzing single ticker: {ticker}")
        
        try:
            if args.detailed:
                # Use enhanced detailed report with full financial breakdown
                print_enhanced_detailed_report(ticker)
            else:
                # Use standard F-Score calculation
                result = calculate_f_score(ticker, use_cache=not args.no_cache)
                print_detailed_f_score_report(result)
            
            return 0
            
        except Exception as e:
            print(f"❌ Error analyzing {ticker}: {e}")
            return 1
    
    # Treat as file
    try:
        tickers = load_tickers_from_csv(input_path)
        print(f"Calculating F-Scores for {len(tickers)} tickers...")
        
        results = []
        for ticker in tickers:
            result = calculate_f_score(ticker, use_cache=not args.no_cache)
            results.append(result)
            
            if args.verbose:
                print(f"\n{ticker} F-Score: {result['total_f_score']}/9")
                print("Breakdown:")
                for key, value in result.items():
                    if key not in ['total_f_score', 'ticker', 'has_previous_year', 'error']:
                        print(f"  {key}: {value}")
        
        # Create DataFrame and save
        df = pd.DataFrame(results)
        
        # Reorder columns
        columns = ['ticker', 'total_f_score']
        other_cols = [col for col in df.columns if col not in columns + ['has_previous_year', 'error']]
        if len(df) > 0:  # Only process if we have data
            df[columns[1]] = pd.to_numeric(df[columns[1]], errors='coerce').fillna(0).astype(int)
            df = df[columns + other_cols]
        
        # Determine output filename
        output_file = args.output or "f_scores.csv"
        df.to_csv(output_file, index=False)
        
        # Summary
        print(f"\n📍 F-Score Summary:")
        print(f"Tickers processed: {len(tickers)}")
        print(f"Total F-Scores calculated: {len(df[df['total_f_score'] > 0])}")
        
        f_scores = df['total_f_score'][df['total_f_score'] > 0]
        if len(f_scores) > 0:
            print(f"Average F-Score: {f_scores.mean():.1f}")
            print(f"F-Score distribution:")
            for score in range(10):
                count = len(f_scores[f_scores == score])
                if count > 0:
                    print(f"  {score}: {count} stocks")
        
        print(f"\n💾 Results saved to {output_file}")
        
        return 0
        
    except Exception as e:
        print(f"❌ Error processing file {input_path}: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
