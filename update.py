#!/usr/bin/env python3
"""ph-stocks: PSE stock snapshot + 90-day history via PSE Edge HTML/JSON."""
import json, re, socket, sys, time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).parent
BASE = "https://edge.pse.com.ph"
H = {"User-Agent": "Mozilla/5.0 (compatible; ph-stocks-bot/1.0)",
     "Accept": "text/html", "Accept-Language": "en-US,en;q=0.9"}

T = [
    ("SM",    "SM Investments Corporation",      599, 520),
    ("SMPH",  "SM Prime Holdings, Inc.",        112, 314),
    ("JFC",   "Jollibee Foods Corporation",      86, 158),
    ("AC",    "Ayala Corporation",               57, 180),
    ("ALI",   "Ayala Land, Inc.",               180, 293),
    ("BDO",   "BDO Unibank, Inc.",              260, 468),
    ("BPI",   "Bank of the Philippine Islands", 234, 101),
    ("GLO",   "Globe Telecom, Inc.",             69, 127),
    ("MBT",   "Metropolitan Bank & Trust Co.",  128, 108),
    ("URC",   "Universal Robina Corporation",   124, 167),
    ("TEL",   "PLDT Inc.",                        6, 134),
    ("JGS",   "JG Summit Holdings, Inc.",       210, 207),
    ("LTG",   "LT Group, Inc.",                   12, 225),
    ("PGOLD", "Puregold Price Club, Inc.",      629, 567),
    ("RRHI",  "Robinsons Retail Holdings, Inc.",646, 589),
    ("GTCAP", "GT Capital Holdings, Inc.",      633, 572),
    ("SECB",  "Security Bank Corporation",       32, 114),
    ("CBC",   "China Banking Corporation",      184, 104),
    ("MEG",   "Megaworld Corporation",          127, 215),
    ("SMC",   "San Miguel Corporation",         154, 165),
    ("MER",   "Manila Electric Company",        118, 137),
]

DELAY = 0.6

# ─── HTML parsers (stockData.do) ───
RF = re.compile(r"<th>\s*(?P<l>[^<]+?)\s*</th>\s*<td[^>]*>(?P<v>.*?)</td>", re.DOTALL)
RC = re.compile(r"(?P<d>up|down)\s+(?P<a>[\d,\.]+)\s*\(\s*(?P<p>[\-\d,\.]+)\s*%\)")
RP = re.compile(r"(?P<pr>[\d,\.]+)\s*\((?P<dt>[^)]+)\)")
RA = re.compile(r"As of\s+(?P<ts>[^<]+?)</span>")
RN = re.compile(r'<div class="compInfo">\s*<p[^>]*>(?P<n>[^<]+)</p>', re.DOTALL)
RL = re.compile(r'<img\s+src="(/clogo/[^"]+)"\s+alt="Logo"', re.IGNORECASE)
RX = re.compile(r'[\d\.\-]+')

LB = {"Status":"status","Market Capitalization":"market_cap",
      "Outstanding Shares":"outstanding_shares","Listed Shares":"listed_shares",
      "Issued Shares":"issued_shares","Free Float Level(%)":"free_float_pct",
      "Foreign Ownership Limit(%)":"foreign_ownership_limit_pct",
      "Last Traded Price":"last_traded_price","Open":"open",
      "Previous Close and Date":"_pc","Change(% Change)":"_ch",
      "Value":"value","Volume":"volume","High":"high","Low":"low",
      "Average Price":"average_price","52-Week High":"fifty_two_week_high",
      "52-Week Low":"fifty_two_week_low",
      "P/E Ratio":"pe_ratio","Sector P/E Ratio":"sector_pe_ratio",
      "Book Value":"book_value","P/BV Ratio":"pbv_ratio"}

def _strip(s):
    s = s.replace("&nbsp;"," ").replace("&amp;","&")
    return re.sub(r"<[^>]+>","",s).strip()

def _f(s):
    if s is None: return None
    try: return float(s.replace(",","").strip())
    except ValueError: return None

def parse(html, sym, name):
    o = {"symbol":sym,"name":name,"as_of":None,"logo_url":None}
    m = RA.search(html)
    if m: o["as_of"] = m.group("ts").strip()
    m = RN.search(html)
    if m: o["name"] = m.group("n").strip()
    m = RL.search(html)
    if m: o["logo_url"] = "https://edge.pse.com.ph" + m.group(1)
    for m in RF.finditer(html):
        lbl = m.group("l").strip()
        key = LB.get(lbl)
        if key is None: continue
        t = _strip(m.group("v"))
        if not t: continue
        if key == "_pc":
            pm = RP.search(t)
            if pm:
                o["previous_close"] = _f(pm.group("pr"))
                o["previous_close_date"] = pm.group("dt").strip()
            continue
        if key == "_ch":
            cm = RC.search(t)
            if cm:
                o["change"] = cm.group("d")
                o["change_amount"] = _f(cm.group("a"))
                o["change_pct"] = _f(cm.group("p"))
            continue
        if key.endswith("_pct"):
            n = RX.search(t)
            o[key] = float(n.group(0)) if n else None
        elif any(k in key for k in ("price","open","high","low","value","volume",
                                     "cap","shares","lot","average","_year","ratio","book","par")):
            o[key] = _f(t)
        else:
            o[key] = t
    return o

# ─── Index page parsers ───
RE_IDX_ROW = re.compile(
    r'<td class="label">(?P<n>[^<]+)</td>\s*'
    r'<td[^>]*>(?P<v>[\d,\.]+)</td>\s*'
    r'<td[^>]*>\s*(?P<c>[\-\d,\.]*)\s*</td>\s*'
    r'<td[^>]*>(?P<p>[^<]*)</td>', re.DOTALL)
RM = re.compile(r"MARKET\s*:\s*(\w+)")
RM2 = re.compile(r"As of\s+([^<]+)</th>")
RK = re.compile(r'<td class="alignL">(?P<k>[^<]+)</td>\s*<td class="alignR">\s*(?P<v>[\d,\.]+)\s*</td>')

def parse_idx(html):
    o = {"as_of":None,"market_status":None,"indices":[],"market_summary":{}}
    m = RM.search(html)
    if m: o["market_status"] = m.group(1).strip()
    m = RM2.search(html)
    if m: o["as_of"] = m.group(1).strip()
    for m in RE_IDX_ROW.finditer(html):
        o["indices"].append({"name":m.group("n").strip(),"value":_f(m.group("v")),
                             "change":_f(m.group("c")) if m.group("c").strip() else None,
                             "change_pct":_f(m.group("p").replace("▲","").replace("▼",""))})
    for m in RK.finditer(html):
        o["market_summary"][m.group("k").strip()] = _f(m.group("v"))
    return o

# ─── HTTP ───
def fetch(url):
    with urlopen(Request(url, headers=H), timeout=30) as r:
        return r.read().decode(r.headers.get_content_charset() or "utf-8", errors="replace")

def fetch_history(cid, sid, start_date, end_date):
    """POST to /common/DisclosureCht.ax — returns list of OHLCV dicts."""
    url = f"{BASE}/common/DisclosureCht.ax"
    body = json.dumps({"cmpy_id": cid, "security_id": sid,
                        "startDate": start_date, "endDate": end_date}).encode()
    req = Request(url, data=body, method="POST", headers={
        **H,
        "X-Requested-With": "XMLHttpRequest",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Referer": f"{BASE}/companyPage/stockData.do?cmpy_id={cid}",
    })
    with urlopen(req, timeout=30) as r:
        data = json.loads(r.read().decode("utf-8", errors="replace"))
    rows = []
    for r in data.get("chartData", []):
        # CHART_DATE format: "Aug 27, 2026 00:00:00" → "2026-08-27"
        d = r["CHART_DATE"][:12]  # "Aug 27, 2026"
        try:
            dt = datetime.strptime(d, "%b %d, %Y").strftime("%Y-%m-%d")
        except ValueError:
            continue
        rows.append({
            "d": dt,
            "o": r["OPEN"],
            "h": r["HIGH"],
            "l": r["LOW"],
            "c": r["CLOSE"],
            "v": int(r["VALUE"]),
        })
    return rows

# ─── Renderers ───
def render_json(quotes, index, gen):
    return json.dumps({"generated_utc":gen,"source":BASE,
                       "index":index,"stocks":quotes},
                      indent=2, ensure_ascii=False) + "\n"

def _money(v): return f"₱{v:,.2f}" if v is not None else "—"
def _num(v):
    if v is None: return "—"
    a = abs(v)
    if a >= 1e9: return f"{v/1e9:.2f}B"
    if a >= 1e6: return f"{v/1e6:.2f}M"
    if a >= 1e3: return f"{v/1e3:.1f}K"
    return f"{v:g}"

def _chg(c):
    if not c.get("change"): return "—"
    arrow = "▲" if c["change"]=="up" else "▼"
    sign = "+" if c["change"]=="up" else "-"
    pct = c.get("change_pct"); amt = c.get("change_amount")
    if pct is None or amt is None: return f"{arrow} {c['change']}"
    return f"{arrow} {sign}{abs(amt):.2f} ({sign}{abs(pct):.2f}%)"

def render_md(quotes, index, gen):
    L = ["# ph-stocks — Philippine Stock Exchange snapshot","",
         f"_Last updated: **{gen}** UTC_","",
         "_Source: [PSE Edge](https://edge.pse.com.ph) — refreshed every 30 minutes_",""]
    if index:
        if index.get("market_status"):
            L.append(f"**Market status:** `{index['market_status']}`  ")
            if index.get("as_of"): L.append(f"**As of:** {index['as_of']}  ")
            L.append("")
        if index.get("indices"):
            L += ["## Indices","","| Index | Value | Change | % Change |","|---|---:|---:|---:|"]
            for idx in index["indices"]:
                v   = f"{idx['value']:,.2f}" if idx.get("value") is not None else "—"
                chg = (f"{idx['change']:+,.2f}" if idx.get("change") is not None else "—")
                pct = (f"{idx['change_pct']:+,.2f}%" if idx.get("change_pct") is not None else "—")
                L.append(f"| {idx['name']} | {v} | {chg} | {pct} |")
            L.append("")
        ms = index.get("market_summary") or {}
        if ms:
            L += ["## Market Summary","","| Metric | Value |","|---|---:|"]
            for k,v in ms.items(): L.append(f"| {k} | {_num(v)} |")
            L.append("")
    L += ["## Stocks","",f"_Tracking {len(quotes)} Philippine blue chips._","",
          "| Symbol | Last | Open | High | Low | Prev Close | Change | Volume | Value | Mkt Cap |",
          "|---|---:|---:|---:|---:|---:|---|---:|---:|---:|"]
    for q in sorted(quotes, key=lambda x: x["symbol"]):
        L.append(f"| **{q['symbol']}** | {_money(q.get('last_traded_price'))} | "
                 f"{_money(q.get('open'))} | {_money(q.get('high'))} | {_money(q.get('low'))} | "
                 f"{_money(q.get('previous_close'))} | {_chg(q)} | {_num(q.get('volume'))} | "
                 f"{_num(q.get('value'))} | {_num(q.get('market_cap'))} |")
    L += ["","---","",
          "Auto-updated every 30 minutes by `.github/workflows/update.yml`.  ",
          "Data source: [PSE Edge](https://edge.pse.com.ph).",""]
    return "\n".join(L)

def main():
    gen = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    print(f"[info] ph-stocks update starting at {gen} UTC")
    quotes = []; fails = []
    for i,(sym,name,cid,sid) in enumerate(T):
        try:
            html = fetch(f"{BASE}/companyPage/stockData.do?cmpy_id={cid}")
            q = parse(html, sym, name)
            if q.get("last_traded_price") is None:
                if q.get("status","").lower()=="suspended" and q.get("previous_close") is not None:
                    q["last_traded_price"] = q["previous_close"]
                    q["note"] = "Suspended — showing previous close"
                    quotes.append(q)
                    print(f"[ok] {sym:6s} SUSPENDED (prev ₱{q['previous_close']:.2f})")
                else:
                    fails.append((sym,f"status={q.get('status')}"))
                    print(f"[warn] {sym}: status={q.get('status')}")
            else:
                quotes.append(q)
                print(f"[ok] {sym:6s} -> ₱{q['last_traded_price']:.2f} "
                      f"({q.get('change','?')} {q.get('change_pct','?')}%)")
        except (HTTPError,URLError,socket.timeout) as e:
            fails.append((sym,str(e)))
            print(f"[err] {sym}: {e}", file=sys.stderr)
        except Exception as e:
            fails.append((sym,repr(e)))
            print(f"[err] {sym}: {e!r}", file=sys.stderr)
        if i < len(T)-1: time.sleep(DELAY)
    print(f"[info] fetched {len(quotes)}/{len(T)} stocks; failures: {len(fails)}")
    for s,e in fails: print(f"        {s}: {e}")
    if not quotes:
        print("[fatal] no stocks", file=sys.stderr); return 1

    print("[info] fetching index page...")
    idx = None
    try:
        idx = parse_idx(fetch(f"{BASE}/index/form.do"))
        print(f"[info] index: market={idx.get('market_status')} indices={len(idx.get('indices') or [])}")
    except Exception as e:
        print(f"[warn] index: {e}", file=sys.stderr)

    # ─── History (90 days, all stocks) ───
    end = datetime.now()
    start = end - timedelta(days=90)
    sd = start.strftime("%m-%d-%Y")
    ed = end.strftime("%m-%d-%Y")
    print(f"[info] fetching 90-day history ({sd} → {ed})...")
    history = {"generated_utc": gen, "stocks": {}}
    for j,(sym,_,cid,sid) in enumerate(T):
        try:
            rows = fetch_history(cid, sid, sd, ed)
            history["stocks"][sym] = rows
            print(f"[hist] {sym:6s} {len(rows)} candles")
        except Exception as e:
            print(f"[warn] history {sym}: {e}", file=sys.stderr)
            history["stocks"][sym] = []
        if j < len(T)-1: time.sleep(DELAY)

    # ─── Write outputs ───
    (ROOT/"stocks.json").write_text(render_json(quotes, idx, gen), encoding="utf-8")
    (ROOT/"stocks.md").write_text(render_md(quotes, idx, gen), encoding="utf-8")
    history_path = ROOT/"history.json"
    history_path.write_text(json.dumps(history, separators=(",",":")), encoding="utf-8")
    print(f"[info] wrote stocks.json ({len(quotes)})")
    print(f"[info] wrote stocks.md ({len(quotes)})")
    print(f"[info] wrote history.json ({sum(len(v) for v in history['stocks'].values())} candles)")
    print("[ok] done")
    return 0

if __name__ == "__main__":
    from urllib.error import HTTPError, URLError
    sys.exit(main())
