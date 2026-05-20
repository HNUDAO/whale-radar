import logging
import time

import requests
import config

logger = logging.getLogger(__name__)

_last_call = 0.0
_MIN_INTERVAL = 0.25

_DEFAULT_OFFSET = 100
_MAX_PAGES = 20


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
        params.get("module"), params.get("action"),
        _masked_key(config.ETHERSCAN_API_KEY),
    )
    try:
        resp = requests.get(config.ETHERSCAN_BASE_URL, params=params, timeout=30)
        resp.raise_for_status()
    except requests.HTTPError as e:
        if resp.status_code == 429:
            logger.error("Etherscan rate limit hit")
        elif resp.status_code == 401 or resp.status_code == 403:
            logger.error("Etherscan auth error (invalid API key?)")
        else:
            logger.error("Etherscan HTTP error: %s", e)
        raise
    except requests.RequestException as e:
        logger.error("Etherscan request failed: %s", e)
        raise

    data = resp.json()
    status = data.get("status", "")
    message = data.get("message", "")
    result = data.get("result", "")

    if status == "1":
        return data

    if "No transactions found" in message or "No transactions found" in str(result):
        return data

    if "rate limit" in str(result).lower() or "Max rate" in str(result):
        logger.error("Etherscan rate limit: %s", result)
        raise RuntimeError(f"Etherscan rate limit: {result}")

    if "Invalid API Key" in str(result):
        logger.error("Etherscan invalid API key")
        raise RuntimeError("Etherscan invalid API key")

    logger.warning("Etherscan unexpected response: status=%s message=%s result=%s",
                   status, message, str(result)[:200])
    return data


def get_latest_block() -> int:
    data = _call({"module": "proxy", "action": "eth_blockNumber"})
    result = data.get("result", "0x0")
    return int(result, 16)


def get_txlist(address: str, start_block: int) -> list[dict]:
    all_txs: list[dict] = []
    for page in range(1, _MAX_PAGES + 1):
        data = _call({
            "module": "account",
            "action": "txlist",
            "address": address,
            "startblock": start_block,
            "page": page,
            "offset": _DEFAULT_OFFSET,
            "sort": "asc",
        })
        result = data.get("result")
        if not isinstance(result, list):
            break
        all_txs.extend(result)
        if len(result) < _DEFAULT_OFFSET:
            break
    return all_txs


def get_tokentx(address: str, start_block: int) -> list[dict]:
    all_txs: list[dict] = []
    for page in range(1, _MAX_PAGES + 1):
        data = _call({
            "module": "account",
            "action": "tokentx",
            "address": address,
            "startblock": start_block,
            "page": page,
            "offset": _DEFAULT_OFFSET,
            "sort": "asc",
        })
        result = data.get("result")
        if not isinstance(result, list):
            break
        all_txs.extend(result)
        if len(result) < _DEFAULT_OFFSET:
            break
    return all_txs
