import math
from config import (
    RISK_PER_TRADE_PCT, MIN_RR_RATIO, HARD_STOP_MAX_PCT,
    MAX_POSITIONS, MAX_POSITION_PCT, VIX_SIZE_REDUCTION,
    VIX_HIGH_THRESHOLD, MONTHLY_DRAWDOWN_STOP_PCT,
)


def calc_stop_loss(entry: float, vcp_contraction_low: float | None) -> float:
    hard_stop = entry * (1 - HARD_STOP_MAX_PCT)
    if vcp_contraction_low and vcp_contraction_low > hard_stop:
        return round(vcp_contraction_low * 0.99, 2)
    return round(hard_stop, 2)


def calc_target(entry: float, stop: float) -> float:
    risk = entry - stop
    return round(entry + risk * MIN_RR_RATIO, 2)


def rr_ratio(entry: float, stop: float, target: float) -> float:
    risk = entry - stop
    reward = target - entry
    return round(reward / risk, 2) if risk > 0 else 0.0


def position_size_shares(
    portfolio_value: float,
    entry: float,
    stop: float,
    vix: float,
    finbot_multiplier: float = 1.0,
) -> int:
    risk_dollars = portfolio_value * RISK_PER_TRADE_PCT * finbot_multiplier
    if vix > VIX_HIGH_THRESHOLD:
        risk_dollars *= VIX_SIZE_REDUCTION
    per_share_risk = entry - stop
    if per_share_risk <= 0:
        return 0
    max_by_risk = math.floor(risk_dollars / per_share_risk)
    max_by_pct = math.floor((portfolio_value * MAX_POSITION_PCT) / entry)
    return max(0, min(max_by_risk, max_by_pct))


def approve_trade(signal: dict, portfolio: "Portfolio", market: dict) -> tuple[bool, str]:
    if not market["allow_new_buys"]:
        return False, "Market in correction — no new buys"

    if len(portfolio.positions) >= MAX_POSITIONS:
        return False, f"Max positions ({MAX_POSITIONS}) reached"

    symbol = signal["symbol"]
    if symbol in portfolio.positions:
        existing_avg = portfolio.positions[symbol]["avg_entry"]
        if signal["entry_price"] < existing_avg:
            return False, f"PTJ Rule: Cannot average down on {symbol}"

    if signal.get("rr_ratio", 0) < MIN_RR_RATIO:
        return False, f"R/R {signal.get('rr_ratio', 0):.1f} below minimum {MIN_RR_RATIO}"

    shares = signal.get("shares", 0)
    cost = shares * signal["entry_price"]
    if cost > portfolio.cash:
        return False, f"Insufficient cash (need ${cost:,.0f}, have ${portfolio.cash:,.0f})"

    return True, "Approved"


def check_monthly_drawdown(portfolio: "Portfolio") -> bool:
    peak = portfolio.performance.get("month_start_value", portfolio.starting_capital)
    current = portfolio.get_total_value()
    drawdown = (peak - current) / peak
    return drawdown >= MONTHLY_DRAWDOWN_STOP_PCT
