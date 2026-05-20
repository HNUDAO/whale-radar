import json
import logging
import os

import config

logger = logging.getLogger(__name__)

_BASE = os.path.dirname(os.path.abspath(__file__))
WHALES_FILE = os.path.join(_BASE, "whales.json")
DEFI_FILE = os.path.join(_BASE, "defi_contracts.json")
EXCHANGE_FILE = os.path.join(_BASE, "exchange_addresses.json")


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
    return _load_json(DEFI_FILE)


def load_exchange_addresses() -> set[str]:
    data = _load_json(EXCHANGE_FILE)
    return {addr.lower() for addr in data.get("addresses", [])}


def _tx_link(tx_hash: str) -> str:
    short = tx_hash[:10] + "..." + tx_hash[-6:]
    return f'<a href="{config.EXPLORER_BASE}/tx/{tx_hash}">{short}</a>'


def _addr_label(address: str, exchanges: set[str]) -> str:
    if address.lower() in exchanges:
        return f"<code>{address[:8]}...{address[-6:]}</code> [Exchange]"
    return f"<code>{address[:8]}...{address[-6:]}</code>"


def check_native_transfer(
    tx: dict, whale_label: str, exchanges: set[str]
) -> str | None:
    value_eth = int(tx.get("value", "0")) / 1e18
    if value_eth < config.NATIVE_THRESHOLD:
        return None
    tx_hash = tx.get("hash", "")
    from_addr = tx.get("from", "???")
    to_addr = tx.get("to", "???")
    return (
        f"\U0001f4b8 <b>Native Transfer</b>\n"
        f"Whale: <code>{whale_label}</code>\n"
        f"Value: {value_eth:.4f} native\n"
        f"From: {_addr_label(from_addr, exchanges)}\n"
        f"To: {_addr_label(to_addr, exchanges)}\n"
        f"TX: {_tx_link(tx_hash)}"
    )


def check_erc20_transfer(
    tx: dict, whale_label: str, exchanges: set[str]
) -> str | None:
    value_raw = int(tx.get("value", "0"))
    decimals = int(tx.get("tokenDecimal", "18") or "18")
    token_symbol = tx.get("tokenSymbol", "UNKNOWN")
    value = value_raw / (10 ** decimals)
    if value < config.ERC20_THRESHOLD:
        return None
    tx_hash = tx.get("hash", "")
    from_addr = tx.get("from", "???")
    to_addr = tx.get("to", "???")
    return (
        f"\U0001f4b0 <b>ERC20 Transfer</b>\n"
        f"Whale: <code>{whale_label}</code>\n"
        f"Value: {value:.4f} {token_symbol}\n"
        f"From: {_addr_label(from_addr, exchanges)}\n"
        f"To: {_addr_label(to_addr, exchanges)}\n"
        f"TX: {_tx_link(tx_hash)}"
    )


def check_defi_interaction(
    tx: dict, whale_label: str, defi_contracts: dict
) -> str | None:
    to_addr = tx.get("to", "").lower()
    contract_info = defi_contracts.get(to_addr)
    if not contract_info:
        return None
    tx_hash = tx.get("hash", "")
    value_eth = int(tx.get("value", "0")) / 1e18
    return (
        f"\U0001f527 <b>DeFi Interaction</b>\n"
        f"Whale: <code>{whale_label}</code>\n"
        f"Protocol: {contract_info.get('name', 'Unknown')} "
        f"({contract_info.get('type', '')})\n"
        f"To: <code>{tx.get('to', '???')}</code>\n"
        f"Value: {value_eth:.4f} native\n"
        f"TX: {_tx_link(tx_hash)}"
    )
