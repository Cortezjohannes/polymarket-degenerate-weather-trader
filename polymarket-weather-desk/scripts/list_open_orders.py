#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from polymarket_client import load_env_file, create_client  # noqa: E402


def main() -> int:
    load_env_file()
    client = create_client()
    orders = client.get_orders()
    live = [o for o in orders if o.get('status') == 'LIVE']
    print(json.dumps(live, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
