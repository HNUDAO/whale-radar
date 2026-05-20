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
    dry_tag = "  [测试模式]" if config.DRY_RUN else ""
    send_message(
        f"🚀 <b>巨鲸雷达 Whale Radar</b>{dry_tag}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📡 链: {config.CHAIN_NAME} ({config.CHAIN_ID})\n"
        f"🔍 浏览器: {config.EXPLORER_BASE}\n"
        f"⏱️ 轮询间隔: {config.POLL_INTERVAL}s\n"
        f"💰 原生币阈值: {config.NATIVE_THRESHOLD} {config.NATIVE_SYMBOL}\n"
        f"🪙 代币阈值: {config.ERC20_THRESHOLD}"
    )


def send_test():
    send_message(
        f"🔧 <b>巨鲸雷达 连通测试</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📡 链: {config.CHAIN_NAME} ({config.CHAIN_ID})\n"
        f"✅ Telegram 连通正常"
    )
