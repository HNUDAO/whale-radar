import argparse
import logging
import sys
import time

import config
import storage
import etherscan_client
import telegram_client
import rules

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("whale-radar")


def _parse_args():
    p = argparse.ArgumentParser(description="Whale Radar")
    p.add_argument("--test-telegram", action="store_true",
                    help="Send a test message and exit")
    p.add_argument("--dry-run-once", action="store_true",
                    help="Poll one round, print alerts, no Telegram")
    p.add_argument("--show-config", action="store_true",
                    help="Print masked config and exit")
    return p.parse_args()


def _show_config():
    def _m(v):
        s = str(v)
        return s[:4] + "..." + s[-4:] if len(s) > 12 else "***"

    print("=== Whale Radar Config ===")
    print(f"  CHAIN_ID:        {config.CHAIN_ID}")
    print(f"  CHAIN_NAME:      {config.CHAIN_NAME}")
    print(f"  NATIVE_SYMBOL:   {config.NATIVE_SYMBOL}")
    print(f"  NATIVE_DECIMALS: {config.NATIVE_DECIMALS}")
    print(f"  EXPLORER_BASE:   {config.EXPLORER_BASE}")
    print(f"  POLL_INTERVAL:   {config.POLL_INTERVAL}s")
    print(f"  NATIVE_THRESHOLD:{config.NATIVE_THRESHOLD}")
    print(f"  ERC20_THRESHOLD: {config.ERC20_THRESHOLD}")
    print(f"  DRY_RUN:         {config.DRY_RUN}")
    print(f"  DATA_DIR:        {config.DATA_DIR}")
    print(f"  DB_PATH:         {config.DB_PATH}")
    print(f"  ETHERSCAN_KEY:   {_m(config.ETHERSCAN_API_KEY)}")
    print(f"  TELEGRAM_TOKEN:  {_m(config.TELEGRAM_BOT_TOKEN)}")
    print(f"  TELEGRAM_CHAT:   {_m(config.TELEGRAM_CHAT_ID)}")
    print(f"  ETHERSCAN_URL:   {config.ETHERSCAN_BASE_URL}")
    print("===========================")


def _init_block(address: str, latest_block: int) -> int:
    last = storage.get_last_block(address)
    if last is not None:
        return last
    logger.info("First run for %s, starting from block %d", address, latest_block)
    storage.set_last_block(address, latest_block)
    return latest_block


def _maybe_alert(
    msg: str | None, tx_key: str, tx_hash: str, alert_type: str,
    address: str, block: int, writer: storage.BatchWriter, dry_once: bool,
):
    if not msg or writer.is_processed(tx_key):
        return
    if dry_once:
        logger.info("[DRY-RUN-ONCE] %s:\n%s", alert_type.upper(), msg)
    else:
        telegram_client.send_message(msg)
    writer.mark_processed(tx_key, tx_hash, alert_type, address, block)


def process_address(
    address: str,
    label: str,
    defi_contracts: dict,
    exchanges: dict[str, dict],
    token_thresholds: dict[str, float],
    latest_block: int,
    dry_once: bool = False,
) -> int:
    start_block = _init_block(address, latest_block) + 1
    max_block = 0
    writer = storage.BatchWriter()
    native_count = 0
    erc20_count = 0

    try:
        for tx in etherscan_client.get_txlist(address, start_block):
            tx_hash = tx.get("hash", "")
            block = int(tx.get("blockNumber", "0"))
            if block > max_block:
                max_block = block

            native_count += 1

            # Native transfer
            msg, key = rules.check_native_transfer(tx, label, exchanges)
            _maybe_alert(msg, key, tx_hash, "native", address, block,
                         writer, dry_once)

            # DeFi interaction
            msg, key = rules.check_defi_interaction(tx, label, defi_contracts)
            _maybe_alert(msg, key, tx_hash, "defi", address, block,
                         writer, dry_once)

            # Exchange deposit (whale → exchange)
            msg, key = rules.check_exchange_deposit(
                tx, address, label, exchanges
            )
            _maybe_alert(msg, key, tx_hash, "ex_deposit", address, block,
                         writer, dry_once)

            # Exchange withdrawal (exchange → whale)
            msg, key = rules.check_exchange_withdrawal(
                tx, address, label, exchanges
            )
            _maybe_alert(msg, key, tx_hash, "ex_withdraw", address, block,
                         writer, dry_once)

        for tx in etherscan_client.get_tokentx(address, start_block):
            tx_hash = tx.get("hash", "")
            block = int(tx.get("blockNumber", "0"))
            if block > max_block:
                max_block = block

            erc20_count += 1

            msg, key = rules.check_erc20_transfer(
                tx, label, exchanges, token_thresholds
            )
            _maybe_alert(msg, key, tx_hash, "erc20", address, block,
                         writer, dry_once)

    except Exception:
        writer.commit()
        raise
    finally:
        writer.close()

    writer.commit()
    if native_count > 0 or erc20_count > 0:
        logger.info(
            "[%s] scanned %d native + %d ERC20 txs, block %d→%d",
            label, native_count, erc20_count, start_block, max_block,
        )
    return max_block


def main():
    args = _parse_args()

    if args.show_config:
        _show_config()
        return

    storage.init_db()

    if args.test_telegram:
        ok = telegram_client.send_test()
        return 0 if ok else 1

    dry_once = args.dry_run_once
    if not dry_once:
        ok = telegram_client.send_startup()
        if not ok:
            logger.error("Startup message failed, check Telegram config")

    whales = rules.load_whales()
    defi_contracts = rules.load_defi_contracts()
    exchanges = rules.load_exchange_addresses()
    token_thresholds = rules.load_token_thresholds()

    if not whales:
        logger.error("No whales configured, exiting")
        return

    logger.info(
        "Monitoring %d whales, %d exchanges, %d defi contracts, poll=%ds",
        len(whales), len(exchanges), len(defi_contracts), config.POLL_INTERVAL,
    )

    if dry_once:
        try:
            latest_block = etherscan_client.get_latest_block()
        except Exception:
            logger.exception("Failed to get latest block")
            return
        logger.info("Latest block: %d", latest_block)
        for address, label in whales.items():
            try:
                process_address(
                    address, label, defi_contracts, exchanges,
                    token_thresholds, latest_block, dry_once=True,
                )
            except Exception:
                logger.exception("Error processing %s (%s)", label, address)
        return

    while True:
        try:
            latest_block = etherscan_client.get_latest_block()
        except Exception:
            logger.exception("Failed to get latest block, sleeping")
            time.sleep(config.POLL_INTERVAL)
            continue

        logger.info("Latest block: %d", latest_block)

        for address, label in whales.items():
            try:
                highest = process_address(
                    address, label, defi_contracts, exchanges,
                    token_thresholds, latest_block,
                )
                if highest > 0:
                    old = storage.get_last_block(address) or 0
                    if highest > old:
                        storage.set_last_block(address, highest)
            except Exception:
                logger.exception("Error processing %s (%s)", label, address)
            time.sleep(1.0)

        time.sleep(config.POLL_INTERVAL)


if __name__ == "__main__":
    main()
