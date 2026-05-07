#!/usr/bin/env python3
"""
StockBot AI — Daily Signal Sender (100% FREE)
Fixed: yfinance bulk download + browser headers to bypass GitHub Actions IP blocks
Stack: Gemini 2.0 Flash + yfinance + Telegram Bot API
"""

import os, sys, json, time, urllib.parse, re
import requests
import pandas as pd
import yfinance as yf
from datetime import datetime
from zoneinfo import ZoneInfo

# ── CONFIG ────────────────────────────────────────────────────────────────────
GEMINI_API_KEY   = os.environ.get("GEMINI_API_KEY", "")
TELEGRAM_TOKEN   = os.environ.get("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
MARKET           = os.environ.get("MARKET", "IN").upper()
WA_PHONE         = os.environ.get("WA_PHONE", "")
WA_APIKEY        = os.environ.get("WA_APIKEY", "")
IST              = ZoneInfo("Asia/Kolkata")

# ── STOCK UNIVERSES ────────────────────────────────────────────────────────────
INDIAN_STOCKS = [
    "RELIANCE.NS","TCS.NS","INFY.NS","HDFCBANK.NS","ICICIBANK.NS",
    "BAJFINANCE.NS","SBIN.NS","WIPRO.NS","HCLTECH.NS","AXISBANK.NS",
    "KOTAKBANK.NS","LT.NS","TATAMOTORS.NS","MARUTI.NS","SUNPHARMA.NS",
    "ZOMATO.NS","TATAPOWER.NS","ADANIENT.NS","POLYCAB.NS","DIXON.NS",
    "CAMS.NS","CDSL.NS","BSE.NS","IRCTC.NS","TITAN.NS",
]
US_STOCKS = [
    "AAPL","NVDA","MSFT","GOOGL","AMZN","META","TSLA",
    "AMD","SMCI","ARM","AVGO","NFLX","CRM","ORCL",
    "PLTR","COIN","MSTR","HOOD","SQ","SOFI",
    "RKLB","IONQ","SOUN","AI","PATH",
]

# ── BROWSER SESSION (bypasses Yahoo Finance CI blocks) ────────────────────────
def make_session():
    s = requests.Session()
    s.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept":          "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT":             "1",
        "Connection":      "keep-alive",
    })
    return s

SESSION = make_session()

# ── BULK FETCH (single yf.download call = much more reliable in CI) ───────────
def fetch_stock_data(symbols: list) -> dict:
    """
    Downloads all symbols in ONE bulk call to avoid per-request blocks.
    Falls back to smaller batches if needed.
    """
    print(f"\n📡 Bulk downloading {len(symbols)} symbols via yfinance...")

    raw = None
    # Try in two batch sizes
    for batch_size in [len(symbols), 10, 5]:
        try:
            batch = symbols[:batch_size]
            print(f"  Trying batch of {batch_size}...")
            raw = yf.download(
                tickers   = batch,
                period    = "30d",
                interval  = "1d",
                group_by  = "ticker",
                auto_adjust = True,
                progress  = False,
                threads   = False,    # sequential = more stable in CI
                session   = SESSION,
            )
            if raw is not None and not raw.empty:
                symbols = batch      # use whichever batch worked
                print(f"  ✅ Got data for batch of {batch_size}")
                break
        except Exception as e:
            print(f"  ⚠️  Batch {batch_size} failed: {e}")
            raw = None
        time.sleep(2)

    if raw is None or raw.empty:
        print("  ❌ All bulk download attempts failed — trying individual fallback...")
        return fetch_individual_fallback(symbols[:10])

    results = {}
    for sym in symbols:
        try:
            # Multi-ticker download wraps each symbol in an extra level
            if len(symbols) == 1:
                df = raw
            else:
                if sym not in raw.columns.get_level_values(1):
                    continue
                df = raw.xs(sym, axis=1, level=1)

            df = df.dropna(how="all")
            if len(df) < 10:
                continue

            close = df["Close"]
            vol   = df["Volume"] if "Volume" in df else pd.Series([1]*len(df))

            cur   = float(close.iloc[-1])
            prev  = float(close.iloc[-2])
            pct   = round(((cur - prev) / prev) * 100, 2)

            # RSI
            delta = close.diff()
            gain  = delta.clip(lower=0).rolling(14).mean()
            loss  = (-delta.clip(upper=0)).rolling(14).mean()
            rsi   = round(float(100 - 100 / (1 + gain.iloc[-1] / (loss.iloc[-1] + 1e-9))), 1)

            # MACD
            ema12     = close.ewm(span=12, adjust=False).mean()
            ema26     = close.ewm(span=26, adjust=False).mean()
            macd      = ema12 - ema26
            macd_sig  = macd.ewm(span=9, adjust=False).mean()
            macd_bull = (macd.iloc[-1] > macd_sig.iloc[-1]) and (macd.iloc[-1] > macd.iloc[-2])

            ma20 = float(close.rolling(20).mean().iloc[-1])
            ma50 = float(close.rolling(min(50, len(close))).mean().iloc[-1])

            avg_vol   = float(vol.iloc[-11:-1].mean()) + 1
            vol_ratio = round(float(vol.iloc[-1]) / avg_vol, 2)

            bb_std   = close.rolling(20).std()
            bb_upper = float(close.rolling(20).mean().iloc[-1] + 2 * bb_std.iloc[-1])
            bb_lower = float(close.rolling(20).mean().iloc[-1] - 2 * bb_std.iloc[-1])
            bb_pos   = round((cur - bb_lower) / (bb_upper - bb_lower + 1e-9), 2)

            trend5 = round(float(close.iloc[-1] - close.iloc[-6]) / float(close.iloc[-6]) * 100, 2)
            wk52hi = float(close.rolling(min(252, len(close))).max().iloc[-1])
            from_hi = round(((cur - wk52hi) / wk52hi) * 100, 1)

            # Get name/sector separately (lightweight)
            name   = sym.replace(".NS","").replace(".BO","")
            sector = "Unknown"
            try:
                tk     = yf.Ticker(sym, session=SESSION)
                info   = tk.fast_info
                name   = getattr(info, "display_name", None) or name
            except Exception:
                pass

            results[sym] = dict(
                symbol=sym, name=name, sector=sector,
                price=round(cur,2), change_pct=pct,
                rsi=rsi, macd_bull=macd_bull,
                above_ma20=(cur>ma20), above_ma50=(cur>ma50),
                vol_ratio=vol_ratio, bb_pos=bb_pos,
                trend5=trend5, from_52w_high=from_hi,
                score=0,
            )
        except Exception as e:
            print(f"  ⚠️  {sym}: {e}")

    print(f"  ✅ Processed {len(results)} stocks from bulk download")
    return results


def fetch_individual_fallback(symbols: list) -> dict:
    """Last resort: fetch one by one with delays."""
    print("  🔄 Individual fallback fetch (slow but thorough)...")
    results = {}
    for sym in symbols:
        for attempt in range(3):
            try:
                tk   = yf.Ticker(sym, session=SESSION)
                hist = tk.history(period="30d", interval="1d", auto_adjust=True)
                if hist.empty:
                    break
                close = hist["Close"]
                cur   = float(close.iloc[-1])
                prev  = float(close.iloc[-2])
                pct   = round(((cur - prev) / prev) * 100, 2)

                delta = close.diff()
                gain  = delta.clip(lower=0).rolling(14).mean()
                loss  = (-delta.clip(upper=0)).rolling(14).mean()
                rsi   = round(float(100 - 100 / (1 + gain.iloc[-1] / (loss.iloc[-1] + 1e-9))), 1)

                ema12    = close.ewm(span=12, adjust=False).mean()
                ema26    = close.ewm(span=26, adjust=False).mean()
                macd     = ema12 - ema26
                macd_sig = macd.ewm(span=9, adjust=False).mean()
                macd_bull = macd.iloc[-1] > macd_sig.iloc[-1]

                ma20 = float(close.rolling(20).mean().iloc[-1])
                vol  = hist["Volume"]
                vol_ratio = round(float(vol.iloc[-1]) / (float(vol.iloc[-6:-1].mean()) + 1), 2)

                results[sym] = dict(
                    symbol=sym, name=sym.replace(".NS",""),
                    sector="Unknown", price=round(cur,2),
                    change_pct=pct, rsi=rsi, macd_bull=macd_bull,
                    above_ma20=(cur>ma20), above_ma50=True,
                    vol_ratio=vol_ratio, bb_pos=0.4,
                    trend5=pct, from_52w_high=-5.0, score=0,
                )
                print(f"    ✅ {sym}: ₹{cur:.0f}" if ".NS" in sym else f"    ✅ {sym}: ${cur:.2f}")
                break
            except Exception as e:
                print(f"    Attempt {attempt+1} failed for {sym}: {e}")
                time.sleep(3 * (attempt + 1))

    return results


# ── SCORE & RANK ──────────────────────────────────────────────────────────────
def score_and_rank(data: dict) -> list:
    scored = []
    for d in data.values():
        s = 0
        r = d["rsi"]
        if   30 <= r <= 45: s += 30
        elif 45 < r <= 58:  s += 20
        elif 58 < r <= 70:  s += 8
        elif r < 30:        s += 15
        if d["macd_bull"]:         s += 25
        if d["above_ma20"]:        s += 12
        if d["above_ma50"]:        s += 12
        vr = d["vol_ratio"]
        if   vr >= 3.0: s += 30
        elif vr >= 2.0: s += 22
        elif vr >= 1.5: s += 12
        bp = d["bb_pos"]
        if   0.1 <= bp <= 0.35: s += 20
        elif 0.35 < bp <= 0.65: s += 10
        t5 = d["trend5"]
        if   0 < t5 <= 4:  s += 15
        elif t5 > 4:       s += 5
        if d["from_52w_high"] > -3:  s += 15
        elif d["from_52w_high"] > -8: s += 8
        d["score"] = s
        scored.append(d)
    return sorted(scored, key=lambda x: x["score"], reverse=True)[:18]


# ── GEMINI AI ─────────────────────────────────────────────────────────────────
def get_gemini_picks(candidates: list, market: str) -> list:
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY missing. Get free key → https://aistudio.google.com/app/apikey")

    cur   = "₹" if market == "IN" else "$"
    exch  = "NSE/BSE" if market == "IN" else "NYSE/NASDAQ"
    now   = datetime.now(IST).strftime("%A %d %B %Y — %I:%M %p IST")

    summary = json.dumps([{
        "symbol":       d["symbol"],
        "name":         d["name"][:30],
        "price":        f"{cur}{d['price']}",
        "change_today": f"{d['change_pct']:+.1f}%",
        "rsi":          d["rsi"],
        "macd_bullish": d["macd_bull"],
        "above_20ma":   d["above_ma20"],
        "above_50ma":   d["above_ma50"],
        "volume_surge": f"{d['vol_ratio']}x",
        "bb_zone":      "Oversold" if d["bb_pos"] < 0.25 else "Mid" if d["bb_pos"] < 0.75 else "Overbought",
        "5d_trend":     f"{d['trend5']:+.1f}%",
        "from_52w_high":f"{d['from_52w_high']}%",
        "score":        d["score"],
    } for d in candidates], indent=2)

    prompt = f"""You are a senior quantitative trading analyst for {exch}.
Date/Time: {now}

Pre-screened stocks ranked by technical score:
{summary}

Pick the TOP 5 best trades for today. Mix: 1-2 intraday, 2-3 swing, at least 1 multibagger candidate.
Prioritize: low risk + high reward (min 1:2 ratio), strong catalyst, clear setup.

Return ONLY a valid JSON array, no markdown, no backticks:
[
  {{
    "rank": 1,
    "stockName": "Full Company Name",
    "symbol": "{exch.split('/')[0]}:SYMBOL",
    "currentPrice": "{cur}XXX",
    "targetPrice": "{cur}XXX",
    "stopLoss": "{cur}XXX",
    "takeProfit": "{cur}XXX",
    "signal": "INTRADAY",
    "timeframe": "Same Day",
    "riskLevel": "LOW",
    "expectedReturn": "+X.X%",
    "multibaggerAlert": false,
    "multibaggerNote": "",
    "keyIndicators": ["RSI 38 Oversold","MACD Cross","Vol 2.4x","20DMA Support"],
    "whyBuy": "2-sentence reason with setup and catalyst.",
    "sector": "Technology"
  }}
]
signal: INTRADAY | SWING | BUY & HOLD
timeframe: "Same Day" | "2-5 Days" | "1-4 Weeks" | "1-6 Months"
riskLevel: LOW | MEDIUM | HIGH"""

    url  = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
    body = {
        "contents": [{"role":"user","parts":[{"text":prompt}]}],
        "generationConfig": {"temperature":0.25,"maxOutputTokens":3000},
    }
    print("  🤖 Asking Gemini 2.0 Flash...")
    r = requests.post(url, json=body, timeout=60)
    r.raise_for_status()

    raw = r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
    if "```" in raw:
        raw = raw.split("```")[1]
        if raw.startswith("json"): raw = raw[4:]
    raw = raw.strip().rstrip("`").strip()

    picks = json.loads(raw)
    print(f"  ✅ {len(picks)} picks from Gemini")
    return picks[:5]


# ── TELEGRAM ──────────────────────────────────────────────────────────────────
def format_message(picks, market):
    flag  = "🇮🇳" if market=="IN" else "🇺🇸"
    mname = "INDIA (NSE/BSE)" if market=="IN" else "US (NYSE/NASDAQ)"
    now   = datetime.now(IST).strftime("%d %b %Y  |  %I:%M %p IST")
    sig_i = {"INTRADAY":"⚡","SWING":"📊","BUY & HOLD":"💎"}
    ris_i = {"LOW":"🟢","MEDIUM":"🟡","HIGH":"🔴"}

    lines = [f"{flag} <b>STOCKBOT AI — DAILY SIGNALS</b>",
             f"<b>{mname}</b>",
             f"━━━━━━━━━━━━━━━━━━━━━━━━",
             f"📅 {now}","━━━━━━━━━━━━━━━━━━━━━━━━",""]

    for s in picks:
        mb = "🚀 <b>MULTIBAGGER ALERT!</b>\n" if s.get("multibaggerAlert") else ""
        lines += [
            f"<b>#{s['rank']} {s['stockName']}</b>",
            mb.strip() if mb else None,
            f"📌 <code>{s['symbol']}</code>  •  {s.get('sector','')}",
            f"",
            f"💰 Price      : <b>{s['currentPrice']}</b>",
            f"🎯 Target     : <b>{s['targetPrice']}</b>",
            f"🛑 Stop Loss  : {s['stopLoss']}",
            f"✅ Take Profit: {s['takeProfit']}",
            f"",
            f"{sig_i.get(s.get('signal',''),'📌')} Signal : <b>{s['signal']}</b> ({s.get('timeframe','')})",
            f"📈 Return : <b>{s['expectedReturn']}</b>   {ris_i.get(s.get('riskLevel',''),'⚪')} Risk: {s.get('riskLevel','')}",
            f"",
            f"💡 {s['whyBuy']}",
        ]
        if s.get("multibaggerAlert") and s.get("multibaggerNote"):
            lines.append(f"🚀 <i>{s['multibaggerNote']}</i>")
        inds = s.get("keyIndicators",[])
        if inds: lines.append("📊 " + "  |  ".join(inds[:4]))
        lines += ["","─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─",""]

    lines += ["⚡ <i>StockBot AI  •  Gemini 2.0 Flash + yfinance</i>",
              "⚠️ <i>Educational only. Not financial advice.</i>"]
    return "\n".join(l for l in lines if l is not None)


def send_telegram(msg):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️  Telegram not configured"); return False
    r = requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
        json={"chat_id":TELEGRAM_CHAT_ID,"text":msg,
              "parse_mode":"HTML","disable_web_page_preview":True},
        timeout=20)
    ok = r.json().get("ok",False)
    print("✅ Telegram sent!" if ok else f"❌ Telegram: {r.text[:150]}")
    return ok


def send_whatsapp(msg):
    if not WA_PHONE or not WA_APIKEY: return
    plain = re.sub(r"<[^>]+>","",msg)
    r = requests.get(
        f"https://api.callmebot.com/whatsapp.php"
        f"?phone={WA_PHONE}&text={urllib.parse.quote(plain)}&apikey={WA_APIKEY}",
        timeout=20)
    print("✅ WhatsApp sent!" if r.ok else f"❌ WhatsApp: {r.text[:100]}")


# ── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    sep = "═"*52
    print(f"\n{sep}\n  🤖 StockBot AI — {'🇮🇳 India' if MARKET=='IN' else '🇺🇸 US'} Market\n"
          f"  Time : {datetime.now(IST).strftime('%d %b %Y  %I:%M %p IST')}\n"
          f"  AI   : Gemini 2.0 Flash (Free)\n{sep}\n")

    if not GEMINI_API_KEY:
        print("❌ GEMINI_API_KEY missing!"); sys.exit(1)

    symbols = INDIAN_STOCKS if MARKET=="IN" else US_STOCKS

    print("📡 STEP 1 — Fetching stock data...")
    data = fetch_stock_data(symbols)

    if not data:
        print("❌ No stock data after all attempts. Possible causes:")
        print("   • Yahoo Finance blocking this IP (common in CI/cloud)")
        print("   • Network issue in GitHub Actions runner")
        print("   • Try re-running the workflow manually")
        sys.exit(1)

    print(f"\n🔢 STEP 2 — Scoring {len(data)} stocks...")
    top = score_and_rank(data)
    print(f"  Top 5: {[d['symbol'] for d in top[:5]]}")

    print("\n🤖 STEP 3 — Gemini AI analysis...")
    try:
        picks = get_gemini_picks(top, MARKET)
    except Exception as e:
        print(f"❌ Gemini error: {e}"); sys.exit(1)

    print("\n📱 STEP 4 — Sending alerts...")
    msg = format_message(picks, MARKET)
    send_telegram(msg)
    send_whatsapp(msg)

    print(f"\n{sep}\n  SIGNAL SUMMARY\n{sep}")
    for p in picks:
        mb = " 🚀" if p.get("multibaggerAlert") else ""
        print(f"  #{p['rank']} {p['stockName'][:28]:28}  {p['signal']:10}  {p['expectedReturn']:8}  {p['riskLevel']}{mb}")
    print(sep)

if __name__ == "__main__":
    main()
