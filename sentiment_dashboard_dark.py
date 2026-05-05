
import os
import math
from datetime import datetime

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st
import yfinance as yf
from ta.momentum import RSIIndicator
from ta.trend import SMAIndicator

try:
    from newsapi import NewsApiClient
except Exception:
    NewsApiClient = None

try:
    from pytrends.request import TrendReq
except Exception:
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
# Theme
# ============================================================
if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = False

LIGHT = {
    "bg": "#f4f7fb",
    "surface": "#ffffff",
    "surface2": "#f8fafc",
    "surface3": "#eef3f8",
    "text": "#0f172a",
    "muted": "#64748b",
    "muted2": "#94a3b8",
    "border": "rgba(15,23,42,.085)",
    "border2": "rgba(15,23,42,.12)",
    "shadow": "0 24px 70px rgba(15,23,42,.08)",
    "shadow2": "0 12px 34px rgba(15,23,42,.07)",
    "green": "#16a34a",
    "green_bg": "rgba(22,163,74,.12)",
    "yellow": "#f59e0b",
    "yellow_bg": "rgba(245,158,11,.13)",
    "red": "#ef4444",
    "red_bg": "rgba(239,68,68,.12)",
    "blue": "#2563eb",
    "blue_bg": "rgba(37,99,235,.11)",
    "purple": "#7c3aed",
    "purple_bg": "rgba(124,58,237,.11)",
}
DARK = {
    "bg": "#070b13",
    "surface": "#101725",
    "surface2": "#141d2e",
    "surface3": "#0c1220",
    "text": "#f8fafc",
    "muted": "#a1aab8",
    "muted2": "#7c8797",
    "border": "rgba(255,255,255,.09)",
    "border2": "rgba(255,255,255,.13)",
    "shadow": "0 28px 80px rgba(0,0,0,.38)",
    "shadow2": "0 16px 40px rgba(0,0,0,.28)",
    "green": "#22c55e",
    "green_bg": "rgba(34,197,94,.14)",
    "yellow": "#fbbf24",
    "yellow_bg": "rgba(251,191,36,.14)",
    "red": "#fb7185",
    "red_bg": "rgba(251,113,133,.14)",
    "blue": "#60a5fa",
    "blue_bg": "rgba(96,165,250,.13)",
    "purple": "#a78bfa",
    "purple_bg": "rgba(167,139,250,.13)",
}


def current_theme():
    return DARK if st.session_state.dark_mode else LIGHT


def inject_css(t):
    st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;650;750;850;900&display=swap');

* {{
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}}

.stApp {{
    background:
      radial-gradient(circle at 8% 0%, rgba(37,99,235,.11), transparent 28%),
      radial-gradient(circle at 96% 4%, rgba(22,163,74,.10), transparent 30%),
      linear-gradient(180deg, {t["bg"]} 0%, {t["surface3"]} 100%);
    color: {t["text"]};
}}

[data-testid="stHeader"] {{ background: rgba(0,0,0,0); }}
[data-testid="stToolbar"] {{ display: none; }}
[data-testid="stDecoration"] {{ display: none; }}

.block-container {{
    padding-top: 1.2rem;
    max-width: 1320px;
}}

button {{
    transition: all .15s ease !important;
}}

div[data-testid="stButton"] button {{
    border-radius: 14px;
    border: 1px solid {t["border"]};
    background: {t["surface"]};
    color: {t["text"]};
    box-shadow: none;
    height: 42px;
    font-weight: 750;
}}

div[data-testid="stButton"] button:hover {{
    border-color: {t["border2"]};
    transform: translateY(-1px);
}}

.hero {{
    background: linear-gradient(135deg, {t["surface"]} 0%, {t["surface2"]} 100%);
    border: 1px solid {t["border"]};
    border-radius: 32px;
    box-shadow: {t["shadow"]};
    padding: 30px 32px;
    margin: 8px 0 20px;
    overflow: hidden;
    position: relative;
}}

.hero::after {{
    content: '';
    position: absolute;
    right: -80px;
    top: -80px;
    width: 240px;
    height: 240px;
    background: radial-gradient(circle, rgba(37,99,235,.10), transparent 65%);
}}

.hero-title {{
    display: flex;
    align-items: center;
    gap: 13px;
    font-size: 43px;
    font-weight: 950;
    letter-spacing: -1.7px;
    color: {t["text"]};
    line-height: 1.02;
}}

.hero-sub {{
    color: {t["muted"]};
    font-size: 15px;
    margin-top: 11px;
    max-width: 820px;
    line-height: 1.5;
}}

.today-summary {{
    margin-top: 18px;
    display: inline-flex;
    align-items: center;
    gap: 10px;
    background: {t["blue_bg"]};
    color: {t["blue"]};
    border: 1px solid rgba(37,99,235,.16);
    border-radius: 999px;
    padding: 10px 14px;
    font-size: 14px;
    font-weight: 800;
}}

.card {{
    background: linear-gradient(180deg, {t["surface"]} 0%, {t["surface2"]} 100%);
    border: 1px solid {t["border"]};
    border-radius: 30px;
    box-shadow: {t["shadow"]};
    padding: 28px;
}}

.action-card {{
    min-height: 360px;
}}

.score-card {{
    min-height: 360px;
}}

.kicker {{
    color: {t["muted"]};
    font-size: 12px;
    font-weight: 900;
    text-transform: uppercase;
    letter-spacing: .78px;
}}

.action-word {{
    font-size: 54px;
    font-weight: 950;
    letter-spacing: -2.3px;
    color: {t["text"]};
    line-height: .96;
    margin-top: 14px;
}}

.main-copy {{
    color: {t["text"]};
    font-size: 18px;
    line-height: 1.52;
    margin-top: 19px;
    max-width: 610px;
}}

.sub-copy {{
    color: {t["muted"]};
    font-size: 14px;
    line-height: 1.48;
    margin-top: 14px;
    max-width: 610px;
}}

.no-sell {{
    margin-top: 16px;
    border-radius: 18px;
    padding: 14px 15px;
    background: {t["blue_bg"]};
    border: 1px solid rgba(37,99,235,.16);
    color: {t["text"]};
    font-size: 14px;
    line-height: 1.45;
}}

.badge {{
    display: inline-flex;
    align-items: center;
    padding: 8px 12px;
    border-radius: 999px;
    font-size: 13px;
    font-weight: 900;
    margin-top: 18px;
}}

.badge-green {{ color: {t["green"]}; background: {t["green_bg"]}; border: 1px solid rgba(34,197,94,.18); }}
.badge-yellow {{ color: {t["yellow"]}; background: {t["yellow_bg"]}; border: 1px solid rgba(245,158,11,.22); }}
.badge-red {{ color: {t["red"]}; background: {t["red_bg"]}; border: 1px solid rgba(239,68,68,.18); }}
.badge-blue {{ color: {t["blue"]}; background: {t["blue_bg"]}; border: 1px solid rgba(37,99,235,.16); }}
.badge-purple {{ color: {t["purple"]}; background: {t["purple_bg"]}; border: 1px solid rgba(124,58,237,.16); }}

.score-top {{
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 16px;
}}

.score-label {{
    color: {t["muted"]};
    font-size: 12px;
    font-weight: 900;
    text-transform: uppercase;
    letter-spacing: .78px;
}}

.score-number {{
    font-size: 92px;
    line-height: .9;
    font-weight: 950;
    letter-spacing: -4px;
    color: {t["text"]};
    margin-top: 8px;
}}

.score-status {{
    color: {t["text"]};
    font-size: 31px;
    font-weight: 950;
    letter-spacing: -1.1px;
    text-align: right;
}}

.score-mini {{
    color: {t["muted"]};
    font-size: 13px;
    font-weight: 750;
    text-align: right;
    margin-top: 6px;
}}

.meter {{
    position: relative;
    height: 18px;
    border-radius: 999px;
    overflow: hidden;
    margin-top: 36px;
    background: linear-gradient(90deg, {t["green"]} 0%, {t["green"]} 33%, {t["yellow"]} 33%, {t["yellow"]} 66%, {t["red"]} 66%, {t["red"]} 100%);
}}

.marker {{
    position: relative;
    width: 20px;
    height: 20px;
    border-radius: 999px;
    background: {t["text"]};
    border: 4px solid {t["surface"]};
    box-shadow: 0 10px 26px rgba(0,0,0,.28);
    margin-top: -19px;
}}

.scale {{
    display: flex;
    justify-content: space-between;
    color: {t["muted"]};
    font-size: 12px;
    font-weight: 850;
    margin-top: 12px;
}}

.score-note {{
    color: {t["muted"]};
    font-size: 15px;
    line-height: 1.48;
    margin-top: 24px;
}}

.buy-plan {{
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    gap: 12px;
    margin-top: 18px;
}}

.buy-tile {{
    border-radius: 20px;
    padding: 15px 14px;
    background: {t["surface"]};
    border: 1px solid {t["border"]};
    box-shadow: {t["shadow2"]};
}}

.buy-label {{
    color: {t["muted"]};
    font-size: 11px;
    font-weight: 900;
    text-transform: uppercase;
    letter-spacing: .65px;
}}

.buy-value {{
    color: {t["text"]};
    font-size: 20px;
    font-weight: 950;
    margin-top: 5px;
    letter-spacing: -.4px;
}}

.section {{
    color: {t["text"]};
    font-size: 24px;
    font-weight: 950;
    letter-spacing: -.5px;
    margin: 24px 0 12px;
}}

.section-sub {{
    color: {t["muted"]};
    font-size: 14px;
    margin-top: -4px;
    margin-bottom: 12px;
}}

.driver-card {{
    background: linear-gradient(180deg, {t["surface"]}, {t["surface2"]});
    border: 1px solid {t["border"]};
    border-radius: 24px;
    box-shadow: {t["shadow2"]};
    padding: 20px;
    min-height: 154px;
}}

.driver-top {{
    color: {t["muted"]};
    font-size: 12px;
    font-weight: 900;
    text-transform: uppercase;
    letter-spacing: .65px;
}}

.driver-title {{
    color: {t["text"]};
    font-size: 23px;
    font-weight: 950;
    margin-top: 8px;
    letter-spacing: -.55px;
}}

.driver-copy {{
    color: {t["muted"]};
    font-size: 14px;
    line-height: 1.45;
    margin-top: 9px;
}}

.metric-card {{
    background: linear-gradient(180deg, {t["surface"]}, {t["surface2"]});
    border: 1px solid {t["border"]};
    border-radius: 24px;
    box-shadow: {t["shadow2"]};
    padding: 18px;
    min-height: 142px;
}}

.metric-name {{
    color: {t["muted"]};
    font-size: 12px;
    font-weight: 900;
    text-transform: uppercase;
    letter-spacing: .65px;
}}

.metric-value {{
    color: {t["text"]};
    font-size: 31px;
    font-weight: 950;
    margin-top: 6px;
    letter-spacing: -.7px;
}}

.metric-help {{
    color: {t["muted"]};
    font-size: 13px;
    line-height: 1.38;
    margin-top: 8px;
}}

.lens-card {{
    background: linear-gradient(180deg, {t["surface"]}, {t["surface2"]});
    border: 1px solid {t["border"]};
    border-radius: 24px;
    box-shadow: {t["shadow2"]};
    padding: 21px;
    min-height: 164px;
}}

.lens-head {{
    color: {t["text"]};
    font-size: 21px;
    font-weight: 950;
    margin-top: 7px;
    letter-spacing: -.45px;
}}

.lens-copy {{
    color: {t["muted"]};
    font-size: 14px;
    line-height: 1.45;
    margin-top: 9px;
}}

.signal-row {{
    display: grid;
    grid-template-columns: 150px 110px 1fr 165px;
    gap: 14px;
    align-items: center;
    background: {t["surface"]};
    border: 1px solid {t["border"]};
    border-radius: 18px;
    padding: 14px 16px;
    margin-bottom: 10px;
    box-shadow: 0 8px 24px rgba(15,23,42,.045);
}}

.signal-name {{
    font-weight: 900;
    color: {t["text"]};
}}

.signal-read {{
    font-weight: 900;
    color: {t["text"]};
}}

.signal-meaning {{
    color: {t["muted"]};
    font-size: 14px;
}}

.signal-do {{
    font-weight: 900;
    color: {t["text"]};
    text-align: right;
}}

.clean-note {{
    color: {t["muted"]};
    font-size: 14px;
    line-height: 1.45;
    margin: 4px 0 14px;
}}

.stTabs [data-baseweb="tab-list"] {{ gap: 8px; }}
.stTabs [data-baseweb="tab"] {{
    border-radius: 999px;
    background: {t["surface"]};
    border: 1px solid {t["border"]};
    color: {t["text"]};
    font-weight: 750;
}}
.stTabs [aria-selected="true"] {{
    border-color: {t["red"]} !important;
}}

.footer {{
    color: {t["muted"]};
    font-size: 12px;
    margin-top: 26px;
    padding-top: 18px;
    border-top: 1px solid {t["border"]};
}}



.hero-updated {{
    color: {t["muted"]};
    font-size: 13px;
    margin-top: 16px;
    font-weight: 700;
}}

.compact-hero {{
    padding: 28px 31px;
}}

.decision-stack {{
    margin-top: 22px;
    display: grid;
    gap: 10px;
}}

.decision-row {{
    display: flex;
    justify-content: space-between;
    gap: 16px;
    align-items: center;
    border: 1px solid {t["border"]};
    background: {t["surface"]};
    border-radius: 18px;
    padding: 13px 14px;
}}

.decision-label {{
    color: {t["muted"]};
    font-size: 12px;
    font-weight: 900;
    text-transform: uppercase;
    letter-spacing: .55px;
}}

.decision-value {{
    color: {t["text"]};
    font-size: 14px;
    font-weight: 900;
    text-align: right;
}}

.heat-explainer {{
    margin-top: 22px;
    border-radius: 18px;
    padding: 14px 15px;
    background: {t["surface"]};
    border: 1px solid {t["border"]};
    color: {t["muted"]};
    font-size: 14px;
    line-height: 1.45;
}}

.two-tile {{
    grid-template-columns: 1fr 1fr;
}}

.single-command-card {{
    min-height: 360px;
}}

.command-grid {{
    display: grid;
    grid-template-columns: 1.15fr .85fr;
    gap: 18px;
    align-items: stretch;
}}

.command-left {{
    background: linear-gradient(180deg, {t["surface"]}, {t["surface2"]});
    border: 1px solid {t["border"]};
    border-radius: 30px;
    box-shadow: {t["shadow"]};
    padding: 30px;
}}

.command-right {{
    background: linear-gradient(180deg, {t["surface"]}, {t["surface2"]});
    border: 1px solid {t["border"]};
    border-radius: 30px;
    box-shadow: {t["shadow"]};
    padding: 30px;
}}

.command-top {{
    display: flex;
    justify-content: space-between;
    gap: 18px;
    align-items: flex-start;
}}

.command-score {{
    text-align: right;
}}

.command-score-num {{
    font-size: 58px;
    line-height: .9;
    font-weight: 950;
    letter-spacing: -2px;
    color: {t["text"]};
}}

.command-score-label {{
    margin-top: 6px;
    color: {t["muted"]};
    font-size: 12px;
    font-weight: 900;
    text-transform: uppercase;
    letter-spacing: .6px;
}}

.command-note {{
    margin-top: 18px;
    color: {t["muted"]};
    font-size: 15px;
    line-height: 1.5;
}}

.mini-meter-wrap {{
    margin-top: 22px;
}}

@media (max-width: 900px) {{
    .command-grid {{ grid-template-columns: 1fr; }}
    .hero-title {{ font-size: 34px; }}
    .action-word {{ font-size: 43px; }}
    .score-number {{ font-size: 72px; }}
    .buy-plan {{ grid-template-columns: 1fr; }}
    .two-tile {{ grid-template-columns: 1fr; }}
    .decision-row {{ flex-direction: column; align-items: flex-start; }}
    .decision-value {{ text-align: left; }}
    .signal-row {{ grid-template-columns: 1fr; gap: 6px; }}
    .signal-do {{ text-align: left; }}
}}
</style>
""", unsafe_allow_html=True)


# ============================================================
# Helpers
# ============================================================
def safe_float(v):
    try:
        if v is None:
            return None
        v = float(v)
        if math.isnan(v):
            return None
        return v
    except Exception:
        return None


def safe_round(v, digits=2):
    v = safe_float(v)
    return None if v is None else round(v, digits)


def clamp(v, lo=0, hi=100):
    v = safe_float(v)
    return None if v is None else max(lo, min(hi, v))


def fmt(v, suffix="", digits=2):
    v = safe_float(v)
    if v is None:
        return "N/A"
    return f"{v:,.0f}{suffix}" if digits == 0 else f"{v:,.{digits}f}{suffix}"


def score_from_range(v, points):
    v = safe_float(v)
    if v is None:
        return None
    points = sorted(points, key=lambda x: x[0])
    if v <= points[0][0]:
        return float(points[0][1])
    if v >= points[-1][0]:
        return float(points[-1][1])
    for (x1, y1), (x2, y2) in zip(points, points[1:]):
        if x1 <= v <= x2:
            pct = (v - x1) / (x2 - x1)
            return y1 + pct * (y2 - y1)
    return None


def heat_label(score):
    if score is None:
        return "Unknown", "badge-blue"
    if score <= 20:
        return "Deep Fear", "badge-green"
    if score <= 33:
        return "Fear", "badge-green"
    if score <= 66:
        return "Normal", "badge-yellow"
    if score <= 80:
        return "Hot", "badge-red"
    return "Very Hot", "badge-red"


def action(score):
    if score is None:
        return (
            "WAIT",
            "Data is incomplete. Use your normal buying plan until the signal refreshes cleanly.",
            "badge-blue",
            "Normal DCA only",
            "Medium",
        )
    if score <= 20:
        return (
            "BUY MORE",
            "Fear is elevated. This is usually a better setup to deploy a larger taxable tranche.",
            "badge-green",
            "150%–200% of normal tranche",
            "Medium-High",
        )
    if score <= 33:
        return (
            "BUY A LITTLE MORE",
            "Market sentiment is fearful. Slightly increase your scheduled buy without trying to call the bottom.",
            "badge-green",
            "125%–150% of normal tranche",
            "Medium",
        )
    if score <= 66:
        return (
            "BUY NORMALLY",
            "No major edge. Keep the plan simple, stay consistent, and avoid overthinking the daily noise.",
            "badge-yellow",
            "100% of normal plan",
            "Medium",
        )
    if score <= 80:
        return (
            "BUY SMALLER",
            "Market is healthy but hot. Keep buying, but avoid a big emotional lump-sum taxable buy today.",
            "badge-red",
            "25%–50% of planned lump sum",
            "Medium-High",
        )
    return (
        "DON’T CHASE",
        "Sentiment is stretched. Keep your scheduled DCA, but avoid forcing a large new buy into a hot market.",
        "badge-red",
        "DCA only / wait for pullback",
        "Medium-High",
    )


def next_cash_plan(score):
    if score is None:
        return "Normal Plan", "100%", "Wait for clean data"
    if score <= 20:
        return "Aggressive Tranche", "50%–75%", "Deploy more now"
    if score <= 33:
        return "Larger Tranche", "30%–50%", "Buy above normal"
    if score <= 66:
        return "Normal DCA", "100%", "Stay on plan"
    if score <= 80:
        return "Smaller Tranche", "25%–50%", "DCA the rest"
    return "Do Not Chase", "0%–25%", "Wait for red days"


def mini_class(name, value):
    if name == "VIX":
        if value is None:
            return "N/A", "badge-blue"
        if value < 14:
            return "Too Calm", "badge-red"
        if value < 20:
            return "Calm", "badge-yellow"
        if value < 28:
            return "Elevated", "badge-yellow"
        return "Fearful", "badge-green"
    if name == "RSI":
        if value is None:
            return "N/A", "badge-blue"
        if value < 35:
            return "Oversold", "badge-green"
        if value <= 65:
            return "Healthy", "badge-yellow"
        return "Hot", "badge-red"
    if name == "Trend":
        if value is None:
            return "N/A", "badge-blue"
        if value < -3:
            return "Below Trend", "badge-green"
        if value <= 8:
            return "Near Trend", "badge-yellow"
        return "Extended", "badge-red"
    if name == "PutCall":
        if value is None:
            return "N/A", "badge-blue"
        if value < .65:
            return "Greedy", "badge-red"
        if value <= 1.1:
            return "Balanced", "badge-yellow"
        return "Fearful", "badge-green"
    return "N/A", "badge-blue"


def metric_card(title, value, badge, badge_class, copy):
    st.markdown(f"""
<div class="metric-card">
  <div class="metric-name">{title}</div>
  <div class="metric-value">{value}</div>
  <div class="badge {badge_class}">{badge}</div>
  <div class="metric-help">{copy}</div>
</div>
""", unsafe_allow_html=True)


def signal_row(signal, current_read, meaning, what_to_do):
    st.markdown(f"""
<div class="signal-row">
  <div class="signal-name">{signal}</div>
  <div class="signal-read">{current_read}</div>
  <div class="signal-meaning">{meaning}</div>
  <div class="signal-do">{what_to_do}</div>
</div>
""", unsafe_allow_html=True)


# ============================================================
# Data Fetch
# ============================================================
@st.cache_data(ttl=900, show_spinner=False)
def fetch_sp500():
    df = yf.Ticker("^GSPC").history(period="1y", interval="1d", auto_adjust=False)
    if df is None or df.empty:
        return None
    df = df.dropna(subset=["Close"]).copy()
    if len(df) < 30:
        return None
    df["RSI"] = RSIIndicator(df["Close"], window=14).rsi()
    df["SMA_200"] = SMAIndicator(df["Close"], window=200).sma_indicator()
    last = df.iloc[-1]
    close = safe_round(last["Close"], 2)
    rsi = safe_round(last["RSI"], 2)
    sma = safe_round(last["SMA_200"], 2)
    dist = safe_round(((close - sma) / sma) * 100, 2) if close and sma else None
    df = df.reset_index()
    if "Date" not in df.columns:
        df = df.rename(columns={df.columns[0]: "Date"})
    return {"close": close, "rsi": rsi, "sma": sma, "dist": dist, "history": df}


@st.cache_data(ttl=900, show_spinner=False)
def fetch_vix():
    df = yf.Ticker("^VIX").history(period="1mo", interval="1d", auto_adjust=False)
    if df is None or df.empty:
        return None
    return safe_round(df["Close"].dropna().iloc[-1], 2)


@st.cache_data(ttl=900, show_spinner=False)
def fetch_pcr():
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
        return safe_round(r.json()["chart_data"][0][0]["last_value"], 2)
    except Exception:
        return None


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_yields():
    url = (
        "https://quote.cnbc.com/quote-html-webservice/restQuote/"
        "symbolType/symbol?"
        "symbols=US1M%7CUS2M%7CUS3M%7CUS4M%7CUS6M%7CUS1Y%7CUS2Y%7CUS3Y%7CUS5Y%7CUS7Y%7CUS10Y%7CUS20Y%7CUS30Y"
        "&requestMethod=itv&noform=1&partnerId=2&fund=1&exthrs=1&output=json&events=1"
    )
    try:
        r = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        quotes = r.json()["FormattedQuoteResult"]["FormattedQuote"]
        return {q["symbol"]: safe_round(str(q["last"]).strip("%"), 3) for q in quotes if q.get("symbol") and q.get("last")}
    except Exception:
        return {}


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_trends(term="stock market crash"):
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
def fetch_news():
    key = None
    try:
        key = st.secrets.get("NEWSAPI_KEY", None)
    except Exception:
        pass
    key = key or os.getenv("NEWSAPI_KEY")
    if not key or NewsApiClient is None:
        return None, "Optional"

    bears = [
        "crash", "collapse", "meltdown", "plunge", "sell-off", "recession", "slowdown",
        "panic", "fear", "turmoil", "bearish", "volatility", "losses", "decline",
        "drop", "downgrade",
    ]
    bulls = [
        "rally", "surge", "soar", "rebound", "recovery", "growth", "momentum",
        "bullish", "optimism", "confidence", "strength", "record high", "gains",
        "outperform", "upgrade",
    ]
    try:
        client = NewsApiClient(api_key=key)
        articles = client.get_everything(q="S&P 500 OR stock market", language="en", page_size=40).get("articles", [])
        titles = [(a.get("title") or "").lower() for a in articles]
        b = sum(any(w in t for w in bears) for t in titles)
        u = sum(any(w in t for w in bulls) for t in titles)
        s = int(clamp(50 + 3 * (u - b), 0, 100))
        return s, "Bullish" if s > 60 else "Bearish" if s < 40 else "Mixed"
    except Exception:
        return None, "Unavailable"


# ============================================================
# Signal Model
# ============================================================
def human_signal_row(name, reading):
    if name == "VIX":
        if reading is None:
            return ["VIX", "Missing", "Volatility data unavailable", "Ignore for now"]
        if reading < 14:
            return ["VIX", fmt(reading), "Market is very calm. Calm markets can become complacent.", "Slight caution"]
        if reading < 20:
            return ["VIX", fmt(reading), "Volatility is normal. No major fear discount.", "Neutral"]
        if reading < 28:
            return ["VIX", fmt(reading), "Some fear is showing up.", "Slightly better buy setup"]
        return ["VIX", fmt(reading), "Fear is elevated. Better prices may be appearing.", "Better buy setup"]

    if name == "RSI":
        if reading is None:
            return ["RSI", "Missing", "Momentum unavailable", "Ignore for now"]
        if reading < 35:
            return ["RSI", fmt(reading), "Market looks oversold.", "Better buy setup"]
        if reading <= 65:
            return ["RSI", fmt(reading), "Momentum looks normal.", "Neutral"]
        if reading <= 72:
            return ["RSI", fmt(reading), "Momentum is hot.", "Buy smaller"]
        return ["RSI", fmt(reading), "Momentum is very hot.", "Do not chase"]

    if name == "S&P vs 200D":
        if reading is None:
            return ["S&P vs 200D", "Missing", "Trend distance unavailable", "Ignore for now"]
        if reading < -8:
            return ["S&P vs 200D", fmt(reading, "%"), "Market is well below its long-term trend.", "Better buy setup"]
        if reading < -2:
            return ["S&P vs 200D", fmt(reading, "%"), "Market is slightly below trend.", "Slightly better buy setup"]
        if reading <= 8:
            return ["S&P vs 200D", fmt(reading, "%"), "Market is near its long-term trend.", "Neutral"]
        return ["S&P vs 200D", fmt(reading, "%"), "Market is stretched above trend.", "Buy smaller"]

    if name == "Put/Call":
        if reading is None:
            return ["Put/Call", "Missing", "Options sentiment unavailable", "Ignore for now"]
        if reading < 0.65:
            return ["Put/Call", fmt(reading), "Too much call buying. Traders are leaning greedy.", "Buy smaller"]
        if reading <= 1.10:
            return ["Put/Call", fmt(reading), "Options positioning is balanced.", "Neutral"]
        return ["Put/Call", fmt(reading), "More hedging and fear in options.", "Better buy setup"]

    if name == "10Y-2Y":
        if reading is None:
            return ["10Y-2Y", "Missing", "Yield curve unavailable", "Ignore for now"]
        if reading < 0:
            return ["10Y-2Y", fmt(reading, "%", 3), "Yield curve is inverted. Macro deserves caution.", "Small caution"]
        return ["10Y-2Y", fmt(reading, "%", 3), "Yield curve is positive. Macro backdrop is okay.", "Small impact"]

    if name == "Google Trends":
        if reading is None:
            return ["Google Trends", "Missing", "Search sentiment unavailable", "Ignore for now"]
        if reading >= 60:
            return ["Google Trends", fmt(reading, "", 0), "Crash searches are rising. Public fear may be increasing.", "Can improve buy setup"]
        return ["Google Trends", fmt(reading, "", 0), "No major fear-search spike.", "Small impact"]

    if name == "News":
        if reading is None:
            return ["News", "Missing", "Headline sentiment unavailable", "Ignore for now"]
        if reading > 60:
            return ["News", fmt(reading, "", 0), "Headlines are optimistic.", "Slight caution"]
        if reading < 40:
            return ["News", fmt(reading, "", 0), "Headlines are negative.", "Can improve buy setup"]
        return ["News", fmt(reading, "", 0), "Headline tone is mixed.", "Small impact"]

    return [name, str(reading), "Unknown", "Neutral"]


def driver_severity(action_text):
    if action_text in ["Do not chase", "Buy smaller"]:
        return 5
    if action_text in ["Better buy setup", "Slightly better buy setup"]:
        return 4
    if action_text in ["Slight caution", "Small caution", "Can improve buy setup"]:
        return 3
    if action_text in ["Neutral", "Small impact"]:
        return 2
    return 1


def build_driver_rows(vix, rsi, dist, pcr, curve, trends, news):
    rows = [
        human_signal_row("VIX", vix),
        human_signal_row("RSI", rsi),
        human_signal_row("S&P vs 200D", dist),
        human_signal_row("Put/Call", pcr),
        human_signal_row("10Y-2Y", curve),
        human_signal_row("Google Trends", trends),
        human_signal_row("News", news),
    ]
    df = pd.DataFrame(rows, columns=["Signal", "Current Read", "What it says", "What to do"])
    df["_severity"] = df["What to do"].apply(driver_severity)
    return df


def build_score(vix, rsi, dist, pcr, curve, trends, news):
    # Important: this is a Market Heat Score.
    # Higher = hotter/more greedy. Lower = more fearful/better entry.
    rows = [
        {
            "Indicator": "VIX",
            "Reading": fmt(vix),
            "Score": score_from_range(vix, [(12, 85), (18, 62), (25, 38), (35, 15), (50, 5)]),
            "Weight": .24,
            "Meaning": "Volatility/fear. High VIX usually improves entry points.",
        },
        {
            "Indicator": "RSI",
            "Reading": fmt(rsi),
            "Score": score_from_range(rsi, [(25, 10), (35, 25), (50, 50), (65, 72), (75, 90), (85, 100)]),
            "Weight": .21,
            "Meaning": "Momentum temperature. High RSI means hot.",
        },
        {
            "Indicator": "S&P vs 200D",
            "Reading": fmt(dist, "%"),
            "Score": score_from_range(dist, [(-20, 8), (-10, 20), (0, 48), (8, 68), (15, 84), (25, 96)]),
            "Weight": .21,
            "Meaning": "Distance from long-term trend.",
        },
        {
            "Indicator": "Put/Call",
            "Reading": fmt(pcr),
            "Score": score_from_range(pcr, [(0.55, 90), (.75, 70), (.95, 52), (1.15, 35), (1.4, 15)]),
            "Weight": .15,
            "Meaning": "Low can mean call chasing. High can mean fear.",
        },
        {
            "Indicator": "10Y-2Y",
            "Reading": fmt(curve, "%", 3),
            "Score": score_from_range(curve, [(-1.2, 70), (-.5, 58), (0, 50), (.8, 45), (1.5, 48)]),
            "Weight": .07,
            "Meaning": "Macro context, not the whole decision.",
        },
        {
            "Indicator": "Google Trends",
            "Reading": fmt(trends, "", 0),
            "Score": score_from_range(trends, [(0, 72), (20, 62), (50, 45), (80, 25), (100, 10)]),
            "Weight": .06,
            "Meaning": "Crash-search interest. Spikes imply public fear.",
        },
        {
            "Indicator": "News",
            "Reading": fmt(news, "", 0),
            "Score": news,
            "Weight": .06,
            "Meaning": "Optional headline tone.",
        },
    ]
    df = pd.DataFrame(rows)
    good = df.dropna(subset=["Score"]).copy()
    if good.empty:
        return None, df
    good["AdjWeight"] = good["Weight"] / good["Weight"].sum()
    score = int(round((good["Score"] * good["AdjWeight"]).sum()))
    return int(clamp(score, 0, 100)), df


def confidence_text(score, signal_df):
    usable = signal_df[signal_df["Current Read"] != "Missing"]
    if usable.empty:
        return "Low", "Most inputs are missing, so use normal DCA only."

    caution_count = usable["What to do"].isin(["Buy smaller", "Do not chase", "Slight caution", "Small caution"]).sum()
    buy_count = usable["What to do"].isin(["Better buy setup", "Slightly better buy setup", "Can improve buy setup"]).sum()

    if score is None:
        return "Low", "Composite score is unavailable."
    if caution_count >= 2 and score >= 67:
        return "Medium-High", "Multiple signals agree the market is hot. This supports smaller lump-sum buys, not selling."
    if buy_count >= 2 and score <= 33:
        return "Medium-High", "Multiple signals agree fear is elevated. This supports larger tranches."
    return "Medium", "Signals are mixed enough that the safest move is to stay disciplined, not make an emotional trade."


def lens_copy(signal_df, dist):
    rsi_row = signal_df[signal_df["Signal"] == "RSI"]
    pcr_row = signal_df[signal_df["Signal"] == "Put/Call"]

    buffett = "Patience beats chasing. Current conditions do not look like a fat pitch for a huge lump sum."
    bogle = "Keep scheduled broad-index buying active. The app sizes the buy; it should not turn you into a trader."
    momentum = "Trend remains constructive if the S&P is near or above its 200-day average, but hot momentum deserves discipline."

    if not rsi_row.empty and "hot" in rsi_row.iloc[0]["What it says"].lower():
        buffett = "RSI is hot, so this is not a fat pitch. Be patient with large taxable buys."
    if not pcr_row.empty and "greedy" in pcr_row.iloc[0]["What it says"].lower():
        buffett = "Options sentiment looks greedy. Good investors do not chase crowded enthusiasm."

    if dist is not None and dist > 0:
        momentum = "S&P is above the 200-day average, so the trend is constructive. Caution does not mean bearish."
    elif dist is not None and dist < 0:
        momentum = "S&P is below trend, which can improve future entry points but also adds near-term risk."

    return buffett, bogle, momentum


# ============================================================
# Controls
# ============================================================
t = current_theme()
inject_css(t)

c1, c2, c3 = st.columns([.72, .14, .14])
with c2:
    st.toggle("Dark mode", key="dark_mode")
with c3:
    if st.button("Refresh", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

t = current_theme()
inject_css(t)

with st.spinner("Building today’s market read..."):
    spx = fetch_sp500()
    vix = fetch_vix()
    pcr = fetch_pcr()
    yields = fetch_yields()
    trends = fetch_trends()
    news_score, news_label = fetch_news()

if spx is None:
    st.error("Could not load S&P 500 data from Yahoo Finance. Refresh in a few minutes.")
    st.stop()

us2y = yields.get("US2Y") if yields else None
us10y = yields.get("US10Y") if yields else None
curve = safe_round(us10y - us2y, 3) if us2y is not None and us10y is not None else None

score, breakdown = build_score(vix, spx["rsi"], spx["dist"], pcr, curve, trends, news_score)
heat, heat_class = heat_label(score)
act, act_copy, act_class, tranche, base_conf = action(score)
plan_name, now_percent, plan_action = next_cash_plan(score)
signal_df = build_driver_rows(vix, spx["rsi"], spx["dist"], pcr, curve, trends, news_score)
confidence, confidence_reason = confidence_text(score, signal_df)
marker_left = 0 if score is None else max(0, min(100, score))

today_summary = {
    "BUY MORE": "Fear is elevated. Bigger tranches are reasonable.",
    "BUY A LITTLE MORE": "Fear is present. Slightly increase the next buy.",
    "BUY NORMALLY": "Balanced setup. Stay on the normal plan.",
    "BUY SMALLER": "Hot market. Use a smaller tranche today.",
    "DON’T CHASE": "Stretched market. DCA only.",
    "WAIT": "Data incomplete. Use normal DCA until refresh.",
}.get(act, "Use the signal to size the next buy.")

buffett_lens, bogle_lens, momentum_lens = lens_copy(signal_df, spx["dist"])


# ============================================================
# UI
# ============================================================
st.markdown(f"""
<div class="hero compact-hero">
  <div class="hero-title">📈 Should I Buy Today?</div>
  <div class="hero-sub">One simple answer for long-term index investors: buy more, buy normally, buy smaller, or wait.</div>
  <div class="today-summary">{today_summary}</div>
  <div class="hero-updated">Updated {datetime.now().strftime("%b %d, %Y %I:%M %p")}</div>
</div>
""", unsafe_allow_html=True)

st.markdown(f"""
<div class="command-grid">
  <div class="command-left">
    <div class="command-top">
      <div>
        <div class="kicker">Today’s Move</div>
        <div class="action-word">{act}</div>
      </div>
      <div class="command-score">
        <div class="command-score-num">{score if score is not None else "N/A"}</div>
        <div class="command-score-label">{heat} heat</div>
      </div>
    </div>

    <div class="main-copy">{act_copy}</div>

    <div class="decision-stack">
      <div class="decision-row">
        <span class="decision-label">Buy today</span>
        <span class="decision-value">{now_percent} of planned lump sum</span>
      </div>
      <div class="decision-row">
        <span class="decision-label">Rest of cash</span>
        <span class="decision-value">{plan_action}</span>
      </div>
      <div class="decision-row">
        <span class="decision-label">Avoid</span>
        <span class="decision-value">Large emotional buy</span>
      </div>
    </div>
  </div>

  <div class="command-right">
    <div class="score-label">Market Heat Meter</div>
    <div class="score-mini" style="text-align:left;margin-top:6px;">0 = fearful / better entry · 100 = hot / buy less</div>

    <div class="mini-meter-wrap">
      <div class="meter"></div>
      <div class="marker" style="left: calc({marker_left}% - 10px);"></div>
      <div class="scale"><span>Buy More</span><span>Normal</span><span>Buy Less</span></div>
    </div>

    <div class="command-note">
      <b>Beginner read:</b> this does not say “sell.” It says the market is hot enough that a smaller taxable buy is smarter than chasing.
    </div>
  </div>
</div>
""", unsafe_allow_html=True)


st.markdown(f'<div class="section">Why the app says {act}</div>', unsafe_allow_html=True)
st.markdown('<div class="section-sub">The top drivers behind today’s recommendation, written for normal humans.</div>', unsafe_allow_html=True)

top_drivers = signal_df.sort_values("_severity", ascending=False).head(3)
d1, d2, d3 = st.columns(3)
for col, (_, row) in zip([d1, d2, d3], top_drivers.iterrows()):
    with col:
        st.markdown(f"""
<div class="driver-card">
  <div class="driver-top">{row["Signal"]} · {row["Current Read"]}</div>
  <div class="driver-title">{row["What to do"]}</div>
  <div class="driver-copy">{row["What it says"]}</div>
</div>
""", unsafe_allow_html=True)

st.markdown('<div class="section">Signal Confidence</div>', unsafe_allow_html=True)
c1, c2 = st.columns([.32, .68])
with c1:
    st.markdown(f"""
<div class="driver-card">
  <div class="driver-top">Confidence</div>
  <div class="driver-title">{confidence}</div>
  <div class="driver-copy">This reflects whether multiple inputs agree.</div>
</div>
""", unsafe_allow_html=True)
with c2:
    st.markdown(f"""
<div class="driver-card">
  <div class="driver-top">Why confidence is not fake certainty</div>
  <div class="driver-title">Use it to size the buy, not predict the market</div>
  <div class="driver-copy">{confidence_reason}</div>
</div>
""", unsafe_allow_html=True)


st.markdown('<div class="section">Quick Read</div>', unsafe_allow_html=True)
a, b, c, d = st.columns(4)
vix_b, vix_c = mini_class("VIX", vix)
rsi_b, rsi_c = mini_class("RSI", spx["rsi"])
trend_b, trend_c = mini_class("Trend", spx["dist"])
pcr_b, pcr_c = mini_class("PutCall", pcr)

with a:
    metric_card("VIX", fmt(vix), vix_b, vix_c, "Fear gauge. Higher usually means better entry opportunities.")
with b:
    metric_card("RSI", fmt(spx["rsi"]), rsi_b, rsi_c, "Momentum temperature. High = hot; low = washed out.")
with c:
    metric_card("S&P vs 200D", fmt(spx["dist"], "%"), trend_b, trend_c, "How far the market sits from its long-term trend.")
with d:
    metric_card("Put/Call", fmt(pcr), pcr_b, pcr_c, "Options sentiment. Low can signal too much call chasing.")


st.markdown('<div class="section">Investor Lens</div>', unsafe_allow_html=True)
x, y, z = st.columns(3)
with x:
    st.markdown(f"""
<div class="lens-card">
  <div class="kicker">Buffett Lens</div>
  <div class="lens-head">Do not chase</div>
  <div class="lens-copy">{buffett_lens}</div>
</div>
""", unsafe_allow_html=True)
with y:
    st.markdown(f"""
<div class="lens-card">
  <div class="kicker">Bogle Lens</div>
  <div class="lens-head">Stay consistent</div>
  <div class="lens-copy">{bogle_lens}</div>
</div>
""", unsafe_allow_html=True)
with z:
    st.markdown(f"""
<div class="lens-card">
  <div class="kicker">Momentum Lens</div>
  <div class="lens-head">Respect the trend</div>
  <div class="lens-copy">{momentum_lens}</div>
</div>
""", unsafe_allow_html=True)


st.markdown('<div class="section">All Signals</div>', unsafe_allow_html=True)
st.markdown('<div class="section-sub">Readable signal rows. No black-box table required.</div>', unsafe_allow_html=True)
for _, row in signal_df.drop(columns=["_severity"]).iterrows():
    signal_row(row["Signal"], row["Current Read"], row["What it says"], row["What to do"])


st.markdown('<div class="section">Advanced View</div>', unsafe_allow_html=True)
tab1, tab2, tab3 = st.tabs(["Scoring Math", "S&P Trend", "Treasury Curve"])

with tab1:
    st.markdown('<div class="clean-note">Advanced users can inspect the model inputs and weights. Higher score means hotter market, not better market.</div>', unsafe_allow_html=True)
    raw_df = breakdown.copy()
    raw_df["Score"] = raw_df["Score"].apply(lambda x: "N/A" if pd.isna(x) else round(float(x), 1))
    raw_df["Weight"] = raw_df["Weight"].apply(lambda x: f"{int(round(float(x) * 100))}%")
    st.dataframe(raw_df, use_container_width=True, hide_index=True)

with tab2:
    hist = spx["history"]
    fig = go.Figure()
    if "Date" in hist and "Close" in hist:
        fig.add_trace(go.Scatter(x=hist["Date"], y=hist["Close"], mode="lines", name="S&P 500"))
    if "Date" in hist and "SMA_200" in hist:
        fig.add_trace(go.Scatter(x=hist["Date"], y=hist["SMA_200"], mode="lines", name="200D SMA"))
    fig.update_layout(
        height=410,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": t["text"]},
        margin=dict(l=10, r=10, t=20, b=10),
        legend=dict(orientation="h"),
        hovermode="x unified",
    )
    st.plotly_chart(fig, use_container_width=True)

with tab3:
    if yields:
        order = ["US1M", "US2M", "US3M", "US4M", "US6M", "US1Y", "US2Y", "US3Y", "US5Y", "US7Y", "US10Y", "US20Y", "US30Y"]
        ydf = pd.DataFrame([{"Maturity": m, "Yield (%)": yields.get(m)} for m in order if yields.get(m) is not None])
        st.dataframe(ydf, use_container_width=True, hide_index=True)
        if not ydf.empty:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=ydf["Maturity"], y=ydf["Yield (%)"], mode="lines+markers", name="Yield"))
            fig.update_layout(
                height=360,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font={"color": t["text"]},
                margin=dict(l=10, r=10, t=20, b=10),
                hovermode="x unified",
            )
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Treasury yields unavailable right now.")


st.markdown("""
<div class="footer">
Educational only. Not financial advice. Best use: decide whether to buy more, normally, smaller, or not chase.
This app is designed for long-term index investors sizing taxable buys, not traders trying to predict tomorrow.
</div>
""", unsafe_allow_html=True)
