#!/usr/bin/env python3
"""CLI for F-Score calculation."""

import argparse
import pandas as pd
from ..analysis.fscore_calculator import score_company
from ..utils import search_stockanalysis

def main():
    """Main CLI function."""
    parser = argparse.ArgumentParser(
        description='Calculate Piotroski F-Scores for stocks',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s tickers.csv --output scores.csv
  %(prog)s VOLV-B.ST --detailed
  %(prog)s nordrest
  %(prog)s nordrest --list-alternatives
  %(prog)s tickers.csv --use-quarterly --no-cache
        """
    )
    
    parser.add_argument('ticker_file', help='CSV file with ticker symbols, single ticker, or company name')
    parser.add_argument('--output', '-o', help='Output CSV file')
    parser.add_argument('--use-quarterly', action='store_true', help='Prefer quarterly data')
    parser.add_argument('--no-cache', action='store_true', help='Disable caching')
    parser.add_argument('--detailed', action='store_true', help='Show detailed breakdown')
    parser.add_argument(
        '--list-alternatives',
        action='store_true',
        help='For a single company name: show possible stockanalysis.com matches and exit',
    )
    
    args = parser.parse_args()
    
    # Check if single ticker/name or file
    if args.ticker_file.endswith('.csv'):
        # Load tickers from file
        try:
            df = pd.read_csv(args.ticker_file)
            tickers = df['ticker'].tolist()
        except Exception as e:
            print(f"Error loading tickers: {e}")
            return
    else:
        # Single ticker or company name
        if args.list_alternatives:
            matches = search_stockanalysis(args.ticker_file, max_results=15)
            if not matches:
                print(f"No stockanalysis.com matches for '{args.ticker_file}'.")
                return
            print(f"Matches for '{args.ticker_file}' on stockanalysis.com:\n")
            for m in matches:
                print(f"  {m.symbol:12}  {m.name}")
                print(f"    {m.url}")
            return
        tickers = [args.ticker_file]
    
    # Calculate F-Scores
    results = []
    for ticker in tickers:
        print(f"\nProcessing {ticker}...")
        try:
            result = score_company(ticker, use_quarterly=args.use_quarterly)
            results.append(result)
            
            if args.detailed:
                print(f"F-Score: {result['total_f_score']}/9")
                print(f"Data source: {result.get('data_source', 'unknown')}")
                if 'has_previous_year' in result:
                    print(f"Previous year data: {'Yes' if result['has_previous_year'] else 'No'}")
        except Exception as e:
            print(f"Error processing {ticker}: {e}")
            results.append({'total_f_score': 0, 'error': str(e), 'ticker': ticker})
    
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