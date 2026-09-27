#!/usr/bin/env python3
"""ph-stocks: PSE stock snapshot via Yahoo Finance (yfinance)."""

import json
from datetime import datetime, timezone
from pathlib import Path

import yfinance as yf

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


def fetch_one(symbol, name):
    for suffix in (".PS", ""):
        sym = f"{symbol}{suffix}"
        try:
            t = yf.Ticker(sym)
            fast = getattr(t, "fast_info", None)
            if fast is None:
                continue
            price = fast.get("last_price") or fast.get("previous_close")
            prev_close = fast.get("previous_close")
            currency = fast.get("currency")
            if price is None or prev_close is None or prev_close == 0:
                continue
            change_pct = (float(price) - float(prev_close)) / float(prev_close) * 100
            return {
                "symbol": symbol,
                "name": name,
                "price": round(float(price), 2),
                "currency": currency,
                "change_pct": round(float(change_pct), 2),
                "previous_close": round(float(prev_close), 2),
            }
        except Exception:
            continue
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
        lines.append(f"| {r['symbol']} | {r['name']} | {r['currency']} {r['price']:,.2f} | {arrow} {r['change_pct']:+.2f}% | {r['previous_close']:,.2f} |")
    lines.append("")
    lines.append("_Auto-updated every 30 min via GitHub Actions. Source: [Yahoo Finance](https://finance.yahoo.com/) via [yfinance](https://github.com/ranaroussi/yfinance)._")
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
