#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo
import argparse

HEADERS = {
    'User-Agent': 'SusanoomonWeatherDesk/1.0',
    'Accept': 'application/json',
    'Origin': 'https://polymarket.com',
    'Referer': 'https://polymarket.com/',
}
WX_HEADERS = {
    'User-Agent': 'SusanoomonWeatherDesk/1.0',
    'Accept': 'application/geo+json',
}
ET = ZoneInfo('America/New_York')
US_CITIES = {'Austin','Chicago','Seattle','Atlanta','Dallas','Miami','Denver','Houston','Los Angeles','San Francisco','NYC','New York City'}


def fetch_json(url: str, headers: dict[str, str]):
    req = Request(url, headers=headers)
    with urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def parse_bucket(question: str):
    m = re.search(r'be (\d+)°F or below', question)
    if m:
        return f"{m.group(1)}°F or below", (-999, int(m.group(1)))
    m = re.search(r'be between (\d+)-(\d+)°F', question)
    if m:
        return f"{m.group(1)}-{m.group(2)}°F", (int(m.group(1)), int(m.group(2)))
    m = re.search(r'be (\d+)°F or higher', question)
    if m:
        return f"{m.group(1)}°F or higher", (int(m.group(1)), 999)
    return None, None


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


def station_day_max(station: str, target_date: str):
    meta = fetch_json(f'https://api.weather.gov/stations/{station}', WX_HEADERS)
    lon, lat = meta['geometry']['coordinates']
    points = fetch_json(f'https://api.weather.gov/points/{lat},{lon}', WX_HEADERS)
    hourly = fetch_json(points['properties']['forecastHourly'], WX_HEADERS)
    periods = hourly['properties'].get('periods', [])
    day_periods = []
    for p in periods:
        dt = datetime.fromisoformat(p['startTime'])
        if dt.date().isoformat() == target_date:
            day_periods.append((p['startTime'], p['temperature']))
    if not day_periods:
        return None, [], None, lon, lat
    max_temp = max(t for _, t in day_periods)
    max_times = [datetime.fromisoformat(s).astimezone(ET).strftime('%I:%M%p ET') for s, t in day_periods if t == max_temp][:3]
    update_time = hourly['properties'].get('updateTime') or hourly['properties'].get('generatedAt')
    return max_temp, max_times, update_time, lon, lat


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--date', required=True, help='Target date in YYYY-MM-DD')
    parser.add_argument('--cross-check-openmeteo', action='store_true')
    args = parser.parse_args()

    month_name = datetime.fromisoformat(args.date).strftime('%B')
    day_num = datetime.fromisoformat(args.date).day

    rows = []
    for offset in range(0, 5000, 200):
        events = fetch_json(f'https://gamma-api.polymarket.com/events?tag_slug=weather&active=true&closed=false&archived=false&limit=200&offset={offset}', HEADERS)
        if not events:
            break
        for ev in events:
            title = ev.get('title', '')
            prefix = 'Highest temperature in '
            suffix = f' on {month_name} {day_num}?'
            if not title.startswith(prefix) or suffix not in title:
                continue
            city = title[len(prefix):].split(suffix)[0]
            if city not in US_CITIES:
                continue
            desc = ev.get('description') or ''
            station, station_reason = resolve_station(desc, ev.get('resolutionSource') or '')
            if station == 'unknown':
                continue
            try:
                noaa_max, noaa_times, updated, lon, lat = station_day_max(station, args.date)
            except Exception:
                continue
            if noaa_max is None:
                continue
            implied = None
            all_buckets = []
            for mk in ev.get('markets', []):
                label, rng = parse_bucket(mk.get('question', ''))
                if not rng:
                    continue
                rec = {'label': label, 'range': rng, 'bid': mk.get('bestBid'), 'ask': mk.get('bestAsk'), 'last': mk.get('lastTradePrice')}
                all_buckets.append(rec)
                if rng[0] <= noaa_max <= rng[1]:
                    implied = rec
            if not implied:
                continue
            rec = {
                'city': city,
                'station': station,
                'station_reason': station_reason,
                'noaa_max': noaa_max,
                'noaa_times_et': noaa_times,
                'implied_bucket': implied['label'],
                'implied_bid': implied['bid'],
                'implied_ask': implied['ask'],
                'implied_last': implied['last'],
            }
            if args.cross_check_openmeteo:
                om = fetch_json(f'https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&daily=temperature_2m_max&temperature_unit=fahrenheit&timezone=auto&forecast_days=7', {})
                om_map = dict(zip(om['daily']['time'], om['daily']['temperature_2m_max']))
                rec['openmeteo_max'] = om_map.get(args.date)
            rows.append(rec)
        if len(events) < 200:
            break

    rows.sort(key=lambda r: (r['implied_ask'] if r['implied_ask'] is not None else 999, r['city']))
    print(json.dumps(rows, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
