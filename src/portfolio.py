import json
import os
import datetime
import math
from config import STARTING_CAPITAL

PORTFOLIO_PATH = "data/portfolio.json"
TRADES_PATH = "data/trades_log.csv"


class Portfolio:
    def __init__(self, data: dict):
        self.cash = data["cash"]
        self.starting_capital = data.get("starting_capital", STARTING_CAPITAL)
        self.positions = data.get("positions", {})
        self.trades_history = data.get("trades_history", [])
        self.performance = data.get("performance", {})
        self.monthly_drawdown_stop_active = data.get("monthly_drawdown_stop_active", False)

    @classmethod
    def load(cls) -> "Portfolio":
        if os.path.exists(PORTFOLIO_PATH):
            with open(PORTFOLIO_PATH) as f:
                return cls(json.load(f))
        return cls({
            "cash": STARTING_CAPITAL,
            "starting_capital": STARTING_CAPITAL,
            "positions": {},
            "trades_history": [],
            "performance": {
                "realized_pnl": 0.0,
                "total_trades": 0,
                "winning_trades": 0,
                "month_start_value": STARTING_CAPITAL,
                "peak_value": STARTING_CAPITAL,
                "max_drawdown_pct": 0.0,
            },
            "monthly_drawdown_stop_active": False,
        })

    def save(self):
        os.makedirs("data", exist_ok=True)
        with open(PORTFOLIO_PATH, "w") as f:
            json.dump(self._to_dict(), f, indent=2, default=str)

    def _to_dict(self) -> dict:
        return {
            "last_updated": str(datetime.datetime.utcnow()),
            "cash": round(self.cash, 2),
            "starting_capital": self.starting_capital,
            "positions": self.positions,
            "trades_history": self.trades_history[-100:],
            "performance": self.performance,
            "monthly_drawdown_stop_active": self.monthly_drawdown_stop_active,
        }

    def get_total_value(self, prices: dict | None = None) -> float:
        pos_value = sum(
            p["shares"] * (prices.get(sym, p.get("current_price", p["avg_entry"])) if prices else p.get("current_price", p["avg_entry"]))
            for sym, p in self.positions.items()
        )
        return round(self.cash + pos_value, 2)

    def update_prices(self, prices: dict):
        for sym, pos in self.positions.items():
            price = prices.get(sym, pos["avg_entry"])
            pos["current_price"] = round(price, 2)
            pos["unrealized_pnl"] = round((price - pos["avg_entry"]) * pos["shares"], 2)
            pos["unrealized_pnl_pct"] = round(((price - pos["avg_entry"]) / pos["avg_entry"]) * 100, 2)

        total = self.get_total_value(prices)
        peak = self.performance.get("peak_value", total)
        if total > peak:
            self.performance["peak_value"] = total
        if peak > 0:
            dd = round(((peak - total) / peak) * 100, 2)
            self.performance["max_drawdown_pct"] = max(dd, self.performance.get("max_drawdown_pct", 0))

    def open_position(self, symbol: str, shares: int, price: float, stop: float, target: float, rr: float, meta: dict):
        import random
        slippage = 1 + random.uniform(-0.001, 0.003)
        exec_price = round(price * slippage, 2)

        if symbol in self.positions:
            existing = self.positions[symbol]
            total_shares = existing["shares"] + shares
            avg = round((existing["avg_entry"] * existing["shares"] + exec_price * shares) / total_shares, 2)
            existing["shares"] = total_shares
            existing["avg_entry"] = avg
        else:
            self.positions[symbol] = {
                "shares": shares,
                "avg_entry": exec_price,
                "entry_date": str(datetime.date.today()),
                "stop_loss": stop,
                "target": target,
                "rr_ratio": rr,
                "current_price": exec_price,
                "unrealized_pnl": 0.0,
                "unrealized_pnl_pct": 0.0,
                **meta,
            }

        self.cash -= exec_price * shares
        self._log_trade(symbol, "BUY", shares, exec_price, meta)
        self.performance["total_trades"] = self.performance.get("total_trades", 0) + 1

    def close_position(self, symbol: str, price: float, partial_pct: float = 1.0, reason: str = ""):
        if symbol not in self.positions:
            return
        import random
        slippage = 1 + random.uniform(-0.002, 0.001)
        exec_price = round(price * slippage, 2)

        pos = self.positions[symbol]
        shares_to_sell = math.floor(pos["shares"] * partial_pct)
        if shares_to_sell == 0:
            shares_to_sell = pos["shares"]

        pnl = (exec_price - pos["avg_entry"]) * shares_to_sell
        self.cash += exec_price * shares_to_sell
        self.performance["realized_pnl"] = round(self.performance.get("realized_pnl", 0) + pnl, 2)

        if pnl > 0:
            self.performance["winning_trades"] = self.performance.get("winning_trades", 0) + 1

        self._log_trade(symbol, f"SELL ({reason})", shares_to_sell, exec_price, {"pnl": round(pnl, 2)})
        self.performance["total_trades"] = self.performance.get("total_trades", 0) + 1

        pos["shares"] -= shares_to_sell
        if pos["shares"] <= 0:
            del self.positions[symbol]

    def _log_trade(self, symbol: str, action: str, shares: int, price: float, meta: dict):
        trade = {
            "date": str(datetime.date.today()),
            "symbol": symbol,
            "action": action,
            "shares": shares,
            "price": price,
            "value": round(shares * price, 2),
            **{k: v for k, v in meta.items() if k not in ("criteria",)},
        }
        self.trades_history.append(trade)
        os.makedirs("data", exist_ok=True)
        with open(TRADES_PATH, "a") as f:
            f.write(",".join(str(v) for v in trade.values()) + "\n")

    def check_stops_and_targets(self, prices: dict) -> list[dict]:
        actions = []
        for sym, pos in list(self.positions.items()):
            price = prices.get(sym, pos.get("current_price", pos["avg_entry"]))
            if price <= pos["stop_loss"]:
                actions.append({"symbol": sym, "action": "STOP_LOSS", "price": price})
            elif price >= pos["target"]:
                actions.append({"symbol": sym, "action": "TAKE_PROFIT", "price": price})
        return actions

    @property
    def win_rate(self) -> float:
        total = self.performance.get("total_trades", 0)
        wins = self.performance.get("winning_trades", 0)
        return round(wins / total, 3) if total > 0 else 0.0
