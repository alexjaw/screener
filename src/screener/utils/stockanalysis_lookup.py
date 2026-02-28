"""Resolve company names to stockanalysis.com tickers and URLs.

This module fetches stock lists from stockanalysis.com (e.g. Nasdaq Stockholm)
and supports searching by company name to get the correct ticker and page URL.
Used by the F-Score CLI when the user passes a company name instead of a ticker.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import Optional

import requests
from bs4 import BeautifulSoup

# Exchange list pages we scrape to resolve company names (path relative to stockanalysis.com)
EXCHANGE_LISTS = {
    "STO": "https://stockanalysis.com/list/nasdaq-stockholm/",
    # Add more as needed: "US": "https://stockanalysis.com/stocks/", ...
}

# Cache: exchange -> list of (symbol, company_name); cleared on first load per exchange
_list_cache: dict[str, list[tuple[str, str]]] = {}
_cache_ts: dict[str, float] = {}
CACHE_TTL_SEC = 3600  # 1 hour

# Request session with a browser-like User-Agent
_session: Optional[requests.Session] = None


def _session_get() -> requests.Session:
    global _session
    if _session is None:
        _session = requests.Session()
        _session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            )
        })
    return _session


@dataclass
class StockAnalysisMatch:
    """A single match from stockanalysis.com search."""

    symbol: str
    name: str
    url: str
    exchange: str

    def financials_url(self) -> str:
        """URL to the financials page (for scraping)."""
        if self.exchange == "STO":
            return f"https://stockanalysis.com/quote/sto/{self.symbol}/financials/"
        return f"https://stockanalysis.com/stocks/{self.symbol}/financials/"


def _fetch_exchange_list(exchange: str) -> list[tuple[str, str]]:
    """Fetch and parse the stock list for an exchange. Returns [(symbol, company_name), ...]."""
    url = EXCHANGE_LISTS.get(exchange)
    if not url:
        return []

    resp = _session_get().get(url, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "lxml")

    rows: list[tuple[str, str]] = []
    for table in soup.find_all("table"):
        for tr in table.find_all("tr")[1:]:  # skip header
            cells = tr.find_all(["td", "th"])
            if len(cells) < 3:
                continue
            symbol = ""
            name = ""
            # STO list: col0=No, col1=Symbol (link), col2=Company Name
            for idx, cell in enumerate(cells):
                a = cell.find("a", href=True)
                if a:
                    href = a.get("href") or ""
                    if "/quote/sto/" in href:
                        m = re.search(r"/quote/sto/([^/]+)/?", href)
                        if m:
                            symbol = m.group(1)
                    elif "/stocks/" in href:
                        m = re.search(r"/stocks/([^/]+)/?", href)
                        if m:
                            symbol = m.group(1)
                if not name and idx == 2:
                    name = (cell.get_text() or "").strip()
            if not name and len(cells) > 2:
                name = (cells[2].get_text() or "").strip()
            if symbol:
                rows.append((symbol, name or ""))

    return rows


def _get_cached_list(exchange: str) -> list[tuple[str, str]]:
    """Return cached list for exchange; fetch and cache if missing or stale."""
    now = time.time()
    if exchange not in _list_cache or (now - _cache_ts.get(exchange, 0)) > CACHE_TTL_SEC:
        _list_cache[exchange] = _fetch_exchange_list(exchange)
        _cache_ts[exchange] = now
    return _list_cache[exchange]


def _normalize_query(q: str) -> str:
    """Normalize for fuzzy matching: lowercase, collapse spaces, remove common suffixes."""
    s = (q or "").lower().strip()
    s = re.sub(r"\s+", " ", s)
    for suffix in [" ab", " ab (publ)", " (publ)", " holding", " group", " inc", " inc.", " plc", " corp", " corporation"]:
        if s.endswith(suffix):
            s = s[: -len(suffix)].strip()
    return s


def _score_match(query_norm: str, name: str, symbol: str) -> float:
    """Higher = better match. Prefer exact and prefix matches."""
    if not name:
        return 0.0
    name_norm = _normalize_query(name)
    symbol_lower = (symbol or "").lower()
    # Exact match on symbol
    if query_norm == symbol_lower:
        return 100.0
    # Query equals normalized name
    if query_norm == name_norm:
        return 95.0
    # Name or symbol starts with query
    if name_norm.startswith(query_norm) or symbol_lower.startswith(query_norm):
        return 90.0 - len(query_norm) * 0.1
    # Query in name or symbol
    if query_norm in name_norm:
        return 70.0 - name_norm.index(query_norm) * 0.1
    if query_norm in symbol_lower:
        return 65.0
    # Word overlap
    q_words = set(query_norm.split())
    n_words = set(name_norm.split())
    overlap = len(q_words & n_words) / max(len(q_words), 1)
    return overlap * 50.0


def get_stockanalysis_url(ticker: str, exchange: str = "STO") -> str:
    """Return the main stockanalysis.com page URL for a ticker."""
    ticker = (ticker or "").strip()
    if not ticker:
        return ""
    if exchange == "STO":
        return f"https://stockanalysis.com/quote/sto/{ticker}/"
    return f"https://stockanalysis.com/stocks/{ticker}/"


def search_stockanalysis(
    query: str,
    *,
    exchanges: Optional[list[str]] = None,
    max_results: int = 20,
) -> list[StockAnalysisMatch]:
    """Search stockanalysis.com by company name or ticker; return best matches.

    Parameters
    ----------
    query : str
        Company name or ticker (e.g. "nordrest", "Nordrest Holding", "NREST").
    exchanges : list of str, optional
        Exchanges to search. Defaults to ["STO"] (Nasdaq Stockholm).
    max_results : int
        Maximum number of matches to return.

    Returns
    -------
    list of StockAnalysisMatch
        Matches with symbol, name, url, exchange; sorted by relevance.
    """
    if not (query or "").strip():
        return []
    exchanges = exchanges or ["STO"]
    query_norm = _normalize_query(query)

    candidates: list[tuple[float, StockAnalysisMatch]] = []
    for exchange in exchanges:
        for symbol, name in _get_cached_list(exchange):
            score = _score_match(query_norm, name, symbol)
            if score <= 0:
                continue
            url = get_stockanalysis_url(symbol, exchange)
            candidates.append((score, StockAnalysisMatch(symbol=symbol, name=name, url=url, exchange=exchange)))

    candidates.sort(key=lambda x: (-x[0], x[1].name))
    return [m for _, m in candidates[:max_results]]


def find_ticker_stockanalysis(
    company_name: str,
    *,
    exchanges: Optional[list[str]] = None,
) -> Optional[StockAnalysisMatch]:
    """Return the single best stockanalysis.com match for a company name, or None."""
    matches = search_stockanalysis(company_name, exchanges=exchanges, max_results=1)
    return matches[0] if matches else None


def clear_cache() -> None:
    """Clear the in-memory list cache (e.g. for tests)."""
    global _list_cache, _cache_ts
    _list_cache = {}
    _cache_ts = {}
