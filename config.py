import os
import logging

logger = logging.getLogger(__name__)

_required = ["ETHERSCAN_API_KEY", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"]
_missing = [k for k in _required if k not in os.environ]
if _missing:
    raise EnvironmentError(f"Missing required env vars: {', '.join(_missing)}")

ETHERSCAN_API_KEY = os.environ["ETHERSCAN_API_KEY"]
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
CHAIN_ID = int(os.environ.get("CHAIN_ID", "1"))
POLL_INTERVAL = int(os.environ.get("POLL_INTERVAL", "60"))
NATIVE_THRESHOLD = float(os.environ.get("NATIVE_THRESHOLD", "10"))
ERC20_THRESHOLD = float(os.environ.get("ERC20_THRESHOLD", "100000"))
ETHERSCAN_BASE_URL = os.environ.get(
    "ETHERSCAN_BASE_URL", "https://api.etherscan.io/v2/api"
)

EXPLORER_URLS: dict[int, str] = {
    1: "https://etherscan.io",
    137: "https://polygonscan.com",
    56: "https://bscscan.com",
    42161: "https://arbiscan.io",
    10: "https://optimistic.etherscan.io",
    43114: "https://snowtrace.io",
    8453: "https://basescan.org",
}
EXPLORER_BASE = EXPLORER_URLS.get(CHAIN_ID, f"https://etherscan.io")

DATA_DIR = os.environ.get("DATA_DIR", ".")
DB_PATH = os.path.join(DATA_DIR, "radar.sqlite3")

os.makedirs(DATA_DIR, exist_ok=True)
