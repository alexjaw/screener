#!/usr/bin/env python3
"""CLI for ticker data analysis."""

import argparse
import yfinance as yf
import pandas as pd

def main():
    """Main CLI function."""
    parser = argparse.ArgumentParser(
        description='Get detailed ticker data',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s VOLV-B.ST
  %(prog)s SAND.ST --period 1y
        """
    )
    
    parser.add_argument('ticker', help='Ticker symbol to analyze')
    parser.add_argument('--period', default='1y', help='Data period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)')
    parser.add_argument('--interval', default='1d', help='Data interval (1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo)')
    
    args = parser.parse_args()
    
    try:
        # Get ticker data
        ticker = yf.Ticker(args.ticker)
        info = ticker.info
        hist = ticker.history(period=args.period, interval=args.interval)
        
        if hist.empty:
            print(f"No data found for {args.ticker}")
            return
        
        # Display basic info
        print(f"\n📊 {args.ticker} - {info.get('longName', 'N/A')}")
        print(f"Current Price: {info.get('currentPrice', 'N/A')} {info.get('currency', '')}")
        print(f"Market Cap: {info.get('marketCap', 'N/A')}")
        print(f"Sector: {info.get('sector', 'N/A')}")
        print(f"Industry: {info.get('industry', 'N/A')}")
        
        # Display price data
        print(f"\n📈 Price Data ({args.period}):")
        print(f"Latest: {hist['Close'].iloc[-1]:.2f}")
        print(f"Open: {hist['Open'].iloc[-1]:.2f}")
        print(f"High: {hist['High'].iloc[-1]:.2f}")
        print(f"Low: {hist['Low'].iloc[-1]:.2f}")
        print(f"Volume: {hist['Volume'].iloc[-1]:,}")
        
        # Calculate returns
        if len(hist) > 1:
            period_return = ((hist['Close'].iloc[-1] / hist['Close'].iloc[0]) - 1) * 100
            print(f"Period Return: {period_return:.2f}%")
        
        # Display recent data
        print(f"\n📋 Recent Data:")
        print(hist.tail().round(2))
        
    except Exception as e:
        print(f"Error fetching data for {args.ticker}: {e}")

if __name__ == "__main__":
    main()