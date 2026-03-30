---
name: polymarket-weather-desk
description: Deterministic workflow for Polymarket weather trading research, monitoring, and execution. Use when scanning March/next-day US weather markets, comparing open weather positions against the correct NOAA station, mapping the right bucket from Gamma/Polymarket weather markets, ranking buckets by confidence or price cap, rotating out-of-bucket positions, or executing price-aware buys/sells without drifting into generic forecast summaries.
---

# Polymarket Weather Desk

Use this skill for weather-market work that must be **precise**, **repeatable**, and **execution-aware**.

## Core rules
- Use **Gamma/Polymarket directly** for markets and event descriptions.
- Resolve the exact station from **description text first**. If description text and another field disagree, trust the explicit station naming in the description.
- Use NOAA **forecastHourly** and compute the **station-local resolution date max**.
- Enumerate **all buckets** before making judgments.
- Separate:
  - what resolves the market
  - what NOAA predicts
  - what the market currently prices
- For confidence checks, optionally compare against Open-Meteo, but do **not** substitute it for the exact-station NOAA method.

## Quick workflows

### 1. Compare current positions to NOAA
Run:

```bash
cd /data/.openclaw/workspace/skills/polymarket-weather-desk && python3 scripts/weather_positions_report.py
```

This prints a deterministic table with:
- city
- date
- exact station
- bucket
- NOAA max
- ET time of max
- IN/OUT bucket status
- current price/value/P&L

Use this instead of freeform reasoning for periodic reports.

### 2. Scan the March/next-day US board
Run:

```bash
cd /data/.openclaw/workspace/skills/polymarket-weather-desk && python3 scripts/scan_us_board.py --date YYYY-MM-DD
```

Optional confidence cross-check:

```bash
cd /data/.openclaw/workspace/skills/polymarket-weather-desk && python3 scripts/scan_us_board.py --date YYYY-MM-DD --cross-check-openmeteo
```

Use this for ranking cities by:
- right bucket + price cap
- confidence
- cheap upside
- source agreement / disagreement

### 3. Buy a bucket deterministically
At exact ask:

```bash
cd /data/.openclaw/workspace/skills/polymarket-weather-desk && python3 scripts/buy_bucket.py <market-slug> --usd 4 --at-ask
```

At your own limit price:

```bash
cd /data/.openclaw/workspace/skills/polymarket-weather-desk && python3 scripts/buy_bucket.py <market-slug> --usd 4 --price 0.31
```

### 4. Sell a held position deterministically
At current bid:

```bash
cd /data/.openclaw/workspace/skills/polymarket-weather-desk && python3 scripts/sell_position.py <market-slug> --at-bid
```

At current ask:

```bash
cd /data/.openclaw/workspace/skills/polymarket-weather-desk && python3 scripts/sell_position.py <market-slug> --at-ask
```

At your own limit price:

```bash
cd /data/.openclaw/workspace/skills/polymarket-weather-desk && python3 scripts/sell_position.py <market-slug> --price 0.93
```

Emergency-style sell:

```bash
cd /data/.openclaw/workspace/skills/polymarket-weather-desk && python3 scripts/sell_position.py <market-slug> --market
```

### 5. Rotate one bucket into another

```bash
cd /data/.openclaw/workspace/skills/polymarket-weather-desk && python3 scripts/rotate_bucket.py --sell-slug <old-slug> --buy-slug <new-slug> --sell-price 0.33 --buy-price 0.22 --usd 4
```

Use this when you want a deterministic sell+buy pair instead of a freeform rotation.

### 6. List or cancel open orders
List live orders:

```bash
cd /data/.openclaw/workspace/skills/polymarket-weather-desk && python3 scripts/list_open_orders.py
```

Cancel all live orders:

```bash
cd /data/.openclaw/workspace/skills/polymarket-weather-desk && python3 scripts/cancel_open_orders.py --all
```

Cancel specific order(s):

```bash
cd /data/.openclaw/workspace/skills/polymarket-weather-desk && python3 scripts/cancel_open_orders.py --id <order-id>
```

## Rotation / exit judgment
Use the script outputs first, then apply this logic:
- if current bucket is wrong and replacement bucket is still cheap + confidence is acceptable → rotate
- if current bucket is wrong and replacement bucket is already expensive or confidence is weak → exit, do not force a rotate
- if source disagreement is sharp, lower confidence even if one bucket looks cheap

## Execution doctrine
Read `references/execution-doctrine.md` when the task involves selling, rotating, stops, or take-profit behavior.

Hard rule:
- `sell` or `rotate` does **not** automatically mean panic liquidation.
- Check best bid, best ask, and last trade first.
- Work near ask / inside spread when time allows.
- Only use emergency-style dumping when certainty is explicitly more important than price.

## References
- `references/workflow.md` — concise operating workflow for scans, position checks, and rotations
- `references/execution-doctrine.md` — execution rules for exits, profit protection, and automation discipline

## Scripts
- `scripts/weather_positions_report.py` — deterministic live position vs NOAA report
- `scripts/scan_us_board.py` — deterministic March/next-day US board scan
- `scripts/buy_bucket.py` — deterministic bucket entry helper
- `scripts/sell_position.py` — deterministic position exit helper
- `scripts/rotate_bucket.py` — deterministic sell+buy rotation helper
- `scripts/list_open_orders.py` — list live orders
- `scripts/cancel_open_orders.py` — cancel live orders
- `scripts/market_utils.py` — market snapshot helpers
- `scripts/polymarket_client.py` — helper client copied in for reliable wallet/position access

## Notes
- This skill is meant to reduce drift and hallucination.
- Prefer the scripts over freeform reasoning whenever exactness matters.
- If a script fails, report the exact failure instead of substituting another source or hand-waving.
