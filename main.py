import logging
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


def _init_block(address: str, latest_block: int) -> int:
    last = storage.get_last_block(address)
    if last is not None:
        return last
    logger.info(
        "First run for %s, starting from latest block %d", address, latest_block
    )
    storage.set_last_block(address, latest_block)
    return latest_block


def process_address(
    address: str,
    label: str,
    defi_contracts: dict,
    exchanges: set[str],
    latest_block: int,
):
    start_block = _init_block(address, latest_block) + 1
    max_block = start_block
    writer = storage.BatchWriter()

    try:
        for tx in etherscan_client.get_txlist(address, start_block):
            tx_hash = tx.get("hash", "")
            block = int(tx.get("blockNumber", "0"))
            if block > max_block:
                max_block = block
            if writer.is_processed(tx_hash):
                continue

            msg = rules.check_native_transfer(tx, label, exchanges)
            if not msg:
                msg = rules.check_defi_interaction(tx, label, defi_contracts)
            if msg:
                telegram_client.send_message(msg)
            writer.mark_processed(tx_hash)

        for tx in etherscan_client.get_tokentx(address, start_block):
            tx_hash = tx.get("hash", "")
            block = int(tx.get("blockNumber", "0"))
            if block > max_block:
                max_block = block
            if writer.is_processed(tx_hash):
                continue

            msg = rules.check_erc20_transfer(tx, label, exchanges)
            if msg:
                telegram_client.send_message(msg)
            writer.mark_processed(tx_hash)

    finally:
        writer.commit()
        writer.close()

    if max_block > start_block:
        storage.set_last_block(address, max_block)


def main():
    storage.init_db()
    telegram_client.send_startup()

    whales = rules.load_whales()
    defi_contracts = rules.load_defi_contracts()
    defi_contracts = {k.lower(): v for k, v in defi_contracts.items()}
    exchanges = rules.load_exchange_addresses()

    if not whales:
        logger.error("No whales configured, exiting")
        return

    logger.info(
        "Monitoring %d whale addresses, poll interval=%ds",
        len(whales),
        config.POLL_INTERVAL,
    )

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
                process_address(address, label, defi_contracts, exchanges, latest_block)
            except Exception:
                logger.exception("Error processing %s (%s)", label, address)

        time.sleep(config.POLL_INTERVAL)


if __name__ == "__main__":
    main()
