#!/usr/bin/env python3
"""ph-stocks: PSE stock snapshot via PSE Edge HTML.

PSE Edge (https://edge.pse.com.ph) is the official disclosure portal of the
Philippine Stock Exchange. It exposes live quote data as server-rendered HTML
on the per-company Stock Data page. No API key, no JS challenge, no auth.

Strategy:
  1. Resolve each ticker to its `cmpy_id` via the autocomplete endpoint
     (cached on first run to `ticker_map.json`).
  2. For each stock, GET /companyPage/stockData.do?cmpy_id=<id>.
  3. Parse the server-rendered HTML with regex to extract Last Traded Price,
     Open, High, Low, Previous Close, Change, Volume, Value, Market Cap,
     Outstanding Shares, 52W High/Low, As-of timestamp, Status.
 4. Also fetch /index/form.do for PSEi + sector indices + market summary.
  5. Write `stocks.json` (machine-readable) and `stocks.md` (human-readable).

Stdlib only. No pip install. Runs in <30s.
"""
