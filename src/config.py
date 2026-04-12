import os

FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY", "")
FRED_API_KEY = os.getenv("FRED_API_KEY", "")

STARTING_CAPITAL = 100_000.00
MAX_POSITIONS = 8
MAX_POSITION_PCT = 0.15
RISK_PER_TRADE_PCT = 0.01
MIN_RR_RATIO = 5.0
HARD_STOP_MAX_PCT = 0.08
TAKE_PROFIT_PARTIAL_PCT = 0.50
MONTHLY_DRAWDOWN_STOP_PCT = 0.10
VIX_HIGH_THRESHOLD = 30.0
VIX_SIZE_REDUCTION = 0.50

MIN_CANSLIM_SCORE = 5          # raised from 4 — only elite setups
MIN_TREND_TEMPLATE_SCORE = 8   # all 8 criteria must pass — no exceptions
MIN_RS_PERCENTILE = 85         # top 15% of market only
BREAKOUT_VOLUME_MULTIPLIER = 1.5   # higher conviction breakout required
MIN_VCP_CONTRACTIONS = 2       # at least 2 confirmed contractions
MIN_EARNINGS_SURPRISE_PCT = 0  # must have non-negative recent EPS surprise

FINBOT_REPO = "jayj221/FinancialMarket_Intelbot"
FINBOT_REPORT_DIR = "../FinancialMarket_Intelbot/reports"

BOT_NAME = "AI TradeBot"
