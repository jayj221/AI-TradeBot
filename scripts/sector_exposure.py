import json
import datetime
import os
import yfinance as yf

TODAY = str(datetime.date.today())

SECTOR_MAP = {
    "AAPL": "Technology", "MSFT": "Technology", "NVDA": "Technology",
    "GOOGL": "Communication", "META": "Communication", "NFLX": "Communication",
    "AMZN": "Consumer Discretionary", "TSLA": "Consumer Discretionary",
    "CRWD": "Technology", "ANET": "Technology", "DDOG": "Technology",
    "AXON": "Industrials", "DECK": "Consumer Discretionary",
}


def main():
    os.makedirs("data", exist_ok=True)
    try:
        with open("data/portfolio.json") as f:
            p = json.load(f)
    except FileNotFoundError:
        print("[sector_exposure] No portfolio file")
        return

    positions = p.get("positions", {})
    total_value = p.get("cash", 0)
    sector_values: dict[str, float] = {}

    for sym, pos in positions.items():
        try:
            price = float(yf.Ticker(sym).fast_info.last_price)
        except Exception:
            price = pos.get("avg_entry", 0)
        val = price * pos["shares"]
        total_value += val
        sector = SECTOR_MAP.get(sym, "Other")
        sector_values[sector] = sector_values.get(sector, 0) + val

    exposure = {
        sector: {
            "value": round(val, 2),
            "pct_of_portfolio": round(val / total_value * 100, 2) if total_value > 0 else 0,
        }
        for sector, val in sector_values.items()
    }

    output = {
        "date": TODAY,
        "total_value": round(total_value, 2),
        "cash_pct": round(p.get("cash", 0) / total_value * 100, 2) if total_value > 0 else 100,
        "sectors": exposure,
    }
    with open("data/sector_exposure.json", "w") as f:
        json.dump(output, f, indent=2)
    print(f"[sector_exposure] Done — {len(exposure)} sectors tracked")


if __name__ == "__main__":
    main()
