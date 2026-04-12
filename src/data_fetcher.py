import time
import yfinance as yf
import pandas as pd
import finnhub
from config import FINNHUB_API_KEY

_fh = finnhub.Client(api_key=FINNHUB_API_KEY)


def get_ohlcv(symbol: str, period: str = "2y") -> pd.DataFrame | None:
    try:
        df = yf.Ticker(symbol).history(period=period)
        if df.empty or len(df) < 200:
            return None
        df.index = df.index.tz_localize(None)
        return df[["Open", "High", "Low", "Close", "Volume"]].rename(columns=str.lower)
    except Exception as e:
        print(f"[fetcher] ohlcv {symbol}: {e}")
        return None


def get_quote(symbol: str) -> dict | None:
    try:
        info = yf.Ticker(symbol).fast_info
        return {
            "price": round(info.last_price, 2),
            "prev_close": round(info.previous_close, 2),
        }
    except Exception:
        return None


def get_fundamentals(symbol: str) -> dict:
    try:
        info = yf.Ticker(symbol).info
        return {
            "eps_growth": info.get("earningsGrowth"),
            "revenue_growth": info.get("revenueGrowth"),
            "roe": info.get("returnOnEquity"),
            "shares_outstanding": info.get("sharesOutstanding"),
            "high_52w": info.get("fiftyTwoWeekHigh"),
            "low_52w": info.get("fiftyTwoWeekLow"),
            "market_cap": info.get("marketCap"),
        }
    except Exception:
        return {}


def get_analyst_recs(symbol: str) -> list[dict]:
    try:
        recs = _fh.recommendation_trends(symbol) or []
        time.sleep(1.1)
        return recs
    except Exception:
        return []


def get_earnings_surprise(symbol: str) -> list[dict]:
    try:
        data = _fh.company_earnings(symbol, limit=4) or []
        time.sleep(1.1)
        return data
    except Exception:
        return []


def get_sp500_tickers() -> list[str]:
    try:
        table = pd.read_html("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies")[0]
        return table["Symbol"].str.replace(".", "-", regex=False).tolist()
    except Exception:
        return ["AAPL", "MSFT", "NVDA", "GOOGL", "META", "AMZN", "TSLA", "SPY", "JPM", "V"]
