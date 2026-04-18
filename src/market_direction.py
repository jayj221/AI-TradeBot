import yfinance as yf
import pandas as pd
from fredapi import Fred
from config import FRED_API_KEY, VIX_HIGH_THRESHOLD

_fred = None


def _get_fred():
    global _fred
    if _fred is None:
        _fred = Fred(api_key=FRED_API_KEY)
    return _fred


def classify_market() -> dict:
    spy = yf.Ticker("SPY").history(period="6mo")
    if spy.empty:
        return {
            "classification": "CORRECTION",
            "above_sma50": False, "above_sma200": False,
            "distribution_days": 0, "follow_through_day": False,
            "vix": 20.0, "vix_elevated": False,
            "yield_spread_10y2y": None, "allow_new_buys": False,
        }
    if hasattr(spy.index, "tz") and spy.index.tz is not None:
        spy.index = spy.index.tz_convert(None)
    close = spy["Close"]
    volume = spy["Volume"]

    sma50 = close.rolling(50).mean()
    sma200 = close.rolling(200).mean()

    dist_day = (close.pct_change() <= -0.002) & (volume > volume.shift(1))
    dist_count = int(dist_day.rolling(25).sum().iloc[-1])

    above_50 = float(close.iloc[-1]) > float(sma50.iloc[-1])
    above_200 = float(close.iloc[-1]) > float(sma200.iloc[-1])

    ftd = False
    rally_days = 0
    pct_changes = close.pct_change().tail(15).values
    for i, chg in enumerate(pct_changes):
        if chg > 0:
            rally_days += 1
            if rally_days >= 4 and chg >= 0.0125:
                ftd = True
                break
        else:
            rally_days = 0

    if above_50 and dist_count <= 3:
        classification = "CONFIRMED_UPTREND"
    elif above_50 and dist_count <= 5:
        classification = "UPTREND_UNDER_PRESSURE"
    else:
        classification = "CORRECTION"

    try:
        vix_series = _get_fred().get_series("VIXCLS").dropna()
        vix = round(float(vix_series.iloc[-1]), 2)
    except Exception:
        try:
            vix_df = yf.Ticker("^VIX").history(period="5d")
            vix = round(float(vix_df["Close"].iloc[-1]), 2)
        except Exception:
            vix = 20.0

    try:
        yc = _get_fred().get_series("T10Y2Y").dropna()
        yield_spread = round(float(yc.iloc[-1]), 3)
    except Exception:
        yield_spread = None

    return {
        "classification": classification,
        "above_sma50": above_50,
        "above_sma200": above_200,
        "distribution_days": dist_count,
        "follow_through_day": ftd,
        "vix": vix,
        "vix_elevated": vix > VIX_HIGH_THRESHOLD,
        "yield_spread_10y2y": yield_spread,
        "allow_new_buys": classification != "CORRECTION",
    }
