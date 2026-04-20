import json
import datetime
import os
import yfinance as yf

TODAY = datetime.date.today()


def load_portfolio() -> dict:
    try:
        with open("data/portfolio.json") as f:
            return json.load(f)
    except Exception:
        return {"cash": 100000.0, "starting_capital": 100000.0, "positions": {}, "trades_history": []}


def fetch_price(sym: str) -> float | None:
    try:
        hist = yf.Ticker(sym).history(period="2d")
        if hist.empty:
            return None
        return round(float(hist["Close"].iloc[-1]), 2)
    except Exception:
        return None


def main():
    p = load_portfolio()
    positions = p.get("positions", {})
    cash = p.get("cash", 100000.0)
    start = p.get("starting_capital", 100000.0)
    trades = p.get("trades_history", [])

    prices = {}
    for sym in positions:
        price = fetch_price(sym)
        if price:
            prices[sym] = price

    pos_value = sum(
        prices.get(sym, pos.get("current_price", pos.get("avg_entry", 0))) * pos["shares"]
        for sym, pos in positions.items()
    )
    total = round(cash + pos_value, 2)
    ret = round((total - start) / start * 100, 2)
    wins = sum(1 for t in trades if t.get("pnl", 0) > 0)
    win_rate = round(wins / len(trades) * 100, 1) if trades else 0.0

    lines = [
        f"# 🤖 AI TradeBot — Daily Summary {TODAY}",
        "",
        "> Autonomous paper trading | Minervini SEPA + O'Neil CAN SLIM + PTJ Risk Rules",
        "",
        "---",
        "",
        "## Portfolio Snapshot",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Total Value | ${total:,.2f} |",
        f"| Cash | ${cash:,.2f} |",
        f"| Invested | ${pos_value:,.2f} |",
        f"| Return | {ret:+.2f}% |",
        f"| Open Positions | {len(positions)} |",
        f"| Total Trades | {len(trades)} |",
        f"| Win Rate | {win_rate}% |",
        "",
    ]

    if positions:
        lines += ["## Open Positions", "", "| Symbol | Shares | Entry | Current | P&L |", "|--------|--------|-------|---------|-----|"]
        for sym, pos in positions.items():
            entry = pos.get("avg_entry", 0)
            cur = prices.get(sym, entry)
            pnl = round((cur - entry) * pos["shares"], 2)
            pnl_pct = round((cur - entry) / entry * 100, 2) if entry else 0
            pnl_str = f"${pnl:+,.2f} ({pnl_pct:+.2f}%)"
            lines.append(f"| {sym} | {pos['shares']} | ${entry:.2f} | ${cur:.2f} | {pnl_str} |")
        lines.append("")

    if trades:
        recent = sorted(trades, key=lambda x: x.get("date", ""), reverse=True)[:5]
        lines += ["## Recent Trades", "", "| Date | Symbol | Action | Price | P&L |", "|------|--------|--------|-------|-----|"]
        for t in recent:
            pnl = t.get("pnl")
            pnl_str = f"${pnl:+,.2f}" if pnl is not None else "Open"
            lines.append(f"| {t.get('date','—')} | {t.get('symbol','—')} | {t.get('action','—')} | ${t.get('price',0):.2f} | {pnl_str} |")
        lines.append("")

    lines += [
        "---",
        "",
        f"*AI TradeBot | {TODAY} | Paper trading — not financial advice*",
    ]

    os.makedirs("reports", exist_ok=True)
    path = f"reports/{TODAY}.md"
    with open(path, "w") as f:
        f.write("\n".join(lines))
    print(f"[AI TradeBot] Summary saved → {path}")


if __name__ == "__main__":
    main()
