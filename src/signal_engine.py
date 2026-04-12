import pandas as pd
from minervini_screener import screen as minervini_screen
from canslim_screener import score as canslim_score
from finbot_reader import get_finbot_signal
from risk_manager import calc_stop_loss, calc_target, rr_ratio, position_size_shares
from config import MIN_RR_RATIO


def build_signals(
    candidates: list[dict],
    market: dict,
    portfolio: "Portfolio",
    finbot_data: dict,
) -> list[dict]:
    signals = []

    for c in candidates:
        symbol = c["symbol"]
        df = c["df"]
        fundamentals = c["fundamentals"]
        analyst_recs = c["analyst_recs"]
        rs_pct = c["rs_pct"]

        minervini = minervini_screen(symbol, df, c["universe_returns"])
        if minervini is None:
            continue

        canslim = canslim_score(
            df, fundamentals, analyst_recs, rs_pct,
            market_uptrend=market["allow_new_buys"]
        )

        if not canslim["qualifies"]:
            continue

        entry_info = minervini["signals"]["entry"]
        if not entry_info["triggered"]:
            candidates_for_watchlist = {
                "symbol": symbol,
                "trend_template": minervini["trend_template"],
                "canslim": canslim,
                "watchlist_only": True,
            }
            signals.append(candidates_for_watchlist)
            continue

        entry_price = entry_info["pivot"]
        finbot = get_finbot_signal(symbol, finbot_data)

        vcp = minervini["signals"]["vcp"]
        contraction_lows = df["close"].tail(10).min() if vcp["detected"] else None
        stop = calc_stop_loss(entry_price, float(contraction_lows) if contraction_lows else None)
        target = calc_target(entry_price, stop)
        rr = rr_ratio(entry_price, stop, target)

        if rr < MIN_RR_RATIO:
            continue

        shares = position_size_shares(
            portfolio.get_total_value(),
            entry_price,
            stop,
            market["vix"],
            finbot["size_multiplier"],
        )

        if shares <= 0:
            continue

        signals.append({
            "symbol": symbol,
            "entry_price": entry_price,
            "stop_loss": stop,
            "target": target,
            "rr_ratio": rr,
            "shares": shares,
            "entry_type": entry_info["type"],
            "trend_template": minervini["trend_template"],
            "canslim": canslim,
            "finbot": finbot,
            "rs_percentile": rs_pct,
            "watchlist_only": False,
        })

    return sorted(
        [s for s in signals if not s.get("watchlist_only")],
        key=lambda x: x["canslim"]["score"] + x["trend_template"]["passes"],
        reverse=True,
    ) + [s for s in signals if s.get("watchlist_only")]
