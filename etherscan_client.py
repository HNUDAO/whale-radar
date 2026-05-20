import logging
import time

import requests
import config

logger = logging.getLogger(__name__)

_last_call = 0.0
_MIN_INTERVAL = 0.25  # respect free-tier rate limit (5 req/s)


def _masked_key(key: str) -> str:
    if len(key) <= 8:
        return "***"
    return key[:4] + "..." + key[-4:]


def _rate_limit():
    global _last_call
    elapsed = time.monotonic() - _last_call
    if elapsed < _MIN_INTERVAL:
        time.sleep(_MIN_INTERVAL - elapsed)
    _last_call = time.monotonic()


def _call(params: dict) -> dict:
    _rate_limit()
    params["apikey"] = config.ETHERSCAN_API_KEY
    params["chainid"] = config.CHAIN_ID
    logger.debug(
        "Etherscan call module=%s action=%s key=%s",
        params.get("module"),
        params.get("action"),
        _masked_key(config.ETHERSCAN_API_KEY),
    )
    resp = requests.get(config.ETHERSCAN_BASE_URL, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    if data.get("status") != "1" and data.get("message") != "No transactions found":
        logger.warning("Etherscan warning: %s", data.get("result", ""))
    return data


def get_latest_block() -> int:
    data = _call({"module": "proxy", "action": "eth_blockNumber"})
    result = data.get("result", "0x0")
    return int(result, 16)


def get_txlist(address: str, start_block: int) -> list[dict]:
    data = _call({
        "module": "account",
        "action": "txlist",
        "address": address,
        "startblock": start_block,
        "sort": "asc",
    })
    return data.get("result") if isinstance(data.get("result"), list) else []


def get_tokentx(address: str, start_block: int) -> list[dict]:
    data = _call({
        "module": "account",
        "action": "tokentx",
        "address": address,
        "startblock": start_block,
        "sort": "asc",
    })
    return data.get("result") if isinstance(data.get("result"), list) else []
