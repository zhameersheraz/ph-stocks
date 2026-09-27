# ph-stocks

A live snapshot of top Philippine Stock Exchange (PSE) tickers. Auto-updates every 30 minutes via GitHub Actions.

## What

Pulls current price, % change, and previous close for ~20 PSE-listed companies from Yahoo Finance, writes them to:

- [`stocks.json`](./stocks.json) — raw data
- [`stocks.md`](./stocks.md) — human-readable Markdown table

## How

1. [`update.py`](./update.py) — fetches data via the [`yfinance`](https://github.com/ranaroussi/yfinance) Python library (Yahoo Finance PSE symbols, suffix `.PS`).
2. [`.github/workflows/update.yml`](./.github/workflows/update.yml) — runs the script on `*/30 * * * *` cron, commits only if data changed.
3. Optionally triggered externally by [cron-job.org](https://cron-job.org) via `repository_dispatch` (event type `tick`).

## Why

A small portfolio piece showing:
- API integration (yfinance)
- Scheduled automation (GitHub Actions)
- Clean data output (JSON + Markdown)
- Sensible error handling (failed tickers are skipped, not crashed)

## Tickers tracked

SM, SMPH, JFC, AC, ALI, BDO, BPI, GLO, MPI, MBT, URC, TEL, JGS, LTG, PGOLD, RRHI, GTCAP, SECB, CHIB, MEG

## Notes

- Prices in PHP from Yahoo Finance
- No API key required
- Runs on GitHub Actions free tier (public repo, unlimited minutes)
- During PSE market hours (9:30 AM – 3:30 PM PHT) data is live; off-hours data is last available close
- Failed tickers are listed in `stocks.md` under the warning line and excluded from the table
