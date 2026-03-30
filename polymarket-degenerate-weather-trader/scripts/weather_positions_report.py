#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from polymarket_client import load_env_file, get_positions  # noqa: E402

HEADERS = {
    'User-Agent': 'SusanoomonWeatherMonitor/1.0',
    'Accept': 'application/json',
    'Origin': 'https://polymarket.com',
    'Referer': 'https://polymarket.com/',
}
WX_HEADERS = {
    'User-Agent': 'SusanoomonWeatherMonitor/1.0',
    'Accept': 'application/geo+json',
}
ET = ZoneInfo('America/New_York')


def fetch_json(url: str, headers: dict[str, str]) -> Any:
    req = Request(url, headers=headers)
    with urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def parse_bucket(title: str):
    m = re.search(r'between\s+(\d+)-(\d+)°F', title)
    if m:
        return f"{m.group(1)}-{m.group(2)}°F", int(m.group(1)), int(m.group(2))
    m = re.search(r'(\d+)°F or below', title)
    if m:
        return f"{m.group(1)}°F or below", -999, int(m.group(1))
    m = re.search(r'(\d+)°F or higher', title)
    if m:
        return f"{m.group(1)}°F or higher", int(m.group(1)), 999
    return None, None, None


def extract_city(title: str) -> str:
    m = re.search(r'in\s+(.+?)\s+be', title)
    if m:
        return m.group(1)
    return title


def resolve_station(description: str, resolution_source: str) -> tuple[str, str]:
    desc = description or ''
    if 'KBKF' in desc or 'Buckly' in desc or 'Buckley' in desc:
        return 'KBKF', 'description override'
    m = re.search(r'/([A-Z0-9]{4})\.', desc)
    if m:
        return m.group(1), 'description url'
    m = re.search(r'/([A-Z0-9]{4})$', resolution_source or '')
    if m:
        return m.group(1), 'resolutionSource tail'
    return 'unknown', 'unresolved'


def station_day_max_temp(station: str, target_date: str):
    meta = fetch_json(f'https://api.weather.gov/stations/{station}', WX_HEADERS)
    lon, lat = meta['geometry']['coordinates']
    points = fetch_json(f'https://api.weather.gov/points/{lat},{lon}', WX_HEADERS)
    hourly = fetch_json(points['properties']['forecastHourly'], WX_HEADERS)
    periods = hourly['properties'].get('periods', [])
    filtered = []
    for p in periods:
        dt = datetime.fromisoformat(p['startTime'])
        if dt.date().isoformat() == target_date:
            filtered.append((p['startTime'], p['temperature']))
    if not filtered:
        return None, [], hourly['properties'].get('updateTime') or hourly['properties'].get('generatedAt')
    max_temp = max(t for _, t in filtered)
    max_times = [
        datetime.fromisoformat(s).astimezone(ET).strftime('%I:%M%p ET')
        for s, t in filtered if t == max_temp
    ]
    updated = hourly['properties'].get('updateTime') or hourly['properties'].get('generatedAt')
    return max_temp, max_times[:3], updated


def fmt_money(v: float) -> str:
    return f"${v:.2f}"


def main() -> int:
    load_env_file()
    positions = [
        p for p in get_positions(limit=200)
        if 'highest temperature' in (p.get('title', '') or '').lower() and float(p.get('currentValue') or 0) > 0.05
    ]
    if not positions:
        print('No live weather positions.')
        return 0

    rows = []
    problems = []
    for p in positions:
        title = p.get('title', '')
        slug = p.get('slug', '')
        try:
            market = fetch_json(f'https://gamma-api.polymarket.com/markets?slug={slug}', HEADERS)[0]
        except Exception as e:
            problems.append(f"{title}: market lookup failed ({e})")
            continue
        event = (market.get('events') or [{}])[0]
        description = (event.get('description') or '') + ' ' + (market.get('description') or '')
        station, station_reason = resolve_station(description, event.get('resolutionSource') or market.get('resolutionSource') or '')
        bucket, lo, hi = parse_bucket(title)
        target_date = market.get('endDateIso')
        max_temp = None
        max_times = []
        updated = None
        if station != 'unknown' and target_date:
            try:
                max_temp, max_times, updated = station_day_max_temp(station, target_date)
            except Exception as e:
                problems.append(f"{title}: NOAA check failed for {station} ({e})")
        status = 'UNKNOWN'
        if max_temp is not None and lo is not None:
            status = 'IN' if lo <= max_temp <= hi else 'OUT'
        size = float(p.get('size') or 0)
        avg = float(p.get('avgPrice') or 0)
        cur = float(p.get('curPrice') or 0)
        value = float(p.get('currentValue') or 0)
        cost = size * avg
        pnl = value - cost
        rows.append({
            'city': extract_city(title),
            'date': target_date,
            'station': station,
            'station_reason': station_reason,
            'bucket': bucket,
            'forecast_max': max_temp,
            'times': ', '.join(max_times),
            'status': status,
            'cur': cur,
            'value': value,
            'cost': cost,
            'pnl': pnl,
            'updated': updated,
        })

    rows.sort(key=lambda r: (r['date'] or '', r['city']))
    print('Weather positions vs exact-station NOAA')
    print('')
    print('| City | Date | Station | Bucket | NOAA max | ET time of max | IN/OUT | Price | Value | P/L |')
    print('|---|---|---|---|---:|---|---|---:|---:|---:|')
    for r in rows:
        max_s = '—' if r['forecast_max'] is None else str(r['forecast_max'])
        print(f"| {r['city']} | {r['date']} | {r['station']} | {r['bucket']} | {max_s} | {r['times'] or '—'} | {r['status']} | {r['cur']:.3f} | {fmt_money(r['value'])} | {r['pnl']:+.2f} |")

    print('')
    holds = [r['city'] for r in rows if r['status'] == 'IN']
    broken = [r['city'] for r in rows if r['status'] == 'OUT']
    total_value = sum(r['value'] for r in rows)
    total_cost = sum(r['cost'] for r in rows)
    total_pnl = total_value - total_cost
    print(f"Total value: {fmt_money(total_value)} | Net P/L: {total_pnl:+.2f}")
    print(f"In bucket: {', '.join(holds) if holds else 'none'}")
    print(f"Out of bucket: {', '.join(broken) if broken else 'none'}")
    if problems:
        print('')
        print('Verification issues:')
        for p in problems:
            print(f"- {p}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
