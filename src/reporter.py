import datetime
import os


def _fmt(val, prefix="$", decimals=2) -> str:
    if val is None:
        return "N/A"
    if isinstance(val, float) and prefix == "$":
        return f"${val:,.{decimals}f}"
    if isinstance(val, float):
        p = "+" if val > 0 else ""
        return f"{p}{val:.{decimals}f}%"
    return str(val)


def build_session_report(
    portfolio: "Portfolio",
    market: dict,
    trades_executed: list[dict],
    screened: dict,
    prices: dict,
    date: datetime.date,
) -> str:
    total = portfolio.get_total_value(prices)
    total_return = round(((total - portfolio.starting_capital) / portfolio.starting_capital) * 100, 2)
    day_pnl = sum(
        (prices.get(sym, pos.get("current_price", pos["avg_entry"])) - pos.get("prev_close", pos["avg_entry"])) * pos["shares"]
        for sym, pos in portfolio.positions.items()
        if "prev_close" in pos
    )

    lines = [
        f"# AI TradeBot Session Report — {date}",
        "",
        f"> Strategies: Minervini SEPA · O'Neil CAN SLIM · Paul Tudor Jones Risk Rules",
        "",
        "## Session Summary",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Portfolio Value | ${total:,.2f} |",
        f"| Cash Available | ${portfolio.cash:,.2f} |",
        f"| Total Return | {_fmt(total_return, prefix='', decimals=2)}% |",
        f"| Session P&L | ${day_pnl:+,.2f} |",
        f"| Open Positions | {len(portfolio.positions)} |",
        f"| Win Rate | {portfolio.win_rate:.1%} ({portfolio.performance.get('winning_trades', 0)}/{portfolio.performance.get('total_trades', 0)}) |",
        f"| Max Drawdown | {portfolio.performance.get('max_drawdown_pct', 0):.2f}% |",
        "",
        "## Market Conditions",
        "",
        f"| Indicator | Value |",
        f"|-----------|-------|",
        f"| O'Neil Classification | **{market['classification']}** |",
        f"| SPY vs SMA50 | {'Above ✓' if market['above_sma50'] else 'Below ✗'} |",
        f"| SPY vs SMA200 | {'Above ✓' if market['above_sma200'] else 'Below ✗'} |",
        f"| Distribution Days | {market['distribution_days']}/25 |",
        f"| VIX | {market['vix']} {'⚠️ Elevated' if market['vix_elevated'] else ''} |",
        f"| Yield Curve (10Y-2Y) | {market.get('yield_spread_10y2y', 'N/A')} |",
        f"| New Buys Allowed | {'Yes' if market['allow_new_buys'] else 'No — Correction Mode'} |",
        "",
    ]

    if trades_executed:
        lines += [
            "## Trades Executed",
            "",
            "| Symbol | Action | Shares | Price | Value | Stop | Target | R/R | Type |",
            "|--------|--------|--------|-------|-------|------|--------|-----|------|",
        ]
        for t in trades_executed:
            lines.append(
                f"| {t['symbol']} | {t['action']} | {t.get('shares', '')} | "
                f"${t.get('price', 0):,.2f} | ${t.get('value', 0):,.0f} | "
                f"${t.get('stop_loss', 0):,.2f} | ${t.get('target', 0):,.2f} | "
                f"{t.get('rr_ratio', 0):.1f}x | {t.get('entry_type', '')} |"
            )
        lines.append("")

    lines += [
        "## Screening Funnel",
        "",
        f"| Stage | Count |",
        f"|-------|-------|",
        f"| S&P 500 Universe | {screened.get('universe_size', 0)} |",
        f"| Passed Trend Template (8/8) | {screened.get('trend_template_pass', 0)} |",
        f"| Passed CAN SLIM (≥4/7) | {screened.get('canslim_pass', 0)} |",
        f"| Entry Signal Triggered | {screened.get('entry_triggered', 0)} |",
        f"| Passed PTJ R/R ≥5:1 | {screened.get('rr_pass', 0)} |",
        f"| Trades Executed | {len(trades_executed)} |",
        "",
    ]

    if portfolio.positions:
        lines += [
            "## Open Positions",
            "",
            "| Symbol | Shares | Entry | Current | Unrealized P&L | Stop | Target | Status |",
            "|--------|--------|-------|---------|----------------|------|--------|--------|",
        ]
        for sym, pos in portfolio.positions.items():
            price = prices.get(sym, pos.get("current_price", pos["avg_entry"]))
            pnl = round((price - pos["avg_entry"]) * pos["shares"], 2)
            pnl_pct = round(((price - pos["avg_entry"]) / pos["avg_entry"]) * 100, 2)
            stop_dist = round(((price - pos["stop_loss"]) / price) * 100, 1)
            status = "⚠️ Near Stop" if stop_dist < 3 else "✓ Healthy"
            lines.append(
                f"| {sym} | {pos['shares']} | ${pos['avg_entry']:,.2f} | ${price:,.2f} | "
                f"${pnl:+,.2f} ({pnl_pct:+.1f}%) | ${pos['stop_loss']:,.2f} | "
                f"${pos['target']:,.2f} | {status} |"
            )
        lines.append("")

    watchlist = screened.get("watchlist", [])[:10]
    if watchlist:
        lines += [
            "## Watchlist — Setup Candidates",
            "",
            "| Symbol | TT Score | CAN SLIM | RS% | Setup |",
            "|--------|----------|----------|-----|-------|",
        ]
        for w in watchlist:
            lines.append(
                f"| {w['symbol']} | {w['trend_template']['passes']}/8 | "
                f"{w['canslim']['score']}/7 | {w.get('rs_percentile', 'N/A')} | "
                f"Watching — no trigger yet |"
            )
        lines.append("")

    lines += [
        "## Risk Management Status",
        "",
        f"| Rule | Status |",
        f"|------|--------|",
        f"| PTJ Monthly Drawdown Stop (>10%) | {'🔴 ACTIVE — No new buys' if portfolio.monthly_drawdown_stop_active else '✅ Clear'} |",
        f"| VIX Position Sizing | {'⚠️ Reduced 50%' if market['vix_elevated'] else 'Normal'} |",
        f"| Average Down Block | Always Active |",
        f"| Max Positions ({8}) | {len(portfolio.positions)}/{8} used |",
        "",
        "---",
        f"*Generated: {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')} | "
        f"Strategies: Minervini SEPA + O'Neil CAN SLIM + PTJ Risk Rules | "
        f"Data: [FinancialMarket_Intelbot](https://github.com/jayj221/FinancialMarket_Intelbot) · Finnhub · FRED*",
    ]

    return "\n".join(lines)


def save_report(content: str, date: datetime.date) -> str:
    os.makedirs("reports", exist_ok=True)
    path = f"reports/{date}.md"
    with open(path, "w") as f:
        f.write(content)
    return path
