import pandas as pd
from indicators import accumulation_distribution_ratio, rs_percentile, sma
from config import MIN_CANSLIM_SCORE


def score(
    df: pd.DataFrame,
    fundamentals: dict,
    analyst_recs: list[dict],
    rs_pct: float,
    market_uptrend: bool,
) -> dict:
    c = float(df["close"].iloc[-1])
    high52 = float(df["close"].rolling(252).max().iloc[-1])
    acc_dist = accumulation_distribution_ratio(df)

    eps_growth = fundamentals.get("eps_growth") or 0
    annual_eps = fundamentals.get("annual_eps_growth") or 0

    rec_improving = False
    if len(analyst_recs) >= 2:
        latest = analyst_recs[0]
        prior = analyst_recs[1]
        rec_improving = (latest.get("buy", 0) + latest.get("strongBuy", 0)) > (
            prior.get("buy", 0) + prior.get("strongBuy", 0)
        )

    criteria = {
        "C_eps_growth_25pct": isinstance(eps_growth, (int, float)) and eps_growth >= 0.40,   # raised to 40%
        "A_annual_growth": isinstance(annual_eps, (int, float)) and annual_eps >= 0.25,
        "N_near_52wk_high": c >= high52 * 0.90,   # tighter — within 10% of high
        "S_accumulation": acc_dist > 0.60,          # stronger accumulation
        "L_rs_rank_80": rs_pct >= 85,               # top 15% only
        "I_institutional_sponsorship": rec_improving,
        "M_market_uptrend": market_uptrend,
    }

    # Hard block: never trade in correction regardless of score
    if not market_uptrend:
        return {"score": 0, "max": 7, "qualifies": False, "criteria": criteria}

    total = sum(criteria.values())
    return {
        "score": total,
        "max": 7,
        "qualifies": total >= MIN_CANSLIM_SCORE,
        "criteria": criteria,
    }
