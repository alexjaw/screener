#!/usr/bin/env python3
"""
Enhanced Piotroski F-Score Calculator

Calculates Piotroski F-Score (0-9) using multiple data sources:
1. Quarterly/Annual reports (via AI PDF parser)
2. Web scraping from company websites
3. Yahoo Finance (fallback)

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

# Import enhanced data-fetcher system
from financial_models import FinancialData
from financial_fetcher import fetch_financials
from financial_parser import parse_financials
from data_fetcher_fscore import compute_fscore

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
    
    cache_time = os.path.getmtime(cache_file)
    age_days = (time_module.time() - cache_time) / (24 * 3600)
    return age_days < FSCORE_CACHE_DAYS

def load_fscore_from_cache(ticker: str) -> Optional[Dict[str, Any]]:
    """Load F-Score data from cache if available and fresh."""
    cache_file = get_fscore_cache_file(ticker)
    
    if not is_fscore_cache_fresh(cache_file):
        return None
    
    try:
        with open(cache_file, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None

def save_fscore_to_cache(ticker: str, data: Dict[str, Any]):
    """Save F-Score data to cache."""
    cache_file = get_fscore_cache_file(ticker)
    
    cache_data = {
        'ticker': ticker,
        'calculated_at': time_module.time(),
        'f_score_result': data
    }
    
    with open(cache_file, 'w') as f:
        json.dump(cache_data, f, indent=2)

def convert_financial_data_to_fscore_data(financial_data: FinancialData) -> FScoreData:
    """Convert FinancialData to FScoreData format."""
    # Calculate derived metrics
    total_assets = financial_data.total_assets_cur
    total_equity = total_assets - financial_data.long_term_debt_cur - financial_data.current_liabilities_cur
    
    roa = financial_data.net_income_cur / max(total_assets, 1)
    gross_margin = (financial_data.revenue_cur - financial_data.cogs_cur) / max(financial_data.revenue_cur, 1)
    asset_turnover = financial_data.revenue_cur / max(total_assets, 1)
    debt_to_equity = financial_data.long_term_debt_cur / max(total_equity, 1)
    current_ratio = financial_data.current_assets_cur / max(financial_data.current_liabilities_cur, 1)
    leverage_ratio = financial_data.long_term_debt_cur / max(total_assets, 1)
    
    return FScoreData(
        net_income=financial_data.net_income_cur,
        operating_cash_flow=financial_data.cfo_cur,
        roa=roa,
        gross_margin=gross_margin,
        asset_turnover=asset_turnover,
        debt_to_equity=debt_to_equity,
        current_ratio=current_ratio,
        shares_outstanding=financial_data.shares_cur,
        leverage_ratio=leverage_ratio
    )

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
        # Without previous year data, give neutral scores
        breakdown['higher_gross_margin'] = 0
        breakdown['higher_asset_turnover'] = 0
    
    breakdown['total_f_score'] = score
    breakdown['ticker'] = 'unknown'  # Will be set by caller
    breakdown['has_previous_year'] = prev_data is not None
    
    return breakdown

def fetch_financial_data_yahoo(ticker: str) -> Optional[FScoreData]:
    """Fallback: Fetch financial data from Yahoo Finance."""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        financials = stock.financials
        balance_sheet = stock.balance_sheet
        cash_flow = stock.cashflow
        
        if len(financials.columns) < 2:
            return None
            
        latest_year = financials.columns[0]
        prev_year = financials.columns[1]
        
        # Extract key metrics
        def safe_extract(df, field, year, default=0):
            field_variations = [field, field.replace(' ', ''), field.replace('Total ', '')]
            for variation in field_variations:
                if variation in df.index:
                    try:
                        return df.loc[variation, year]
                    except:
                        continue
            return default
        
        # Current year data
        net_income_curr = safe_extract(financials, 'Net Income', latest_year) or 0
        revenue_curr = safe_extract(financials, 'Total Revenue', latest_year) or 0
        cost_of_revenue_curr = safe_extract(financials, 'Cost Of Goods Sold', latest_year) or 0
        total_assets_curr = safe_extract(balance_sheet, 'Total Assets', latest_year) or 0
        stockholders_equity_curr = safe_extract(balance_sheet, 'Stockholders Equity', latest_year) or 1
        long_term_debt_curr = safe_extract(balance_sheet, 'Long Term Debt', latest_year) or 0
        current_assets_curr = safe_extract(balance_sheet, 'Current Assets', latest_year) or 0
        current_liabilities_curr = safe_extract(balance_sheet, 'Current Liabilities', latest_year) or 1
        shares_curr = info.get('sharesOutstanding', 0) or 0
        cfo_curr = safe_extract(cash_flow, 'Total Cash From Operating Activities', latest_year) or 0
        
        # Calculate derived metrics
        roa = net_income_curr / max(total_assets_curr, 1)
        gross_margin = (revenue_curr - cost_of_revenue_curr) / max(revenue_curr, 1)
        asset_turnover = revenue_curr / max(total_assets_curr, 1)
        debt_to_equity = long_term_debt_curr / max(stockholders_equity_curr, 1)
        current_ratio = current_assets_curr / max(current_liabilities_curr, 1)
        leverage_ratio = long_term_debt_curr / max(total_assets_curr, 1)
        
        return FScoreData(
            net_income=net_income_curr,
            operating_cash_flow=cfo_curr,
            roa=roa,
            gross_margin=gross_margin,
            asset_turnover=asset_turnover,
            debt_to_equity=debt_to_equity,
            current_ratio=current_ratio,
            shares_outstanding=shares_curr,
            leverage_ratio=leverage_ratio
        )
        
    except Exception as e:
        print(f"Yahoo Finance fallback failed for {ticker}: {e}")
        return None

def calculate_f_score(ticker: str, use_cache: bool = True, use_quarterly: bool = False) -> Dict[str, Any]:
    """
    Calculate F-Score for a single ticker using enhanced data sources.
    
    Args:
        ticker: Stock symbol
        use_cache: Whether to use cached results if available
        use_quarterly: Whether to prefer quarterly data over annual
        
    Returns:
        Dictionary with F-Score and breakdown
    """
    # Try to load from cache first
    if use_cache:
        cached_result = load_fscore_from_cache(ticker)
        if cached_result is not None:
            print(f"Loaded F-Score from cache: {ticker}")
            return cached_result['f_score_result']
    
    print(f"Calculating enhanced F-Score for {ticker}...")
    
    # Try enhanced data-fetcher system first
    try:
        # Map ticker to company name for data-fetcher
        ticker_to_company = {
            'BIOA-B.ST': 'BioArctic',
            'SAAB-B.ST': 'SAAB', 
            'INT.ST': 'Intellego Technologies',
            'VOLV-B.ST': 'Volvo',
            'EVO.ST': 'Evolution Gaming',
            'ERIC-B.ST': 'Ericsson',
            'NDA-SE.ST': 'Nordea',
            'TELIA.ST': 'Telia',
            'SAND.ST': 'Sandvik',
            'ASSA-B.ST': 'Assa Abloy',
            'ATCO-A.ST': 'Atlas Copco A',
            'ATCO-B.ST': 'Atlas Copco B',
        }
        
        company_name = ticker_to_company.get(ticker, ticker)
        
        # Fetch financial data using enhanced system
        financial_data = fetch_financials(company_name)
        
        if financial_data and financial_data.revenue_cur > 0:
            print(f"✅ Using enhanced data-fetcher for {ticker}")
            
            # Convert to FScoreData format
            current_data = convert_financial_data_to_fscore_data(financial_data)
            
            # For previous year data, we'd need to fetch it separately
            # For now, we'll calculate without previous year comparison
            prev_data = None
            
            # Calculate F-Score
            result = calculate_piotroski_f_score(current_data, prev_data)
            result['ticker'] = ticker
            result['data_source'] = 'enhanced_data_fetcher'
            
            # Save to cache
            save_fscore_to_cache(ticker, result)
            
            return result
            
    except Exception as e:
        print(f"Enhanced data-fetcher failed for {ticker}: {e}")
    
    # Fallback to Yahoo Finance
    print(f"🔄 Falling back to Yahoo Finance for {ticker}")
    try:
        data = fetch_financial_data_yahoo(ticker)
        
        if data is None:
            result = {'total_f_score': 0, 'error': 'insufficient_data', 'ticker': ticker, 'data_source': 'yahoo_fallback'}
        else:
            # Calculate F-Score (without previous year for now)
            result = calculate_piotroski_f_score(data, None)
            result['ticker'] = ticker
            result['data_source'] = 'yahoo_finance'
        
        # Save to cache
        save_fscore_to_cache(ticker, result)
        
        return result
        
    except Exception as e:
        print(f"Yahoo Finance fallback failed for {ticker}: {e}")
        return {'total_f_score': 0, 'error': 'all_sources_failed', 'ticker': ticker}

def main():
    """Main function for standalone usage."""
    parser = argparse.ArgumentParser(description='Calculate Piotroski F-Scores for stocks')
    parser.add_argument('ticker_file', help='CSV file with ticker symbols')
    parser.add_argument('--output', '-o', help='Output CSV file')
    parser.add_argument('--use-quarterly', action='store_true', help='Prefer quarterly data')
    parser.add_argument('--no-cache', action='store_true', help='Disable caching')
    
    args = parser.parse_args()
    
    # Load tickers
    try:
        df = pd.read_csv(args.ticker_file)
        tickers = df['ticker'].tolist()
    except Exception as e:
        print(f"Error loading tickers: {e}")
        return
    
    # Calculate F-Scores
    results = []
    for ticker in tickers:
        print(f"\nProcessing {ticker}...")
        result = calculate_f_score(ticker, use_cache=not args.no_cache, use_quarterly=args.use_quarterly)
        results.append(result)
    
    # Create results DataFrame
    results_df = pd.DataFrame(results)
    
    # Save results
    if args.output:
        results_df.to_csv(args.output, index=False)
        print(f"\nResults saved to {args.output}")
    else:
        print(results_df)

if __name__ == "__main__":
    main()