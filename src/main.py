import sys
import os
import json
import datetime

import data_fetcher as fetcher
import market_direction as md
import signal_engine as se
import risk_manager as rm
import reporter
import finbot_reader
from portfolio import Portfolio
from indicators import rs_percentile
from config import FINNHUB_API_KEY, FRED_API_KEY, BOT_NAME

MODE = os.getenv("TRADEBOT_MODE", "close")
WATCHLIST_PATH = "data/watchlist.json"


def load_universe():
    tickers = fetcher.get_sp500_tickers()
    universe_data = {}
    universe_returns = []

    print(f"[{BOT_NAME}] Loading universe ({len(tickers[:50])} tickers)...")
    for i, sym in enumerate(tickers[:50]):
        df = fetcher.get_ohlcv(sym, period="2y")
        if df is not None and len(df) >= 252:
            ret = float((df["close"].iloc[-1] / df["close"].iloc[-252] - 1) * 100)
            universe_data[sym] = {"df": df, "returns_12m": ret}
            universe_returns.append(ret)
        if (i + 1) % 10 == 0:
            print(f"[{BOT_NAME}] {i+1}/50 loaded")

    return universe_data, universe_returns


def build_candidates(universe_data: dict, universe_returns: list[float]) -> list[dict]:
    candidates = []
    for sym, data in universe_data.items():
        rs_pct = rs_percentile(data["returns_12m"], universe_returns)
        fundamentals = fetcher.get_fundamentals(sym)
        analyst_recs = fetcher.get_analyst_recs(sym)
        earnings = fetcher.get_earnings_surprise(sym)
        candidates.append({
            "symbol": sym,
            "df": data["df"],
            "rs_pct": rs_pct,
            "fundamentals": fundamentals,
            "analyst_recs": analyst_recs,
            "earnings": earnings,
            "universe_returns": universe_returns,
        })
    return candidates


def run_scan():
    print(f"[{BOT_NAME}] Morning scan — {datetime.date.today()}")

    market = md.classify_market()
    print(f"[{BOT_NAME}] Market: {market['classification']} | VIX: {market['vix']}")

    finbot_data = finbot_reader.fetch_latest_report()
    universe_data, universe_returns = load_universe()
    candidates = build_candidates(universe_data, universe_returns)

    portfolio = Portfolio.load()
    signals = se.build_signals(candidates, market, portfolio, finbot_data)

    watchlist = [
        {"symbol": s["symbol"], "trend_template": s["trend_template"]["passes"], "canslim": s["canslim"]["score"], "rs_pct": s.get("rs_percentile", 0)}
        for s in signals if s.get("watchlist_only")
    ][:20]

    actionable = [
        {"symbol": s["symbol"], "entry": s["entry_price"], "stop": s["stop_loss"], "target": s["target"], "rr": s["rr_ratio"], "type": s["entry_type"]}
        for s in signals if not s.get("watchlist_only")
    ]

    os.makedirs("data", exist_ok=True)
    with open(WATCHLIST_PATH, "w") as f:
        json.dump({"date": str(datetime.date.today()), "market": market["classification"], "actionable": actionable, "watching": watchlist}, f, indent=2)

    print(f"[{BOT_NAME}] Scan complete — {len(actionable)} actionable, {len(watchlist)} watching")


def run_close():
    print(f"[{BOT_NAME}] Market close — {datetime.date.today()}")

    portfolio = Portfolio.load()
    market = md.classify_market()
    finbot_data = finbot_reader.fetch_latest_report()

    if rm.check_monthly_drawdown(portfolio):
        portfolio.monthly_drawdown_stop_active = True
        market["allow_new_buys"] = False
        print(f"[{BOT_NAME}] Monthly drawdown stop active")
    elif portfolio.monthly_drawdown_stop_active and datetime.date.today().day == 1:
        portfolio.monthly_drawdown_stop_active = False
        portfolio.performance["month_start_value"] = portfolio.get_total_value()

    universe_data, universe_returns = load_universe()
    candidates = build_candidates(universe_data, universe_returns)
    signals = se.build_signals(candidates, market, portfolio, finbot_data)

    prices = {}
    all_syms = list(portfolio.positions.keys()) + [s["symbol"] for s in signals if not s.get("watchlist_only")]
    for sym in set(all_syms):
        q = fetcher.get_quote(sym)
        if q:
            prices[sym] = q["price"]
            if sym in portfolio.positions:
                portfolio.positions[sym]["prev_close"] = q["prev_close"]

    stop_actions = portfolio.check_stops_and_targets(prices)
    trades_executed = []

    for action in stop_actions:
        sym = action["symbol"]
        price = action["price"]
        partial = 0.5 if action["action"] == "TAKE_PROFIT" else 1.0
        portfolio.close_position(sym, price, partial_pct=partial, reason=action["action"])
        trades_executed.append({"symbol": sym, "action": action["action"], "price": price, "shares": "partial" if partial < 1 else "all", "value": 0, "stop_loss": 0, "target": 0, "rr_ratio": 0, "entry_type": action["action"]})

    portfolio.update_prices(prices)

    screened = {
        "universe_size": len(universe_data),
        "trend_template_pass": sum(1 for s in signals if s.get("trend_template", {}).get("passes", 0) == 8),
        "canslim_pass": sum(1 for s in signals if s.get("canslim", {}).get("qualifies", False)),
        "entry_triggered": sum(1 for s in signals if not s.get("watchlist_only")),
        "rr_pass": sum(1 for s in signals if not s.get("watchlist_only")),
        "watchlist": [s for s in signals if s.get("watchlist_only")][:10],
    }

    if market["allow_new_buys"] and not portfolio.monthly_drawdown_stop_active:
        for signal in [s for s in signals if not s.get("watchlist_only")]:
            approved, reason = rm.approve_trade(signal, portfolio, market)
            if not approved:
                print(f"[{BOT_NAME}] {signal['symbol']} blocked: {reason}")
                continue

            portfolio.open_position(
                signal["symbol"], signal["shares"], signal["entry_price"],
                signal["stop_loss"], signal["target"], signal["rr_ratio"],
                {"entry_type": signal["entry_type"], "canslim_score": signal["canslim"]["score"],
                 "trend_template_passes": signal["trend_template"]["passes"],
                 "rs_percentile": signal["rs_percentile"], "finbot_grade": signal["finbot"]["grade"]},
            )
            trades_executed.append({
                "symbol": signal["symbol"], "action": "BUY", "shares": signal["shares"],
                "price": signal["entry_price"], "value": signal["shares"] * signal["entry_price"],
                "stop_loss": signal["stop_loss"], "target": signal["target"],
                "rr_ratio": signal["rr_ratio"], "entry_type": signal["entry_type"],
            })
            print(f"[{BOT_NAME}] BUY {signal['shares']}x {signal['symbol']} @ ${signal['entry_price']:,.2f} | R/R {signal['rr_ratio']:.1f}x")

    portfolio.save()

    report = reporter.build_session_report(portfolio, market, trades_executed, screened, prices, datetime.date.today())
    path = reporter.save_report(report, datetime.date.today())
    print(f"[{BOT_NAME}] Report → {path} | Portfolio: ${portfolio.get_total_value(prices):,.2f}")


def run():
    if not FINNHUB_API_KEY or not FRED_API_KEY:
        print("ERROR: Missing API keys", file=sys.stderr)
        sys.exit(1)

    if MODE == "scan":
        run_scan()
    else:
        run_close()


if __name__ == "__main__":
    run()
