#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from polymarket_client import load_env_file, create_client, cancel_order  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--all', action='store_true', help='Cancel all LIVE orders')
    parser.add_argument('--id', action='append', default=[], help='Specific order id(s) to cancel')
    args = parser.parse_args()

    load_env_file()
    client = create_client()
    targets = []
    if args.all:
        targets.extend([o.get('id') for o in client.get_orders() if o.get('status') == 'LIVE'])
    targets.extend(args.id)
    targets = [t for t in dict.fromkeys(targets) if t]
    if not targets:
        raise SystemExit('No orders selected. Use --all or --id <order-id>.')
    results = []
    for oid in targets:
        try:
            results.append({'id': oid, 'result': cancel_order(oid)})
        except Exception as e:
            results.append({'id': oid, 'error': str(e)})
    print(json.dumps(results, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
