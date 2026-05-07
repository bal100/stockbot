#!/usr/bin/env python3
"""
StockBot AI — Daily Signal Sender (100% FREE)
Stack: Gemini 2.0 Flash + yfinance (curl_cffi) + Telegram
"""

import os, sys, json, time, re, urllib.parse
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

# ── STOCK UNIVERSES ───────────────────────────────────────────────────────────
INDIAN_STOCKS = [
    "RELIANCE.NS","TCS.NS","INFY.NS","HDFCBANK.NS","ICICIBANK.NS",
    "BAJFINANCE.NS","SBIN.NS","WIPRO.NS","HCLTECH.NS","AXISBANK.NS",
    "KOTAKBANK.NS","LT.NS","TATAMOTORS.NS","MARUTI.NS","SUNPHARMA.NS",
    "ZOMATO.NS","TATAPOWER.NS","ADANIENT.NS","POLYCAB.NS","DIXON.NS",
    "CAMS.NS","CDSL.NS","IRCTC.NS","TITAN.NS","NESTLEIND.NS",
]
US_STOCKS = [
    "AAPL","NVDA","MSFT","GOOGL","AMZN","META","TSLA",
    "AMD","SMCI","ARM","AVGO","NFLX","CRM","ORCL","NOW",
    "PLTR","COIN","MSTR","HOOD","SQ","SOFI","RKLB","IONQ","SOUN","AI",
]

# ── FETCH DATA ────────────────────────────────────────────────────────────────
def compute_indicators(close: pd.Series, volume: pd.Series) -> dict:
    """All technical indicators from a close price series."""
    cur  = float(close.iloc[-1])
    prev = float(close.iloc[-2])
    pct  = round((cur - prev) / prev * 100, 2)

    # RSI 14
    delta = close.diff()
    gain  = delta.clip(lower=0).rolling(14).mean()
    loss  = (-delta.clip(upper=0)).rolling(14).mean()
    rsi   = round(float(100 - 100 / (1 + gain.iloc[-1] / (loss.iloc[-1] + 1e-9))), 1)

    # MACD 12/26/9
    ema12     = close.ewm(span=12, adjust=False).mean()
    ema26     = close.ewm(span=26, adjust=False).mean()
    macd_line = ema12 - ema26
    macd_sig  = macd_line.ewm(span=9, adjust=False).mean()
    macd_bull = bool(macd_line.iloc[-1] > macd_sig.iloc[-1] and
                     macd_line.iloc[-1] > macd_line.iloc[-2])

    # Moving averages
    ma20 = float(close.rolling(20).mean().iloc[-1])
    ma50 = float(close.rolling(min(50, len(close))).mean().iloc[-1])

    # Bollinger bands
    bb_std   = close.rolling(20).std().iloc[-1]
    bb_upper = ma20 + 2 * float(bb_std)
    bb_lower = ma20 - 2 * float(bb_std)
    bb_pos   = round((cur - bb_lower) / (bb_upper - bb_lower + 1e-9), 2)

    # Volume ratio (today vs 10-day avg)
    avg_vol   = float(volume.iloc[-11:-1].mean()) + 1
    vol_ratio = round(float(volume.iloc[-1]) / avg_vol, 2)

    # Trend and 52w
    trend5  = round((cur - float(close.iloc[-6])) / float(close.iloc[-6]) * 100, 2)
    wk52hi  = float(close.rolling(min(252, len(close))).max().iloc[-1])
    from_hi = round((cur - wk52hi) / wk52hi * 100, 1)

    return dict(
        price=round(cur, 2), change_pct=pct,
        rsi=rsi, macd_bull=macd_bull,
        above_ma20=(cur > ma20), above_ma50=(cur > ma50),
        vol_ratio=vol_ratio, bb_pos=bb_pos,
        trend5=trend5, from_52w_high=from_hi,
    )


def fetch_stock_data(symbols: list) -> dict:
    """
    Download all symbols in one bulk yf.download() call.
    DO NOT pass session= — newer yfinance uses curl_cffi internally.
    Falls back to smaller batches if needed.
    """
    results = {}

    for batch in [symbols, symbols[:15], symbols[:8]]:
        print(f"  Trying bulk download: {len(batch)} symbols...")
        try:
            raw = yf.download(
                tickers     = batch,
                period      = "60d",
                interval    = "1d",
                group_by    = "ticker",
                auto_adjust = True,
                progress    = False,
                threads     = False,   # sequential = stable in CI
                # NO session= parameter — let yfinance handle auth
            )
        except Exception as e:
            print(f"  ✗ Batch of {len(batch)} failed: {e}")
            time.sleep(3)
            continue

        if raw is None or raw.empty:
            print(f"  ✗ Empty response for batch of {len(batch)}")
            time.sleep(3)
            continue

        print(f"  ✓ Got raw data — processing...")

        for sym in batch:
            try:
                # Single-ticker download has no extra column level
                if len(batch) == 1:
                    df = raw
                else:
                    lvl1 = raw.columns.get_level_values(1)
                    if sym not in lvl1:
                        continue
                    df = raw.xs(sym, axis=1, level=1)

                df = df.dropna(how="all")
                if len(df) < 15:
                    continue

                close  = df["Close"].dropna()
                volume = df["Volume"].fillna(0)
                if len(close) < 15:
                    continue

                ind = compute_indicators(close, volume)
                results[sym] = dict(
                    symbol=sym,
                    name=sym.replace(".NS","").replace(".BO",""),
                    sector="Unknown",
                    score=0,
                    **ind,
                )
            except Exception as e:
                print(f"    ⚠ {sym}: {e}")

        if results:
            print(f"  ✅ Successfully processed {len(results)} stocks")
            return results

        print(f"  ✗ No valid stocks from this batch, trying smaller...")
        time.sleep(5)

    return results   # empty dict if everything failed


# ── SCORE & RANK ──────────────────────────────────────────────────────────────
def score_and_rank(data: dict) -> list:
    for d in data.values():
        s  = 0
        r  = d["rsi"]
        if   30 <= r <= 45: s += 30
        elif 45 <  r <= 58: s += 20
        elif 58 <  r <= 70: s += 8
        elif r < 30:        s += 15

        if d["macd_bull"]:        s += 25
        if d["above_ma20"]:       s += 12
        if d["above_ma50"]:       s += 12

        vr = d["vol_ratio"]
        if   vr >= 3.0: s += 30
        elif vr >= 2.0: s += 22
        elif vr >= 1.5: s += 12

        bp = d["bb_pos"]
        if   0.10 <= bp <= 0.35: s += 20
        elif 0.35 <  bp <= 0.65: s += 10

        t5 = d["trend5"]
        if 0 < t5 <= 4: s += 15
        elif t5 > 4:    s += 5

        if d["from_52w_high"] > -3:  s += 15
        elif d["from_52w_high"] > -8: s += 8

        d["score"] = s

    return sorted(data.values(), key=lambda x: x["score"], reverse=True)[:18]


# ── GEMINI AI ─────────────────────────────────────────────────────────────────
def get_gemini_picks(candidates: list, market: str) -> list:
    cur  = "₹" if market == "IN" else "$"
    exch = "NSE/BSE" if market == "IN" else "NYSE/NASDAQ"
    now  = datetime.now(IST).strftime("%A %d %B %Y — %I:%M %p IST")

    summary = json.dumps([{
        "symbol":        d["symbol"],
        "name":          d["name"][:30],
        "price":         f"{cur}{d['price']}",
        "change_today":  f"{d['change_pct']:+.1f}%",
        "rsi":           d["rsi"],
        "macd_bullish":  d["macd_bull"],
        "above_20ma":    d["above_ma20"],
        "above_50ma":    d["above_ma50"],
        "volume_surge":  f"{d['vol_ratio']}x avg",
        "bb_zone":       "Oversold" if d["bb_pos"]<0.25 else "Mid" if d["bb_pos"]<0.75 else "Overbought",
        "5d_trend":      f"{d['trend5']:+.1f}%",
        "from_52w_high": f"{d['from_52w_high']}%",
        "score":         d["score"],
    } for d in candidates], indent=2)

    prompt = f"""You are a senior quantitative trading analyst for {exch}.
Date/Time: {now}

Pre-screened stocks ranked by multi-factor technical score:
{summary}

Select the TOP 5 best trades for today. Requirements:
- At least 1-2 INTRADAY signals
- At least 1-2 SWING signals  
- At least 1 potential MULTIBAGGER (long-term, low price, high upside)
- Prioritise: LOW risk, HIGH reward (min 1:2 risk/reward ratio)
- All price targets must be realistic based on the current price shown

Return ONLY a valid JSON array. No markdown, no backticks, nothing else:
[
  {{
    "rank": 1,
    "stockName": "Full Company Name",
    "symbol": "{exch.split('/')[0]}:TICKER",
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
    "keyIndicators": ["RSI 38 Oversold","MACD Crossover","Volume 2.4x","20DMA Support"],
    "whyBuy": "2-sentence reason: technical setup + catalyst.",
    "sector": "Technology"
  }}
]

signal must be: INTRADAY | SWING | BUY & HOLD
timeframe must be: "Same Day" | "2-5 Days" | "1-4 Weeks" | "1-6 Months"
riskLevel must be: LOW | MEDIUM | HIGH"""

    url  = (f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}")
    body = {
        "contents": [{"role":"user","parts":[{"text":prompt}]}],
        "generationConfig": {"temperature":0.2,"maxOutputTokens":3000},
    }

    print("  🤖 Calling Gemini 2.0 Flash...")
    r = requests.post(url, json=body, timeout=60)
    r.raise_for_status()

    raw = r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()

    # Strip any markdown fences Gemini might add despite instructions
    if "```" in raw:
        parts = raw.split("```")
        raw   = parts[1] if len(parts) > 1 else raw
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip().strip("`").strip()

    picks = json.loads(raw)
    assert isinstance(picks, list) and len(picks) > 0, "Empty picks list"
    print(f"  ✅ {len(picks)} picks received from Gemini")
    return picks[:5]


# ── FORMAT MESSAGE ────────────────────────────────────────────────────────────
def format_message(picks: list, market: str) -> str:
    flag  = "🇮🇳" if market == "IN" else "🇺🇸"
    mname = "INDIA (NSE/BSE)" if market == "IN" else "US (NYSE/NASDAQ)"
    now   = datetime.now(IST).strftime("%d %b %Y  |  %I:%M %p IST")
    s_ico = {"INTRADAY":"⚡","SWING":"📊","BUY & HOLD":"💎"}
    r_ico = {"LOW":"🟢","MEDIUM":"🟡","HIGH":"🔴"}

    lines = [
        f"{flag} <b>STOCKBOT AI — DAILY SIGNALS</b>",
        f"<b>{mname}</b>",
        f"━━━━━━━━━━━━━━━━━━━━━━━━",
        f"📅 {now}",
        f"━━━━━━━━━━━━━━━━━━━━━━━━",
        "",
    ]
    for s in picks:
        if s.get("multibaggerAlert"):
            lines.append("🚀 <b>⭐ MULTIBAGGER ALERT! ⭐</b>")
        lines += [
            f"<b>#{s['rank']}  {s['stockName']}</b>",
            f"📌 <code>{s['symbol']}</code>  •  {s.get('sector','')}",
            "",
            f"💰 Price       : <b>{s['currentPrice']}</b>",
            f"🎯 Target      : <b>{s['targetPrice']}</b>",
            f"🛑 Stop Loss   : {s['stopLoss']}",
            f"✅ Take Profit : {s['takeProfit']}",
            "",
            f"{s_ico.get(s.get('signal',''),'📌')} Signal  : <b>{s.get('signal','')}</b>  ({s.get('timeframe','')})",
            f"📈 Return  : <b>{s.get('expectedReturn','')}</b>   {r_ico.get(s.get('riskLevel',''),'⚪')} Risk: {s.get('riskLevel','')}",
            "",
            f"💡 {s.get('whyBuy','')}",
        ]
        if s.get("multibaggerAlert") and s.get("multibaggerNote"):
            lines.append(f"🚀 <i>{s['multibaggerNote']}</i>")
        inds = s.get("keyIndicators", [])
        if inds:
            lines.append("📊 " + "  |  ".join(inds[:4]))
        lines += ["", "─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─", ""]

    lines += [
        "⚡ <i>StockBot AI  •  Gemini 2.0 Flash + yfinance</i>",
        "⚠️ <i>Educational only. Not financial advice.</i>",
    ]
    return "\n".join(lines)


# ── SEND ──────────────────────────────────────────────────────────────────────
def send_telegram(msg: str) -> bool:
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️  Telegram not configured (TELEGRAM_TOKEN / TELEGRAM_CHAT_ID missing)")
        return False
    r = requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
        json={
            "chat_id":                  TELEGRAM_CHAT_ID,
            "text":                     msg,
            "parse_mode":               "HTML",
            "disable_web_page_preview": True,
        },
        timeout=20,
    )
    data = r.json()
    if data.get("ok"):
        print("✅ Telegram — sent!")
        return True
    print(f"❌ Telegram error: {data.get('description','unknown')}")
    return False


def send_whatsapp(msg: str):
    if not WA_PHONE or not WA_APIKEY:
        return
    plain = re.sub(r"<[^>]+>", "", msg)
    r = requests.get(
        "https://api.callmebot.com/whatsapp.php",
        params={"phone": WA_PHONE, "text": plain, "apikey": WA_APIKEY},
        timeout=20,
    )
    print("✅ WhatsApp — sent!" if r.ok else f"❌ WhatsApp error: {r.text[:100]}")


# ── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    sep = "═" * 54
    print(f"\n{sep}")
    print(f"  🤖 StockBot AI  |  {'🇮🇳 India (NSE/BSE)' if MARKET=='IN' else '🇺🇸 US (NYSE/NASDAQ)'}")
    print(f"  🕐 {datetime.now(IST).strftime('%d %b %Y  %I:%M %p IST')}")
    print(f"  ⚙️  AI: Gemini 2.0 Flash  |  Data: yfinance (curl_cffi)")
    print(f"{sep}\n")

    if not GEMINI_API_KEY:
        print("❌ GEMINI_API_KEY not set → get free key at aistudio.google.com")
        sys.exit(1)

    symbols = INDIAN_STOCKS if MARKET == "IN" else US_STOCKS

    # ── Step 1: Fetch ────────────────────────────────────────────────────────
    print("📡 STEP 1 — Fetching stock data (no session passthrough)...")
    data = fetch_stock_data(symbols)

    if not data:
        print("\n❌ FATAL: Could not fetch any stock data.")
        print("   Likely cause: yfinance / Yahoo Finance issue on this runner.")
        print("   Try: re-run the workflow manually in GitHub Actions.")
        sys.exit(1)

    # ── Step 2: Score ────────────────────────────────────────────────────────
    print(f"\n🔢 STEP 2 — Scoring {len(data)} stocks...")
    top = score_and_rank(data)
    print(f"  Top candidates: {[d['symbol'] for d in top[:5]]}")

    # ── Step 3: Gemini ───────────────────────────────────────────────────────
    print("\n🤖 STEP 3 — Gemini AI analysis...")
    try:
        picks = get_gemini_picks(top, MARKET)
    except Exception as e:
        print(f"❌ Gemini failed: {e}")
        sys.exit(1)

    # ── Step 4: Send ─────────────────────────────────────────────────────────
    print("\n📱 STEP 4 — Sending alerts...")
    msg = format_message(picks, MARKET)
    send_telegram(msg)
    send_whatsapp(msg)

    # ── Summary ──────────────────────────────────────────────────────────────
    print(f"\n{sep}\n  SIGNAL SUMMARY\n{sep}")
    for p in picks:
        mb = " 🚀 MULTIBAGGER" if p.get("multibaggerAlert") else ""
        print(f"  #{p['rank']}  {p['stockName'][:26]:26}  "
              f"{p['signal']:10}  {p['expectedReturn']:8}  "
              f"Risk:{p['riskLevel']}{mb}")
    print(f"{sep}\n")


if __name__ == "__main__":
    main()
