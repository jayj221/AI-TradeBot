import pandas as pd
import pandas_ta as ta
import numpy as np
from scipy.signal import find_peaks


def sma(series: pd.Series, period: int) -> pd.Series:
    return series.rolling(period).mean()


def ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def rsi(series: pd.Series, period: int = 14) -> float | None:
    r = ta.rsi(series, length=period)
    return round(float(r.iloc[-1]), 2) if r is not None and not r.dropna().empty else None


def macd_histogram(series: pd.Series) -> float | None:
    m = ta.macd(series)
    if m is None or m.empty:
        return None
    col = [c for c in m.columns if "MACDh" in c]
    return round(float(m[col[0]].iloc[-1]), 4) if col else None


def volume_ratio(volume: pd.Series, period: int = 50) -> float:
    avg = volume.rolling(period).mean().iloc[-1]
    return round(float(volume.iloc[-1] / avg), 2) if avg > 0 else 1.0


def rs_percentile(symbol_returns: float, universe_returns: list[float]) -> float:
    below = sum(1 for r in universe_returns if r <= symbol_returns)
    return round((below / len(universe_returns)) * 100, 1) if universe_returns else 50.0


def accumulation_distribution_ratio(df: pd.DataFrame, period: int = 50) -> float:
    up_vol = df[df["close"] > df["close"].shift(1)]["volume"].rolling(period).sum().iloc[-1]
    total_vol = df["volume"].rolling(period).sum().iloc[-1]
    return round(float(up_vol / total_vol), 3) if total_vol > 0 else 0.5


def detect_vcp(df: pd.DataFrame) -> dict:
    close = df["close"].values
    volume = df["volume"].values

    peaks_idx, _ = find_peaks(close, prominence=close.mean() * 0.03)
    troughs_idx, _ = find_peaks(-close, prominence=close.mean() * 0.02)

    if len(peaks_idx) < 2 or len(troughs_idx) < 1:
        return {"detected": False, "pivot": None, "contractions": 0}

    recent_peak = peaks_idx[-1]
    base_start = int(max(0, recent_peak - 65 * 1))

    base_troughs = [t for t in troughs_idx if t > recent_peak]
    base_peaks = [p for p in peaks_idx if p > recent_peak]

    if len(base_troughs) < 2:
        return {"detected": False, "pivot": None, "contractions": 0}

    contractions = []
    for i in range(len(base_troughs) - 1):
        depth_i = (close[base_peaks[i] if i < len(base_peaks) else recent_peak] - close[base_troughs[i]]) / close[base_peaks[i] if i < len(base_peaks) else recent_peak]
        depth_next = (close[base_peaks[i + 1] if i + 1 < len(base_peaks) else recent_peak] - close[base_troughs[i + 1]]) / close[base_peaks[i + 1] if i + 1 < len(base_peaks) else recent_peak]
        vol_ratio_i = volume[base_troughs[i]]
        vol_ratio_next = volume[base_troughs[i + 1]]
        if depth_next < depth_i * 0.6 and vol_ratio_next < vol_ratio_i:
            contractions.append({"depth_pct": round(depth_next * 100, 2)})

    last_5 = close[-5:]
    final_tight = (last_5.max() - last_5.min()) / last_5.mean() < 0.025

    pivot = round(float(close[-5:].max()), 2) if final_tight else None
    detected = len(contractions) >= 2 and final_tight

    return {
        "detected": detected,
        "pivot": pivot,
        "contractions": len(contractions),
        "tight_range": final_tight,
    }


def breakout_signal(df: pd.DataFrame, pivot: float) -> bool:
    close = float(df["close"].iloc[-1])
    vol_r = volume_ratio(df["volume"])
    return close > pivot and vol_r >= 1.4


def pocket_pivot(df: pd.DataFrame) -> bool:
    vol = df["volume"].values
    close = df["close"].values
    today_up = close[-1] > close[-2]
    if not today_up:
        return False
    max_down_vol = max(vol[i] for i in range(-11, -1) if close[i] < close[i - 1])
    return float(vol[-1]) > max_down_vol
