import pandas as pd
import numpy as np
from scipy.signal import find_peaks


def sma(series: pd.Series, period: int) -> pd.Series:
    return series.rolling(period).mean()


def ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def rsi(series: pd.Series, period: int = 14) -> float | None:
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    r = 100 - (100 / (1 + rs))
    val = r.iloc[-1]
    return round(float(val), 2) if pd.notna(val) else None


def macd_histogram(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> float | None:
    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    hist = macd_line - signal_line
    val = hist.iloc[-1]
    return round(float(val), 4) if pd.notna(val) else None


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

    base_troughs = [t for t in troughs_idx if t > recent_peak]
    base_peaks = [p for p in peaks_idx if p > recent_peak]

    if len(base_troughs) < 2:
        return {"detected": False, "pivot": None, "contractions": 0}

    contractions = []
    for i in range(len(base_troughs) - 1):
        ref_peak_i = base_peaks[i] if i < len(base_peaks) else recent_peak
        ref_peak_next = base_peaks[i + 1] if i + 1 < len(base_peaks) else recent_peak
        depth_i = (close[ref_peak_i] - close[base_troughs[i]]) / close[ref_peak_i]
        depth_next = (close[ref_peak_next] - close[base_troughs[i + 1]]) / close[ref_peak_next]
        if depth_next < depth_i * 0.6 and volume[base_troughs[i + 1]] < volume[base_troughs[i]]:
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
    if not close[-1] > close[-2]:
        return False
    down_vols = [vol[i] for i in range(-11, -1) if close[i] < close[i - 1]]
    if not down_vols:
        return False
    return float(vol[-1]) > max(down_vols)
