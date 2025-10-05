from __future__ import annotations
import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import Iterable, List, Optional, Literal
import yfinance as yf
from datetime import date, timedelta
import argparse
import os
import stat
import hashlib
import json
import time as time_module

# Import F-Score functionality
try:
    from fscore import calculate_f_score
    FSCORE_AVAILABLE = True
except ImportError:
    FSCORE_AVAILABLE = False
    print("Warning: fscore.py module not found. F-Score functionality disabled.")

NordicSuffix = Literal[".ST", ".CO", ".HE", ".OL", ".IC"]
SWEDEN_SUFFIX = ".ST"
NORWAY_SUFFIX = ".OL"
FINLAND_SUFFIX = ".HE"
DENMARK_SUFFIX = ".CO"
ICELAND_SUFFIX = ".IC"

# Cache configuration
CACHE_DIR = "cache"
DATA_CACHE_DAYS = 1  # Refresh cache if data is older than 1 day

def ensure_cache_dir():
    """Create cache directory if it doesn't exist."""
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR)

def generate_cache_key(tickers: List[str], start_date: str, end_date: str) -> str:
    """Generate a unique cache key for the given parameters."""
    # Sort tickers for consistent hashing
    ticker_str = "_".join(sorted(tickers))
    data_str = f"{ticker_str}_{start_date}_{end_date}"
    return hashlib.md5(data_str.encode()).hexdigest()

def is_cache_fresh(cache_file: str, max_age_days: int = DATA_CACHE_DAYS) -> bool:
    """Check if cache file is fresh enough."""
    if not os.path.exists(cache_file):
        return False
    
    # Simple check - just return True if file exists and is recent enough
    # For now, assume cache is fresh if it exists (can be enhanced later)
    return True

def save_to_cache(tickers: List[str], start_date: str, end_date: str, data: pd.DataFrame):
    """Save fetched data to cache."""
    ensure_cache_dir()
    
    cache_key = generate_cache_key(tickers, start_date, end_date)
    cache_file = os.path.join(CACHE_DIR, f"{cache_key}.csv")
    
    # Save metadata
    metadata = {
        "tickers": sorted(tickers),
        "start_date": start_date,
        "end_date": end_date,
        "data_shape": list(data.shape),
        "cached_at": time_module.time()
    }
    
    metadata_file = os.path.join(CACHE_DIR, f"{cache_key}_metadata.json")
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    # Save data as CSV for portability
    data.to_csv(cache_file)
    print(f"Cached data for {len(tickers)} tickers ({cache_file})")

def load_from_cache(tickers: List[str], start_date: str, end_date: str, force_refresh: bool = False) -> Optional[pd.DataFrame]:
    """Load data from cache if available and fresh."""
    ensure_cache_dir()
    
    cache_key = generate_cache_key(tickers, start_date, end_date)
    cache_file = os.path.join(CACHE_DIR, f"{cache_key}.csv")
    metadata_file = os.path.join(CACHE_DIR, f"{cache_key}_metadata.json")
    
    # Check if cache exists and is fresh
    if not force_refresh and is_cache_fresh(cache_file):
        try:
            data = pd.read_csv(cache_file, index_col=0, parse_dates=True)
            print(f"Loaded {len(data.columns)} tickers from cache ({cache_file})")
            return data
        except Exception as e:
            print(f"Cache load failed: {e}, fetching fresh data...")
    
    return None

@dataclass(frozen=True)
class ScreenConfig:
    months: tuple[int, int, int] = (3, 6, 12)
    min_history_months: int = 14        # small buffer beyond longest lookback
    price_col: str = "Adj Close"
    trading_days_per_month: int = 21
    require_positive_each: bool = False # set True to keep only if all 3 legs > 0
    top_n: Optional[int] = 25           # None = return all ranked
    
    # F-Score related settings
    include_f_score: bool = True         # Include F-Score in ranking
    f_score_weight: float = 0.3         # Weight for F-Score in composite score
    momentum_weight: float = 0.7         # Weight for momentum in composite score
    min_f_score: Optional[int] = None    # Minimum F-Score threshold (None = no filter)

def _months_to_days(m: int, days_per_month: int) -> int:
    return int(m * days_per_month)

def find_closest_trading_day(target_date: date, market: str = "NYSE") -> str:
    """
    Find the closest trading day for a given date.
    If the date falls on weekends or holidays, returns the closest weekday.
    """
    # For simplicity, we'll move weekend dates to Friday (if Saturday/Saturday)
    # This is a basic implementation - in production you'd want to use trading calendars
    if target_date.weekday() == 5:  # Saturday -> Friday
        target_date = target_date - timedelta(days=1)
    elif target_date.weekday() == 6:  # Sunday -> Monday (or Friday if Monday is also holiday)
        target_date = target_date - timedelta(days=2)
    
    return target_date.isoformat()

def fetch_prices(tickers: Iterable[str], start: Optional[str] = None, end: Optional[str] = None, use_cache: bool = True, force_refresh: bool = False) -> pd.DataFrame:
    if end is None:
        end = date.today().isoformat()
    if start is None:
        start = (date.today() - timedelta(days=450)).isoformat()
    
    ticker_list = list(tickers)
    
    # Try to load from cache first
    if use_cache:
        cached_data = load_from_cache(ticker_list, start, end, force_refresh)
        if cached_data is not None:
            return cached_data
    
    # Fetch fresh data from Yahoo Finance
    print(f"Fetching fresh data for {len(ticker_list)} tickers from {start} to {end}")
    
    # Yahoo Finance excludes the end date, so add 1 day to include it
    end_actual = (date.fromisoformat(end) + timedelta(days=1)).isoformat()
    
    data = yf.download(ticker_list, start=start, end=end_actual, auto_adjust=False, progress=False, group_by="ticker", threads=True)
    
    # Extract price data and transpose to (date x ticker)
    if isinstance(data.columns, pd.MultiIndex):
        # MultiIndex case: stack tickers into index and select Adj Close
        px = data.stack(level=0, future_stack=True)
        # Select the Adj Close column and unstack to get tickers as columns
        adj_close_col = "Adj Close" if "Adj Close" in data.columns.levels[1] else "Close"
        px = px[adj_close_col].unstack()
    else:
        # Single ticker case
        adj_close_col = "Adj Close" if "Adj Close" in data.columns else "Close"
        px = data[adj_close_col].to_frame()
        px.columns = list(tickers)
    
    result = px.sort_index()
    
    # Save to cache if we fetched fresh data
    if use_cache:
        save_to_cache(ticker_list, start, end, result)
    
    return result

def momentum_screen(
    tickers: Iterable[str],
    config: ScreenConfig = ScreenConfig(),
    restrict_suffixes: Optional[Iterable[NordicSuffix]] = (".ST", ".CO", ".HE", ".OL", ".IC"),
    debug_ticker: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    use_cache: bool = True,
    force_refresh: bool = False,
    use_quarterly: bool = False,
) -> pd.DataFrame:
    tickers = list(dict.fromkeys(tickers))
    if restrict_suffixes:
        tickers = [t for t in tickers if any(t.endswith(s) for s in restrict_suffixes)]
    px = fetch_prices(tickers, start=start_date, end=end_date, use_cache=use_cache, force_refresh=force_refresh)
    px = px.ffill().dropna(axis=1, how="any")  # drop tickers with missing history

    # Debug output for specific ticker
    if debug_ticker and debug_ticker in px.columns:
        print(f"\nDEBUG: {debug_ticker} calculation details:")
        print(f"Date range: {px.index[0].date()} to {px.index[-1].date()}")
        print(f"Total trading days: {len(px)}")
        print(f"Latest price: {px[debug_ticker].iloc[-1]:.2f}")

    # Compute total returns and prices for each horizon using business-day offsets
    days = [ _months_to_days(m, config.trading_days_per_month) for m in config.months ]
    rets = {}
    prices = {}
    
    for m, d in zip(config.months, days):
        # Only calculate returns if we have enough data
        if len(px) > d:
            rets[m] = px.pct_change(d).iloc[-1]  # last available point
            prices[f"price_{m}m"] = px.iloc[-1-d]  # price d days ago
        else:
            print(f"Warning: Not enough data for {m}-month calculation (need {d} days, have {len(px)})")
            # Skip this calculation - will result in NaN, which gets filtered out
            rets[m] = pd.Series([np.nan] * len(px.columns), index=px.columns)
            prices[f"price_{m}m"] = px.iloc[0]  # fallback to first available
        
        # Debug output for specific ticker
        if debug_ticker and debug_ticker in px.columns:
            end_date = px.index[-1].date()
            start_date = px.index[-1-d].date() if len(px) > d else px.index[0].date()
            end_price = px[debug_ticker].iloc[-1]
            start_price = px[debug_ticker].iloc[-1-d] if len(px) > d else px[debug_ticker].iloc[0]
            return_pct = (end_price / start_price) - 1
            print(f"{m}-month: {start_date} to {end_date} ({d} days): {start_price:.2f} → {end_price:.2f} = {return_pct*100:.1f}%")

    df = pd.DataFrame(rets)
    df.columns = [f"ret_{m}m" for m in config.months]
    df["mom_score"] = df.mean(axis=1)
    
    # Add current and historical prices
    df["price_today"] = px.iloc[-1]
    for key, series in prices.items():
        df[key] = series

    # Add F-Score if enabled and available
    if config.include_f_score and FSCORE_AVAILABLE:
        print("Calculating F-Scores for momentum screening...")
        f_scores = []
        for ticker in df.index:
            try:
                f_score_result = calculate_f_score(ticker, use_quarterly=use_quarterly)
                f_scores.append(f_score_result['total_f_score'])
            except Exception as e:
                print(f"Warning: Could not calculate F-Score for {ticker}: {e}")
                f_scores.append(0)
        
        df["f_score"] = f_scores
        
        # Apply minimum F-Score filter if specified
        if config.min_f_score is not None:
            df = df[df["f_score"] >= config.min_f_score]
            print(f"Filtered to stocks with F-Score >= {config.min_f_score}")
        
        # Calculate composite score (momentum + F-Score)
        # Normalize F-Score to 0-1 range (0-9 scale)
        normalized_f_score = df["f_score"] / 9.0
        
        # Normalize momentum score to similar range
        # This assumes momentum scores are already in percentage form
        if df["mom_score"].max() > 10:  # If in percentage form
            normalized_momentum = df["mom_score"] / 100.0
        else:
            normalized_momentum = df["mom_score"]
        
        # Weighted combination
        df["quality_momentum"] = (
            config.momentum_weight * normalized_momentum + 
            config.f_score_weight * normalized_f_score
        ) * 100  # Convert back to percentage-ish scale
        
        # Sort by composite score
        df = df.sort_values("quality_momentum", ascending=False)
        print(f"Ranked by Quality-Momentum composite score ({config.momentum_weight:.1f}/0.3)")
    else:
        if config.include_f_score and not FSCORE_AVAILABLE:
            print("Warning: F-Score requested but fscore.py module not available")
        df = df.sort_values("mom_score", ascending=False)

    if config.require_positive_each:
        mask = (df[[c for c in df.columns if c.startswith("ret_")]] > 0).all(axis=1)
        df = df[mask]

    df = df.replace([np.inf, -np.inf], np.nan).dropna()

    if config.top_n:
        df = df.head(config.top_n)

    # Format the output: convert returns to % and price columns to currency
    result = df.copy()
    
    # Format return columns as percentages
    ret_cols = [c for c in df.columns if c.startswith("ret_")]
    for col in ret_cols:
        result[col] = (result[col] * 100).round(1)
    
    # Format momentum score as percentage
    result["mom_score"] = (result["mom_score"] * 100).round(1)
    
    # Format price columns to 2 decimal places
    price_cols = ["price_today"] + [c for c in df.columns if c.startswith("price_")]
    for col in price_cols:
        result[col] = result[col].round(2)
    
    return result

def load_tickers_from_csv(filepath: str) -> List[str]:
    """
    Load ticker symbols from a CSV file.
    
    CSV format can be:
    - Simple: just ticker symbols (one per row, first column)
    - Structured: header row with 'ticker', optional 'sector', 'market_cap_threshold' columns
    
    Args:
        filepath: Path to CSV file
        
    Returns:
        List of ticker symbols
    """
    try:
        import pandas as pd
        
        # Try to read CSV
        df = pd.read_csv(filepath)
        
        # Handle different CSV formats
        if 'ticker' in df.columns:
            # Structured format with header
            tickers = df['ticker'].dropna().tolist()
        else:
            # Simple format - first column as tickers
            tickers = df.iloc[:, 0].dropna().tolist()
        
        # Clean up tickers (remove whitespace, empty strings)
        tickers = [str(t).strip() for t in tickers if str(t).strip()]
        
        print(f"Loaded {len(tickers)} tickers from {filepath}")
        if len(tickers) < 5:  # Show all if small list
            print(f"Tickers: {', '.join(tickers)}")
        else:  # Show first few if large list
            print(f"Tickers: {', '.join(tickers[:5])}... ({len(tickers)} total)")
        
        return tickers
        
    except FileNotFoundError:
        raise FileNotFoundError(f"Ticker file not found: {filepath}")
    except Exception as e:
        raise ValueError(f"Error reading ticker file {filepath}: {e}")

def parse_date(date_string: str) -> date:
    """Parse date string in YYYY-MM-DD format."""
    try:
        return date.fromisoformat(date_string)
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid date format: {date_string}. Use YYYY-MM-DD")

def main():
    parser = argparse.ArgumentParser(description="Nordic Stock Momentum Screener")
    parser.add_argument(
        "--start-date", 
        type=str,
        default=None,
        help="Start date for data fetching (YYYY-MM-DD). Default: 1 year ago"
    )
    parser.add_argument(
        "--end-date",
        type=str, 
        default=None,
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
        default="tickers.csv",
        help="CSV file containing ticker symbols to analyze (default: tickers.csv)"
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
    start_date_adj = find_closest_trading_day(start_date)
    end_date_adj = find_closest_trading_day(end_date)
    
    print(f"Momentum screening from {start_date_adj} to {end_date_adj}")
    
    # Load ticker universe from file
    try:
        universe = load_tickers_from_csv(args.ticker_file)
    except (FileNotFoundError, ValueError) as e:
        print(f"❌ Error: {e}")
        print("\nCreating default tickers.csv file with Nordic universe...")
        # Create default file and use fallback list
        import pandas as pd
        default_tickers = [
            # Sweden
            "VOLV-B.ST","EVO.ST","ERIC-B.ST","NDA-SE.ST","TELIA.ST","SAND.ST","ASSA-B.ST","ATCO-A.ST","ATCO-B.ST",
            # Norway
            "EQNR.OL","ORK.OL","NHY.OL","YAR.OL",
            # Finland
            "NOKIA.HE","KNEBV.HE","FORTUM.HE",
            # Denmark
            "MAERSK-B.CO","CARL-B.CO","NOVO-B.CO","DSV.CO",
        ]
        
        # Save default file
        df = pd.DataFrame({'ticker': default_tickers})
        df.to_csv("tickers.csv", index=False)
        print("Created tickers.csv with default Nordic universe")
        
        universe = default_tickers
    
    cfg = ScreenConfig(
        months=(3,6,12), 
        require_positive_each=False, 
        top_n=args.top_n,
        include_f_score=not args.no_f_score,
        min_f_score=args.min_f_score,
        f_score_weight=args.f_score_weight,
        momentum_weight=args.momentum_weight
    )
    ranked = momentum_screen(universe, cfg, debug_ticker=args.debug_ticker, start_date=start_date_adj, end_date=end_date_adj, use_cache=not args.no_cache, force_refresh=args.force_refresh, use_quarterly=args.use_quarterly)
    
    # Configure pandas to display all columns
    import pandas as pd
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', None)
    pd.set_option('display.max_colwidth', None)
    
    print(ranked)
    
    # Optional: save to CSV
    if args.debug_ticker:
        filename = f"nordic_momentum_{end_date_adj.replace('-', '')}.csv"
        print(f"\nResults also saved to {filename}")
        ranked.to_csv(filename)

if __name__ == "__main__":
    main()
