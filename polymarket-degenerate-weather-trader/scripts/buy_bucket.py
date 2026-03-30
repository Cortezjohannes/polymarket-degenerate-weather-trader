#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from polymarket_client import load_env_file, place_limit_order  # noqa: E402
from market_utils import market_snapshot  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('slug')
    parser.add_argument('--usd', type=float, required=True)
    parser.add_argument('--price', type=float, help='Explicit limit price')
    parser.add_argument('--at-ask', action='store_true', help='Use current best ask')
    args = parser.parse_args()
    if not args.price and not args.at_ask:
        raise SystemExit('Choose --price or --at-ask')

    load_env_file()
    snap = market_snapshot(args.slug)
    price = args.price if args.price is not None else float(snap['bestAsk'])
    size = round(args.usd / price, 3)
    result = place_limit_order(token_id=snap['tokenId'], side='BUY', price=price, size=size)
    print(json.dumps({'snapshot': snap, 'price_used': price, 'size': size, 'result': result}, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
