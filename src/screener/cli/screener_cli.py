#!/usr/bin/env python3
"""CLI for momentum screening."""

import argparse
from datetime import date, timedelta
from ..core.momentum import momentum_screen, ScreenConfig, NordicSuffix

def parse_date(date_str: str) -> date:
    """Parse date string in YYYY-MM-DD format."""
    return date.fromisoformat(date_str)

def main():
    """Main CLI function."""
    parser = argparse.ArgumentParser(
        description="Nordic Stock Momentum Screener",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --ticker-file tickers.csv
  %(prog)s --top-n 10 --min-f-score 6
  %(prog)s --debug-ticker VOLV-B.ST --use-quarterly
        """
    )
    
    parser.add_argument(
        "--start-date",
        type=str,
        help="Start date for data fetching (YYYY-MM-DD). Default: 1 year ago"
    )
    parser.add_argument(
        "--end-date", 
        type=str,
        help="End date for data fetching (YYYY-MM-DD). Default: today"
    )
    parser.add_argument(
        "--debug-ticker",
        type=str,
        help="Ticker symbol to show detailed debug information for (e.g., SAND.ST)"
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=20,
        help="Number of top stocks to return (default: 20)"
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Disable caching and always fetch fresh data"
    )
    parser.add_argument(
        "--force-refresh",
        action="store_true", 
        help="Force refresh cache even if it's fresh"
    )
    parser.add_argument(
        "--ticker-file",
        type=str,
        default="src/screener/data/tickers.csv",
        help="CSV file containing ticker symbols to analyze (default: src/screener/data/tickers.csv)"
    )
    parser.add_argument(
        "--no-f-score",
        action="store_true",
        help="Disable F-Score calculation (momentum only)"
    )
    parser.add_argument(
        "--min-f-score",
        type=int,
        default=None,
        help="Minimum F-Score threshold (default: None, no filter)"
    )
    parser.add_argument(
        "--f-score-weight",
        type=float,
        default=0.3,
        help="Weight for F-Score in composite score (default: 0.3)"
    )
    parser.add_argument(
        "--momentum-weight",
        type=float,
        default=0.7,
        help="Weight for momentum in composite score (default: 0.7)"
    )
    parser.add_argument(
        "--use-quarterly",
        action='store_true',
        help="Prefer quarterly/interim reports over annual reports for F-Score calculation"
    )
    
    args = parser.parse_args()
    
    # Set defaults
    end_date = date.today() if args.end_date is None else parse_date(args.end_date)
    start_date = (end_date - timedelta(days=450)) if args.start_date is None else parse_date(args.start_date)
    
    # Adjust dates to closest trading days
    start_date_adj = start_date
    end_date_adj = end_date
    
    print(f"Momentum screening from {start_date_adj} to {end_date_adj}")
    
    # Load ticker universe from file
    try:
        import pandas as pd
        ticker_df = pd.read_csv(args.ticker_file)
        universe = ticker_df['ticker'].tolist()
        print(f"Loaded {len(universe)} tickers from {args.ticker_file}")
        print(f"Tickers: {', '.join(universe[:5])}{'...' if len(universe) > 5 else ''} ({len(universe)} total)")
    except Exception as e:
        print(f"Error loading tickers from {args.ticker_file}: {e}")
        return
    
    # Configure screening
    cfg = ScreenConfig(
        include_f_score=not args.no_f_score,
        min_f_score=args.min_f_score,
        f_score_weight=args.f_score_weight,
        momentum_weight=args.momentum_weight
    )
    
    # Run screening
    ranked = momentum_screen(
        universe, 
        cfg, 
        debug_ticker=args.debug_ticker, 
        start_date=start_date_adj, 
        end_date=end_date_adj, 
        use_cache=not args.no_cache, 
        force_refresh=args.force_refresh, 
        use_quarterly=args.use_quarterly
    )
    
    # Configure pandas to display all columns
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', None)
    pd.set_option('display.max_colwidth', None)
    
    # Show top N results
    if not ranked.empty:
        top_results = ranked.head(args.top_n)
        print(top_results)
        
        # Save results
        output_file = f"nordic_momentum_{end_date_adj.strftime('%Y%m%d')}.csv"
        ranked.to_csv(output_file)
        print(f"\nResults also saved to {output_file}")
    else:
        print("No results found.")

if __name__ == "__main__":
    main()