#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from polymarket_client import load_env_file, get_positions, place_limit_order  # noqa: E402
from market_utils import market_snapshot  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--sell-slug', required=True)
    parser.add_argument('--buy-slug', required=True)
    parser.add_argument('--sell-price', type=float, help='Explicit sell price')
    parser.add_argument('--buy-price', type=float, help='Explicit buy price')
    parser.add_argument('--usd', type=float, default=4.0, help='Buy-side notional')
    parser.add_argument('--sell-at-bid', action='store_true')
    parser.add_argument('--buy-at-ask', action='store_true')
    args = parser.parse_args()

    load_env_file()
    positions = {p.get('slug'): p for p in get_positions(limit=200)}
    pos = positions.get(args.sell_slug)
    if not pos:
        raise SystemExit(f'Sell position not found: {args.sell_slug}')
    sell_snap = market_snapshot(args.sell_slug)
    buy_snap = market_snapshot(args.buy_slug)
    sell_price = args.sell_price if args.sell_price is not None else float(sell_snap['bestBid'] if args.sell_at_bid or args.sell_price is None else sell_snap['bestBid'])
    buy_price = args.buy_price if args.buy_price is not None else float(buy_snap['bestAsk'] if args.buy_at_ask or args.buy_price is None else buy_snap['bestAsk'])
    sell_size = float(pos.get('size') or 0)
    buy_size = round(args.usd / buy_price, 3)
    sell_result = place_limit_order(token_id=sell_snap['tokenId'], side='SELL', price=sell_price, size=sell_size)
    buy_result = place_limit_order(token_id=buy_snap['tokenId'], side='BUY', price=buy_price, size=buy_size)
    print(json.dumps({
        'sell_snapshot': sell_snap,
        'buy_snapshot': buy_snap,
        'sell_price': sell_price,
        'sell_size': sell_size,
        'buy_price': buy_price,
        'buy_size': buy_size,
        'sell_result': sell_result,
        'buy_result': buy_result,
    }, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
