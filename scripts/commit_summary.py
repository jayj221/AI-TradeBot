import json
import sys

with open("data/portfolio.json") as f:
    p = json.load(f)

total = p["cash"] + sum(pos.get("current_price", pos["avg_entry"]) * pos["shares"] for pos in p["positions"].values())
ret = round(((total - p["starting_capital"]) / p["starting_capital"]) * 100, 2)
trades = len(p.get("trades_history", []))
positions = len(p["positions"])

prefix = "+" if ret >= 0 else ""
print(f"Portfolio ${total:,.0f} ({prefix}{ret}%) | {positions} positions | {trades} total trades")
