from __future__ import annotations
"""
AURUM Data Fetcher
===================
Pulls all market data needed by the system from Yahoo Finance.
No API keys required. Free tier is sufficient for daily data.

Returns a standardized DataBundle that every module can consume.
"""

import yfinance as yf
import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional


# Yahoo Finance tickers for our universe
TICKER_MAP = {
    # Precious metals
    'GC1': 'GC=F',       # Gold futures
    'SI1': 'SI=F',       # Silver futures
    'PL1': 'PL=F',       # Platinum futures
    'PA1': 'PA=F',       # Palladium futures
    # Industrial metals
    'HG1': 'HG=F',       # Copper futures
    # No aluminum futures on Yahoo — use AA (Alcoa) as rough proxy
    # Equities / ETFs
    'GLD': 'GLD',         # Gold ETF
    'SLV': 'SLV',         # Silver ETF
    'GDX': 'GDX',         # Gold miners
    'NEM': 'NEM',         # Newmont
    'AEM': 'AEM',         # Agnico Eagle
    'GOLD': 'GOLD',       # Barrick
    'COPX': 'COPX',       # Copper miners
    'FCX': 'FCX',         # Freeport-McMoRan
    'RIO': 'RIO',         # Rio Tinto
    'URA': 'URA',         # Uranium ETF
    'LIT': 'LIT',         # Lithium ETF
    'MP': 'MP',           # Rare earth
    # Macro
    'ES1': 'ES=F',        # S&P 500 futures
    'VIX': '^VIX',        # VIX Index (spot)
    'VXX': 'VXX',         # VIX ETN (futures-based)
    'DXY': 'DX-Y.NYB',   # US Dollar Index
}


@dataclass
class DataBundle:
    """Standardized data package consumed by all modules."""
    timestamp: str
    prices: dict[str, float]              # Current/latest close prices
    returns_1d: dict[str, float]          # 1-day return
    returns_5d: dict[str, float]          # 5-day return
    returns_21d: dict[str, float]         # 21-day return
    above_50d_ma: dict[str, bool]         # Price > 50-day MA
    at_20d_high: dict[str, bool]          # Price at 20-day high
    vix: float
    vxx: float  # VIX ETN (futures-based)
    gold_price: float
    silver_price: float
    copper_price: float
    gold_silver_ratio: float
    gold_copper_ratio: float
    gold_rv_21d: float                    # Gold 21-day realized vol (annualized)
    gold_rv_5d: float                     # Gold 5-day realized vol
    gold_rv_percentile: float             # Percentile vs trailing 252 days
    gold_friday_return: float             # Today's gold return (if Friday)
    gold_volume_zscore: float             # Volume z-score
    history: pd.DataFrame                 # Full price history for backtesting
    errors: list[str] = field(default_factory=list)


def fetch_data(lookback_days: int = 365, date: Optional[str] = None) -> DataBundle:
    """
    Fetch all required market data.

    Args:
        lookback_days: How much history to pull (default 1 year)
        date: Optional specific date to evaluate (for backtesting).
              If None, uses most recent available data.

    Returns:
        DataBundle with all computed features
    """
    errors = []
    end_date = datetime.now()
    start_date = end_date - timedelta(days=lookback_days + 60)  # Extra buffer

    # Pull all tickers at once for efficiency
    tickers_to_fetch = list(TICKER_MAP.values())
    print(f"  Fetching {len(tickers_to_fetch)} instruments from Yahoo Finance...")

    try:
        # Use period='1y' to get most recent data including today
        raw = yf.download(
            tickers_to_fetch,
            period='1y',
            progress=False,
            auto_adjust=True,
        )
    except Exception as e:
        errors.append(f"Yahoo Finance download failed: {e}")
        return _empty_bundle(errors)

    # Also fetch current real-time quotes for key tickers
    realtime_prices = {}
    for key, ticker in [('GLD', 'GLD'), ('SLV', 'SLV'), ('VIX', '^VIX'), ('VXX', 'VXX')]:
        try:
            t = yf.Ticker(ticker)
            info = t.fast_info
            if hasattr(info, 'last_price') and info.last_price:
                realtime_prices[key] = float(info.last_price)
        except:
            pass

    # Handle single vs multi-ticker download format
    if isinstance(raw.columns, pd.MultiIndex):
        close = raw['Close']
        volume = raw['Volume']
    else:
        close = raw[['Close']].rename(columns={'Close': tickers_to_fetch[0]})
        volume = raw[['Volume']].rename(columns={'Volume': tickers_to_fetch[0]})

    # If evaluating a specific date, truncate
    if date:
        target = pd.Timestamp(date)
        close = close.loc[:target]
        volume = volume.loc[:target]

    if close.empty:
        errors.append("No data returned from Yahoo Finance")
        return _empty_bundle(errors)

    # Reverse map: Yahoo ticker → our ticker
    reverse_map = {v: k for k, v in TICKER_MAP.items()}

    # Rename columns to our internal names
    close_renamed = close.rename(columns=reverse_map)
    volume_renamed = volume.rename(columns=reverse_map)

    # Latest row
    latest = close_renamed.iloc[-1]
    latest_vol = volume_renamed.iloc[-1] if not volume_renamed.empty else pd.Series()

    # Compute returns
    def safe_return(series, periods):
        if len(series) < periods + 1:
            return np.nan
        return (series.iloc[-1] / series.iloc[-periods - 1]) - 1

    prices = {}
    returns_1d = {}
    returns_5d = {}
    returns_21d = {}
    above_50d_ma = {}
    at_20d_high = {}

    for col in close_renamed.columns:
        series = close_renamed[col].dropna()
        if len(series) < 2:
            errors.append(f"Insufficient data for {col}")
            continue

        prices[col] = float(series.iloc[-1])
        returns_1d[col] = safe_return(series, 1)
        returns_5d[col] = safe_return(series, 5)
        returns_21d[col] = safe_return(series, 21)

        # 50-day MA
        if len(series) >= 50:
            ma50 = series.rolling(50).mean().iloc[-1]
            above_50d_ma[col] = bool(series.iloc[-1] > ma50)
        else:
            above_50d_ma[col] = False

        # 20-day high
        if len(series) >= 20:
            high_20d = series.rolling(20).max().iloc[-1]
            at_20d_high[col] = bool(series.iloc[-1] >= high_20d * 0.998)  # Within 0.2%
        else:
            at_20d_high[col] = False

    # Gold-specific features
    gc_series = close_renamed.get('GC1', pd.Series(dtype=float)).dropna()
    # Use realtime prices if available, otherwise fall back to historical
    gold_price = realtime_prices.get('GLD', prices.get('GLD', prices.get('GC1', 0)))
    silver_price = realtime_prices.get('SLV', prices.get('SLV', prices.get('SI1', 0)))
    copper_price = prices.get('HG1', 0)

    # Ratios
    gold_silver_ratio = gold_price / silver_price if silver_price > 0 else 0
    gold_copper_ratio = gold_price / copper_price if copper_price > 0 else 0

    # Gold realized vol
    if len(gc_series) >= 22:
        gc_log_returns = np.log(gc_series / gc_series.shift(1)).dropna()
        gold_rv_21d = float(gc_log_returns.iloc[-21:].std() * np.sqrt(252) * 100)
        gold_rv_5d = float(gc_log_returns.iloc[-5:].std() * np.sqrt(252) * 100)

        # Percentile of 21d RV vs trailing year
        rv_series = gc_log_returns.rolling(21).std() * np.sqrt(252) * 100
        rv_series = rv_series.dropna()
        if len(rv_series) > 20:
            current_rv = rv_series.iloc[-1]
            gold_rv_percentile = float((rv_series < current_rv).sum() / len(rv_series) * 100)
        else:
            gold_rv_percentile = 50.0
    else:
        gold_rv_21d = 0
        gold_rv_5d = 0
        gold_rv_percentile = 50.0

    # Gold Friday return (latest day)
    gold_friday_return = returns_1d.get('GC1', returns_1d.get('GLD', 0))
    if gold_friday_return is None or np.isnan(gold_friday_return):
        gold_friday_return = 0.0

    # Gold volume z-score
    gc_vol_series = volume_renamed.get('GC1', pd.Series(dtype=float)).dropna()
    if len(gc_vol_series) >= 21:
        vol_mean = gc_vol_series.iloc[-21:].mean()
        vol_std = gc_vol_series.iloc[-21:].std()
        if vol_std > 0:
            gold_volume_zscore = float((gc_vol_series.iloc[-1] - vol_mean) / vol_std)
        else:
            gold_volume_zscore = 0.0
    else:
        gold_volume_zscore = 0.0

    vix = realtime_prices.get('VIX', prices.get('VIX', 15.0))
    vxx = realtime_prices.get('VXX', prices.get('VXX', 0))

    # Use current timestamp if we have realtime prices, otherwise use last data point
    if realtime_prices:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
    else:
        timestamp = str(close_renamed.index[-1].date()) if not close_renamed.empty else str(datetime.now().date())

    return DataBundle(
        timestamp=timestamp,
        prices=prices,
        returns_1d=returns_1d,
        returns_5d=returns_5d,
        returns_21d=returns_21d,
        above_50d_ma=above_50d_ma,
        at_20d_high=at_20d_high,
        vix=vix,
        vxx=vxx,
        gold_price=gold_price,
        silver_price=silver_price,
        copper_price=copper_price,
        gold_silver_ratio=gold_silver_ratio,
        gold_copper_ratio=gold_copper_ratio,
        gold_rv_21d=gold_rv_21d,
        gold_rv_5d=gold_rv_5d,
        gold_rv_percentile=gold_rv_percentile,
        gold_friday_return=gold_friday_return,
        gold_volume_zscore=gold_volume_zscore,
        history=close_renamed,
        errors=errors,
    )


def _empty_bundle(errors: list[str]) -> DataBundle:
    """Return an empty data bundle when fetch fails."""
    return DataBundle(
        timestamp=str(datetime.now().date()),
        prices={}, returns_1d={}, returns_5d={}, returns_21d={},
        above_50d_ma={}, at_20d_high={},
        vix=0, vxx=0, gold_price=0, silver_price=0, copper_price=0,
        gold_silver_ratio=0, gold_copper_ratio=0,
        gold_rv_21d=0, gold_rv_5d=0, gold_rv_percentile=50,
        gold_friday_return=0, gold_volume_zscore=0,
        history=pd.DataFrame(),
        errors=errors,
    )


def generate_demo_data() -> DataBundle:
    """Generate simulated data for demo mode (no internet needed)."""
    import random
    random.seed(42)

    prices = {
        'GC1': 2935.40, 'SI1': 33.12, 'HG1': 4.52, 'PL1': 1015.30,
        'PA1': 985.60, 'GLD': 270.15, 'GDX': 38.90, 'NEM': 42.75,
        'AEM': 78.20, 'GOLD': 18.45, 'COPX': 25.30, 'FCX': 44.80,
        'RIO': 67.50, 'URA': 28.40, 'LIT': 42.10, 'MP': 18.90,
        'ES1': 6050.0, 'VIX': 19.8, 'DXY': 104.2,
    }

    returns_1d = {k: random.gauss(0.002, 0.01) for k in prices}
    returns_1d['GC1'] = 0.012  # Gold up 1.2% today (moderately strong)
    returns_1d['VIX'] = 0.08   # VIX up 8%

    returns_5d = {k: random.gauss(0.005, 0.02) for k in prices}
    returns_5d['GC1'] = 0.025  # Gold up 2.5% this week

    returns_21d = {k: random.gauss(0.01, 0.04) for k in prices}
    returns_21d['GC1'] = 0.045
    returns_21d['SI1'] = 0.022
    returns_21d['HG1'] = -0.015

    above_50d = {k: random.random() > 0.4 for k in prices}
    above_50d['GC1'] = True
    above_50d['SI1'] = True

    at_20d = {k: random.random() > 0.7 for k in prices}
    at_20d['GC1'] = True

    return DataBundle(
        timestamp="2026-02-13 (DEMO)",
        prices=prices,
        returns_1d=returns_1d,
        returns_5d=returns_5d,
        returns_21d=returns_21d,
        above_50d_ma=above_50d,
        at_20d_high=at_20d,
        vix=19.8,
        vxx=65.0,
        gold_price=2935.40,
        silver_price=33.12,
        copper_price=4.52,
        gold_silver_ratio=88.6,
        gold_copper_ratio=649.4,
        gold_rv_21d=18.5,
        gold_rv_5d=22.3,
        gold_rv_percentile=62.0,
        gold_friday_return=0.012,
        gold_volume_zscore=1.4,
        history=pd.DataFrame(),
        errors=["DEMO MODE — simulated data, not real market prices"],
    )
