import os
import logging

logger = logging.getLogger(__name__)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# --- Auto-load .env without python-dotenv ---
_env_path = os.path.join(PROJECT_ROOT, ".env")
if os.path.isfile(_env_path):
    with open(_env_path, encoding="utf-8") as _f:
        for _line in _f:
            _line = _line.strip()
            if not _line or _line.startswith("#") or "=" not in _line:
                continue
            _k, _, _v = _line.partition("=")
            _k = _k.strip()
            _v = _v.strip()
            if _k and _k not in os.environ:
                os.environ[_k] = _v

# --- Validate required env vars ---
_required = ["ETHERSCAN_API_KEY", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"]
_missing = [k for k in _required if k not in os.environ]
if _missing:
    raise EnvironmentError(f"Missing required env vars: {', '.join(_missing)}")

# --- API keys ---
ETHERSCAN_API_KEY = os.environ["ETHERSCAN_API_KEY"]
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

# --- Chain config ---
CHAIN_ID = int(os.environ.get("CHAIN_ID", "1"))
CHAIN_NAME = os.environ.get("CHAIN_NAME", "")

_CHAIN_NAMES: dict[int, str] = {
    1: "Ethereum", 137: "Polygon", 56: "BSC",
    42161: "Arbitrum", 10: "Optimism", 43114: "Avalanche", 8453: "Base",
}
if not CHAIN_NAME:
    CHAIN_NAME = _CHAIN_NAMES.get(CHAIN_ID, f"Chain-{CHAIN_ID}")

# --- Native token config ---
NATIVE_SYMBOL = os.environ.get("NATIVE_SYMBOL", "")
_NATIVE_SYMBOLS: dict[int, str] = {
    1: "ETH", 137: "MATIC", 56: "BNB",
    42161: "ETH", 10: "ETH", 43114: "AVAX", 8453: "ETH",
}
if not NATIVE_SYMBOL:
    NATIVE_SYMBOL = _NATIVE_SYMBOLS.get(CHAIN_ID, "native")

NATIVE_DECIMALS = int(os.environ.get("NATIVE_DECIMALS", "0") or "0") or 18

# --- Explorer ---
EXPLORER_URLS: dict[int, str] = {
    1: "https://etherscan.io",
    137: "https://polygonscan.com",
    56: "https://bscscan.com",
    42161: "https://arbiscan.io",
    10: "https://optimistic.etherscan.io",
    43114: "https://snowtrace.io",
    8453: "https://basescan.org",
}
EXPLORER_BASE = os.environ.get("EXPLORER_BASE", "") or EXPLORER_URLS.get(
    CHAIN_ID, "https://etherscan.io"
)

# --- Polling ---
POLL_INTERVAL = int(os.environ.get("POLL_INTERVAL", "60"))
NATIVE_THRESHOLD = float(os.environ.get("NATIVE_THRESHOLD", "10"))
ERC20_THRESHOLD = float(os.environ.get("ERC20_THRESHOLD", "100000"))

# --- Etherscan ---
ETHERSCAN_BASE_URL = os.environ.get(
    "ETHERSCAN_BASE_URL", "https://api.etherscan.io/v2/api"
)

# --- DRY_RUN ---
DRY_RUN = os.environ.get("DRY_RUN", "").lower() in ("true", "1", "yes")

# --- Storage ---
DATA_DIR = os.environ.get("DATA_DIR", ".")
DB_PATH = os.path.join(DATA_DIR, "radar.sqlite3")
os.makedirs(DATA_DIR, exist_ok=True)
