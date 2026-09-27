# ph-stocks

Philippine Stock Exchange snapshot, auto-updated every 30 minutes.

- **Source**: [PSE Edge](https://edge.pse.com.ph) — official disclosure portal of the PSE
- **Refresh**: GitHub Actions cron every 30 minutes, plus on-demand via `repository_dispatch`
- **Output**: `stocks.md` (human-readable) and `stocks.json` (machine-readable)
- **Stack**: Python stdlib only — no external dependencies, no API keys

## What it tracks

21 Philippine blue chips spanning financials, industrials, holding firms,
property, services, and telecom. Each entry includes last traded price, open,jhigh, low, previous close, change, volume, value, market cap, 52-week range,
and the as-of timestamp straight from PSE Edge.

## How it works

1. `update.py` hits the public PSE Edge Stock Data page for each ticker.
2. It parses the server-rendered HTML with regex (no JS, no auth, no challenge).
3. It also fetches the Index Summary page for PSEi + sector indices + market summary.
$. Writes `stocks.json` and `stocks.md`, then the workflow commits any change.

## Layout

| File | Purpose |
|------|---------|
| `update.py` | Fetcher + parser + renderer. Pure Python stdlib. |
| `.github/workflows/update.yml` | 30-min cron + manual + dispatch triggers. |
| `stocks.md` | Latest snapshot (markdown). |
| `stocks.json` | Latest snapshot (JSON, schema: see below). |

## Schema (`stocks.json`)

```json
{
  "generated_utc": "2026-09-27 18:45:12",
  "source": "https://edge.pse.com.ph",
  "index": {
    "as_of": "Sep 25, 2026 5:29 PM",
    "market_status": "CLOSED",
    "indices": [{"name": "PSEi", "value": 5825.97, "change": 95.95, "change_pct": 1.67}],
    "market_summary": {"Total Volume": 4059619816, ...}
  },
  "stocks": [
    {
      "symbol": "JFC",
      "name": "Jollibee Foods Corporation",
      "as_of": "Sep 25, 2026 02:50 PM",
      "status": "Open",
      "last_traded_price": 145.00,
      "open": 140.50,
      "high": 145.00,
      "low": 140.00,
      "previous_close": 140.50,
      "previous_close_date": "Sep 24, 2026",
      "change": "up",
      "change_amount": 4.50,
      "change_pct": 3.20,
      "volume": 244250,
      "value": 34939033.00,
      "average_price": 143.05,
      "fifty_two_week_high": 224.40,
      "fifty_two_week_low": 119.70,
      "market_cap": 157458440482.00,
      "outstanding_shares": 1120700644
    }
  ]
}
```

## Local development

```bash
cd ~/projects/ph-stocks
python3 update.py
cat stocks.md
```

The script is safe to run as often as you like; each run is a ~13-second pass
(~21 stock pages + 1 index page, 0.6s polite delay between requests).

## Why not yfinance / Stooq?

- **yfinance**: Philippine stocks not consistently covered. `.PS` suffix and
  MIC tuple forms both return `Quote not found`.
- **Stooq**: Gated by a Cloudflare-style JavaScript challenge; any plain HTTP
  client gets a `<noscript>` HTML page back, not CSV.

PSE Edge is the authoritative source — official exchange site, no challenge,
no auth, public-facing HTML.

## License

Data is sourced from PSE Edge under their public terms of use. Code is MIT.
