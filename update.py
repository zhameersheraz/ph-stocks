#!/usr/bin/env python3
import json, re, sys, time
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).parent
BASE = "https://edge.pse.com.ph"
H = {"User-Agent":"Mozilla/5.0 (compatible; ph-stocks-bot/1.0)",
     "Accept":"text/html","Accept-Language":"en-US,en;q=0.9"}

T = [
    ("SM",599),("SMPH",112),("JFC",86),("AC",57),("ALI",180),("BDO",260),
    ("BPI",234),("GLO",69),("MBT",128),("URC",124),("TEL",6),("JGS",210),
    ("LTG",12),("PGOLD",629),("RRHI",646),("GTCAP",633),("SECB",32),
    ("CBC",184),("MEG",127),("SMC",154),("MER",118),
]

N = {"SM":"SM Investments Corporation","SMPH":"SM Prime Holdings, Inc.",
     "JFC":"Jollibee Foods Corporation","AC":"Ayala Corporation",
     "ALI":"Ayala Land, Inc.","BDO":"BDO Unibank, Inc.",
     "BPI":"Bank of the Philippine Islands","GLO":"Globe Telecom, Inc.",
     "MBT":"Metropolitan Bank & Trust Co.","URC":"Universal Robina Corporation",
     "TEL":"PLDT Inc.","JGS":"JG Summit Holdings, Inc.","LTG":"LT Group, Inc.",
     "PGOLD":"Puregold Price Club, Inc.","RRHI":"Robinsons Retail Holdings, Inc.",
     "GTCAP":"GT Capital Holdings, Inc.","SECB":"Security Bank Corporation",
     "CBC":"China Banking Corporation","MEG":"Megaworld Corporation",
     "SMC":"San Miguel Corporation","MER":"Manila Electric Company"}

DELAY = 0.6

RF = re.compile(r"<th>\s*(?P<l>[^<]+?)\s*</th>\s*<td[^>]*>(?P<v>.*?)</td>", re.DOTALL)
RC = re.compile(r"(?P<d>up|down)\s+(?P<a>[\d,\.]+)\s*\(\s*(?P<p>[\-\d,\.]+)\s*%\)")
RP = re.compile(r"(?P<pr>[\d,\.]+)\s*\((?P<dt>[^)]+)\)")
RA = re.compile(r"As of\s+(?P<ts>[^<]+?)</span>")
RN = re.compile(r'<div class="compInfo">\s*<p[^>]*>(?P<n>[^<]+)</p>', re.DOTALL)
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

def parse(html, sym):
    o = {"symbol":sym,"name":N.get(sym,sym),"as_of":None}
    m = RA.search(html)
    if m: o["as_of"] = m.group("ts").strip()
    m = RN.search(html)
    if m: o["name"] = m.group("n").strip()
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

RI = re.compile(r'<td class="label">(?P<n>[^<]+)</td>\s*'
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
    for m in RI.finditer(html):
        o["indices"].append({"name":m.group("n").strip(),"value":_f(m.group("v")),
                             "change":_f(m.group("c")) if m.group("c").strip() else None,
                             "change_pct":_f(m.group("p").replace("▲","").replace("▼",""))})
    for m in RK.finditer(html):
        o["market_summary"][m.group("k").strip()] = _f(m.group("v"))
    return o

def fetch(url):
    with urlopen(Request(url, headers=H), timeout=30) as r:
        return r.read().decode(r.headers.get_content_charset() or "utf-8", errors="replace")

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
            for i in index["indices"]:
                v = f"{i['value']:,.2f}" if i.get("value") is not None else "—"
                c = (f"{i['change']:+,.2f}" if i.get("change") is not None else "—")
                p = (f"{i['change_pct']:+,.2f}%" if i.get("change_pct") is not None else "—")
                L.append(f"| {i['name']} | {v} | {c} | {p} |")
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
                 f"{_money(q.get('previous_close'))} | {_chg(q)} | "
                 f"{_num(q.get('volume'))} | {_num(q.get('value'))} | {_num(q.get('market_cap'))} |")
    L += ["","---","",
          "Auto-updated every 30 minutes by `.github/workflows/update.yml`.  ",
          "Data source: [PSE Edge](https://edge.pse.com.ph).",""]
    return "\n".join(L)

def main():
    gen = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    print(f"[info] ph-stocks update starting at {gen} UTC")
    quotes = []; fails = []
    for i,(sym,cid) in enumerate(T):
        try:
            html = fetch(f"{BASE}/companyPage/stockData.do?cmpy_id={cid}")
            q = parse(html, sym)
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
                print(f"[ok] {sym:6s} -> ₱{q['last_traded_price']:.2f} ({q.get('change','?')} {q.get('change_pct','?')}%)")
        except Exception as e:
            fails.append((sym,str(e)))
            print(f"[err] {sym}: {e}", file=sys.stderr)
        if i < len(T)-1: time.sleep(DELAY)
    print(f"[info] fetched {len(quotes)}/{len(T)}; failures: {len(fails)}")
    for s,e in fails: print(f"        {s}: {e}")
    if not quotes:
        print("[fatal] no stocks", file=sys.stderr); return 1
    print("[info] fetching index...")
    idx = None
    try:
        idx = parse_idx(fetch(f"{BASE}/index/form.do"))
        print(f"[info] index: market={idx.get('market_status')} indices={len(idx.get('indices') or [])}")
    except Exception as e:
        print(f"[warn] index: {e}", file=sys.stderr)
    time.sleep(DELAY)
    payload = {"generated_utc":gen,"source":BASE,"index":idx,"stocks":quotes}
    (ROOT/"stocks.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (ROOT/"stocks.md").write_text(render_md(quotes, idx, gen), encoding="utf-8")
    print(f"[info] wrote stocks.json ({len(quotes)})")
    print(f"[info] wrote stocks.md ({len(quotes)})")
    print("[ok] done")
    return 0

if __name__ == "__main__":
    sys.exit(main())
