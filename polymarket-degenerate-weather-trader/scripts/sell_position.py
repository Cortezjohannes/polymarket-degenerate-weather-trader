#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from polymarket_client import load_env_file, get_positions, place_limit_order, place_market_order  # noqa: E402
from market_utils import market_snapshot  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('slug')
    parser.add_argument('--price', type=float, help='Explicit limit sell price')
    parser.add_argument('--at-bid', action='store_true', help='Sell at current best bid')
    parser.add_argument('--at-ask', action='store_true', help='Sell at current best ask')
    parser.add_argument('--market', action='store_true', help='Use FAK market sell for full size')
    args = parser.parse_args()
    if not any([args.price is not None, args.at_bid, args.at_ask, args.market]):
        raise SystemExit('Choose one of --price, --at-bid, --at-ask, or --market')

    load_env_file()
    positions = {p.get('slug'): p for p in get_positions(limit=200)}
    pos = positions.get(args.slug)
    if not pos:
        raise SystemExit(f'Position not found for slug: {args.slug}')
    size = float(pos.get('size') or 0)
    snap = market_snapshot(args.slug)
    if args.market:
        result = place_market_order(token_id=snap['tokenId'], side='SELL', amount=size, order_type='FAK')
        print(json.dumps({'snapshot': snap, 'size': size, 'mode': 'market_fak', 'result': result}, indent=2))
        return 0
    if args.price is not None:
        price = args.price
    elif args.at_ask:
        price = float(snap['bestAsk'])
    else:
        price = float(snap['bestBid'])
    result = place_limit_order(token_id=snap['tokenId'], side='SELL', price=price, size=size)
    print(json.dumps({'snapshot': snap, 'size': size, 'price_used': price, 'mode': 'limit', 'result': result}, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
