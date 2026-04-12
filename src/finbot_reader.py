import os
import re
import datetime
import requests
from config import FINBOT_REPO, FINBOT_REPORT_DIR


def _parse_report(content: str) -> dict:
    macro_match = re.search(r"Macro Score\s*\|\s*([\d.]+)/100\s*\|\s*(\w+)", content)
    macro_score = float(macro_match.group(1)) if macro_match else None

    market_match = re.search(r"\*\*Classification:\*\*\s*([A-Z\s]+)", content)
    market_class = market_match.group(1).strip() if market_match else None

    asset_scores = {}
    for match in re.finditer(r"\|\s*(\w+)\s*\|[^|]+\|[^|]+\|[^|]+\|[^|]+\|[^|]+\|\s*([\d.]+)/100\s*\|\s*\*\*([A-F])\*\*", content):
        symbol, score, grade = match.group(1), float(match.group(2)), match.group(3)
        asset_scores[symbol] = {"composite_score": score, "grade": grade}

    return {
        "macro_score": macro_score,
        "market_classification": market_class,
        "asset_scores": asset_scores,
    }


def fetch_latest_report() -> dict:
    today = datetime.date.today()

    for days_back in range(3):
        target_date = today - datetime.timedelta(days=days_back)
        local_path = os.path.join(FINBOT_REPORT_DIR, f"{target_date}.md")

        if os.path.exists(local_path):
            with open(local_path, "r") as f:
                return _parse_report(f.read())

        try:
            url = f"https://raw.githubusercontent.com/{FINBOT_REPO}/main/reports/{target_date}.md"
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                return _parse_report(resp.text)
        except Exception:
            pass

    return {"macro_score": None, "market_classification": None, "asset_scores": {}}


def get_finbot_signal(symbol: str, finbot_data: dict) -> dict:
    asset_data = finbot_data.get("asset_scores", {}).get(symbol, {})
    macro_score = finbot_data.get("macro_score") or 50.0
    market_class = finbot_data.get("market_classification") or ""

    grade = asset_data.get("grade", "C")
    composite = asset_data.get("composite_score", 50.0)

    size_multiplier = 1.25 if grade in ("A", "B") else 0.75 if grade in ("D", "F") else 1.0
    macro_risk = "CORRECTION" in (market_class or "")

    return {
        "grade": grade,
        "composite_score": composite,
        "size_multiplier": size_multiplier,
        "macro_risk_flag": macro_risk,
    }
