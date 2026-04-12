import pandas as pd
from indicators import sma, rs_percentile, detect_vcp, breakout_signal, pocket_pivot
from config import MIN_TREND_TEMPLATE_SCORE, MIN_RS_PERCENTILE, MIN_VCP_CONTRACTIONS, BREAKOUT_VOLUME_MULTIPLIER


def trend_template(df: pd.DataFrame, rs_pct: float) -> dict:
    close = df["close"]
    c = float(close.iloc[-1])

    s50 = float(sma(close, 50).iloc[-1])
    s150 = float(sma(close, 150).iloc[-1])
    s200 = float(sma(close, 200).iloc[-1])
    s200_21 = float(sma(close, 200).iloc[-22]) if len(close) >= 222 else s200

    high52 = float(close.rolling(252).max().iloc[-1])
    low52 = float(close.rolling(252).min().iloc[-1])

    criteria = {
        "above_150_200": c > s150 and c > s200,
        "sma150_above_200": s150 > s200,
        "sma200_trending_up": s200 > s200_21,
        "sma50_above_150_200": s50 > s150 and s50 > s200,
        "above_sma50": c > s50,
        "above_52wk_low_30pct": c >= low52 * 1.30,
        "within_25pct_52wk_high": c >= high52 * 0.75,
        "rs_rank_above_70": rs_pct >= MIN_RS_PERCENTILE,
    }

    passes = sum(criteria.values())
    return {
        "passes": passes,
        "max": 8,
        "qualifies": passes == 8,
        "criteria": criteria,
        "rs_percentile": rs_pct,
    }


def entry_signal(df: pd.DataFrame) -> dict:
    vcp = detect_vcp(df)
    entry = {"type": None, "pivot": None, "triggered": False}

    if vcp["detected"] and vcp["pivot"] and vcp["contractions"] >= MIN_VCP_CONTRACTIONS:
        triggered = breakout_signal(df, vcp["pivot"])
        entry = {
            "type": "VCP_BREAKOUT",
            "pivot": vcp["pivot"],
            "triggered": triggered,
            "contractions": vcp["contractions"],
        }
    elif pocket_pivot(df) and vcp.get("contractions", 0) >= 1:
        entry = {
            "type": "POCKET_PIVOT",
            "pivot": round(float(df["close"].iloc[-1]), 2),
            "triggered": True,
            "contractions": vcp.get("contractions", 0),
        }

    return {"vcp": vcp, "entry": entry}


def screen(symbol: str, df: pd.DataFrame, universe_12m_returns: list[float]) -> dict | None:
    if df is None or len(df) < 252:
        return None

    returns_12m = float((df["close"].iloc[-1] / df["close"].iloc[-252] - 1) * 100)
    rs_pct = rs_percentile(returns_12m, universe_12m_returns)

    tt = trend_template(df, rs_pct)
    if not tt["qualifies"]:
        return None

    signals = entry_signal(df)

    return {
        "symbol": symbol,
        "trend_template": tt,
        "signals": signals,
        "returns_12m": round(returns_12m, 2),
    }
