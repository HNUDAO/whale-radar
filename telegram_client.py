import logging

import requests
import config

logger = logging.getLogger(__name__)

_API = "https://api.telegram.org"


def _masked_token(token: str) -> str:
    if len(token) <= 8:
        return "***"
    return token[:4] + "..." + token[-4:]


def send_message(text: str):
    if config.DRY_RUN:
        logger.info("[DRY_RUN] Telegram message:\n%s", text)
        return

    url = f"{_API}/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": config.TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    try:
        resp = requests.post(url, json=payload, timeout=30)
        resp.raise_for_status()
        logger.info("Telegram message sent ok")
    except Exception:
        logger.exception(
            "Telegram send failed, token=%s",
            _masked_token(config.TELEGRAM_BOT_TOKEN),
        )


def send_startup():
    send_message(
        f"⚡ <b>Whale Radar</b> started\n"
        f"Chain: {config.CHAIN_NAME} ({config.CHAIN_ID})\n"
        f"Explorer: {config.EXPLORER_BASE}\n"
        f"DRY_RUN: {config.DRY_RUN}"
    )


def send_test():
    send_message(
        f"🔧 <b>Whale Radar</b> test message\n"
        f"Chain: {config.CHAIN_NAME} ({config.CHAIN_ID})\n"
        f"Explorer: {config.EXPLORER_BASE}"
    )
