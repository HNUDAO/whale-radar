import html
import json
import logging
import os

import config

logger = logging.getLogger(__name__)

_BASE = os.path.dirname(os.path.abspath(__file__))
WHALES_FILE = os.path.join(_BASE, "whales.json")
DEFI_FILE = os.path.join(_BASE, "defi_contracts.json")
EXCHANGE_FILE = os.path.join(_BASE, "exchange_addresses.json")
TOKEN_THRESHOLDS_FILE = os.path.join(_BASE, "token_thresholds.json")


# ---------------------------------------------------------------------------
# JSON loaders
# ---------------------------------------------------------------------------

def _load_json(path: str) -> dict:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        logger.exception("Failed to load %s", path)
        return {}


def load_whales() -> dict:
    return _load_json(WHALES_FILE)


def load_defi_contracts() -> dict:
    data = _load_json(DEFI_FILE)
    chain_contracts = data.get(str(config.CHAIN_ID))
    if isinstance(chain_contracts, dict):
        return {k.lower(): v for k, v in chain_contracts.items()}
    return {k.lower(): v for k, v in data.items()}


def load_exchange_addresses() -> dict[str, dict]:
    data = _load_json(EXCHANGE_FILE)
    result: dict[str, dict] = {}
    addresses = data.get("addresses")
    if isinstance(addresses, list):
        for addr in addresses:
            if isinstance(addr, str):
                result[addr.lower()] = {"name": "Exchange", "type": "CEX"}
    else:
        for addr, info in data.items():
            if isinstance(info, dict):
                result[addr.lower()] = info
            elif isinstance(info, str):
                result[addr.lower()] = {"name": info, "type": "CEX"}
    return result


def load_token_thresholds() -> dict[str, float]:
    data = _load_json(TOKEN_THRESHOLDS_FILE)
    return {k.upper(): v for k, v in data.items() if isinstance(v, (int, float))}


# ---------------------------------------------------------------------------
# tx_key builders
# ---------------------------------------------------------------------------

def native_tx_key(tx: dict) -> str:
    return f"native:{tx.get('hash', '')}"


def defi_tx_key(tx: dict) -> str:
    return f"defi:{tx.get('hash', '')}"


def erc20_tx_key(tx: dict) -> str:
    contract = tx.get("contractAddress", "").lower()
    tx_hash = tx.get("hash", "")
    log_index = tx.get("logIndex")
    if log_index is not None and str(log_index) != "":
        return f"erc20:{contract}:{tx_hash}:{log_index}"
    from_addr = tx.get("from", "")
    to_addr = tx.get("to", "")
    value = tx.get("value", "0")
    return f"erc20:{contract}:{tx_hash}:{from_addr}:{to_addr}:{value}"


def ex_deposit_key(tx: dict) -> str:
    return f"ex_deposit:{tx.get('hash', '')}"


def ex_withdraw_key(tx: dict) -> str:
    return f"ex_withdraw:{tx.get('hash', '')}"


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def _esc(s: str) -> str:
    return html.escape(str(s))


def _tx_link(tx_hash: str) -> str:
    short = tx_hash[:10] + "..." + tx_hash[-6:]
    return f'<a href="{config.EXPLORER_BASE}/tx/{tx_hash}">{short}</a>'


def _addr_label(address: str, exchanges: dict[str, dict]) -> str:
    info = exchanges.get(address.lower())
    if info:
        name = _esc(info.get("name", "Exchange"))
        return f"<code>{address[:8]}...{address[-6:]}</code> [{name}]"
    return f"<code>{address[:8]}...{address[-6:]}</code>"


def _get_erc20_threshold(tx: dict, token_thresholds: dict[str, float]) -> float:
    symbol = tx.get("tokenSymbol", "").upper()
    if symbol in token_thresholds:
        return token_thresholds[symbol]
    return config.ERC20_THRESHOLD


# ---------------------------------------------------------------------------
# Alert checkers
# ---------------------------------------------------------------------------

def check_native_transfer(
    tx: dict, whale_label: str, exchanges: dict[str, dict]
) -> tuple[str | None, str]:
    value_native = int(tx.get("value", "0")) / (10 ** config.NATIVE_DECIMALS)
    if value_native < config.NATIVE_THRESHOLD:
        return None, native_tx_key(tx)
    tx_hash = tx.get("hash", "")
    from_addr = tx.get("from", "???")
    to_addr = tx.get("to", "???")
    msg = (
        f"\U0001f4b8 <b>Native Transfer</b>\n"
        f"Whale: <code>{_esc(whale_label)}</code>\n"
        f"Value: {value_native:.4f} {_esc(config.NATIVE_SYMBOL)}\n"
        f"From: {_addr_label(from_addr, exchanges)}\n"
        f"To: {_addr_label(to_addr, exchanges)}\n"
        f"TX: {_tx_link(tx_hash)}"
    )
    return msg, native_tx_key(tx)


def check_erc20_transfer(
    tx: dict, whale_label: str, exchanges: dict[str, dict],
    token_thresholds: dict[str, float],
) -> tuple[str | None, str]:
    value_raw = int(tx.get("value", "0"))
    decimals = int(tx.get("tokenDecimal", "18") or "18")
    token_symbol = tx.get("tokenSymbol", "UNKNOWN")
    value = value_raw / (10 ** decimals)
    threshold = _get_erc20_threshold(tx, token_thresholds)
    if value < threshold:
        return None, erc20_tx_key(tx)
    tx_hash = tx.get("hash", "")
    from_addr = tx.get("from", "???")
    to_addr = tx.get("to", "???")
    msg = (
        f"\U0001f4b0 <b>ERC20 Transfer</b>\n"
        f"Whale: <code>{_esc(whale_label)}</code>\n"
        f"Value: {value:.4f} {_esc(token_symbol)}\n"
        f"From: {_addr_label(from_addr, exchanges)}\n"
        f"To: {_addr_label(to_addr, exchanges)}\n"
        f"TX: {_tx_link(tx_hash)}"
    )
    return msg, erc20_tx_key(tx)


def check_defi_interaction(
    tx: dict, whale_label: str, defi_contracts: dict,
) -> tuple[str | None, str]:
    to_addr = tx.get("to", "").lower()
    contract_info = defi_contracts.get(to_addr)
    if not contract_info:
        return None, defi_tx_key(tx)
    tx_hash = tx.get("hash", "")
    value_native = int(tx.get("value", "0")) / (10 ** config.NATIVE_DECIMALS)
    msg = (
        f"\U0001f527 <b>DeFi Interaction</b>\n"
        f"Whale: <code>{_esc(whale_label)}</code>\n"
        f"Protocol: {_esc(contract_info.get('name', 'Unknown'))} "
        f"({_esc(contract_info.get('type', ''))})\n"
        f"To: <code>{_esc(tx.get('to', '???'))}</code>\n"
        f"Value: {value_native:.4f} {_esc(config.NATIVE_SYMBOL)}\n"
        f"TX: {_tx_link(tx_hash)}"
    )
    return msg, defi_tx_key(tx)


def check_exchange_deposit(
    tx: dict, whale_addr: str, whale_label: str,
    exchanges: dict[str, dict],
) -> tuple[str | None, str]:
    from_addr = tx.get("from", "").lower()
    to_addr = tx.get("to", "").lower()
    if from_addr != whale_addr.lower():
        return None, ex_deposit_key(tx)
    ex_info = exchanges.get(to_addr)
    if not ex_info:
        return None, ex_deposit_key(tx)
    value_native = int(tx.get("value", "0")) / (10 ** config.NATIVE_DECIMALS)
    if value_native < config.NATIVE_THRESHOLD:
        return None, ex_deposit_key(tx)
    tx_hash = tx.get("hash", "")
    msg = (
        f"\U0001f3e6 <b>Exchange Deposit</b>\n"
        f"Whale: <code>{_esc(whale_label)}</code> → {_esc(ex_info.get('name', 'Exchange'))}\n"
        f"Value: {value_native:.4f} {_esc(config.NATIVE_SYMBOL)}\n"
        f"From: {_addr_label(tx.get('from', '???'), exchanges)}\n"
        f"To: {_addr_label(tx.get('to', '???'), exchanges)}\n"
        f"TX: {_tx_link(tx_hash)}"
    )
    return msg, ex_deposit_key(tx)


def check_exchange_withdrawal(
    tx: dict, whale_addr: str, whale_label: str,
    exchanges: dict[str, dict],
) -> tuple[str | None, str]:
    from_addr = tx.get("from", "").lower()
    to_addr = tx.get("to", "").lower()
    if to_addr != whale_addr.lower():
        return None, ex_withdraw_key(tx)
    ex_info = exchanges.get(from_addr)
    if not ex_info:
        return None, ex_withdraw_key(tx)
    value_native = int(tx.get("value", "0")) / (10 ** config.NATIVE_DECIMALS)
    if value_native < config.NATIVE_THRESHOLD:
        return None, ex_withdraw_key(tx)
    tx_hash = tx.get("hash", "")
    msg = (
        f"\U0001f4b3 <b>Exchange Withdrawal</b>\n"
        f"{_esc(ex_info.get('name', 'Exchange'))} → <code>{_esc(whale_label)}</code>\n"
        f"Value: {value_native:.4f} {_esc(config.NATIVE_SYMBOL)}\n"
        f"From: {_addr_label(tx.get('from', '???'), exchanges)}\n"
        f"To: {_addr_label(tx.get('to', '???'), exchanges)}\n"
        f"TX: {_tx_link(tx_hash)}"
    )
    return msg, ex_withdraw_key(tx)
