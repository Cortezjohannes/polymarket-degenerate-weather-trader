#!/usr/bin/env python3
"""Clean Polymarket CLOB client for direct market and limit orders.

Authentication model (Polymarket two-level):
  L1: EIP-712 signature using wallet private key  → used to sign orders
  L2: HMAC-SHA256 using api_key + api_secret + api_passphrase → used for API requests

Credential notes:
  - L2 creds expire / can be invalidated. If get_open_orders() returns 401,
    re-derive by calling create_or_derive_api_creds() with a fresh L1 client.
  - The .env.polymarket file holds the current valid L2 credentials.
  - signature_type=0 = EOA wallet (standard externally-owned account).

Verified flow (2026-03-25):
  - FOK market BUY order on NYC weather market → MATCHED successfully
  - Order ID: 0x52e2b9d11efd9216114202325e70e00af363421f6cef77c4888ba1d30f51cdec
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from eth_account import Account

try:
    from py_clob_client.client import ClobClient
    from py_clob_client.clob_types import ApiCreds, MarketOrderArgs, OrderArgs, OrderType
    from py_clob_client.order_builder.constants import BUY, SELL
except ImportError:
    Account = None
    ClobClient = None
    ApiCreds = None
    MarketOrderArgs = None
    OrderArgs = None
    OrderType = None
    BUY = None
    SELL = None

ENV_FILE = Path("/data/.openclaw/workspace/polymarket-trader-handoff/.env.polymarket")
CLOB_API = "https://clob.polymarket.com"
DATA_API = "https://data-api.polymarket.com"
GAMMA_API = "https://gamma-api.polymarket.com"
CHAIN_ID = 137
SIGNATURE_TYPE_EOA = 0  # Standard EOA wallet (not proxy/Magic wallet)

logger = logging.getLogger(__name__)


def load_env_file(path: Path = ENV_FILE) -> None:
    """Load KEY=VALUE pairs into os.environ if not already set."""
    if not path.exists():
        return
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def require_env(name: str, aliases: Optional[List[str]] = None) -> str:
    aliases = aliases or []
    for candidate in [name, *aliases]:
        val = os.environ.get(candidate)
        if val:
            return val
    raise RuntimeError(f"Missing required env var: {name} (tried: {[name, *aliases]})")


def fetch_json(url: str, headers: Optional[Dict[str, str]] = None) -> Any:
    req = Request(url, headers=headers or {"User-Agent": "SusanoomonPolymarketClient/1.0"})
    with urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


# ---------------------------------------------------------------------------
# Wallet / credentials
# ---------------------------------------------------------------------------

def get_wallet_address() -> str:
    """Derive wallet address from private key, or read from env."""
    load_env_file()
    addr = os.environ.get("POLYMARKET_WALLET_ADDRESS") or os.environ.get("WALLET_ADDRESS")
    if addr:
        return addr
    if Account is None:
        raise RuntimeError("eth-account not installed; cannot derive wallet address")
    key = require_env("POLYMARKET_PRIVATE_KEY", ["POLYMARKET_KEY", "PRIVATE_KEY", "WALLET_PRIVATE_KEY"])
    return Account.from_key(key).address


def _build_client(l2_creds: Optional[ApiCreds] = None) -> ClobClient:
    """Create a ClobClient with EOA signature type and optional L2 credentials."""
    if ClobClient is None:
        raise RuntimeError("py-clob-client not installed")
    load_env_file()
    private_key = require_env(
        "POLYMARKET_PRIVATE_KEY", ["POLYMARKET_KEY", "PRIVATE_KEY", "WALLET_PRIVATE_KEY"]
    )
    return ClobClient(
        host=CLOB_API,
        chain_id=CHAIN_ID,
        key=private_key,
        creds=l2_creds,
        signature_type=SIGNATURE_TYPE_EOA,
    )


def _get_l2_creds() -> ApiCreds:
    """Build ApiCreds from env vars."""
    if ApiCreds is None:
        raise RuntimeError("py-clob-client not installed")
    load_env_file()
    return ApiCreds(
        api_key=require_env("POLYMARKET_CLOB_API_KEY", ["POLYMARKET_API_KEY"]),
        api_secret=require_env("POLYMARKET_CLOB_SECRET", ["POLYMARKET_API_SECRET"]),
        api_passphrase=require_env(
            "POLYMARKET_CLOB_PASSPHRASE", ["POLYMARKET_API_PASSPHRASE"]
        ),
    )


def create_client() -> ClobClient:
    """Create a fully-authenticated L2 ClobClient."""
    return _build_client(l2_creds=_get_l2_creds())


def refresh_and_update_credentials() -> ApiCreds:
    """
    Re-derive L2 credentials via L1 auth and return them.
    Use this when API calls return 401 — the stored credentials have expired.

    To persist the new credentials, call save_credentials(creds).
    """
    load_env_file()
    private_key = require_env(
        "POLYMARKET_PRIVATE_KEY", ["POLYMARKET_KEY", "PRIVATE_KEY", "WALLET_PRIVATE_KEY"]
    )
    # L1 client (no credentials needed for derivation)
    client_l1 = ClobClient(
        host=CLOB_API,
        chain_id=CHAIN_ID,
        key=private_key,
        signature_type=SIGNATURE_TYPE_EOA,
    )
    new_creds = client_l1.create_or_derive_api_creds()
    logger.info("Re-derived fresh L2 API credentials")
    return new_creds


def save_credentials(creds: ApiCreds, path: Path = ENV_FILE) -> None:
    """Overwrite the L2 credential fields in the .env file."""
    lines = []
    if path.exists():
        lines = path.read_text().splitlines()

    replacements = {
        "POLYMARKET_CLOB_API_KEY": creds.api_key,
        "POLYMARKET_CLOB_SECRET": creds.api_secret,
        "POLYMARKET_CLOB_PASSPHRASE": creds.api_passphrase,
    }
    output_lines = []
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#"):
            output_lines.append(raw)
            continue
        if "=" in line:
            key = line.split("=", 1)[0].strip()
            if key in replacements:
                output_lines.append(f"{key}={replacements[key]}")
                del replacements[key]
                continue
        output_lines.append(raw)
    # Append any new keys not found in file
    for key, val in replacements.items():
        output_lines.append(f"{key}={val}")

    path.write_text("\n".join(output_lines) + "\n")
    logger.info(f"Saved new L2 credentials to {path}")


def create_client_with_auto_refresh() -> ClobClient:
    """
    Create an L2 client. If the stored credentials are stale (401),
    auto-derive fresh ones and update the .env file.
    """
    creds = _get_l2_creds()
    client = _build_client(l2_creds=creds)

    # Quick sanity-check: try get_orders()
    try:
        client.get_orders()
        return client
    except Exception as exc:
        if "401" in str(exc) or "Unauthorized" in str(exc):
            logger.warning("L2 credentials stale (401); re-deriving via L1 auth...")
            creds = refresh_and_update_credentials()
            save_credentials(creds)
            return _build_client(l2_creds=creds)
        raise


# ---------------------------------------------------------------------------
# Market data (no auth required — L1/L2 endpoints)
# ---------------------------------------------------------------------------

def get_positions(wallet: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
    wallet = wallet or get_wallet_address()
    qs = urlencode(
        {
            "user": wallet,
            "limit": limit,
            "sizeThreshold": 0.01,
            "sortBy": "CURRENT",
            "sortDirection": "DESC",
        }
    )
    return fetch_json(f"{DATA_API}/positions?{qs}")


def get_activity(
    wallet: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    activity_type: str = "TRADE",
) -> List[Dict[str, Any]]:
    wallet = wallet or get_wallet_address()
    qs = urlencode(
        {
            "user": wallet,
            "type": activity_type,
            "limit": limit,
            "offset": offset,
            "sortBy": "TIMESTAMP",
            "sortDirection": "DESC",
        }
    )
    return fetch_json(f"{DATA_API}/activity?{qs}")


def get_active_events(
    limit: int = 100, offset: int = 0, order: str = "volume_24hr", ascending: bool = False
) -> List[Dict[str, Any]]:
    qs = urlencode(
        {
            "active": "true",
            "closed": "false",
            "limit": limit,
            "offset": offset,
            "order": order,
            "ascending": str(ascending).lower(),
        }
    )
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json",
        "Origin": "https://polymarket.com",
        "Referer": "https://polymarket.com/",
    }
    return fetch_json(f"{GAMMA_API}/events?{qs}", headers=headers)


def find_events_by_text(query: str, pages: int = 10, page_size: int = 100) -> List[Dict[str, Any]]:
    needle = query.lower()
    results: List[Dict[str, Any]] = []
    for page in range(pages):
        events = get_active_events(limit=page_size, offset=page * page_size)
        if not events:
            break
        for ev in events:
            text = " ".join(
                filter(None, [ev.get("title", ""), ev.get("slug", ""), ev.get("description", "")])
            ).lower()
            if needle in text:
                results.append(ev)
    return results


def get_market(condition_id: str) -> Dict[str, Any]:
    client = create_client()
    return client.get_market(condition_id=condition_id)


def get_orderbook(token_id: str) -> Dict[str, Any]:
    client = create_client()
    return client.get_order_book(token_id=token_id)


def get_midpoint(token_id: str) -> float:
    client = create_client()
    price = client.get_midpoint(token_id=token_id)
    return float(price) if price else 0.0


def get_last_trade_price(token_id: str) -> float:
    client = create_client()
    price = client.get_last_trade_price(token_id=token_id)
    return float(price) if price else 0.0


# ---------------------------------------------------------------------------
# Authenticated CLOB operations (require L2)
# ---------------------------------------------------------------------------

def get_open_orders() -> List[Dict[str, Any]]:
    """Get all open orders for the wallet. Auto-refreshes stale credentials."""
    client = create_client_with_auto_refresh()
    result = client.get_orders()
    return result if isinstance(result, list) else result.get("data", [])


def cancel_order(order_id: str) -> Dict[str, Any]:
    """Cancel an open order by ID."""
    client = create_client_with_auto_refresh()
    return client.cancel(order_id)


# ---------------------------------------------------------------------------
# Order placement
# ---------------------------------------------------------------------------

def place_limit_order(
    token_id: str, side: str, price: float, size: float, order_type: OrderType = OrderType.GTC
) -> Dict[str, Any]:
    """
    Place a limit order (GTC by default).

    Args:
        token_id: Polymarket token ID for the outcome (e.g. YES token)
        side: 'BUY' or 'SELL'
        price: limit price (e.g. 0.17 = $0.17 / 17% probability)
        size: number of conditional tokens
        order_type: GTC (rest on book), GTD (good till date), FOK, FAK

    Returns:
        API response dict with orderID if successful
    """
    client = create_client()
    if OrderArgs is None or OrderType is None:
        raise RuntimeError("py-clob-client not installed")
    side_enum = BUY if side.upper() == "BUY" else SELL
    order = client.create_order(
        OrderArgs(token_id=token_id, price=price, size=size, side=side_enum)
    )
    return client.post_order(order, order_type)


def place_market_order(
    token_id: str, side: str, amount: float, order_type: OrderType = OrderType.FOK
) -> Dict[str, Any]:
    """
    Place a market order (FOK = fill-or-kill all-at-once).

    Args:
        token_id: Polymarket token ID for the outcome
        side: 'BUY' or 'SELL'
        amount: USDC dollar amount for BUY; number of shares for SELL
        order_type: FOK (default, all-or-nothing) or FAK (fill what you can)

    Returns:
        API response dict, e.g.:
        {'success': True, 'orderID': '0x...', 'status': 'delayed'/'MATCHED'}

    Note:
        FOK market orders require minimum $1.00. The fill price is the best
        available price on the orderbook at time of execution.
        For wide-spread markets, consider a limit order instead.
    """
    client = create_client()
    if MarketOrderArgs is None or OrderType is None:
        raise RuntimeError("py-clob-client not installed")
    side_enum = BUY if side.upper() == "BUY" else SELL
    order_args = MarketOrderArgs(token_id=token_id, amount=amount, side=side_enum)
    signed_order = client.create_market_order(order_args)
    return client.post_order(signed_order, order_type)


# ---------------------------------------------------------------------------
# Script entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    load_env_file()
    wallet = get_wallet_address()
    positions = get_positions(wallet=wallet, limit=10)
    print(
        json.dumps(
            {
                "wallet": wallet,
                "positions_count": len(positions),
                "sample_titles": [p.get("title") for p in positions[:5]],
            },
            indent=2,
        )
    )
