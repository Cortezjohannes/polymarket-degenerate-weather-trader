#!/usr/bin/env python3
from __future__ import annotations

import json
from urllib.request import Request, urlopen

HEADERS = {
    'User-Agent': 'SusanoomonWeatherDesk/1.0',
    'Accept': 'application/json',
    'Origin': 'https://polymarket.com',
    'Referer': 'https://polymarket.com/',
}


def fetch_json(url: str, headers: dict[str, str] | None = None):
    req = Request(url, headers=headers or HEADERS)
    with urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def market_by_slug(slug: str) -> dict:
    data = fetch_json(f'https://gamma-api.polymarket.com/markets?slug={slug}', HEADERS)
    if not data:
        raise RuntimeError(f'No market found for slug: {slug}')
    return data[0]


def yes_token_id(market: dict) -> str:
    token_ids = json.loads(market.get('clobTokenIds') or '[]')
    outcomes = json.loads(market.get('outcomes') or '[]')
    if not token_ids:
        raise RuntimeError('No token ids found')
    if outcomes and outcomes[0].upper() == 'YES':
        return token_ids[0]
    # fall back to first token; weather buckets are single YES markets in current usage
    return token_ids[0]


def market_snapshot(slug: str) -> dict:
    m = market_by_slug(slug)
    return {
        'slug': slug,
        'question': m.get('question'),
        'bestBid': m.get('bestBid'),
        'bestAsk': m.get('bestAsk'),
        'lastTradePrice': m.get('lastTradePrice'),
        'tokenId': yes_token_id(m),
    }
