#!/usr/bin/env python3
"""
Individual Ticker Data Fetcher

Fetches and displays detailed price data for a single stock ticker.
Default: Last month of data with clean table formatting.
"""

from __future__ import annotations
import pandas as pd
import numpy as np
from datetime import date, timedelta
import argparse
import sys
from typing import Optional

# Import our existing cache functionality
from screeer import (
    find_closest_trading_day, 
    ensure_cache_dir, 
    is_cache_fresh,
    load_from_cache,
    save_to_cache,
    generate_cache_key
)

def fetch_ticker_data(ticker: str, start_date: Optional[str] = None, end_date: Optional[str] = None, use_cache: bool = True) -> pd.DataFrame:
    """
    Fetch detailed price data for a single ticker.
    
    Args:
        ticker: Stock symbol (e.g., "SAND.ST")
        start_date: Start date in YYYY-MM-DD format (default: 1 month ago)
        end_date: End date in YYYY-MM-DD format (default: today)
        use_cache: Whether to use cached data if available
    
    Returns:
        DataFrame with OHLCV data for the ticker
    """
    # Set defaults
    if end_date is None:
        end_date = date.today().isoformat()
    if start_date is None:
        start_date = (date.today() - timedelta(days=30)).isoformat()
    
    # Adjust dates to closest trading days
    start_date_adj = find_closest_trading_day(date.fromisoformat(start_date))
    end_date_adj = find_closest_trading_day(date.fromisoformat(end_date))
    
    print(f"Fetching {ticker} data from {start_date_adj} to {end_date_adj}")
    
    # Try cache first
    if use_cache:
        cached_data = load_from_cache([ticker], start_date_adj, end_date_adj)
        if cached_data is not None:
            return cached_data
    
    # Fetch fresh data
    import yfinance as yf
    
    # Add 1 day to end date to include it (Yahoo Finance quirk)
    end_actual = (date.fromisoformat(end_date_adj) + timedelta(days=1)).isoformat()
    
    data = yf.download(ticker, start=start_date_adj, end=end_actual, auto_adjust=False, progress=False)
    
    # Handle different data structures
    if isinstance(data.columns, pd.MultiIndex):
        # Multi-index case (multiple tickers) - select ticker columns
        price_columns = ['Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume']
        selected_data = {}
        
        for price_type in price_columns:
            col_key = (price_type, ticker)
            if col_key in data.columns:
                selected_data[price_type] = data[col_key]
        
        price_data = pd.DataFrame(selected_data).dropna()
    else:
        # Single ticker case
        price_data = data.dropna()
    
    # Ensure we have price data
    if price_data.empty:
        raise ValueError(f"No price data found for {ticker}")
    
    # Cache if enabled
    if use_cache:
        save_to_cache([ticker], start_date_adj, end_date_adj, price_data)
    
    return price_data

def get_company_info(ticker: str) -> dict:
    """
    Fetch company information including full name and market cap.
    
    Args:
        ticker: Stock symbol
    
    Returns:
        Dict with 'name' and 'market_cap' keys
    """
    import yfinance as yf
    
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        company_name = info.get('longName', info.get('shortName', ticker))
        
        # Market cap in various currencies/units
        market_cap = info.get('marketCap', 0)
        if market_cap == 0:
            market_cap = info.get('totalAssets', 0)  # Fallback for some REITs
        
        return {
            'name': company_name,
            'market_cap': market_cap,
            'currency': info.get('currency', 'USD'),
            'country': info.get('country', 'Unknown')
        }
    except Exception as e:
        print(f"Warning: Could not fetch company info for {ticker}: {e}")
        return {
            'name': ticker,
            'market_cap': 0,
            'currency': 'USD',
            'country': 'Unknown'
        }

def format_market_cap(market_cap: int, currency: str) -> str:
    """Format market cap with appropriate suffixes (B, M, etc.)"""
    if market_cap == 0:
        return "N/A"
    
    if market_cap >= 1_000_000_000:
        return f"{market_cap / 1_000_000_000:.1f}B {currency}"
    elif market_cap >= 1_000_000:
        return f"{market_cap / 1_000_000:.0f}M {currency}"
    else:
        return f"{market_cap:,} {currency}"

def format_price_table(data: pd.DataFrame, ticker: str) -> None:
    """
    Display price data in a clean, formatted table.
    """
    # Get company information
    company_info = get_company_info(ticker)
    
    print(f"\n📊 {ticker} Price Data ({len(data)} trading days)")
    print("=" * 80)
    print(f"Company: {company_info['name']}")
    print(f"Market Cap: {format_market_cap(company_info['market_cap'], company_info['currency'])}")
    print(f"Country: {company_info['country']}")
    print("-" * 80)
    
    # Format the data for display
    display_data = data.copy()
    
    # Round price columns to 2 decimal places
    price_cols = ['Open', 'High', 'Low', 'Close', 'Adj Close']
    for col in price_cols:
        if col in display_data.columns:
            display_data[col] = display_data[col].round(2)
    
    # Format volume column
    if 'Volume' in display_data.columns:
        display_data['Volume'] = display_data['Volume'].apply(lambda x: f"{x:,.0f}" if pd.notnull(x) else "")
    
    # Reset index to make dates a regular column
    display_data = display_data.reset_index()
    # Convert the date column (which was the index) to date format
    display_data['Date'] = pd.to_datetime(display_data['Date']).dt.date
    
    # Sort by date in descending order (most recent first)
    display_data = display_data.sort_values('Date', ascending=False)
    
    # Reorder columns for better display
    column_order = ['Date'] + price_cols + ['Volume']
    display_data = display_data[[col for col in column_order if col in display_data.columns]]
    
    # Display the table
    print(display_data.to_string(index=False))
    
    # Add summary statistics
    print(f"\n📈 {ticker} Summary")
    print("-" * 40)
    
    if price_cols and any(col in data.columns for col in price_cols):
        price_col = 'Adj Close' if 'Adj Close' in data.columns else 'Close'
        latest_price = data[price_col].iloc[-1]
        earliest_price = data[price_col].iloc[0]
        high_price = data['High'].max()
        low_price = data['Low'].min()
        
        # Calculate returns
        total_return = ((latest_price / earliest_price) - 1) * 100
        
        print(f"Start Price:     {earliest_price:.2f}")
        print(f"End Price:       {latest_price:.2f}")
        print(f"Period High:     {high_price:.2f}")
        print(f"Period Low:      {low_price:.2f}")
        print(f"Total Return:    {total_return:+.1f}%")
        
        # Daily statistics
        daily_returns = data[price_col].pct_change().dropna()
        if len(daily_returns) > 0:
            avg_daily_return = daily_returns.mean() * 100
            volatility = daily_returns.std() * 100
            print(f"Avg Daily Ret:   {avg_daily_return:+.2f}%")
            print(f"Volatility:      {volatility:.2f}%")

def main():
    parser = argparse.ArgumentParser(description="Fetch and display detailed data for a single stock ticker")
    parser.add_argument("ticker", help="Stock ticker symbol (e.g., SAND.ST)")
    parser.add_argument("--start-date", type=str, help="Start date (YYYY-MM-DD). Default: 1 month ago")
    parser.add_argument("--end-date", type=str, help="End date (YYYY-MM-DD). Default: today")
    parser.add_argument("--no-cache", action="store_true", help="Disable caching")
    parser.add_argument("--csv", help="Save to CSV file", metavar="FILENAME")
    
    args = parser.parse_args()
    
    try:
        # Fetch data
        data = fetch_ticker_data(
            ticker=args.ticker,
            start_date=args.start_date,
            end_date=args.end_date,
            use_cache=not args.no_cache
        )
        
        if data.empty:
            print(f"❌ No data found for {args.ticker}")
            return
        
        # Display formatted table
        format_price_table(data, args.ticker)
        
        # Save to CSV if requested
        if args.csv:
            data.to_csv(args.csv)
            print(f"\n💾 Data saved to {args.csv}")
            
    except Exception as e:
        print(f"❌ Error fetching data for {args.ticker}: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
