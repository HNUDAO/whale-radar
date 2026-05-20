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
            "Telegram send failed, token=%s", _masked_token(config.TELEGRAM_BOT_TOKEN)
        )


def send_startup():
    send_message(
        "⚡ <b>Whale Radar</b> started\n"
        f"Chain ID: {config.CHAIN_ID}\n"
        f"Explorer: {config.EXPLORER_BASE}"
    )
