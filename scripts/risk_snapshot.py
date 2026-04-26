import yfinance as yf
import json
import datetime
import os

TODAY = str(datetime.date.today())

def tz(h):
    if hasattr(h.index, "tz") and h.index.tz:
        h.index = h.index.tz_convert(None)
    return h

def main():
    os.makedirs("data", exist_ok=True)
    with open("data/portfolio.json") as f:
        p = json.load(f)

    prices = {}
    for sym in p.get("positions", {}):
        try:
            h = tz(yf.Ticker(sym).history(period="2d"))
            if not h.empty:
                prices[sym] = round(float(h["Close"].iloc[-1]), 2)
        except Exception:
            pass

    pos_value = sum(
        prices.get(sym, pos.get("avg_entry", 0)) * pos["shares"]
        for sym, pos in p.get("positions", {}).items()
    )
    total = round(p["cash"] + pos_value, 2)
    ret = round((total - p["starting_capital"]) / p["starting_capital"] * 100, 2)
    trades = p.get("trades_history", [])
    wins = sum(1 for t in trades if t.get("pnl", 0) > 0)

    result = {
        "date": TODAY,
        "total_value": total,
        "cash": p["cash"],
        "invested": round(pos_value, 2),
        "return_pct": ret,
        "open_positions": len(p.get("positions", {})),
        "total_trades": len(trades),
        "win_rate": round(wins / len(trades) * 100, 1) if trades else 0.0,
        "monthly_drawdown_stop": p.get("monthly_drawdown_stop_active", False),
    }

    with open("data/risk_metrics.json", "w") as f:
        json.dump(result, f, indent=2)
    print(f"[risk] Done — ${total:,.2f} ({ret:+.2f}%)")

if __name__ == "__main__":
    main()
