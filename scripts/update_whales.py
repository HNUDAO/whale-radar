"""
Optional script: fetch top ETH holders from Etherscan and update whales.json.

Usage:
    ETHERSCAN_API_KEY=xxx python scripts/update_whales.py

NOTE: The Etherscan "tokenholder" API requires a PRO plan.
If you get a "Account API rate limit reached" or "Missing/Invalid API Key"
error, your plan does not support this endpoint.
This script does NOT affect the main whale-radar program.
"""
import json
import os
import sys

import requests

API_KEY = os.environ.get("ETHERSCAN_API_KEY", "")
BASE_URL = os.environ.get("ETHERSCAN_BASE_URL", "https://api.etherscan.io/v2/api")
CHAIN_ID = int(os.environ.get("CHAIN_ID", "1"))
WHALES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "whales.json")
TOP_N = int(os.environ.get("TOP_N", "10"))

# ETH contract address for top holder query
ETH_CONTRACT = "0x0000000000000000000000000000000000000000"


def main():
    if not API_KEY:
        print("ERROR: ETHERSCAN_API_KEY env var not set")
        sys.exit(1)

    print(f"Fetching top {TOP_N} ETH holders from Etherscan ...")

    params = {
        "module": "token",
        "action": "tokenholderlist",
        "contractaddress": ETH_CONTRACT,
        "page": 1,
        "offset": TOP_N,
        "chainid": CHAIN_ID,
        "apikey": API_KEY,
    }

    try:
        resp = requests.get(BASE_URL, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"ERROR: request failed: {e}")
        sys.exit(1)

    if data.get("status") != "1":
        result = str(data.get("result", ""))
        print(f"Etherscan error: {result}")
        if "rate limit" in result.lower() or "pro" in result.lower():
            print("NOTE: The tokenholder endpoint requires an Etherscan PRO plan.")
            print("You can manually edit whales.json instead.")
        sys.exit(1)

    holders = data.get("result", [])
    if not isinstance(holders, list):
        print(f"Unexpected response: {holders}")
        sys.exit(1)

    whales = {}
    for i, h in enumerate(holders):
        addr = h.get("TokenHolderAddress", "")
        if addr:
            whales[addr] = f"Top Holder #{i + 1}"

    with open(WHALES_FILE, "w", encoding="utf-8") as f:
        json.dump(whales, f, indent=4)

    print(f"Updated {WHALES_FILE} with {len(whales)} addresses")


if __name__ == "__main__":
    main()
