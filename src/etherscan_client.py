import logging
import time

import requests
import config

logger = logging.getLogger(__name__)

_last_call = 0.0
_MIN_INTERVAL = 0.5
_MAX_RETRIES = 3
_RETRY_BACKOFF = 2.0

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


def _is_rate_limited(result_str: str) -> bool:
    lower = result_str.lower()
    return "rate limit" in lower or "max rate" in lower or "max calls" in lower


def _call(params: dict) -> dict:
    params["apikey"] = config.ETHERSCAN_API_KEY
    params["chainid"] = config.CHAIN_ID
    logger.debug(
        "Etherscan call module=%s action=%s key=%s",
        params.get("module"), params.get("action"),
        _masked_key(config.ETHERSCAN_API_KEY),
    )

    for attempt in range(1, _MAX_RETRIES + 1):
        _rate_limit()
        try:
            resp = requests.get(config.ETHERSCAN_BASE_URL, params=params, timeout=30)
            resp.raise_for_status()
        except requests.HTTPError as e:
            if resp.status_code == 429 and attempt < _MAX_RETRIES:
                wait = _RETRY_BACKOFF ** attempt
                logger.warning("Etherscan 429, retry %d/%d in %.1fs", attempt, _MAX_RETRIES, wait)
                time.sleep(wait)
                continue
            if resp.status_code == 429:
                logger.error("Etherscan rate limit hit after %d retries", _MAX_RETRIES)
            elif resp.status_code in (401, 403):
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

        if _is_rate_limited(str(result)):
            if attempt < _MAX_RETRIES:
                wait = _RETRY_BACKOFF ** attempt
                logger.warning("Etherscan rate limit, retry %d/%d in %.1fs: %s",
                               attempt, _MAX_RETRIES, wait, str(result)[:100])
                time.sleep(wait)
                continue
            logger.error("Etherscan rate limit after %d retries: %s", _MAX_RETRIES, result)
            raise RuntimeError(f"Etherscan rate limit: {result}")

        if "Invalid API Key" in str(result):
            logger.error("Etherscan invalid API key")
            raise RuntimeError("Etherscan invalid API key")

        logger.warning("Etherscan unexpected response: status=%s message=%s result=%s",
                       status, message, str(result)[:200])
        return data

    raise RuntimeError("Etherscan max retries exceeded")


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
