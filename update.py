#!/usr/bin/env python3
"""ph-stocks: PSE stock snapshot via Stooq CSV."""
import csv
import json
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError
# Top PSE-listed Philippine companies (symbol, display name)
TICKERS = [
    ("SM",    "SM Investments Corp."),
    ("SMPH",  "SM Prime Holdings"),
    ("JFC",   "Jollibee Foods Corp."),
    ("AC",    "Ayala Corporation"),
    ("ALI",   "Ayala Land, Inc."),
    ("BDO",   "BDO Unibank, Inc."),
    ("BPI",   "Bank of the Philippine Islands"),
    ("GLO",   "Globe Telecom, Inc."),
    ("MPI",   "Metro Pacific Investments"),
    ("MBT",   "Metropolitan Bank & Trust"),
    ("URC",   "Universal Robina Corp."),
    ("TEL",   "PLDT Inc."),
    ("JGS",   "JG Summit Holdings"),
    ("LTG",   "LT Group, Inc."),
    ("PGOLD", "Puregold Price Club"),
    ("RRHI",  "Robinsons Retail Holdings"),
    ("GTCAP", "GT Capital Holdings"),
    ("SECB",  "Security Bank"),
    ("CHIB",  "China Banking Corp."),
    ("MEG",   "Megaworld Corp."),
]
ROOT = Path(__file__).parent
STOOQ_URL = "https://stooq.com/q/d/l/?s={sym}.ph&i=d"
HEADERS = {"User-Agent": "Mozilla/5.0 (ph-stocks-bot)"}
def fetch_one(symbol, name):
    url = STOOQ_URL.format(sym=symbol.lower())
    try:
        req = Request(url, headers=HEADERS)
        with urlopen(req, timeout=20) as resp:
            data = resp.read().decode("utf-8", errors="replace").strip()
    except (HTTPError, URLError, TimeoutError, Exception):
        return None
    if not data or "No data" in data:
        return None
    rows = list(csv.DictReader(StringIO(data)))
    if not rows:
        return None
    try:
        latest = rows[-1]
        prev = rows[-2] if len(rows) > 1 else None
        close = float(latest["Close"])
        prev_close = float(prev["Close"]) if prev else close
        change_pct = ((close - prev_close) / prev_close * 100) if prev_close else 0.0
        return {
            "symbol": symbol,
            "name": name,
            "price": round(close, 2),
            "currency": "PHP",
            "change_pct": round(float(change_pct), 2),
            "previous_close": round(float(prev_close), 2),
        }
    except (KeyError, ValueError, IndexError):
        return None
def fetch_all():
    rows, failed = [], []
    for sym, name in TICKERS:
        r = fetch_one(sym, name)
        if r:
            rows.append(r)
        else:
            failed.append(sym)
    return rows, failed
def write_outputs(rows, failed):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    payload = {"updated_at": now, "count": len(rows), "failed": failed, "stocks": rows}
    (ROOT / "stocks.json").write_text(json.dumps(payload, indent=2))
    lines = [
        "# ph-stocks", "",
        f"Last updated: **{now}**", "",
        f"Showing **{len(rows)}** Philippine Stock Exchange (PSE) tickers.", "",
        "| Symbol | Name | Price | Change % | Prev Close |",
        "|---|---|---:|---:|---:|",
    ]
    for r in sorted(rows, key=lambda x: -abs(x["change_pct"])):
        arrow = "🟢" if r["change_pct"] > 0 else ("🔴" if r["change_pct"] < 0 else "⚪")
        lines.append(f"| {r['symbol']} | {r['name']} | PHP {r['price']:,.2f} | {arrow} {r['change_pct']:+.2f}% | {r['previous_close']:,.2f} |")
    lines.append("")
    lines.append("_Auto-updated every 30 min via GitHub Actions. Source: [Stooq](https://stooq.com)._")
    if failed:
        lines.append("")
        lines.append(f"⚠️ Could not fetch: {', '.join(failed)}")
    (ROOT / "stocks.md").write_text("\n".join(lines))
def main():
    rows, failed = fetch_all()
    if not rows:
        raise SystemExit("No stocks fetched — aborting.")
    write_outputs(rows, failed)
    print(f"Updated {len(rows)} stocks ({len(failed)} failed)")
if __name__ == "__main__":
    main()
