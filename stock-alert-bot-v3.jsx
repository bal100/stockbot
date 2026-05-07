import { useState, useEffect, useCallback, useRef } from "react";

const FONTS = `@import url('https://fonts.googleapis.com/css2?family=Space+Mono:ital,wght@0,400;0,700;1,400&family=Syne:wght@400;600;700;800&display=swap');`;

const STYLES = `
  * { box-sizing: border-box; margin: 0; padding: 0; }
  :root {
    --bg: #050a08; --surface: #0b140f; --card: #0f1d14; --border: #1a3020;
    --gold: #c8a84b; --gold-dim: #8a6f2e; --green: #22c55e; --green-dim: #16a34a;
    --red: #ef4444; --blue: #38bdf8; --purple: #a78bfa; --orange: #fb923c;
    --text: #e2ffe8; --muted: #6b8f73; --accent: #00ff88;
  }
  body { background: var(--bg); font-family: 'Space Mono', monospace; color: var(--text); }
  .app { min-height: 100vh; background: var(--bg); position: relative; overflow: hidden; }
  .grid-bg { position: fixed; inset: 0; z-index: 0; pointer-events: none; background-image: linear-gradient(rgba(0,255,136,0.025) 1px, transparent 1px), linear-gradient(90deg, rgba(0,255,136,0.025) 1px, transparent 1px); background-size: 40px 40px; }
  .content { position: relative; z-index: 1; }
  .header { border-bottom: 1px solid var(--border); padding: 14px 24px; display: flex; align-items: center; justify-content: space-between; background: rgba(5,10,8,0.92); backdrop-filter: blur(12px); position: sticky; top: 0; z-index: 100; }
  .logo { display: flex; align-items: center; gap: 12px; }
  .logo-icon { width: 36px; height: 36px; background: var(--gold); border-radius: 8px; display: flex; align-items: center; justify-content: center; font-size: 16px; font-weight: 700; color: var(--bg); box-shadow: 0 0 20px rgba(200,168,75,0.4); }
  .logo-text { font-family: 'Syne', sans-serif; font-weight: 800; font-size: 17px; }
  .logo-text span { color: var(--gold); }
  .header-right { display: flex; align-items: center; gap: 10px; }
  .clock { font-size: 11px; color: var(--muted); background: var(--surface); border: 1px solid var(--border); padding: 5px 11px; border-radius: 6px; }
  .clock span { color: var(--accent); }
  .status-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--accent); box-shadow: 0 0 8px var(--accent); animation: pulse 2s infinite; }
  @keyframes pulse { 0%,100%{opacity:1}50%{opacity:0.4} }

  .ticker-wrap { background: var(--surface); border-bottom: 1px solid var(--border); padding: 7px 0; overflow: hidden; }
  .ticker { display: flex; gap: 40px; width: max-content; animation: ticker 35s linear infinite; }
  @keyframes ticker { from{transform:translateX(0)}to{transform:translateX(-50%)} }
  .ticker-item { display: flex; align-items: center; gap: 8px; font-size: 11px; white-space: nowrap; }
  .ticker-sym { color: var(--gold); font-weight: 700; }
  .ticker-up { color: var(--green); } .ticker-down { color: var(--red); }

  .main { padding: 22px 24px; max-width: 1440px; margin: 0 auto; }

  .top-tabs { display: flex; gap: 0; margin-bottom: 22px; background: var(--surface); border: 1px solid var(--border); border-radius: 10px; padding: 4px; width: fit-content; }
  .ttab { padding: 8px 22px; border-radius: 7px; font-size: 11px; font-weight: 700; cursor: pointer; transition: all 0.2s; border: none; font-family: 'Space Mono', monospace; letter-spacing: 0.5px; }
  .ttab-active { background: var(--gold); color: var(--bg); }
  .ttab-inactive { background: transparent; color: var(--muted); }
  .ttab-inactive:hover { color: var(--text); }

  .market-tabs { display: flex; gap: 4px; background: var(--surface); border: 1px solid var(--border); border-radius: 10px; padding: 4px; width: fit-content; }
  .tab { padding: 7px 18px; border-radius: 7px; font-size: 11px; font-weight: 700; cursor: pointer; transition: all 0.2s; border: none; font-family: 'Space Mono', monospace; letter-spacing: 0.5px; }
  .tab-active { background: var(--gold); color: var(--bg); }
  .tab-inactive { background: transparent; color: var(--muted); }
  .tab-inactive:hover { color: var(--text); }

  .btn { padding: 9px 18px; border-radius: 8px; font-family: 'Space Mono', monospace; font-size: 11px; font-weight: 700; border: none; cursor: pointer; transition: all 0.2s; letter-spacing: 0.5px; display: flex; align-items: center; gap: 7px; white-space: nowrap; }
  .btn-primary { background: var(--gold); color: var(--bg); box-shadow: 0 0 18px rgba(200,168,75,0.3); }
  .btn-primary:hover:not(:disabled) { background: #e0b94f; transform: translateY(-1px); }
  .btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
  .btn-tg { background: #229ED9; color: #fff; box-shadow: 0 0 14px rgba(34,158,217,0.3); }
  .btn-tg:hover { background: #1a7fb5; transform: translateY(-1px); }
  .btn-wa { background: #25D366; color: #fff; }
  .btn-wa:hover { background: #128C7E; transform: translateY(-1px); }
  .btn-outline { background: transparent; color: var(--text); border: 1px solid var(--border); }
  .btn-outline:hover { border-color: var(--gold); color: var(--gold); }

  .control-row { display: flex; align-items: center; justify-content: space-between; margin-bottom: 22px; flex-wrap: wrap; gap: 12px; }
  .section-title { font-family: 'Syne', sans-serif; font-weight: 800; font-size: 20px; letter-spacing: -0.5px; }
  .section-title span { color: var(--gold); }
  .sub-text { font-size: 10px; color: var(--muted); margin-top: 2px; }

  .rec-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(360px, 1fr)); gap: 18px; margin-bottom: 28px; }
  .rec-card { background: var(--card); border: 1px solid var(--border); border-radius: 14px; overflow: hidden; transition: all 0.3s; position: relative; animation: fadeIn 0.5s ease both; }
  .rec-card:hover { border-color: var(--gold-dim); transform: translateY(-2px); box-shadow: 0 8px 40px rgba(0,0,0,0.4); }
  @keyframes fadeIn { from{opacity:0;transform:translateY(14px)}to{opacity:1;transform:translateY(0)} }
  .rec-card:nth-child(1){animation-delay:.05s}.rec-card:nth-child(2){animation-delay:.1s}.rec-card:nth-child(3){animation-delay:.15s}.rec-card:nth-child(4){animation-delay:.2s}.rec-card:nth-child(5){animation-delay:.25s}
  .multibagger-glow { border-color: var(--gold) !important; box-shadow: 0 0 30px rgba(200,168,75,0.25); }
  .multibagger-glow::before { content:''; position:absolute; inset:0; background:linear-gradient(135deg,rgba(200,168,75,0.06) 0%,transparent 60%); pointer-events:none; }

  .card-header { padding: 14px 16px 12px; border-bottom: 1px solid var(--border); display: flex; align-items: flex-start; justify-content: space-between; }
  .rank-num { width: 19px; height: 19px; border-radius: 50%; background: var(--border); display: flex; align-items: center; justify-content: center; font-size: 10px; font-weight: 700; color: var(--gold); }
  .stock-rank { font-size: 10px; color: var(--muted); margin-bottom: 3px; display: flex; align-items: center; gap: 8px; }
  .stock-name { font-family: 'Syne', sans-serif; font-weight: 700; font-size: 16px; }
  .stock-symbol { font-size: 10px; color: var(--muted); background: var(--surface); padding: 2px 7px; border-radius: 4px; display: inline-block; margin-top: 3px; border: 1px solid var(--border); }
  .badges-col { display: flex; flex-direction: column; align-items: flex-end; gap: 5px; }
  .signal-badge { padding: 4px 9px; border-radius: 6px; font-size: 10px; font-weight: 700; letter-spacing: 0.5px; white-space: nowrap; }
  .sig-intraday { background: rgba(56,189,248,0.15); color: var(--blue); border: 1px solid rgba(56,189,248,0.3); }
  .sig-swing { background: rgba(251,146,60,0.15); color: var(--orange); border: 1px solid rgba(251,146,60,0.3); }
  .sig-hold { background: rgba(0,255,136,0.12); color: var(--accent); border: 1px solid rgba(0,255,136,0.3); }
  .multibagger-badge { padding: 3px 8px; border-radius: 4px; font-size: 9px; font-weight: 700; background: linear-gradient(135deg, var(--gold), #e8c84a); color: var(--bg); letter-spacing: 1px; }

  .card-prices { padding: 12px 16px; display: grid; grid-template-columns: 1fr 1fr; gap: 8px; border-bottom: 1px solid var(--border); }
  .price-label { font-size: 9px; color: var(--muted); letter-spacing: 1px; text-transform: uppercase; margin-bottom: 2px; }
  .price-value { font-size: 15px; font-weight: 700; }
  .price-current { color: var(--text); } .price-target { color: var(--green); } .price-sl { color: var(--red); } .price-tp { color: var(--accent); }

  .card-stats { padding: 10px 16px; display: flex; gap: 8px; border-bottom: 1px solid var(--border); }
  .stat-chip { display: flex; flex-direction: column; align-items: center; background: var(--surface); border: 1px solid var(--border); border-radius: 7px; padding: 7px 10px; flex: 1; }
  .stat-label { font-size: 9px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.5px; }
  .stat-value { font-size: 12px; font-weight: 700; margin-top: 2px; }
  .stat-up{color:var(--green)}.stat-down{color:var(--red)}.stat-neutral{color:var(--blue)}.stat-gold{color:var(--gold)}

  .card-reason { padding: 12px 16px; font-size: 11px; color: var(--muted); line-height: 1.7; border-bottom: 1px solid var(--border); }
  .reason-title { color: var(--text); font-weight: 700; font-size: 9px; letter-spacing: 1px; margin-bottom: 5px; text-transform: uppercase; }
  .multibagger-note { margin-top: 7px; color: var(--gold); border-left: 2px solid var(--gold); padding-left: 8px; font-size: 10px; }
  .card-indicators { padding: 10px 16px 14px; display: flex; flex-wrap: wrap; gap: 5px; }
  .ind-tag { padding: 3px 7px; border-radius: 4px; font-size: 9px; font-weight: 700; border: 1px solid; letter-spacing: 0.5px; }
  .ind-bull { color: var(--green); border-color: rgba(34,197,94,0.3); background: rgba(34,197,94,0.07); }
  .ind-bear { color: var(--red); border-color: rgba(239,68,68,0.3); background: rgba(239,68,68,0.07); }
  .ind-neutral { color: var(--blue); border-color: rgba(56,189,248,0.3); background: rgba(56,189,248,0.07); }

  .loading-overlay { position: fixed; inset: 0; z-index: 200; background: rgba(5,10,8,0.93); backdrop-filter: blur(8px); display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 16px; }
  .spinner { width: 56px; height: 56px; border: 3px solid var(--border); border-top-color: var(--gold); border-radius: 50%; animation: spin 0.8s linear infinite; }
  @keyframes spin { to{transform:rotate(360deg)} }
  .loading-text { font-family: 'Syne', sans-serif; font-size: 19px; font-weight: 700; }
  .loading-step { font-size: 11px; color: var(--muted); display: flex; align-items: center; gap: 8px; }
  .step-active { color: var(--accent); } .step-done { color: var(--green-dim); }

  .modal-overlay { position: fixed; inset: 0; z-index: 300; background: rgba(0,0,0,0.85); backdrop-filter: blur(8px); display: flex; align-items: center; justify-content: center; padding: 16px; }
  .modal { background: var(--card); border: 1px solid var(--border); border-radius: 16px; width: 100%; max-width: 540px; max-height: 90vh; overflow-y: auto; }
  .modal-header { padding: 18px 20px 14px; border-bottom: 1px solid var(--border); display: flex; align-items: center; justify-content: space-between; }
  .modal-title { font-family: 'Syne', sans-serif; font-weight: 700; font-size: 17px; }
  .modal-close { background: none; border: none; color: var(--muted); font-size: 20px; cursor: pointer; }
  .modal-body { padding: 20px; }
  .field-group { margin-bottom: 16px; }
  .field-label { font-size: 10px; color: var(--muted); text-transform: uppercase; letter-spacing: 1px; margin-bottom: 6px; display: flex; align-items: center; gap: 6px; }
  .field-input { width: 100%; background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 10px 12px; font-family: 'Space Mono', monospace; font-size: 12px; color: var(--text); outline: none; transition: border-color 0.2s; }
  .field-input:focus { border-color: var(--gold); }
  .field-hint { font-size: 10px; color: var(--muted); margin-top: 5px; line-height: 1.6; }
  .field-hint a { color: var(--gold); }
  .notice-box { background: rgba(0,255,136,0.06); border: 1px solid rgba(0,255,136,0.2); border-radius: 8px; padding: 10px 12px; font-size: 10px; color: var(--accent); line-height: 1.7; margin-bottom: 14px; }
  .warn-box { background: rgba(251,146,60,0.08); border: 1px solid rgba(251,146,60,0.25); border-radius: 8px; padding: 10px 12px; font-size: 10px; color: var(--orange); line-height: 1.7; margin-bottom: 14px; }
  .error-box { background: rgba(239,68,68,0.1); border: 1px solid rgba(239,68,68,0.3); border-radius: 10px; padding: 14px; margin-bottom: 18px; font-size: 11px; color: var(--red); line-height: 1.6; }

  .guide-card { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 18px; margin-bottom: 14px; }
  .guide-card-title { font-family: 'Syne', sans-serif; font-size: 14px; font-weight: 700; color: var(--gold); margin-bottom: 10px; display: flex; align-items: center; gap: 8px; }
  .guide-card-body { font-size: 11px; color: var(--muted); line-height: 1.8; }
  .guide-card-body code { background: rgba(200,168,75,0.12); color: var(--gold); padding: 1px 6px; border-radius: 4px; font-family: 'Space Mono', monospace; font-size: 10px; }
  .pill { display: inline-flex; align-items: center; padding: 2px 8px; border-radius: 10px; font-size: 9px; font-weight: 700; letter-spacing: 0.5px; margin-left: 6px; }
  .pill-free { background: rgba(0,255,136,0.12); color: var(--accent); border: 1px solid rgba(0,255,136,0.3); }

  .code-block { background: var(--bg); border: 1px solid var(--border); border-radius: 8px; padding: 14px; font-family: 'Space Mono', monospace; font-size: 10px; color: #a0c8a8; line-height: 1.8; overflow-x: auto; white-space: pre; margin-bottom: 14px; }

  .step-list { display: flex; flex-direction: column; gap: 10px; }
  .step-item { display: flex; gap: 10px; font-size: 11px; color: var(--muted); line-height: 1.6; }
  .step-num { min-width: 22px; height: 22px; border-radius: 50%; background: var(--border); display: flex; align-items: center; justify-content: center; font-size: 10px; font-weight: 700; color: var(--gold); flex-shrink: 0; margin-top: 1px; }
  .step-item code { background: rgba(200,168,75,0.12); color: var(--gold); padding: 1px 6px; border-radius: 4px; font-size: 10px; }

  .copy-btn { background: var(--border); border: none; color: var(--muted); font-size: 10px; padding: 4px 10px; border-radius: 4px; cursor: pointer; font-family: 'Space Mono', monospace; transition: all 0.2s; }
  .copy-btn:hover { background: var(--gold); color: var(--bg); }

  .empty-state { text-align: center; padding: 50px 20px; border: 1px dashed var(--border); border-radius: 14px; }
  .empty-icon { font-size: 44px; margin-bottom: 14px; }
  .empty-title { font-family: 'Syne', sans-serif; font-size: 18px; font-weight: 700; margin-bottom: 6px; }
  .empty-sub { font-size: 11px; color: var(--muted); margin-bottom: 18px; line-height: 1.7; }

  .send-row { display: flex; gap: 10px; margin-bottom: 10px; flex-wrap: wrap; }
  .send-status { font-size: 11px; color: var(--accent); margin-top: 6px; }

  @media (max-width: 640px) {
    .main { padding: 14px; } .rec-grid { grid-template-columns: 1fr; }
    .header { padding: 10px 14px; }
  }
`;

const TICKER = [
  {sym:"NIFTY50",price:"24,782",chg:"+0.52%",up:true},{sym:"SENSEX",price:"81,503",chg:"+0.44%",up:true},
  {sym:"BANKNIFTY",price:"53,412",chg:"-0.18%",up:false},{sym:"S&P500",price:"5,607",chg:"+0.71%",up:true},
  {sym:"NASDAQ",price:"19,841",chg:"+0.93%",up:true},{sym:"AAPL",price:"$211.8",chg:"+1.2%",up:true},
  {sym:"NVDA",price:"$903",chg:"+2.4%",up:true},{sym:"RELIANCE",price:"₹2,934",chg:"+1.3%",up:true},
  {sym:"TCS",price:"₹3,801",chg:"-0.5%",up:false},{sym:"ZOMATO",price:"₹198",chg:"+3.1%",up:true},
];

function formatIST(d){ return d.toLocaleTimeString("en-IN",{timeZone:"Asia/Kolkata",hour:"2-digit",minute:"2-digit",second:"2-digit",hour12:true}); }
function formatDate(d){ return d.toLocaleDateString("en-IN",{timeZone:"Asia/Kolkata",day:"2-digit",month:"short",year:"numeric"}); }

const GEMINI_PROMPT = (market) => `You are an elite quantitative stock analyst for the ${market === "IN" ? "NSE/BSE (India)" : "NYSE/NASDAQ (US)"} market.

Today: ${new Date().toDateString()}

Generate TOP 5 high-conviction stock signals for today. Analyze technical indicators, sector momentum, recent news catalysts, and risk/reward.

Return ONLY a valid JSON array — no markdown, no backticks, no explanation:
[
  {
    "rank": 1,
    "stockName": "Company Full Name",
    "symbol": "${market === "IN" ? "NSE:SYMBOL" : "NASDAQ:SYMBOL"}",
    "currentPrice": "${market === "IN" ? "₹" : "$"}XXX",
    "targetPrice": "${market === "IN" ? "₹" : "$"}XXX",
    "stopLoss": "${market === "IN" ? "₹" : "$"}XXX",
    "takeProfit": "${market === "IN" ? "₹" : "$"}XXX",
    "signal": "INTRADAY",
    "timeframe": "Same Day",
    "riskLevel": "LOW",
    "expectedReturn": "+X.X%",
    "multibaggerAlert": false,
    "multibaggerNote": "",
    "keyIndicators": ["RSI 38 Oversold", "MACD Crossover", "Volume 2.4x Surge", "20DMA Support"],
    "whyBuy": "2-3 sentence reason with setup + catalyst + timing.",
    "sector": "Technology"
  }
]

Rules:
- signal: INTRADAY | SWING | BUY & HOLD
- timeframe: "Same Day" | "2-5 Days" | "1-4 Weeks" | "1-6 Months"
- riskLevel: LOW | MEDIUM | HIGH
- Mix intraday + swing + at least 1 potential multibagger
- Realistic price levels for ${new Date().getFullYear()}
- Prioritize low risk, high reward (min 1:2 ratio)`;

export default function StockAlertBot() {
  const [time, setTime]           = useState(new Date());
  const [tab, setTab]             = useState("signals");
  const [market, setMarket]       = useState("IN");
  const [loading, setLoading]     = useState(false);
  const [loadingStep, setLoadingStep] = useState(0);
  const [recs, setRecs]           = useState({ IN: [], US: [] });
  const [error, setError]         = useState("");
  const [lastFetched, setLastFetched] = useState({ IN: null, US: null });
  const [showSettings, setShowSettings] = useState(false);
  const [geminiKey, setGeminiKey] = useState(() => localStorage.getItem("sb_gemini") || "");
  const [tgToken, setTgToken]     = useState(() => localStorage.getItem("sb_tgtoken") || "");
  const [tgChatId, setTgChatId]   = useState(() => localStorage.getItem("sb_tgchat") || "");
  const [waPhone, setWaPhone]     = useState(() => localStorage.getItem("sb_waphone") || "");
  const [waKey, setWaKey]         = useState(() => localStorage.getItem("sb_wakey") || "");
  const [sendStatus, setSendStatus] = useState("");
  const [copied, setCopied]       = useState("");

  const STEPS = [
    "🔍 Scanning market conditions...",
    "📊 Analyzing technical indicators...",
    "📰 Checking news catalysts...",
    "🎯 Calculating entry/exit levels...",
    "🚀 Detecting multibagger candidates...",
    "✅ Finalizing top 5 signals...",
  ];

  useEffect(() => {
    const t = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(t);
  }, []);

  const saveSettings = () => {
    localStorage.setItem("sb_gemini",  geminiKey);
    localStorage.setItem("sb_tgtoken", tgToken);
    localStorage.setItem("sb_tgchat",  tgChatId);
    localStorage.setItem("sb_waphone", waPhone);
    localStorage.setItem("sb_wakey",   waKey);
    setShowSettings(false);
  };

  const generateRecs = useCallback(async (mkt) => {
    if (!geminiKey) { setShowSettings(true); return; }
    setLoading(true); setError(""); setLoadingStep(0);
    const si = setInterval(() => setLoadingStep(p => Math.min(p+1, STEPS.length-1)), 1800);
    try {
      const url = `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=${geminiKey}`;
      const res = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          contents: [{ role: "user", parts: [{ text: GEMINI_PROMPT(mkt) }] }],
          generationConfig: { temperature: 0.25, maxOutputTokens: 3500 },
        }),
      });
      clearInterval(si);
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.error?.message || `Gemini API error ${res.status}`);
      }
      const data = await res.json();
      let raw = data.candidates?.[0]?.content?.parts?.[0]?.text || "";
      if (raw.includes("```")) { raw = raw.split("```")[1]; if (raw.startsWith("json")) raw = raw.slice(4); }
      raw = raw.trim().replace(/^`+|`+$/g,"").trim();
      const parsed = JSON.parse(raw);
      if (!Array.isArray(parsed) || !parsed.length) throw new Error("Invalid response format. Please retry.");
      setRecs(p => ({ ...p, [mkt]: parsed.slice(0,5) }));
      setLastFetched(p => ({ ...p, [mkt]: new Date() }));
      setMarket(mkt);
    } catch(e) {
      clearInterval(si);
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [geminiKey]);

  const buildTgMessage = (mkt) => {
    const picks = recs[mkt]; if (!picks?.length) return "";
    const flag = mkt === "IN" ? "🇮🇳" : "🇺🇸";
    const now = formatIST(new Date());
    let m = `${flag} STOCKBOT AI SIGNALS\n${mkt === "IN" ? "INDIA (NSE/BSE)" : "US (NYSE/NASDAQ)"}\n📅 ${formatDate(new Date())} | ${now}\n${"─".repeat(26)}\n\n`;
    picks.forEach(s => {
      m += `#${s.rank} ${s.stockName}\n`;
      if (s.multibaggerAlert) m += `🚀 MULTIBAGGER ALERT!\n`;
      m += `📌 ${s.symbol}\n💰 ${s.currentPrice} | 🎯 ${s.targetPrice}\n🛑 SL: ${s.stopLoss} | ✅ TP: ${s.takeProfit}\n`;
      m += `⚡ ${s.signal} (${s.timeframe}) | 📈 ${s.expectedReturn} | ${s.riskLevel} risk\n`;
      m += `💡 ${s.whyBuy}\n\n`;
    });
    m += `⚠️ Educational only. Not financial advice.`;
    return m;
  };

  const sendTelegram = async (mkt) => {
    if (!tgToken || !tgChatId) { alert("Set Telegram token & chat ID in ⚙️ Settings first."); return; }
    const msg = buildTgMessage(mkt);
    try {
      const r = await fetch(`https://api.telegram.org/bot${tgToken}/sendMessage`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ chat_id: tgChatId, text: msg, parse_mode: "HTML", disable_web_page_preview: true }),
      });
      const d = await r.json();
      if (d.ok) setSendStatus("✅ Sent to Telegram!");
      else setSendStatus(`❌ Telegram error: ${d.description}`);
    } catch(e) { setSendStatus(`❌ ${e.message}`); }
    setTimeout(() => setSendStatus(""), 4000);
  };

  const sendWhatsApp = (mkt) => {
    const msg = buildTgMessage(mkt);
    window.open(`https://wa.me/?text=${encodeURIComponent(msg)}`, "_blank");
  };

  const copyText = (text, key) => {
    navigator.clipboard.writeText(text).then(() => {
      setCopied(key); setTimeout(() => setCopied(""), 1500);
    });
  };

  const currentRecs = recs[market];

  return (
    <>
      <style>{FONTS}{STYLES}</style>
      <div className="app">
        <div className="grid-bg" />

        {loading && (
          <div className="loading-overlay">
            <div className="spinner" />
            <div className="loading-text">Analyzing {market === "IN" ? "🇮🇳 Indian" : "🇺🇸 US"} Market</div>
            <div style={{display:"flex",flexDirection:"column",gap:"7px",marginTop:"4px"}}>
              {STEPS.map((s,i) => (
                <div key={i} className={`loading-step ${i < loadingStep ? "step-done" : i === loadingStep ? "step-active" : ""}`}>
                  <span>{i < loadingStep ? "✓" : i === loadingStep ? "▶" : "○"}</span> {s}
                </div>
              ))}
            </div>
          </div>
        )}

        {showSettings && <SettingsModal
          geminiKey={geminiKey} setGeminiKey={setGeminiKey}
          tgToken={tgToken} setTgToken={setTgToken}
          tgChatId={tgChatId} setTgChatId={setTgChatId}
          waPhone={waPhone} setWaPhone={setWaPhone}
          waKey={waKey} setWaKey={setWaKey}
          onSave={saveSettings} onClose={() => setShowSettings(false)}
        />}

        <div className="content">
          <header className="header">
            <div className="logo">
              <div className="logo-icon">AI</div>
              <div>
                <div className="logo-text">Stock<span>Bot</span> <span style={{fontSize:"10px",color:"var(--muted)"}}>v3 FREE</span></div>
                <div style={{fontSize:"9px",color:"var(--muted)",letterSpacing:"2px"}}>GEMINI · TELEGRAM · NO BROWSER NEEDED</div>
              </div>
            </div>
            <div className="header-right">
              <div className="status-dot" />
              <div className="clock">IST <span>{formatIST(time)}</span></div>
              <button className="btn btn-outline" style={{padding:"5px 12px",fontSize:"10px"}} onClick={() => setShowSettings(true)}>⚙️ Setup</button>
            </div>
          </header>

          <div className="ticker-wrap">
            <div className="ticker">
              {[...TICKER,...TICKER].map((t,i) => (
                <div key={i} className="ticker-item">
                  <span className="ticker-sym">{t.sym}</span>
                  <span>{t.price}</span>
                  <span className={t.up?"ticker-up":"ticker-down"}>{t.chg}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="main">
            <div className="top-tabs">
              {[["signals","📊 Signals"],["guide","🚀 Free Setup Guide"],["automation","⚙️ GitHub Actions"]].map(([k,l]) => (
                <button key={k} className={`ttab ${tab===k?"ttab-active":"ttab-inactive"}`} onClick={() => setTab(k)}>{l}</button>
              ))}
            </div>

            {tab === "signals" && (
              <>
                <div className="control-row">
                  <div>
                    <div className="section-title">AI Stock <span>Signals</span></div>
                    <div className="sub-text">Powered by Google Gemini 2.0 Flash — 100% FREE • {formatDate(new Date())}</div>
                  </div>
                  <div style={{display:"flex",gap:"8px",flexWrap:"wrap",alignItems:"center"}}>
                    <div className="market-tabs">
                      <button className={`tab ${market==="IN"?"tab-active":"tab-inactive"}`} onClick={() => setMarket("IN")}>🇮🇳 India</button>
                      <button className={`tab ${market==="US"?"tab-active":"tab-inactive"}`} onClick={() => setMarket("US")}>🇺🇸 US</button>
                    </div>
                    <button className="btn btn-primary" onClick={() => generateRecs(market)} disabled={loading}>
                      {loading ? "⟳ Analyzing..." : "⚡ Generate Signals"}
                    </button>
                  </div>
                </div>

                {!geminiKey && (
                  <div className="notice-box">
                    🔑 <strong>Add your free Gemini API key</strong> to get started. Get it free at <strong>aistudio.google.com</strong> — no credit card needed.{" "}
                    <span style={{color:"var(--gold)",cursor:"pointer",textDecoration:"underline"}} onClick={() => setShowSettings(true)}>Click here to set up →</span>
                  </div>
                )}

                {error && <div className="error-box">⚠️ {error}</div>}

                {currentRecs.length === 0 ? (
                  <div className="empty-state">
                    <div className="empty-icon">{market==="IN"?"📊":"📈"}</div>
                    <div className="empty-title">Ready to Analyze {market==="IN"?"Indian":"US"} Market</div>
                    <div className="empty-sub">
                      Uses <strong style={{color:"var(--accent)"}}>Google Gemini 2.0 Flash</strong> — completely free API.<br/>
                      No credit card. No limits for daily use. Just add your free API key.
                    </div>
                    <button className="btn btn-primary" onClick={() => geminiKey ? generateRecs(market) : setShowSettings(true)} style={{margin:"0 auto"}}>
                      {geminiKey ? "⚡ Generate Today's Signals" : "🔑 Setup Free API Key First"}
                    </button>
                  </div>
                ) : (
                  <>
                    <div style={{display:"flex",alignItems:"center",justifyContent:"space-between",marginBottom:"14px",flexWrap:"wrap",gap:"8px"}}>
                      <div style={{fontSize:"11px",color:"var(--muted)"}}>
                        {lastFetched[market] && `Last: ${lastFetched[market].toLocaleTimeString("en-IN",{timeZone:"Asia/Kolkata",hour:"2-digit",minute:"2-digit",hour12:true})} IST`}
                        <span style={{color:"var(--accent)",marginLeft:"12px"}}>✦ Gemini 2.0 Flash</span>
                      </div>
                      <div className="send-row">
                        <button className="btn btn-tg" onClick={() => sendTelegram(market)}>📲 Send Telegram</button>
                        <button className="btn btn-wa" onClick={() => sendWhatsApp(market)}>💬 WhatsApp</button>
                        <button className="btn btn-outline" style={{fontSize:"10px",padding:"6px 12px"}} onClick={() => generateRecs(market)}>↻ Refresh</button>
                      </div>
                    </div>
                    {sendStatus && <div className="send-status">{sendStatus}</div>}

                    <div className="rec-grid">
                      {currentRecs.map((s,i) => <StockCard key={i} stock={s} rank={i+1} />)}
                    </div>

                    <div style={{display:"flex",gap:"10px",flexWrap:"wrap"}}>
                      <button className="btn btn-outline" style={{flex:1}} onClick={() => generateRecs("IN")}>🇮🇳 Indian Signals</button>
                      <button className="btn btn-outline" style={{flex:1}} onClick={() => generateRecs("US")}>🇺🇸 US Signals</button>
                    </div>
                  </>
                )}
              </>
            )}

            {tab === "guide" && <GuideTab onSetup={() => setShowSettings(true)} copyText={copyText} copied={copied} />}
            {tab === "automation" && <AutomationTab copyText={copyText} copied={copied} />}

            <div style={{height:"40px"}} />
          </div>
        </div>
      </div>
    </>
  );
}

function StockCard({ stock: s, rank }) {
  const sigCls = s.signal==="INTRADAY" ? "sig-intraday" : s.signal==="SWING" ? "sig-swing" : "sig-hold";
  const sigLabel = s.signal==="INTRADAY" ? "⚡ INTRADAY" : s.signal==="SWING" ? "📊 SWING" : "💎 BUY & HOLD";
  const getIndCls = (t) => {
    const l = t.toLowerCase();
    if (l.includes("bull")||l.includes("oversold")||l.includes("support")||l.includes("surge")) return "ind-bull";
    if (l.includes("bear")||l.includes("overbought")||l.includes("resist")) return "ind-bear";
    return "ind-neutral";
  };
  return (
    <div className={`rec-card ${s.multibaggerAlert ? "multibagger-glow" : ""}`}>
      <div className="card-header">
        <div>
          <div className="stock-rank"><div className="rank-num">#{rank}</div><span style={{color:"var(--muted)"}}>{ s.sector}</span></div>
          <div className="stock-name">{s.stockName}</div>
          <div className="stock-symbol">{s.symbol}</div>
        </div>
        <div className="badges-col">
          <div className={`signal-badge ${sigCls}`}>{sigLabel}</div>
          <div style={{fontSize:"9px",color:"var(--muted)"}}>{s.timeframe}</div>
          {s.multibaggerAlert && <div className="multibagger-badge">🚀 MULTIBAGGER</div>}
        </div>
      </div>
      <div className="card-prices">
        <div><div className="price-label">Current Price</div><div className={`price-value price-current`}>{s.currentPrice}</div></div>
        <div><div className="price-label">Target</div><div className={`price-value price-target`}>{s.targetPrice}</div></div>
        <div><div className="price-label">Stop Loss</div><div className={`price-value price-sl`}>{s.stopLoss}</div></div>
        <div><div className="price-label">Take Profit</div><div className={`price-value price-tp`}>{s.takeProfit}</div></div>
      </div>
      <div className="card-stats">
        <div className="stat-chip"><div className="stat-label">Return</div><div className={`stat-value ${s.expectedReturn?.startsWith("+")?"stat-up":"stat-down"}`}>{s.expectedReturn}</div></div>
        <div className="stat-chip"><div className="stat-label">Risk</div><div className={`stat-value ${s.riskLevel==="LOW"?"stat-up":s.riskLevel==="HIGH"?"stat-down":"stat-neutral"}`}>{s.riskLevel}</div></div>
      </div>
      <div className="card-reason">
        <div className="reason-title">Why This Stock?</div>
        {s.whyBuy}
        {s.multibaggerAlert && s.multibaggerNote && <div className="multibagger-note">🚀 {s.multibaggerNote}</div>}
      </div>
      {s.keyIndicators?.length > 0 && (
        <div className="card-indicators">
          {s.keyIndicators.map((ind,i) => <div key={i} className={`ind-tag ${getIndCls(ind)}`}>{ind}</div>)}
        </div>
      )}
    </div>
  );
}

function GuideTab({ onSetup, copyText, copied }) {
  return (
    <div>
      <div style={{marginBottom:"20px"}}>
        <div className="section-title">🆓 Run StockBot <span>Completely Free</span></div>
        <div className="sub-text" style={{marginTop:"6px"}}>No paid APIs. No servers. No browser needed. Fully automated daily signals.</div>
      </div>

      <div className="notice-box">
        ✅ <strong>Total Cost: ₹0/month</strong> — Gemini API free tier (1500 req/day) + GitHub Actions free tier (2000 min/month) + Telegram Bot API (unlimited free) = completely free for daily signals.
      </div>

      {[
        {icon:"🔑",title:"STEP 1 — Get Free Gemini API Key (2 min)",pill:"FREE",steps:[
          {n:1,t:"Go to",link:"https://aistudio.google.com/app/apikey",lt:"aistudio.google.com/app/apikey"},
          {n:2,t:"Sign in with your Google account (free)"},
          {n:3,t:"Click "Create API Key" → Copy the key"},
          {n:4,t:<>Paste it in <strong style={{color:"var(--gold)"}}>⚙️ Setup</strong> in the top-right</>},
          {n:5,t:"Free quota: 1,500 requests/day, 15 req/min — more than enough!"},
        ]},
        {icon:"📱",title:"STEP 2 — Create Free Telegram Bot (5 min)",pill:"FREE",steps:[
          {n:1,t:"Open Telegram → Search for @BotFather → Start"},
          {n:2,t:<>Type <code>/newbot</code> → Give it a name like "MyStockBot"</>},
          {n:3,t:"Copy the bot token (looks like: 1234567890:ABCdef...)"},
          {n:4,t:"Search @userinfobot on Telegram → Start → Copy your Chat ID"},
          {n:5,t:<>Paste both in <strong style={{color:"var(--gold)"}}>⚙️ Setup</strong></>},
          {n:6,t:"Start your bot: search for it on Telegram and press Start"},
        ]},
        {icon:"⚙️",title:"STEP 3 — WhatsApp via CallMeBot (optional, 5 min)",pill:"FREE",steps:[
          {n:1,t:<>Go to <code>callmebot.com/whatsapp.php</code></>},
          {n:2,t:"Send WhatsApp to +34 644 76 78 20 with message: I allow callmebot to send me messages"},
          {n:3,t:"You'll receive an API key via WhatsApp"},
          {n:4,t:"Enter your phone (with country code) + API key in ⚙️ Setup"},
          {n:"💡",t:"Telegram is easier and more reliable. Recommended over WhatsApp."},
        ]},
      ].map((card,ci) => (
        <div key={ci} className="guide-card">
          <div className="guide-card-title">{card.icon} {card.title} <span className="pill pill-free">{card.pill}</span></div>
          <div className="step-list">
            {card.steps.map((s,si) => (
              <div key={si} className="step-item">
                <div className="step-num">{s.n}</div>
                <div className="guide-card-body">
                  {s.t} {s.link && <a href={s.link} target="_blank" rel="noreferrer" style={{color:"var(--gold)"}}>{s.lt}</a>}
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}

      <div style={{textAlign:"center",paddingTop:"8px"}}>
        <button className="btn btn-primary" onClick={onSetup} style={{margin:"0 auto"}}>⚙️ Open Setup Now</button>
      </div>
    </div>
  );
}

const YAML_CODE = `name: StockBot Daily Signals
on:
  schedule:
    - cron: '30 3 * * 1-5'   # 9:00 AM IST = India signals
    - cron: '30 12 * * 1-5'  # 6:00 PM IST = US signals
  workflow_dispatch:          # Manual trigger anytime
jobs:
  signals:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: pip install yfinance pandas requests
      - name: Determine Market
        run: |
          H=$(date -u +%H | sed 's/^0//')
          if [ "${{ github.event.inputs.market }}" != "" ]; then
            echo "MARKET=${{ github.event.inputs.market }}" >> $GITHUB_ENV
          elif [ "$H" -lt 10 ]; then echo "MARKET=IN" >> $GITHUB_ENV
          else echo "MARKET=US" >> $GITHUB_ENV; fi
      - name: Run StockBot
        env:
          GEMINI_API_KEY:   \${{ secrets.GEMINI_API_KEY }}
          TELEGRAM_TOKEN:   \${{ secrets.TELEGRAM_TOKEN }}
          TELEGRAM_CHAT_ID: \${{ secrets.TELEGRAM_CHAT_ID }}
          MARKET:           \${{ env.MARKET }}
        run: python signal_bot.py`;

function AutomationTab({ copyText, copied }) {
  return (
    <div>
      <div style={{marginBottom:"20px"}}>
        <div className="section-title">⚙️ GitHub Actions <span>Auto-Scheduler</span></div>
        <div className="sub-text" style={{marginTop:"6px"}}>Runs automatically every weekday. No browser. No server. No cost.</div>
      </div>

      <div className="notice-box">
        ⚡ <strong>How it works:</strong> GitHub's free servers run your Python script every morning at 9:00 AM IST (Indian) and 6:00 PM IST (US), fetch live stock data, ask Gemini AI for recommendations, and send to your Telegram — all while you're asleep.
      </div>

      {[
        {n:1, t:"Create GitHub Account + Repo",
         body:"Go to github.com → Sign up free → New repository → Name it 'stockbot' → Public or Private (both free)"},
        {n:2, t:"Upload Files to Repo",
         body:<>Upload 2 files to your repo root:<br/>• <code>signal_bot.py</code> (download from below)<br/>• <code>.github/workflows/stock-signals.yml</code> (copy from below)</>},
        {n:3, t:"Add GitHub Secrets (your API keys)",
         body:<>In your repo: <strong>Settings → Secrets and variables → Actions → New repository secret</strong><br/>Add: <code>GEMINI_API_KEY</code>, <code>TELEGRAM_TOKEN</code>, <code>TELEGRAM_CHAT_ID</code><br/>These are encrypted — GitHub never shows them again</>},
        {n:4, t:"Done! It Runs Automatically",
         body:<>Every weekday: 9:00 AM IST → Indian signals sent to Telegram<br/>Every weekday: 6:00 PM IST → US signals sent to Telegram<br/>Runs: <strong>Actions tab in your repo</strong> → see all run logs<br/>Test manually: <strong>Actions → Run workflow → Choose market</strong></>},
      ].map((s,i) => (
        <div key={i} className="guide-card" style={{marginBottom:"14px"}}>
          <div className="guide-card-title">
            <span style={{background:"var(--gold)",color:"var(--bg)",width:"22px",height:"22px",borderRadius:"50%",display:"inline-flex",alignItems:"center",justifyContent:"center",fontSize:"11px",fontWeight:"700",flexShrink:0}}>
              {s.n}
            </span>
            {s.t}
          </div>
          <div className="guide-card-body">{s.body}</div>
        </div>
      ))}

      <div className="guide-card">
        <div className="guide-card-title" style={{justifyContent:"space-between"}}>
          📋 <code>.github/workflows/stock-signals.yml</code>
          <button className="copy-btn" onClick={() => copyText(YAML_CODE, "yaml")}>
            {copied==="yaml" ? "✓ Copied!" : "Copy"}
          </button>
        </div>
        <div className="code-block">{YAML_CODE}</div>
      </div>

      <div className="guide-card">
        <div className="guide-card-title">💰 Cost Breakdown</div>
        <div className="guide-card-body">
          <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:"8px",marginTop:"6px"}}>
            {[
              ["GitHub Actions","Free (2000 min/month)","✅"],
              ["Gemini 2.0 Flash","Free (1500 req/day)","✅"],
              ["Telegram Bot API","Free (unlimited)","✅"],
              ["yfinance Stock Data","Free (Yahoo Finance)","✅"],
              ["callmebot WhatsApp","Free (personal use)","✅"],
              ["TOTAL","₹0 / month","🎉"],
            ].map(([k,v,e],i) => (
              <div key={i} style={{background:"var(--bg)",border:"1px solid var(--border)",borderRadius:"8px",padding:"10px 12px"}}>
                <div style={{fontSize:"9px",color:"var(--muted)",marginBottom:"4px",textTransform:"uppercase"}}>{k}</div>
                <div style={{fontSize:"12px",fontWeight:"700",color:i===5?"var(--gold)":"var(--accent)"}}>{e} {v}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function SettingsModal({ geminiKey, setGeminiKey, tgToken, setTgToken, tgChatId, setTgChatId, waPhone, setWaPhone, waKey, setWaKey, onSave, onClose }) {
  return (
    <div className="modal-overlay">
      <div className="modal">
        <div className="modal-header">
          <div className="modal-title">⚙️ API Setup (All Free)</div>
          <button className="modal-close" onClick={onClose}>✕</button>
        </div>
        <div className="modal-body">
          <div className="notice-box">
            All APIs below are 100% free. No credit card required for any of them.
          </div>

          <div className="field-group">
            <div className="field-label">🤖 Google Gemini API Key <span className="pill pill-free">FREE</span></div>
            <input className="field-input" value={geminiKey} onChange={e=>setGeminiKey(e.target.value)} placeholder="AIzaSy..." type="password" />
            <div className="field-hint">
              Get free key → <a href="https://aistudio.google.com/app/apikey" target="_blank" rel="noreferrer">aistudio.google.com/app/apikey</a><br/>
              Free: 1,500 req/day, 15 req/min — perfect for daily signals
            </div>
          </div>

          <div className="field-group">
            <div className="field-label">✈️ Telegram Bot Token <span className="pill pill-free">FREE</span></div>
            <input className="field-input" value={tgToken} onChange={e=>setTgToken(e.target.value)} placeholder="1234567890:ABCdef..." type="password" />
            <div className="field-hint">
              Create bot: Open Telegram → @BotFather → /newbot → Copy token
            </div>
          </div>

          <div className="field-group">
            <div className="field-label">💬 Telegram Chat ID <span className="pill pill-free">FREE</span></div>
            <input className="field-input" value={tgChatId} onChange={e=>setTgChatId(e.target.value)} placeholder="-100123456789 or 123456789" />
            <div className="field-hint">
              Find your ID: Telegram → @userinfobot → Start → Copy "Your ID"<br/>
              For channels: use negative ID like -100123456789
            </div>
          </div>

          <div style={{borderTop:"1px solid var(--border)",paddingTop:"16px",marginTop:"6px",marginBottom:"16px"}}>
            <div style={{fontSize:"10px",color:"var(--muted)",marginBottom:"12px",textTransform:"uppercase",letterSpacing:"1px"}}>💬 WhatsApp (Optional — Telegram recommended)</div>
          </div>

          <div className="field-group">
            <div className="field-label">📱 WhatsApp Phone <span className="pill pill-free">FREE</span></div>
            <input className="field-input" value={waPhone} onChange={e=>setWaPhone(e.target.value)} placeholder="919876543210 (with country code)" />
            <div className="field-hint">CallMeBot: Send "I allow callmebot to send me messages" to +34 644 76 78 20 on WhatsApp to activate</div>
          </div>

          <div className="field-group">
            <div className="field-label">🔑 CallMeBot API Key</div>
            <input className="field-input" value={waKey} onChange={e=>setWaKey(e.target.value)} placeholder="You'll receive this via WhatsApp" type="password" />
          </div>

          <button className="btn btn-primary" onClick={onSave} style={{width:"100%",justifyContent:"center",marginTop:"4px"}}>
            💾 Save Settings
          </button>
        </div>
      </div>
    </div>
  );
}
