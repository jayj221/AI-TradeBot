import yfinance as yf
import json
import datetime
import os

TODAY = str(datetime.date.today())
SYMBOLS = [
    "NVDA", "META", "AMZN", "AAPL", "MSFT", "GOOGL",
    "CRWD", "ANET", "AXON", "DECK", "SNOW", "DDOG", "ZS", "MELI", "CELH",
]

def tz(h):
    if hasattr(h.index, "tz") and h.index.tz:
        h.index = h.index.tz_convert(None)
    return h

def main():
    os.makedirs("data", exist_ok=True)
    passed, failed = [], []
    for sym in SYMBOLS:
        try:
            h = tz(yf.Ticker(sym).history(period="1y"))
            if h.empty or len(h) < 200:
                failed.append(sym)
                continue
            c = float(h["Close"].iloc[-1])
            s50 = float(h["Close"].rolling(50).mean().iloc[-1])
            s150 = float(h["Close"].rolling(150).mean().iloc[-1])
            s200 = float(h["Close"].rolling(200).mean().iloc[-1])
            hi52 = float(h["Close"].rolling(252).max().iloc[-1])
            lo52 = float(h["Close"].rolling(252).min().iloc[-1])
            score = sum([c > s50, c > s150, c > s200, s50 > s150,
                         s150 > s200, c >= lo52 * 1.3, c >= hi52 * 0.75])
            if score >= 5:
                passed.append({"symbol": sym, "price": round(c, 2), "trend_score": score})
            else:
                failed.append(sym)
        except Exception as e:
            print(f"[screener] {sym}: {e}")
            failed.append(sym)

    with open("data/screener_results.json", "w") as f:
        json.dump({"date": TODAY, "passed": passed, "failed": failed}, f, indent=2)
    print(f"[screener] Done — {len(passed)} passed: {[p['symbol'] for p in passed]}")

if __name__ == "__main__":
    main()
