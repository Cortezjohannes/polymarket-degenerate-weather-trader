# polymarket-weather-desk

Deterministic skill + script toolkit for **Polymarket weather trading**.

This repository packages a reusable weather desk workflow for:
- scanning US weather markets directly from **Gamma / Polymarket**
- resolving the **exact station** from market description text
- comparing buckets against **NOAA hourly max** on the station-local resolution date
- ranking buckets by confidence, price cap, or source agreement
- reporting live positions against exact-station NOAA
- executing deterministic **buy / sell / rotate / cancel** actions

The goal is to reduce drift, vague reasoning, and prompt-only hallucination in weather-market workflows.

---

## What this repo contains

- `polymarket-weather-desk/` — the skill folder
- `dist/polymarket-weather-desk.skill` — packaged skill archive

Inside the skill:
- `SKILL.md` — usage guide and workflows
- `references/` — execution doctrine and workflow notes
- `scripts/` — deterministic utilities for scans, reports, and execution

---

## Core design principles

This project follows a strict hierarchy:
1. **Gamma / Polymarket market description** for station identity
2. **NOAA forecastHourly** for station-local date max
3. optional cross-check with a second source for confidence
4. deterministic scripts over loose prompt-only analysis

It distinguishes between:
- what resolves the market
- what NOAA predicts
- what the market currently prices

It also distinguishes between:
- take profit
- profit-protection exit
- emergency exit

Those are not the same thing, and the tooling is designed to avoid blending them together.

---

## Included scripts

### Research / monitoring
- `scripts/weather_positions_report.py`  
  Prints a deterministic table of live weather positions vs exact-station NOAA.

- `scripts/scan_us_board.py`  
  Scans active US weather markets for a target date and maps the NOAA-implied bucket.

### Execution
- `scripts/buy_bucket.py`  
  Deterministic limit buy helper.

- `scripts/sell_position.py`  
  Deterministic sell helper with bid / ask / custom / market modes.

- `scripts/rotate_bucket.py`  
  Deterministic sell+buy rotation helper.

- `scripts/list_open_orders.py`  
  Lists live orders.

- `scripts/cancel_open_orders.py`  
  Cancels live orders.

- `scripts/polymarket_client.py`  
  Lightweight Polymarket helper client used by the scripts.

---

## Example usage

### Report live positions against exact-station NOAA
```bash
cd polymarket-weather-desk
python3 scripts/weather_positions_report.py
```

### Scan the March 29 US board
```bash
cd polymarket-weather-desk
python3 scripts/scan_us_board.py --date 2026-03-29
```

### Scan with secondary-source confidence check
```bash
cd polymarket-weather-desk
python3 scripts/scan_us_board.py --date 2026-03-29 --cross-check-openmeteo
```

### Buy a bucket at the current ask
```bash
cd polymarket-weather-desk
python3 scripts/buy_bucket.py highest-temperature-in-nyc-on-march-29-2026-54-55f --usd 4 --at-ask
```

### Sell a position at a custom limit price
```bash
cd polymarket-weather-desk
python3 scripts/sell_position.py highest-temperature-in-miami-on-march-29-2026-78-79f --price 0.985
```

### Rotate one bucket into another
```bash
cd polymarket-weather-desk
python3 scripts/rotate_bucket.py \
  --sell-slug highest-temperature-in-atlanta-on-march-29-2026-66-67f \
  --buy-slug highest-temperature-in-atlanta-on-march-29-2026-64-65f \
  --sell-price 0.33 \
  --buy-price 0.22 \
  --usd 4
```

---

## Skill packaging

The packaged skill archive lives at:
- `dist/polymarket-weather-desk.skill`

This allows the skill to be distributed or installed cleanly while preserving the source skill folder in-repo.

---

## Secrets / credential safety

This repository intentionally excludes live credential files.

Ignored / excluded patterns include:
- `.env`
- `.env.*`
- `.env.polymarket`
- virtualenv folders
- Python cache artifacts

The scripts expect credentials to be provided locally in the runtime environment or local non-versioned env files, not committed into the repository.

---

## Status

This repo is intended to be the evolving foundation for a more reliable weather-trading workflow:
- deterministic reporting
- deterministic board scans
- deterministic execution helpers
- less drift
- less improvisation
- better discipline

If you are using it live, prefer the scripts over freeform ad hoc reasoning whenever precision matters.
