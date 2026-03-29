# Workflow

## Position review
1. Read live positions from the wallet.
2. For each weather position, fetch Gamma market by slug.
3. Resolve the exact station from description text first.
4. Pull NOAA `forecastHourly` and compute the station-local day max.
5. Mark the position IN / OUT of bucket.
6. Report current price, value, cost, and net P/L.

## Board scan
1. Scan active Gamma weather events for the requested date.
2. Filter to US cities if requested.
3. Resolve station from description text first.
4. Compute NOAA hourly max for the target date.
5. Map the exact bucket.
6. Optionally cross-check with Open-Meteo for confidence.
7. Rank by the user's requested criteria (confidence, price cap, mismatch, etc.).

## Rotation logic
- Sell the wrong bucket only after checking the live tape.
- Compare the current wrong-bucket price to the right-bucket price before rotating.
- Prefer exiting over rotating if the replacement bucket is already expensive or confidence is weak.
