"""Core momentum screening logic."""

from __future__ import annotations
import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import Iterable, List, Optional, Literal
import yfinance as yf
from datetime import date, timedelta
import os
import hashlib
import json
import time as time_module

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
    
    cache_time = os.path.getmtime(cache_file)
    age_days = (time_module.time() - cache_time) / (24 * 3600)
    return age_days < max_age_days

def load_from_cache(cache_file: str) -> Optional[pd.DataFrame]:
    """Load data from cache if available and fresh."""
    if not is_cache_fresh(cache_file):
        return None
    
    try:
        return pd.read_csv(cache_file, index_col=0, parse_dates=True)
    except (FileNotFoundError, pd.errors.EmptyDataError):
        return None

def save_to_cache(tickers: List[str], start_date: str, end_date: str, data: pd.DataFrame):
    """Save data to cache."""
    ensure_cache_dir()
    cache_key = generate_cache_key(tickers, start_date, end_date)
    cache_file = os.path.join(CACHE_DIR, f"{cache_key}.csv")
    metadata_file = os.path.join(CACHE_DIR, f"{cache_key}_metadata.json")
    
    # Save data
    data.to_csv(cache_file)
    
    # Save metadata
    metadata = {
        'tickers': tickers,
        'start_date': str(start_date),
        'end_date': str(end_date),
        'cached_at': time_module.time(),
        'shape': list(data.shape)
    }
    
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)

def fetch_prices(tickers: List[str], start: str, end: str, use_cache: bool = True, force_refresh: bool = False) -> pd.DataFrame:
    """Fetch price data for multiple tickers."""
    if use_cache and not force_refresh:
        cache_key = generate_cache_key(tickers, start, end)
        cache_file = os.path.join(CACHE_DIR, f"{cache_key}.csv")
        cached_data = load_from_cache(cache_file)
        if cached_data is not None:
            print(f"Cached data for {len(tickers)} tickers ({start} to {end})")
            return cached_data
    
    print(f"Fetching fresh data for {len(tickers)} tickers from {start} to {end}")
    
    # Fetch data
    data = yf.download(tickers, start=start, end=end, group_by='ticker')
    
    # Handle single ticker case
    if len(tickers) == 1:
        ticker = tickers[0]
        if isinstance(data.columns, pd.MultiIndex):
            # Multi-level columns case
            if ticker in data.columns.levels[0]:
                # Use 'Close' instead of 'Adj Close' since yfinance now uses auto_adjust=True by default
                data = data[ticker]['Close'].to_frame()
                data.columns = [ticker]
            else:
                print(f"Warning: No data found for {ticker}")
                data = pd.DataFrame()
        else:
            # Single level columns case
            if 'Close' in data.columns:
                data = data[['Close']].copy()
                data.columns = [ticker]
            else:
                print(f"Warning: No Close data found for {ticker}")
                data = pd.DataFrame()
    else:
        # Multi-ticker case - extract Close
        close_data = {}
        for ticker in tickers:
            if isinstance(data.columns, pd.MultiIndex):
                if ticker in data.columns.levels[0]:
                    close_data[ticker] = data[ticker]['Close']
                else:
                    print(f"Warning: No data found for {ticker}")
            else:
                # Single ticker case but multiple tickers requested
                if ticker in data.columns:
                    close_data[ticker] = data[ticker]
                else:
                    print(f"Warning: No data found for {ticker}")
        
        if close_data:
            data = pd.DataFrame(close_data)
        else:
            data = pd.DataFrame()
    
    # Cache the result
    if use_cache:
        save_to_cache(tickers, start, end, data)
    
    return data

def find_closest_trading_day(target_date: date) -> date:
    """Find the closest trading day to the target date."""
    # Simple implementation - just return the target date
    # In a production system, you might want to check actual trading calendars
    return target_date

@dataclass
class ScreenConfig:
    """Configuration for momentum screening."""
    include_f_score: bool = True
    min_f_score: Optional[int] = None
    f_score_weight: float = 0.3
    momentum_weight: float = 0.7

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
    """Perform momentum screening on a list of tickers."""
    tickers = list(dict.fromkeys(tickers))
    if restrict_suffixes:
        tickers = [t for t in tickers if any(t.endswith(s) for s in restrict_suffixes)]
    
    px = fetch_prices(tickers, start=start_date, end=end_date, use_cache=use_cache, force_refresh=force_refresh)
    px = px.ffill().dropna(axis=1, how="any")  # drop tickers with missing history
    
    if px.empty:
        return pd.DataFrame()
    
    # Calculate returns
    ret_3m = ((px.iloc[-1] / px.iloc[-63] - 1) * 100).round(1)
    ret_6m = ((px.iloc[-1] / px.iloc[-126] - 1) * 100).round(1)
    ret_12m = ((px.iloc[-1] / px.iloc[-252] - 1) * 100).round(1)
    
    # Calculate momentum score (weighted average)
    momentum_score = (ret_3m * 0.5 + ret_6m * 0.3 + ret_12m * 0.2).round(1)
    
    # Create results DataFrame
    df = pd.DataFrame({
        'ret_3m': ret_3m,
        'ret_6m': ret_6m,
        'ret_12m': ret_12m,
        'mom_score': momentum_score,
        'price_today': px.iloc[-1].round(2),
        'price_3m': px.iloc[-63].round(2),
        'price_6m': px.iloc[-126].round(2),
        'price_12m': px.iloc[-252].round(2),
    })
    
    # Debug information
    if debug_ticker and debug_ticker in df.index:
        print(f"\nDEBUG: {debug_ticker} calculation details:")
        print(f"Date range: {start_date} to {end_date}")
        print(f"Total trading days: {len(px)}")
        print(f"Latest price: {px.iloc[-1][debug_ticker]:.2f}")
        print(f"3-month: {px.index[-63]} to {px.index[-1]} ({len(px)-63} days): {px.iloc[-63][debug_ticker]:.2f} → {px.iloc[-1][debug_ticker]:.2f} = {ret_3m[debug_ticker]:.1f}%")
        print(f"6-month: {px.index[-126]} to {px.index[-1]} ({len(px)-126} days): {px.iloc[-126][debug_ticker]:.2f} → {px.iloc[-1][debug_ticker]:.2f} = {ret_6m[debug_ticker]:.1f}%")
        print(f"12-month: {px.index[-252]} to {px.index[-1]} ({len(px)-252} days): {px.iloc[-252][debug_ticker]:.2f} → {px.iloc[-1][debug_ticker]:.2f} = {ret_12m[debug_ticker]:.1f}%")
    
    # Add F-Score if enabled
    if config.include_f_score:
        try:
            from ..analysis.fscore_calculator import score_company
            print("Calculating F-Scores for momentum screening...")
            f_scores = []
            for ticker in df.index:
                try:
                    f_score_result = score_company(ticker, use_quarterly=use_quarterly)
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
            df["quality_momentum"] = (
                df["mom_score"] * config.momentum_weight + 
                df["f_score"] * config.f_score_weight * 10  # Scale F-Score to 0-10 range
            ).round(6)
            
            # Sort by composite score
            df = df.sort_values("quality_momentum", ascending=False)
            print(f"Ranked by Quality-Momentum composite score ({config.momentum_weight}/{config.f_score_weight})")
            
        except ImportError:
            print("Warning: F-Score calculation not available")
            df = df.sort_values("mom_score", ascending=False)
            print("Ranked by momentum score only")
    else:
        df = df.sort_values("mom_score", ascending=False)
        print("Ranked by momentum score only")
    
    return df
