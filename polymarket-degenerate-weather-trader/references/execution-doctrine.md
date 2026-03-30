# Execution Doctrine

## Core rules
- Distinguish take profit, profit-protection exit, and emergency exit.
- `sell` or `rotate` does **not** imply panic liquidation.
- Before selling, inspect best bid, best ask, and last trade.
- Prefer near-ask or inside-spread exits when time allows.
- Use bid-side / market-style execution only when immediate certainty is explicitly more important than price.

## Weather-market specifics
- Use Gamma/Polymarket description text first to resolve station identity.
- If description text and another field disagree, trust the explicit station naming in the description.
- Compare buckets using NOAA `forecastHourly` on the station-local resolution date.
- When models disagree sharply, lower confidence even if one source looks attractive.

## Automation rule
- Prompt-only cron logic is not reliable enough for execution-critical sells.
- Use deterministic scripts for position reporting and market scans.
- Explicitly verify fill state after execution-sensitive operations.
