"""
Should I Buy Today? — Minimalist Long-Term Investor Copilot

Run:
    streamlit run should_i_buy_today_world_class.py

Purpose:
    A clean buy-sizing tool for long-term index investors.
    It sizes NEW buys. It does not generate sell signals.
"""

from __future__ import annotations

import math
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st
import yfinance as yf

try:
    from newsapi import NewsApiClient
except Exception:  # optional
    NewsApiClient = None

try:
    from pytrends.request import TrendReq
except Exception:  # optional
    TrendReq = None


# ============================================================
# App Config
# ============================================================
st.set_page_config(
    page_title="Should I Buy Today?",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ============================================================
# Small Utilities
# ============================================================
def safe_float(v: Any) -> Optional[float]:
    try:
        if v is None:
            return None
        x = float(v)
        if math.isnan(x) or math.isinf(x):
            return None
        return x
    except Exception:
        return None


def clamp(v: Any, lo: float = 0, hi: float = 100) -> Optional[float]:
    x = safe_float(v)
    if x is None:
        return None
    return max(lo, min(hi, x))


def fmt(v: Any, suffix: str = "", digits: int = 2) -> str:
    x = safe_float(v)
    if x is None:
        return "N/A"
    if digits == 0:
        return f"{x:,.0f}{suffix}"
    return f"{x:,.{digits}f}{suffix}"


def score_from_range(v: Any, points: List[Tuple[float, float]]) -> Optional[float]:
    x = safe_float(v)
    if x is None:
        return None
    pts = sorted(points, key=lambda p: p[0])
    if x <= pts[0][0]:
        return float(pts[0][1])
    if x >= pts[-1][0]:
        return float(pts[-1][1])
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        if x1 <= x <= x2:
            pct = (x - x1) / (x2 - x1)
            return y1 + pct * (y2 - y1)
    return None


def compute_rsi(close: pd.Series, window: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / window, min_periods=window, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / window, min_periods=window, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, pd.NA)
    return 100 - (100 / (1 + rs))


# ============================================================
# Theme + Design System
# ============================================================
if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = False

THEMES = {
    "light": {
        "bg": "#f5f7fb",
        "bg2": "#edf2f7",
        "surface": "rgba(255,255,255,.78)",
        "surface_solid": "#ffffff",
        "surface2": "rgba(248,250,252,.88)",
        "text": "#0f172a",
        "muted": "#64748b",
        "muted2": "#94a3b8",
        "border": "rgba(15,23,42,.10)",
        "shadow": "0 28px 80px rgba(15,23,42,.10)",
        "shadow2": "0 14px 36px rgba(15,23,42,.075)",
        "green": "#16a34a",
        "yellow": "#f59e0b",
        "orange": "#f97316",
        "red": "#ef4444",
        "blue": "#2563eb",
        "purple": "#7c3aed",
    },
    "dark": {
        "bg": "#070b13",
        "bg2": "#0d1320",
        "surface": "rgba(16,23,37,.78)",
        "surface_solid": "#101725",
        "surface2": "rgba(20,29,46,.86)",
        "text": "#f8fafc",
        "muted": "#a1aab8",
        "muted2": "#7c8797",
        "border": "rgba(255,255,255,.10)",
        "shadow": "0 30px 90px rgba(0,0,0,.38)",
        "shadow2": "0 18px 44px rgba(0,0,0,.30)",
        "green": "#22c55e",
        "yellow": "#fbbf24",
        "orange": "#fb923c",
        "red": "#fb7185",
        "blue": "#60a5fa",
        "purple": "#a78bfa",
    },
}


def theme() -> Dict[str, str]:
    return THEMES["dark" if st.session_state.dark_mode else "light"]


def inject_css(t: Dict[str, str]) -> None:
    st.markdown(
        f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;650;750;850;900&display=swap');

* {{
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}}

:root {{
  --bg: {t['bg']};
  --bg2: {t['bg2']};
  --surface: {t['surface']};
  --surface-solid: {t['surface_solid']};
  --surface2: {t['surface2']};
  --text: {t['text']};
  --muted: {t['muted']};
  --muted2: {t['muted2']};
  --border: {t['border']};
  --shadow: {t['shadow']};
  --shadow2: {t['shadow2']};
  --green: {t['green']};
  --yellow: {t['yellow']};
  --orange: {t['orange']};
  --red: {t['red']};
  --blue: {t['blue']};
  --purple: {t['purple']};
}}

.stApp {{
  color: var(--text);
  background:
    radial-gradient(circle at 8% 0%, rgba(96,165,250,.16), transparent 26%),
    radial-gradient(circle at 96% 6%, rgba(34,197,94,.13), transparent 27%),
    radial-gradient(circle at 62% 100%, rgba(251,113,133,.10), transparent 30%),
    linear-gradient(180deg, var(--bg) 0%, var(--bg2) 100%);
}}

[data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stDecoration"] {{
  background: transparent !important;
}}
[data-testid="stToolbar"], [data-testid="stDecoration"] {{ display: none !important; }}
.block-container {{
  max-width: 1240px;
  padding-top: 1.1rem;
  padding-bottom: 3rem;
  position: relative;
  z-index: 2;
}}

@keyframes aurora {{
  0%,100% {{ transform: translate3d(-2%, -2%, 0) scale(1); opacity: .72; }}
  50% {{ transform: translate3d(2%, 3%, 0) scale(1.06); opacity: .98; }}
}}
@keyframes rise {{
  from {{ opacity: 0; transform: translateY(18px) scale(.985); filter: blur(6px); }}
  to {{ opacity: 1; transform: translateY(0) scale(1); filter: blur(0); }}
}}
@keyframes shimmer {{
  0% {{ transform: translateX(-140%); opacity: 0; }}
  18% {{ opacity: .85; }}
  100% {{ transform: translateX(240%); opacity: 0; }}
}}
@keyframes livePulse {{
  0% {{ box-shadow: 0 0 0 0 rgba(34,197,94,.45); transform: scale(.92); }}
  70% {{ box-shadow: 0 0 0 10px rgba(34,197,94,0); transform: scale(1.06); }}
  100% {{ box-shadow: 0 0 0 0 rgba(34,197,94,0); transform: scale(.92); }}
}}
@keyframes scorePop {{
  0% {{ opacity: 0; transform: translateY(14px) scale(.85); }}
  70% {{ opacity: 1; transform: translateY(-3px) scale(1.03); }}
  100% {{ opacity: 1; transform: translateY(0) scale(1); }}
}}
@keyframes markerPulse {{
  0%,100% {{ transform: scale(1); box-shadow: 0 10px 28px rgba(0,0,0,.28), 0 0 0 0 rgba(255,255,255,.30); }}
  50% {{ transform: scale(1.08); box-shadow: 0 18px 44px rgba(0,0,0,.34), 0 0 0 10px rgba(255,255,255,0); }}
}}

.stApp::before {{
  content: "";
  position: fixed;
  inset: -18%;
  z-index: 0;
  pointer-events: none;
  background:
    radial-gradient(circle at 18% 18%, rgba(96,165,250,.19), transparent 27%),
    radial-gradient(circle at 84% 12%, rgba(34,197,94,.14), transparent 28%),
    radial-gradient(circle at 58% 88%, rgba(251,113,133,.13), transparent 30%);
  filter: blur(28px);
  animation: aurora 14s ease-in-out infinite;
}}

.topbar {{
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  margin-bottom: 12px;
}}
.brand {{
  display: flex;
  align-items: center;
  gap: 11px;
  color: var(--text);
  font-weight: 950;
  letter-spacing: -.4px;
}}
.brand-badge {{
  width: 38px;
  height: 38px;
  border-radius: 14px;
  display: grid;
  place-items: center;
  background: linear-gradient(135deg, rgba(96,165,250,.18), rgba(34,197,94,.12));
  border: 1px solid var(--border);
  box-shadow: var(--shadow2);
}}
.utility-row {{
  display: flex;
  gap: 10px;
  align-items: center;
}}

button {{ transition: all .16s ease !important; }}
div[data-testid="stButton"] button {{
  height: 42px;
  border-radius: 999px;
  background: var(--surface);
  color: var(--text);
  border: 1px solid var(--border);
  font-weight: 850;
  box-shadow: none;
}}
div[data-testid="stButton"] button:hover {{
  transform: translateY(-1px);
  border-color: rgba(96,165,250,.38);
}}

.hero {{
  position: relative;
  overflow: hidden;
  border-radius: 34px;
  padding: 28px;
  background:
    linear-gradient(135deg, var(--surface) 0%, var(--surface2) 100%);
  border: 1px solid var(--border);
  box-shadow: var(--shadow);
  backdrop-filter: blur(18px);
  animation: rise .62s cubic-bezier(.2,.9,.2,1) both;
}}
.hero::after {{
  content: "";
  position: absolute;
  inset: 0;
  width: 40%;
  background: linear-gradient(90deg, transparent, rgba(255,255,255,.18), transparent);
  animation: shimmer 4.8s ease-in-out infinite;
  pointer-events: none;
}}
.hero-grid {{
  display: grid;
  grid-template-columns: 1.15fr .85fr;
  gap: 18px;
  align-items: stretch;
}}
.hero-title {{
  font-size: clamp(40px, 5.8vw, 82px);
  line-height: .88;
  letter-spacing: -3.3px;
  color: var(--text);
  font-weight: 950;
  margin: 12px 0 0;
}}
.hero-subtitle {{
  color: var(--muted);
  font-size: 16px;
  font-weight: 700;
  margin-top: 14px;
  line-height: 1.46;
  max-width: 680px;
}}
.live-pill {{
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-radius: 999px;
  border: 1px solid rgba(34,197,94,.22);
  background: rgba(34,197,94,.11);
  color: var(--green);
  font-size: 12px;
  font-weight: 950;
}}
.live-dot {{
  width: 9px;
  height: 9px;
  background: var(--green);
  border-radius: 999px;
  animation: livePulse 1.7s ease-out infinite;
}}
.timestamp {{
  color: var(--muted);
  font-size: 12px;
  font-weight: 760;
  margin-top: 18px;
}}

.score-panel {{
  border-radius: 28px;
  padding: 24px;
  background: rgba(255,255,255,.08);
  border: 1px solid var(--border);
}}
.score-top {{
  display: flex;
  justify-content: space-between;
  gap: 14px;
  align-items: flex-start;
}}
.kicker {{
  color: var(--muted);
  font-size: 11px;
  font-weight: 950;
  text-transform: uppercase;
  letter-spacing: .78px;
}}
.score-number {{
  color: var(--text);
  font-size: clamp(64px, 7vw, 104px);
  line-height: .8;
  font-weight: 950;
  letter-spacing: -5px;
  animation: scorePop .76s cubic-bezier(.18,.9,.2,1) both;
}}
.heat-label {{
  color: var(--text);
  text-align: right;
  font-size: 28px;
  font-weight: 950;
  letter-spacing: -1px;
}}
.heat-note {{
  color: var(--muted);
  text-align: right;
  font-size: 12px;
  font-weight: 780;
  margin-top: 6px;
}}
.meter {{
  margin-top: 26px;
  height: 22px;
  border-radius: 999px;
  overflow: hidden;
  position: relative;
  background: linear-gradient(90deg, var(--green) 0%, var(--green) 25%, var(--yellow) 25%, var(--yellow) 65%, var(--orange) 65%, var(--orange) 82%, var(--red) 82%, var(--red) 100%);
}}
.meter::after {{
  content: "";
  position: absolute;
  inset: 0;
  width: 35%;
  background: linear-gradient(90deg, transparent, rgba(255,255,255,.32), transparent);
  animation: shimmer 2.6s ease-in-out infinite;
}}
.marker {{
  position: relative;
  width: 26px;
  height: 26px;
  border-radius: 999px;
  background: var(--text);
  border: 5px solid var(--surface-solid);
  margin-top: -24px;
  animation: markerPulse 2s ease-in-out infinite;
}}
.scale {{
  margin-top: 14px;
  display: flex;
  justify-content: space-between;
  color: var(--muted);
  font-size: 12px;
  font-weight: 850;
}}
.guardrail {{
  margin-top: 20px;
  border-radius: 20px;
  padding: 14px 15px;
  background: rgba(96,165,250,.10);
  border: 1px solid rgba(96,165,250,.17);
  color: var(--muted);
  line-height: 1.42;
  font-size: 13px;
  font-weight: 740;
}}
.guardrail b {{ color: var(--text); }}

.plan-grid {{
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-top: 18px;
}}
.tile {{
  border-radius: 24px;
  padding: 18px;
  background: var(--surface);
  border: 1px solid var(--border);
  box-shadow: var(--shadow2);
  backdrop-filter: blur(16px);
  animation: rise .65s cubic-bezier(.2,.9,.2,1) both;
  transition: transform .18s ease, border-color .18s ease, box-shadow .18s ease;
}}
.tile:hover {{
  transform: translateY(-4px);
  border-color: rgba(96,165,250,.34);
  box-shadow: var(--shadow);
}}
.tile-value {{
  color: var(--text);
  font-size: 20px;
  font-weight: 950;
  letter-spacing: -.45px;
  margin-top: 6px;
}}
.tile-copy {{
  color: var(--muted);
  font-size: 13px;
  line-height: 1.36;
  margin-top: 8px;
}}

.section {{
  color: var(--text);
  font-size: 25px;
  font-weight: 950;
  letter-spacing: -.7px;
  margin: 28px 0 10px;
}}
.section-sub {{
  color: var(--muted);
  font-size: 14px;
  margin-top: -2px;
  margin-bottom: 14px;
}}

.reason-grid {{
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 14px;
}}
.reason-card {{ min-height: 150px; }}
.reason-title {{
  color: var(--text);
  font-size: 21px;
  font-weight: 950;
  letter-spacing: -.4px;
  margin-top: 8px;
}}
.reason-copy {{
  color: var(--muted);
  font-size: 14px;
  line-height: 1.44;
  margin-top: 9px;
}}

.lens-grid {{
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 14px;
}}
.lens-title {{
  color: var(--text);
  font-size: 19px;
  font-weight: 950;
  margin-top: 8px;
}}

.signal-row {{
  display: grid;
  grid-template-columns: 150px 110px 1fr 150px;
  gap: 14px;
  align-items: center;
  border-radius: 18px;
  padding: 14px 16px;
  margin-bottom: 10px;
  background: var(--surface);
  border: 1px solid var(--border);
  box-shadow: 0 8px 24px rgba(15,23,42,.045);
}}
.signal-name, .signal-read, .signal-do {{
  color: var(--text);
  font-weight: 930;
}}
.signal-meaning {{
  color: var(--muted);
  font-size: 14px;
}}
.signal-do {{ text-align: right; }}

.badge {{
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  padding: 7px 10px;
  font-size: 12px;
  font-weight: 950;
  margin-top: 12px;
}}
.good {{ color: var(--green); background: rgba(34,197,94,.12); border: 1px solid rgba(34,197,94,.22); }}
.normal {{ color: var(--yellow); background: rgba(251,191,36,.12); border: 1px solid rgba(251,191,36,.22); }}
.hot {{ color: var(--orange); background: rgba(249,115,22,.12); border: 1px solid rgba(249,115,22,.22); }}
.veryhot {{ color: var(--red); background: rgba(251,113,133,.12); border: 1px solid rgba(251,113,133,.22); }}
.info {{ color: var(--blue); background: rgba(96,165,250,.12); border: 1px solid rgba(96,165,250,.22); }}

.input-panel {{
  border-radius: 26px;
  padding: 18px;
  background: var(--surface);
  border: 1px solid var(--border);
  box-shadow: var(--shadow2);
}}

.stTabs [data-baseweb="tab-list"] {{ gap: 8px; }}
.stTabs [data-baseweb="tab"] {{
  border-radius: 999px;
  background: var(--surface);
  border: 1px solid var(--border);
  color: var(--text);
  font-weight: 800;
}}
.stTabs [aria-selected="true"] {{ border-color: rgba(96,165,250,.45) !important; }}

.footer {{
  color: var(--muted);
  font-size: 12px;
  line-height: 1.5;
  border-top: 1px solid var(--border);
  padding-top: 18px;
  margin-top: 24px;
}}

@media (max-width: 920px) {{
  .hero-grid, .plan-grid, .reason-grid, .lens-grid {{ grid-template-columns: 1fr; }}
  .signal-row {{ grid-template-columns: 1fr; gap: 6px; }}
  .signal-do {{ text-align: left; }}
  .score-top {{ flex-direction: column; }}
  .heat-label, .heat-note {{ text-align: left; }}
}}

@media (prefers-reduced-motion: reduce) {{
  *, *::before, *::after {{
    animation-duration: .001ms !important;
    animation-iteration-count: 1 !important;
    scroll-behavior: auto !important;
  }}
}}
</style>
""",
        unsafe_allow_html=True,
    )


# ============================================================
# Data Fetching
# ============================================================
@st.cache_data(ttl=900, show_spinner=False)
def fetch_sp500() -> Optional[Dict[str, Any]]:
    try:
        df = yf.Ticker("^GSPC").history(period="1y", interval="1d", auto_adjust=False)
        if df is None or df.empty or len(df.dropna(subset=["Close"])) < 220:
            return None
        df = df.dropna(subset=["Close"]).copy()
        df["RSI"] = compute_rsi(df["Close"], 14)
        df["SMA_200"] = df["Close"].rolling(200).mean()
        last = df.iloc[-1]
        close = safe_float(last["Close"])
        sma = safe_float(last["SMA_200"])
        dist = ((close - sma) / sma) * 100 if close and sma else None
        out = df.reset_index().rename(columns={"index": "Date"})
        if "Date" not in out.columns:
            out = out.rename(columns={out.columns[0]: "Date"})
        return {
            "close": round(close, 2) if close else None,
            "rsi": round(safe_float(last["RSI"]), 2) if safe_float(last["RSI"]) is not None else None,
            "sma": round(sma, 2) if sma else None,
            "dist": round(dist, 2) if dist is not None else None,
            "history": out,
        }
    except Exception:
        return None


@st.cache_data(ttl=900, show_spinner=False)
def fetch_vix() -> Optional[float]:
    try:
        df = yf.Ticker("^VIX").history(period="1mo", interval="1d", auto_adjust=False)
        if df is None or df.empty:
            return None
        return round(float(df["Close"].dropna().iloc[-1]), 2)
    except Exception:
        return None


@st.cache_data(ttl=900, show_spinner=False)
def fetch_pcr() -> Optional[float]:
    # CBOE equity put/call ratio via YCharts public chart endpoint.
    # Gracefully returns None if blocked or changed.
    url = (
        "https://ycharts.com/charts/fund_data.json"
        "?calcs=&chartId=&chartType=interactive&correlations=&"
        "customGrowthAmount=&dataInLegend=value&dateSelection=range&"
        "format=real&legendOnChart=false&lineAnnotations=&nameInLegend=name_and_ticker&"
        "partner=basic_2000&performanceDisclosure=false&recessions=false&scaleType=linear&"
        "securities=id%3AI%3ACBOEEPCR%2Cinclude%3Atrue%2C%2C&maxPoints=594"
    )
    try:
        r = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        return round(float(r.json()["chart_data"][0][0]["last_value"]), 2)
    except Exception:
        return None


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_yields() -> Dict[str, float]:
    url = (
        "https://quote.cnbc.com/quote-html-webservice/restQuote/symbolType/symbol?"
        "symbols=US2Y%7CUS10Y&requestMethod=itv&noform=1&partnerId=2&fund=1&"
        "exthrs=1&output=json&events=1"
    )
    try:
        r = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        quotes = r.json()["FormattedQuoteResult"]["FormattedQuote"]
        return {q["symbol"]: float(str(q["last"]).strip("%")) for q in quotes if q.get("symbol") and q.get("last")}
    except Exception:
        return {}


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_trends(term: str = "stock market crash") -> Optional[int]:
    if TrendReq is None:
        return None
    try:
        py = TrendReq(hl="en-US", tz=360, timeout=(10, 25))
        py.build_payload([term], timeframe="now 7-d", geo="US")
        df = py.interest_over_time()
        if df is None or df.empty or term not in df.columns:
            return None
        return int(df[term].dropna().iloc[-1])
    except Exception:
        return None


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_news_score() -> Optional[int]:
    key = None
    try:
        key = st.secrets.get("NEWSAPI_KEY", None)
    except Exception:
        pass
    key = key or os.getenv("NEWSAPI_KEY")
    if not key or NewsApiClient is None:
        return None

    bearish = [
        "crash", "collapse", "meltdown", "plunge", "sell-off", "recession", "panic",
        "fear", "turmoil", "bearish", "volatility", "losses", "decline", "drop",
    ]
    bullish = [
        "rally", "surge", "soar", "rebound", "recovery", "growth", "momentum",
        "bullish", "optimism", "strength", "record high", "gains", "upgrade",
    ]
    try:
        client = NewsApiClient(api_key=key)
        articles = client.get_everything(q="S&P 500 OR stock market", language="en", page_size=40).get("articles", [])
        titles = [(a.get("title") or "").lower() for a in articles]
        bear_count = sum(any(w in t for w in bearish) for t in titles)
        bull_count = sum(any(w in t for w in bullish) for t in titles)
        return int(clamp(50 + 3 * (bull_count - bear_count), 0, 100))
    except Exception:
        return None


# ============================================================
# Signal Model
# ============================================================
def heat_label(score: Optional[int]) -> Tuple[str, str]:
    if score is None:
        return "Unknown", "info"
    if score <= 25:
        return "Fear", "good"
    if score <= 45:
        return "Better Setup", "good"
    if score <= 65:
        return "Normal", "normal"
    if score <= 80:
        return "Hot", "hot"
    return "Very Hot", "veryhot"


def today_call(score: Optional[int]) -> Dict[str, str]:
    if score is None:
        return {
            "call": "BUY NORMALLY",
            "copy": "Data is incomplete. Stay on your normal plan.",
            "now": "100% normal DCA",
            "later": "No extra lump sum",
            "avoid": "Guessing",
            "badge": "info",
            "confidence_base": "Low",
        }
    if score <= 25:
        return {
            "call": "BUY MORE",
            "copy": "Fear is elevated. Good long-term buying setup if cash plan allows.",
            "now": "125%–200%",
            "later": "Keep DCA active",
            "avoid": "Panic waiting",
            "badge": "good",
            "confidence_base": "Medium",
        }
    if score <= 45:
        return {
            "call": "BUY SLIGHTLY MORE",
            "copy": "Conditions are better than normal. Buy a little above schedule.",
            "now": "110%–150%",
            "later": "DCA the rest",
            "avoid": "Overthinking",
            "badge": "good",
            "confidence_base": "Medium",
        }
    if score <= 65:
        return {
            "call": "BUY NORMALLY",
            "copy": "Nothing special. Stay on your regular plan.",
            "now": "100%",
            "later": "Stay scheduled",
            "avoid": "Timing games",
            "badge": "normal",
            "confidence_base": "Medium",
        }
    if score <= 80:
        return {
            "call": "BUY SMALLER",
            "copy": "Market is hot. Keep investing, but size down new lump-sum buys.",
            "now": "25%–50%",
            "later": "DCA the rest",
            "avoid": "Chasing",
            "badge": "hot",
            "confidence_base": "Medium-High",
        }
    return {
        "call": "DON’T CHASE",
        "copy": "Too much enthusiasm. Keep DCA active, but wait on large lump-sum buys.",
        "now": "0%–25%",
        "later": "DCA only",
        "avoid": "FOMO buying",
        "badge": "veryhot",
        "confidence_base": "Medium-High",
    }


def signal_read(signal: str, value: Optional[float]) -> Dict[str, Any]:
    if signal == "VIX":
        if value is None:
            return {"Signal": "VIX", "Read": "Missing", "Meaning": "Volatility data unavailable.", "Action": "Ignore for now", "Severity": 1}
        if value < 14:
            return {"Signal": "VIX", "Read": fmt(value), "Meaning": "Market is very calm. Calm can become complacency.", "Action": "Slight caution", "Severity": 3}
        if value < 20:
            return {"Signal": "VIX", "Read": fmt(value), "Meaning": "Volatility is normal. No major fear discount.", "Action": "Neutral", "Severity": 2}
        if value < 28:
            return {"Signal": "VIX", "Read": fmt(value), "Meaning": "Some fear is showing up.", "Action": "Better setup", "Severity": 4}
        return {"Signal": "VIX", "Read": fmt(value), "Meaning": "Fear is elevated. Better prices may be appearing.", "Action": "Buy more", "Severity": 5}

    if signal == "S&P 500 RSI":
        if value is None:
            return {"Signal": signal, "Read": "Missing", "Meaning": "RSI unavailable.", "Action": "Ignore for now", "Severity": 1}
        if value < 30:
            return {"Signal": signal, "Read": fmt(value), "Meaning": "Oversold. The market may be stretched down short term.", "Action": "Buy more", "Severity": 5}
        if value < 40:
            return {"Signal": signal, "Read": fmt(value), "Meaning": "Near oversold. Buying conditions are improving.", "Action": "Better setup", "Severity": 4}
        if value <= 60:
            return {"Signal": signal, "Read": fmt(value), "Meaning": "Neutral. The market is not stretched.", "Action": "Neutral", "Severity": 2}
        if value <= 70:
            return {"Signal": signal, "Read": fmt(value), "Meaning": "Near overbought. Use some discipline.", "Action": "Buy smaller", "Severity": 4}
        return {"Signal": signal, "Read": fmt(value), "Meaning": "Overbought. The S&P 500 is stretched short term.", "Action": "Do not chase", "Severity": 5}

    if signal == "S&P vs 200D":
        if value is None:
            return {"Signal": signal, "Read": "Missing", "Meaning": "Trend distance unavailable.", "Action": "Ignore for now", "Severity": 1}
        if value < -8:
            return {"Signal": signal, "Read": fmt(value, "%"), "Meaning": "Market is well below long-term trend.", "Action": "Buy more", "Severity": 5}
        if value < -2:
            return {"Signal": signal, "Read": fmt(value, "%"), "Meaning": "Market is below trend.", "Action": "Better setup", "Severity": 4}
        if value <= 8:
            return {"Signal": signal, "Read": fmt(value, "%"), "Meaning": "Market is near long-term trend.", "Action": "Neutral", "Severity": 2}
        return {"Signal": signal, "Read": fmt(value, "%"), "Meaning": "Market is stretched above trend.", "Action": "Buy smaller", "Severity": 5}

    if signal == "Put/Call":
        if value is None:
            return {"Signal": signal, "Read": "Missing", "Meaning": "Options sentiment unavailable.", "Action": "Ignore for now", "Severity": 1}
        if value < 0.65:
            return {"Signal": signal, "Read": fmt(value), "Meaning": "Too much call buying. Traders are leaning greedy.", "Action": "Buy smaller", "Severity": 5}
        if value <= 1.10:
            return {"Signal": signal, "Read": fmt(value), "Meaning": "Options positioning is balanced.", "Action": "Neutral", "Severity": 2}
        return {"Signal": signal, "Read": fmt(value), "Meaning": "More hedging and fear in options.", "Action": "Better setup", "Severity": 4}

    if signal == "10Y-2Y":
        if value is None:
            return {"Signal": signal, "Read": "Missing", "Meaning": "Yield curve unavailable.", "Action": "Ignore for now", "Severity": 1}
        if value < 0:
            return {"Signal": signal, "Read": fmt(value, "%", 3), "Meaning": "Yield curve is inverted. Macro deserves caution.", "Action": "Small caution", "Severity": 3}
        return {"Signal": signal, "Read": fmt(value, "%", 3), "Meaning": "Yield curve is positive. Macro backdrop is okay.", "Action": "Small impact", "Severity": 2}

    if signal == "Google Trends":
        if value is None:
            return {"Signal": signal, "Read": "Missing", "Meaning": "Search sentiment unavailable.", "Action": "Optional", "Severity": 1}
        if value >= 60:
            return {"Signal": signal, "Read": fmt(value, "", 0), "Meaning": "Crash searches are rising. Public fear may be increasing.", "Action": "Better setup", "Severity": 3}
        return {"Signal": signal, "Read": fmt(value, "", 0), "Meaning": "No major fear-search spike.", "Action": "Small impact", "Severity": 2}

    if signal == "News":
        if value is None:
            return {"Signal": signal, "Read": "Missing", "Meaning": "Headline score unavailable.", "Action": "Optional", "Severity": 1}
        if value > 60:
            return {"Signal": signal, "Read": fmt(value, "", 0), "Meaning": "Headlines are optimistic.", "Action": "Slight caution", "Severity": 3}
        if value < 40:
            return {"Signal": signal, "Read": fmt(value, "", 0), "Meaning": "Headlines are negative.", "Action": "Better setup", "Severity": 3}
        return {"Signal": signal, "Read": fmt(value, "", 0), "Meaning": "Headline tone is mixed.", "Action": "Small impact", "Severity": 2}

    return {"Signal": signal, "Read": str(value), "Meaning": "Unknown.", "Action": "Neutral", "Severity": 1}


def build_score(vix: Optional[float], rsi: Optional[float], dist: Optional[float], pcr: Optional[float], curve: Optional[float], trends: Optional[int], news: Optional[int]) -> Tuple[Optional[int], pd.DataFrame]:
    rows = [
        {
            "Indicator": "VIX",
            "Reading": fmt(vix),
            "Score": score_from_range(vix, [(12, 85), (18, 62), (25, 38), (35, 15), (50, 5)]),
            "Weight": 0.24,
            "Meaning": "High VIX = more fear, often better entry points.",
        },
        {
            "Indicator": "S&P 500 RSI",
            "Reading": fmt(rsi),
            "Score": score_from_range(rsi, [(25, 10), (35, 25), (50, 50), (65, 72), (75, 90), (85, 100)]),
            "Weight": 0.21,
            "Meaning": "High RSI = overbought; low RSI = oversold.",
        },
        {
            "Indicator": "S&P vs 200D",
            "Reading": fmt(dist, "%"),
            "Score": score_from_range(dist, [(-20, 8), (-10, 20), (0, 48), (8, 68), (15, 84), (25, 96)]),
            "Weight": 0.21,
            "Meaning": "Distance from long-term trend.",
        },
        {
            "Indicator": "Put/Call",
            "Reading": fmt(pcr),
            "Score": score_from_range(pcr, [(0.55, 90), (0.75, 70), (0.95, 52), (1.15, 35), (1.40, 15)]),
            "Weight": 0.15,
            "Meaning": "Low can mean call chasing. High can mean fear.",
        },
        {
            "Indicator": "10Y-2Y",
            "Reading": fmt(curve, "%", 3),
            "Score": score_from_range(curve, [(-1.2, 70), (-0.5, 58), (0, 50), (0.8, 45), (1.5, 48)]),
            "Weight": 0.07,
            "Meaning": "Macro context only. Small weight.",
        },
        {
            "Indicator": "Google Trends",
            "Reading": fmt(trends, "", 0),
            "Score": score_from_range(trends, [(0, 72), (20, 62), (50, 45), (80, 25), (100, 10)]),
            "Weight": 0.06,
            "Meaning": "Crash-search spikes imply public fear.",
        },
        {
            "Indicator": "News",
            "Reading": fmt(news, "", 0),
            "Score": news,
            "Weight": 0.06,
            "Meaning": "Optional headline tone. Low weight.",
        },
    ]
    df = pd.DataFrame(rows)
    usable = df.dropna(subset=["Score"]).copy()
    if usable.empty:
        return None, df
    usable["AdjWeight"] = usable["Weight"] / usable["Weight"].sum()
    score = int(round((usable["Score"] * usable["AdjWeight"]).sum()))
    return int(clamp(score, 0, 100)), df


def build_signal_df(vix: Optional[float], rsi: Optional[float], dist: Optional[float], pcr: Optional[float], curve: Optional[float], trends: Optional[int], news: Optional[int]) -> pd.DataFrame:
    rows = [
        signal_read("VIX", vix),
        signal_read("S&P 500 RSI", rsi),
        signal_read("S&P vs 200D", dist),
        signal_read("Put/Call", pcr),
        signal_read("10Y-2Y", curve),
        signal_read("Google Trends", trends),
        signal_read("News", news),
    ]
    return pd.DataFrame(rows)


def confidence(score: Optional[int], signals: pd.DataFrame) -> Tuple[str, str]:
    if score is None:
        return "Low", "Most inputs are missing, so stay with normal DCA only."
    usable = signals[signals["Read"] != "Missing"]
    caution = usable["Action"].isin(["Buy smaller", "Do not chase", "Slight caution", "Small caution"]).sum()
    better = usable["Action"].isin(["Buy more", "Better setup"]).sum()
    if score >= 66 and caution >= 2:
        return "Medium-High", "Multiple signals agree the market is hot. That supports smaller new buys, not selling."
    if score <= 45 and better >= 2:
        return "Medium-High", "Multiple signals show fear or better entry conditions. That supports buying above normal if cash plan allows."
    return "Medium", "Signals are mixed enough that discipline matters more than precision."


def top_drivers(signals: pd.DataFrame, n: int = 3) -> pd.DataFrame:
    return signals.sort_values(["Severity"], ascending=False).head(n)


def calculate_buy_amount(planned_amount: float, call: Dict[str, str], risk_mode: str) -> Tuple[float, float]:
    ranges = {
        "BUY MORE": (1.25, 2.00),
        "BUY SLIGHTLY MORE": (1.10, 1.50),
        "BUY NORMALLY": (1.00, 1.00),
        "BUY SMALLER": (0.25, 0.50),
        "DON’T CHASE": (0.00, 0.25),
    }
    lo, hi = ranges.get(call["call"], (1.0, 1.0))
    if risk_mode == "Conservative":
        hi = (lo + hi) / 2
    elif risk_mode == "Aggressive":
        lo = (lo + hi) / 2
    return planned_amount * lo, planned_amount * hi


# ============================================================
# HTML Components
# ============================================================
def tile(label: str, value: str, copy: str = "", badge_class: str = "") -> str:
    badge = f'<div class="badge {badge_class}">{value}</div>' if badge_class else f'<div class="tile-value">{value}</div>'
    return f"""
<div class="tile">
  <div class="kicker">{label}</div>
  {badge}
  <div class="tile-copy">{copy}</div>
</div>
"""


def render_signal_row(row: pd.Series) -> None:
    st.markdown(
        f"""
<div class="signal-row">
  <div class="signal-name">{row['Signal']}</div>
  <div class="signal-read">{row['Read']}</div>
  <div class="signal-meaning">{row['Meaning']}</div>
  <div class="signal-do">{row['Action']}</div>
</div>
""",
        unsafe_allow_html=True,
    )


# ============================================================
# Main App
# ============================================================
t = theme()
inject_css(t)

# Controls
c1, c2, c3 = st.columns([1, 0.13, 0.13])
with c1:
    st.markdown(
        """
<div class="topbar">
  <div class="brand">
    <div class="brand-badge">📈</div>
    <div>Should I Buy Today?</div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )
with c2:
    if st.button("Dark" if not st.session_state.dark_mode else "Light", use_container_width=True):
        st.session_state.dark_mode = not st.session_state.dark_mode
        st.rerun()
with c3:
    if st.button("Refresh", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# Data
spx = fetch_sp500()
vix = fetch_vix()
pcr = fetch_pcr()
yields = fetch_yields()
curve = None
if "US10Y" in yields and "US2Y" in yields:
    curve = round(yields["US10Y"] - yields["US2Y"], 3)
trends = fetch_trends()
news = fetch_news_score()

if spx is None:
    st.error("Could not load S&P 500 data. Check internet connection or yfinance availability.")
    st.stop()

score, breakdown = build_score(vix, spx["rsi"], spx["dist"], pcr, curve, trends, news)
signals = build_signal_df(vix, spx["rsi"], spx["dist"], pcr, curve, trends, news)
call = today_call(score)
heat, heat_class = heat_label(score)
conf, conf_reason = confidence(score, signals)
updated = datetime.now().strftime("%b %-d, %Y %I:%M %p") if os.name != "nt" else datetime.now().strftime("%b %#d, %Y %I:%M %p")
marker_left = 0 if score is None else max(0, min(100, score))
fresh_count = int((signals["Read"] != "Missing").sum())

# Hero
st.markdown(
    f"""
<div class="hero">
  <div class="hero-grid">
    <div>
      <div class="live-pill"><span class="live-dot"></span> Live-ish · {fresh_count}/7 signals loaded</div>
      <div class="hero-title">{call['call']}</div>
      <div class="hero-subtitle">{call['copy']} No panic. This sizes new buys only — it is not a sell signal.</div>
      <div class="timestamp">Updated {updated}</div>
      <div class="guardrail"><b>Core rule:</b> stay invested. The app helps decide how much new cash to deploy, not whether to abandon your long-term plan.</div>
    </div>
    <div class="score-panel">
      <div class="score-top">
        <div>
          <div class="kicker">Market Heat Score</div>
          <div class="score-number">{score if score is not None else '—'}</div>
        </div>
        <div>
          <div class="heat-label">{heat}</div>
          <div class="heat-note">Higher = hotter, not better</div>
        </div>
      </div>
      <div class="meter"></div>
      <div class="marker" style="left: calc({marker_left}% - 13px);"></div>
      <div class="scale"><span>Buy More</span><span>Normal</span><span>Buy Smaller</span><span>Don’t Chase</span></div>
    </div>
  </div>
</div>
""",
    unsafe_allow_html=True,
)

# Simple plan cards
st.markdown(
    f"""
<div class="plan-grid">
  {tile('Today', call['now'], 'Suggested size for the next planned buy.', call['badge'])}
  {tile('Later', call['later'], 'Do not force everything in one shot.')}
  {tile('Avoid', call['avoid'], 'The goal is discipline, not perfect timing.')}
  {tile('Confidence', conf, conf_reason, 'info')}
</div>
""",
    unsafe_allow_html=True,
)

# Optional personal buy plan
st.markdown('<div class="section">Personal Buy Plan</div>', unsafe_allow_html=True)
st.markdown('<div class="section-sub">Optional. Keep it simple: enter planned cash and get a clean dollar range.</div>', unsafe_allow_html=True)
with st.container():
    p1, p2, p3 = st.columns([0.34, 0.33, 0.33])
    with p1:
        planned_amount = st.number_input("Planned buy amount", min_value=0.0, value=10000.0, step=500.0, format="%.0f")
    with p2:
        risk_mode = st.selectbox("Mode", ["Conservative", "Balanced", "Aggressive"], index=1)
    with p3:
        dca_weeks = st.selectbox("DCA rest over", ["2 weeks", "4 weeks", "6 weeks", "8 weeks"], index=1)

buy_lo, buy_hi = calculate_buy_amount(float(planned_amount), call, risk_mode)
remaining_lo = max(0.0, planned_amount - buy_hi)
remaining_hi = max(0.0, planned_amount - buy_lo)
st.markdown(
    f"""
<div class="tile">
  <div class="kicker">Clean Dollar Guidance</div>
  <div class="tile-value">Buy ${buy_lo:,.0f}–${buy_hi:,.0f} now</div>
  <div class="tile-copy">Then DCA roughly ${remaining_lo:,.0f}–${remaining_hi:,.0f} over {dca_weeks}. This is sizing guidance, not a prediction.</div>
</div>
""",
    unsafe_allow_html=True,
)

# Why section
st.markdown(f'<div class="section">Why {call["call"].title()}</div>', unsafe_allow_html=True)
st.markdown('<div class="section-sub">Top drivers only. No noisy dashboard dump.</div>', unsafe_allow_html=True)
driver_html = ""
for _, row in top_drivers(signals).iterrows():
    driver_html += f"""
<div class="tile reason-card">
  <div class="kicker">{row['Signal']} · {row['Read']}</div>
  <div class="reason-title">{row['Action']}</div>
  <div class="reason-copy">{row['Meaning']}</div>
</div>
"""
st.markdown(f'<div class="reason-grid">{driver_html}</div>', unsafe_allow_html=True)

# Investor lens
st.markdown('<div class="section">Investor Lens</div>', unsafe_allow_html=True)
buffett = "Do not chase crowded enthusiasm. Wait for cleaner pitches before deploying huge lump sums."
bogle = "Stay consistent. Broad-index DCA stays on. The app sizes the buy; it does not turn you into a trader."
momentum = "Trend is constructive if the market is above the 200-day average, but hot momentum still deserves discipline."
if spx["dist"] is not None and spx["dist"] < 0:
    momentum = "Market is below trend. That can create better entries, but do not assume the bottom is known."
st.markdown(
    f"""
<div class="lens-grid">
  <div class="tile"><div class="kicker">Buffett Lens</div><div class="lens-title">Do not chase</div><div class="tile-copy">{buffett}</div></div>
  <div class="tile"><div class="kicker">Bogle Lens</div><div class="lens-title">Stay consistent</div><div class="tile-copy">{bogle}</div></div>
  <div class="tile"><div class="kicker">Momentum Lens</div><div class="lens-title">Respect the trend</div><div class="tile-copy">{momentum}</div></div>
</div>
""",
    unsafe_allow_html=True,
)

# Quick signals
st.markdown('<div class="section">Signals</div>', unsafe_allow_html=True)
st.markdown('<div class="section-sub">Readable rows. Keep the top simple; inspect details only if needed.</div>', unsafe_allow_html=True)
for _, row in signals.iterrows():
    render_signal_row(row)

# Advanced view
st.markdown('<div class="section">Advanced View</div>', unsafe_allow_html=True)
with st.expander("Open scoring math and chart"):
    tab1, tab2 = st.tabs(["Scoring Math", "S&P Trend"])
    with tab1:
        raw = breakdown.copy()
        raw["Score"] = raw["Score"].apply(lambda x: "N/A" if pd.isna(x) else round(float(x), 1))
        raw["Weight"] = raw["Weight"].apply(lambda x: f"{int(round(float(x) * 100))}%")
        st.dataframe(raw, use_container_width=True, hide_index=True)
    with tab2:
        hist = spx["history"].copy()
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=hist["Date"], y=hist["Close"], mode="lines", name="S&P 500"))
        fig.add_trace(go.Scatter(x=hist["Date"], y=hist["SMA_200"], mode="lines", name="200D Avg"))
        fig.update_layout(
            height=420,
            margin=dict(l=10, r=10, t=30, b=10),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color=t["text"]),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        )
        fig.update_xaxes(gridcolor="rgba(148,163,184,.18)")
        fig.update_yaxes(gridcolor="rgba(148,163,184,.18)")
        st.plotly_chart(fig, use_container_width=True)

st.markdown(
    """
<div class="footer">
Educational only. Not financial advice. Best use: decide whether to buy more, normally, smaller, or not chase. Built for long-term broad-index investors sizing new cash, not traders predicting tomorrow.
</div>
""",
    unsafe_allow_html=True,
)
