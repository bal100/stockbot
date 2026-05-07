#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════╗
║       StockBot AI — Daily Signal Sender (100% FREE)         ║
║  Stack: Gemini 2.0 Flash + yfinance + Telegram Bot API      ║
║  Scheduler: GitHub Actions (cron, no server needed)         ║
╚══════════════════════════════════════════════════════════════╝

Setup:
  1. Get free Gemini API key → https://aistudio.google.com/app/apikey
  2. Create Telegram bot → message @BotFather on Telegram → /newbot
  3. Get your chat_id → message @userinfobot on Telegram
  4. Add secrets to GitHub repo → Settings > Secrets and variables > Actions
  5. Push this file + .github/workflows/stock-signals.yml to repo
  6. Done! Signals run automatically at 9:00 AM IST and 6:00 PM IST

Environment Variables (set as GitHub Secrets):
  GEMINI_API_KEY    - Google AI Studio free API key
  TELEGRAM_TOKEN    - Telegram bot token from @BotFather
  TELEGRAM_CHAT_ID  - Your Telegram chat/channel ID
  MARKET            - "IN" for Indian, "US" for US (set by workflow)
  WA_PHONE          - (Optional) WhatsApp number with country code e.g. 919876543210
  WA_APIKEY         - (Optional) CallMeBot API key from callmebot.com
"""

import os
import sys
import json
import time
import urllib.parse
import requests
import pandas as pd
import yfinance as yf
from datetime import datetime
from zoneinfo import ZoneInfo

# ── CONFIGURATION ─────────────────────────────────────────────────────────────
GEMINI_API_KEY   = os.environ.get("GEMINI_API_KEY", "")
TELEGRAM_TOKEN   = os.environ.get("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
MARKET           = os.environ.get("MARKET", "IN").upper()
WA_PHONE         = os.environ.get("WA_PHONE", "")
WA_APIKEY        = os.environ.get("WA_APIKEY", "")

IST = ZoneInfo("Asia/Kolkata")

# ── STOCK UNIVERSES ────────────────────────────────────────────────────────────
INDIAN_STOCKS = [
    # Large Cap Blue Chips
    "RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS",
    "BAJFINANCE.NS", "SBIN.NS", "HINDUNILVR.NS", "WIPRO.NS", "HCLTECH.NS",
    "AXISBANK.NS", "KOTAKBANK.NS", "LT.NS", "TATAMOTORS.NS", "MARUTI.NS",
    # Mid Cap Growth
    "ZOMATO.NS", "NYKAA.NS", "PAYTM.NS", "IRCTC.NS", "DMART.NS",
    "TATAPOWER.NS", "ADANIENT.NS", "ADANIGREEN.NS", "POLYCAB.NS", "DIXON.NS",
    "CAMS.NS", "ANGELONE.NS", "CDSL.NS", "BSE.NS", "MCX.NS",
    # Pharma/IT/Auto
    "SUNPHARMA.NS", "CIPLA.NS", "DRREDDY.NS", "TECHM.NS", "MPHASIS.NS",
    "COFORGE.NS", "PERSISTENT.NS", "TITAN.NS", "NESTLEIND.NS", "PIDILITIND.NS",
]

US_STOCKS = [
    # Mega Cap Tech
    "AAPL", "NVDA", "MSFT", "GOOGL", "AMZN", "META", "TSLA",
    # AI / Semiconductors
    "AMD", "SMCI", "ARM", "AVGO", "QCOM", "INTC", "MU",
    # High Growth
    "NFLX", "CRM", "ADBE", "ORCL", "NOW", "SNOW", "DDOG",
    "PLTR", "PATH", "AI", "IONQ", "BBAI", "SOUN",
    # Finance & Crypto Adjacent
    "COIN", "MSTR", "HOOD", "SQ", "PYPL", "SOFI",
    # EV & Space
    "UBER", "ABNB", "SHOP", "RKLB", "JOBY", "ACHR",
]

# ── FETCH REAL-TIME STOCK DATA ─────────────────────────────────────────────────
def fetch_stock_data(symbols: list) -> dict:
    """Download OHLCV + info for each symbol, compute key indicators."""
    print(f"\n📡 Fetching data for {len(symbols)} stocks (this takes ~60s)...")
    results = {}
    failed  = []

    for i, sym in enumerate(symbols):
        try:
            tk   = yf.Ticker(sym)
            hist = tk.history(period="60d", interval="1d", auto_adjust=True)
            if hist.empty or len(hist) < 10:
                failed.append(sym)
                continue

            info  = tk.fast_info  # faster than tk.info
            close = hist["Close"]
            vol   = hist["Volume"]

            # ── Prices ──────────────────────────────────────────────────────
            cur  = float(close.iloc[-1])
            prev = float(close.iloc[-2])
            pct  = round(((cur - prev) / prev) * 100, 2)

            # ── RSI (14-period) ──────────────────────────────────────────────
            delta = close.diff()
            gain  = delta.clip(lower=0).rolling(14).mean()
            loss  = (-delta.clip(upper=0)).rolling(14).mean()
            rs    = gain / (loss + 1e-10)
            rsi   = round(float(100 - 100 / (1 + rs.iloc[-1])), 1)

            # ── MACD (12,26,9) ───────────────────────────────────────────────
            ema12     = close.ewm(span=12, adjust=False).mean()
            ema26     = close.ewm(span=26, adjust=False).mean()
            macd      = ema12 - ema26
            macd_sig  = macd.ewm(span=9, adjust=False).mean()
            macd_hist = float(macd.iloc[-1] - macd_sig.iloc[-1])
            macd_bull = macd_hist > 0 and float(macd.iloc[-1]) > float(macd.iloc[-2])

            # ── Moving Averages ──────────────────────────────────────────────
            ma20 = float(close.rolling(20).mean().iloc[-1])
            ma50 = float(close.rolling(min(50, len(close))).mean().iloc[-1])
            ema9 = float(close.ewm(span=9, adjust=False).mean().iloc[-1])

            # ── Volume Analysis ──────────────────────────────────────────────
            avg_vol   = float(vol.iloc[-11:-1].mean()) + 1
            cur_vol   = float(vol.iloc[-1])
            vol_ratio = round(cur_vol / avg_vol, 2)

            # ── Bollinger Bands ──────────────────────────────────────────────
            bb_mid    = close.rolling(20).mean()
            bb_std    = close.rolling(20).std()
            bb_upper  = float(bb_mid.iloc[-1] + 2 * bb_std.iloc[-1])
            bb_lower  = float(bb_mid.iloc[-1] - 2 * bb_std.iloc[-1])
            bb_pos    = (cur - bb_lower) / (bb_upper - bb_lower + 1e-10)  # 0=lower,1=upper

            # ── 52-week ──────────────────────────────────────────────────────
            wk52_hi  = float(close.rolling(min(252, len(close))).max().iloc[-1])
            wk52_lo  = float(close.rolling(min(252, len(close))).min().iloc[-1])
            from_hi  = round(((cur - wk52_hi) / wk52_hi) * 100, 1)

            # ── 5-day trend ──────────────────────────────────────────────────
            trend5  = float(close.iloc[-1] - close.iloc[-6]) / float(close.iloc[-6]) * 100

            # ── Name / Sector ────────────────────────────────────────────────
            name   = sym.replace(".NS", "").replace(".BO", "")
            sector = "Unknown"
            try:
                full_info = tk.info
                name      = full_info.get("longName", name)
                sector    = full_info.get("sector", "Unknown")
            except Exception:
                pass

            results[sym] = dict(
                symbol=sym, name=name, sector=sector,
                price=round(cur, 2), prev=round(prev, 2), change_pct=pct,
                rsi=rsi, macd_bull=macd_bull, macd_hist=round(macd_hist, 5),
                above_ma20=(cur > ma20), above_ma50=(cur > ma50), above_ema9=(cur > ema9),
                vol_ratio=vol_ratio,
                bb_pos=round(bb_pos, 2),          # <0.2 near low, >0.8 near high
                trend5=round(trend5, 2),
                from_52w_high=from_hi,
                wk52_hi=round(wk52_hi, 2),
            )

            if (i + 1) % 10 == 0:
                print(f"  [{i+1}/{len(symbols)}] processed...")
            time.sleep(0.15)

        except Exception as e:
            failed.append(sym)
            if "404" not in str(e):
                print(f"  ⚠️  {sym}: {e}")

    print(f"  ✅ Fetched {len(results)} stocks | ⚠️  Failed: {len(failed)}")
    return results


# ── SCORE & RANK CANDIDATES ────────────────────────────────────────────────────
def score_and_rank(data: dict, top_n: int = 18) -> list:
    """
    Multi-factor scoring: RSI sweet spot, MACD cross, volume surge,
    MA alignment, BB position, 5-day trend.
    Returns top_n candidates sorted by score descending.
    """
    scored = []
    for sym, d in data.items():
        s = 0

        # RSI: oversold-bounce (best) or healthy momentum
        r = d["rsi"]
        if   30 <= r <= 45: s += 30    # best entry zone
        elif 45 < r <= 58: s += 20
        elif 58 < r <= 70: s += 8
        elif r < 30:        s += 15    # extreme oversold (risky)

        # MACD bullish crossover
        if d["macd_bull"]:   s += 25
        elif d["macd_hist"] > 0: s += 10

        # Above key MAs = uptrend
        if d["above_ma20"]: s += 12
        if d["above_ma50"]: s += 12
        if d["above_ema9"]: s += 8

        # Volume surge = institutional interest
        vr = d["vol_ratio"]
        if   vr >= 3.0: s += 30
        elif vr >= 2.0: s += 22
        elif vr >= 1.5: s += 12

        # Bollinger position (0.1-0.4 = near support = good entry)
        bp = d["bb_pos"]
        if   0.1 <= bp <= 0.35: s += 20   # near lower band = bounce
        elif 0.35 < bp <= 0.65: s += 10   # middle = neutral

        # 5-day trend: slight positive preferred for momentum
        t5 = d["trend5"]
        if   0 < t5 <= 4:  s += 15
        elif t5 > 4:        s += 8
        elif -2 <= t5 <= 0: s += 5

        # Near 52w high breakout (momentum play)
        if d["from_52w_high"] > -3:  s += 15
        elif d["from_52w_high"] > -8: s += 8

        d["score"] = s
        scored.append(d)

    return sorted(scored, key=lambda x: x["score"], reverse=True)[:top_n]


# ── GEMINI AI RECOMMENDATIONS ──────────────────────────────────────────────────
def get_gemini_picks(candidates: list, market: str) -> list:
    """
    Send pre-screened candidates to Gemini 2.0 Flash for final analysis.
    Returns list of 5 structured recommendation dicts.
    """
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is not set. Get a free key at https://aistudio.google.com/app/apikey")

    currency = "₹" if market == "IN" else "$"
    exchange = "NSE/BSE" if market == "IN" else "NYSE/NASDAQ"
    ist_now  = datetime.now(IST).strftime("%A, %d %B %Y — %I:%M %p IST")

    stocks_json = json.dumps([{
        "symbol":       d["symbol"],
        "name":         d["name"][:35],
        "price":        d["price"],
        "change_today": f"{d['change_pct']:+.1f}%",
        "rsi":          d["rsi"],
        "macd_bullish": d["macd_bull"],
        "above_20ma":   d["above_ma20"],
        "above_50ma":   d["above_ma50"],
        "volume_ratio": f"{d['vol_ratio']}x avg",
        "bb_position":  f"{'Oversold' if d['bb_pos'] < 0.25 else 'Mid' if d['bb_pos'] < 0.75 else 'Overbought'}",
        "5d_trend":     f"{d['trend5']:+.1f}%",
        "from_52w_high":f"{d['from_52w_high']}%",
        "sector":       d["sector"],
        "score":        d["score"],
    } for d in candidates], indent=2)

    prompt = f"""You are a senior quantitative trading analyst specializing in {exchange} markets.
Date & Time: {ist_now}

Pre-screened stock candidates ranked by multi-factor technical score:
{stocks_json}

Your task: Select the TOP 5 best trading opportunities for TODAY from this list.

Prioritize:
1. Highest conviction setups (RSI oversold bounce + MACD bullish + volume surge)
2. Clear risk/reward ratio (minimum 1:2 risk/reward)
3. At least 1 potential multibagger (low-price, high-growth potential)
4. Mix signals: 1-2 intraday, 2-3 swing/short-term
5. Low-to-medium risk preferred

For each pick, calculate realistic price targets based on:
- Technical resistance levels
- Percentage move from current price
- Stop loss below key support (MA or recent low)

Return ONLY a valid JSON array — no markdown, no backticks, no explanation:
[
  {{
    "rank": 1,
    "stockName": "Full Company Name",
    "symbol": "{exchange.split('/')[0]}:SYMBOL",
    "currentPrice": "{currency}XXX.XX",
    "targetPrice": "{currency}XXX",
    "stopLoss": "{currency}XXX",
    "takeProfit": "{currency}XXX",
    "signal": "INTRADAY",
    "timeframe": "Same Day",
    "riskLevel": "LOW",
    "expectedReturn": "+X.X%",
    "multibaggerAlert": false,
    "multibaggerNote": "",
    "keyIndicators": ["RSI 38 Oversold", "MACD Crossover", "Volume 2.4x", "20MA Support"],
    "whyBuy": "Clear 2-sentence reason explaining setup and catalyst.",
    "sector": "Technology"
  }},
  ... 4 more
]

signal must be one of: INTRADAY, SWING, BUY & HOLD
timeframe: "Same Day" | "2-5 Days" | "1-4 Weeks" | "1-6 Months"
riskLevel: LOW | MEDIUM | HIGH"""

    url  = (f"https://generativelanguage.googleapis.com/v1beta/"
            f"models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}")
    body = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.25, "maxOutputTokens": 3500},
    }

    print("  🤖 Asking Gemini 2.0 Flash...")
    r = requests.post(url, json=body, timeout=45)
    r.raise_for_status()

    raw = r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()

    # Strip any markdown fences that Gemini might add
    if "```" in raw:
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip().rstrip("`").strip()

    picks = json.loads(raw)
    if not isinstance(picks, list) or len(picks) == 0:
        raise ValueError(f"Gemini returned unexpected data: {raw[:200]}")

    print(f"  ✅ Got {len(picks)} AI recommendations")
    return picks[:5]


# ── FORMAT TELEGRAM MESSAGE ────────────────────────────────────────────────────
def format_telegram_message(picks: list, market: str) -> str:
    flag     = "🇮🇳" if market == "IN" else "🇺🇸"
    mkt_name = "INDIAN MARKET (NSE/BSE)" if market == "IN" else "US MARKET (NYSE/NASDAQ)"
    now      = datetime.now(IST).strftime("%d %b %Y  |  %I:%M %p IST")

    lines = [
        f"{flag} <b>STOCKBOT AI — DAILY SIGNALS</b>",
        f"<b>{mkt_name}</b>",
        f"━━━━━━━━━━━━━━━━━━━━━━━━",
        f"📅 {now}",
        f"━━━━━━━━━━━━━━━━━━━━━━━━",
        "",
    ]

    sig_icon  = {"INTRADAY": "⚡", "SWING": "📊", "BUY & HOLD": "💎"}
    risk_icon = {"LOW": "🟢", "MEDIUM": "🟡", "HIGH": "🔴"}

    for s in picks:
        mb_line = ("🚀 <b>⭐ MULTIBAGGER ALERT! ⭐</b>\n"
                   if s.get("multibaggerAlert") else "")
        s_ico   = sig_icon.get(s.get("signal", ""), "📌")
        r_ico   = risk_icon.get(s.get("riskLevel", ""), "⚪")

        lines.append(f"<b>#{s['rank']} {s['stockName']}</b>")
        if mb_line:
            lines.append(mb_line.strip())
        lines += [
            f"📌 <code>{s['symbol']}</code>  •  {s.get('sector','')}",
            f"",
            f"💰 Price     : <b>{s['currentPrice']}</b>",
            f"🎯 Target    : <b><u>{s['targetPrice']}</u></b>",
            f"🛑 Stop Loss : {s['stopLoss']}",
            f"✅ Take Profit: {s['takeProfit']}",
            f"",
            f"{s_ico} Signal : <b>{s['signal']}</b>  ({s.get('timeframe','')})",
            f"📈 Return : <b>{s['expectedReturn']}</b>   {r_ico} Risk: {s.get('riskLevel','')}",
            f"",
            f"💡 {s['whyBuy']}",
        ]
        if s.get("multibaggerAlert") and s.get("multibaggerNote"):
            lines.append(f"\n🚀 <i>{s['multibaggerNote']}</i>")

        # Indicators
        inds = s.get("keyIndicators", [])
        if inds:
            lines.append("📊 " + "  |  ".join(inds[:4]))

        lines += ["", "─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─", ""]

    lines += [
        "⚡ <i>Powered by StockBot AI</i>",
        "<i>(Gemini 2.0 Flash + yfinance)</i>",
        "",
        "⚠️ <b>Disclaimer:</b> <i>For educational purposes only.",
        "Not financial advice. Always do your own research.</i>",
    ]
    return "\n".join(lines)


# ── SENDERS ────────────────────────────────────────────────────────────────────
def send_telegram(message: str) -> bool:
    """Send formatted HTML message to Telegram."""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️  Telegram not configured (set TELEGRAM_TOKEN + TELEGRAM_CHAT_ID)")
        return False
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id":                  TELEGRAM_CHAT_ID,
        "text":                     message,
        "parse_mode":               "HTML",
        "disable_web_page_preview": True,
    }
    r = requests.post(url, json=payload, timeout=20)
    if r.ok:
        print("✅ Telegram → Sent!")
        return True
    else:
        print(f"❌ Telegram error: {r.status_code} — {r.text[:200]}")
        return False


def send_whatsapp_callmebot(message: str) -> bool:
    """Send via CallMeBot (free WhatsApp API)."""
    if not WA_PHONE or not WA_APIKEY:
        print("ℹ️  WhatsApp not configured, skipping.")
        return False
    # Strip HTML tags for WhatsApp plain text
    import re
    plain = re.sub(r"<[^>]+>", "", message)
    url = (f"https://api.callmebot.com/whatsapp.php"
           f"?phone={WA_PHONE}"
           f"&text={urllib.parse.quote(plain)}"
           f"&apikey={WA_APIKEY}")
    r = requests.get(url, timeout=20)
    if r.ok:
        print("✅ WhatsApp → Sent!")
        return True
    else:
        print(f"❌ WhatsApp error: {r.text[:200]}")
        return False


# ── MAIN ───────────────────────────────────────────────────────────────────────
def main():
    separator = "═" * 52
    print(f"\n{separator}")
    print(f"  🤖 StockBot AI — Daily Signal Bot")
    print(f"  Market   : {'🇮🇳 India (NSE/BSE)' if MARKET == 'IN' else '🇺🇸 US (NYSE/NASDAQ)'}")
    print(f"  Time     : {datetime.now(IST).strftime('%d %b %Y  %I:%M %p IST')}")
    print(f"  AI Model : Gemini 2.0 Flash (Free Tier)")
    print(f"{separator}\n")

    # Validate critical config
    if not GEMINI_API_KEY:
        print("❌ GEMINI_API_KEY is missing! Get free key → https://aistudio.google.com/app/apikey")
        sys.exit(1)
    if not TELEGRAM_TOKEN and not WA_PHONE:
        print("⚠️  No delivery channel configured! Set TELEGRAM_TOKEN or WA_PHONE.")

    # Choose stock list
    symbols = INDIAN_STOCKS if MARKET == "IN" else US_STOCKS

    # Step 1: Fetch real data
    print("📡 STEP 1 — Fetching real-time stock data...")
    stock_data = fetch_stock_data(symbols)
    if not stock_data:
        print("❌ No stock data returned. Check internet connection.")
        sys.exit(1)

    # Step 2: Score & rank
    print("\n🔢 STEP 2 — Scoring and ranking candidates...")
    top_candidates = score_and_rank(stock_data, top_n=18)
    top5_names = [f"{d['symbol']} ({d['score']}pts)" for d in top_candidates[:5]]
    print(f"  Top 5 by score: {', '.join(top5_names)}")

    # Step 3: Gemini AI final picks
    print("\n🤖 STEP 3 — Gemini AI recommendation analysis...")
    try:
        picks = get_gemini_picks(top_candidates, MARKET)
    except Exception as e:
        print(f"❌ Gemini API error: {e}")
        sys.exit(1)

    # Step 4: Format & send
    print("\n📱 STEP 4 — Sending alerts...")
    message = format_telegram_message(picks, MARKET)

    tg_ok = send_telegram(message)
    wa_ok = send_whatsapp_callmebot(message)

    if not tg_ok and not wa_ok:
        print("\n⚠️  No messages were sent. Check your API keys and configs.")
    else:
        print("\n🎉 Done! Signals delivered successfully.")

    # Print picks summary to GitHub Actions log
    print("\n" + separator)
    print("  SIGNAL SUMMARY")
    print(separator)
    for p in picks:
        mb = " 🚀MULTIBAGGER" if p.get("multibaggerAlert") else ""
        print(f"  #{p['rank']} {p['stockName'][:28]:28}  {p['signal']:10}  {p['expectedReturn']:8}  Risk:{p['riskLevel']}{mb}")
    print(separator + "\n")


if __name__ == "__main__":
    main()
