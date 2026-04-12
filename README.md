# AI TradeBot — Autonomous Paper Trader

AI-driven US equity paper trading system on $100,000 virtual capital. Runs twice daily during market hours via GitHub Actions — morning scan at open, session report at close.

## Strategy Stack

**Screening:** Minervini SEPA Trend Template (all 8/8 criteria) → O'Neil CAN SLIM (≥5/7)

**Entry:** VCP (Volatility Contraction Pattern) breakout with ≥2 contractions, or Pocket Pivot — both require volume confirmation (1.5x 50-day average)

**Risk:** Paul Tudor Jones rules — 1% capital per trade, 5:1 minimum R/R, no averaging down, 10% monthly drawdown stop, VIX-adjusted sizing

**Intelligence:** Reads [FinancialMarket_Intelbot](https://github.com/jayj221/FinancialMarket_Intelbot) daily macro grades for position sizing adjustments

## Why High Win Rate

Selectivity is the edge. Most days zero trades execute. The bot only acts when:
- All 8 Minervini trend criteria pass (strongest uptrends only)
- CAN SLIM score ≥ 5/7 (fundamentals + momentum confirmed)
- EPS growth ≥ 40% YoY (accelerating earnings)
- RS percentile ≥ 85 (top 15% of market)
- VCP with ≥ 2 contractions on declining volume (textbook institutional accumulation)
- R/R ≥ 5:1 (PTJ rule — 5x reward for every 1x risk)
- Market in CONFIRMED UPTREND only (no trades in correction)

## Schedule

| Time | Action |
|------|--------|
| 9:35 AM ET | Morning scan — screen S&P 500, build watchlist, save `data/watchlist.json` |
| 4:05 PM ET | Market close — execute signals on closing prices, update portfolio, generate report |

## Reports

Daily session reports in [`reports/`](./reports/) — trades, open positions, screening funnel, risk metrics.

## Setup

```bash
# GitHub Secrets required:
FINNHUB_API_KEY   # free at finnhub.io
FRED_API_KEY      # free at fred.stlouisfed.org
```

## Local Run

```bash
pip install -r requirements.txt
export FINNHUB_API_KEY=your_key FRED_API_KEY=your_key

PYTHONPATH=src TRADEBOT_MODE=scan python src/main.py   # morning scan
PYTHONPATH=src TRADEBOT_MODE=close python src/main.py  # close report
```

## Companion

[FinancialMarket_Intelbot](https://github.com/jayj221/FinancialMarket_Intelbot) — deep daily intelligence reports (FinBERT NLP + SEC EDGAR + FRED macro) that feed into AI TradeBot's position sizing layer.
