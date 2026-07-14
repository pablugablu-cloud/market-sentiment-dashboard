"""
Should I Buy Today? — a market weather report for long-term index investors.

Product principles
-------------------
1. One plain-English answer first. Everything else is optional depth.
2. Weather language everywhere: Cold / Cool / Mild / Warm / Hot.
   Beginners understand weather; nobody needs to know what RSI is to act.
3. Progressive disclosure: Answer -> Why -> Explore -> Audit.
4. The score model, data fallbacks and disclaimers are unchanged from the
   audited version; this redesign is presentation and pedagogy only.
"""

import html as html_lib
import math
import re
from datetime import datetime
from io import StringIO
from zoneinfo import ZoneInfo

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st
import yfinance as yf
from ta.momentum import RSIIndicator
from ta.trend import SMAIndicator

# ============================================================
# App configuration
# ============================================================
st.set_page_config(
    page_title="Should I Buy Today?",
    page_icon="🌤️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

PACIFIC = ZoneInfo("America/Los_Angeles")
NOW_PT = datetime.now(PACIFIC)

if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = False


# ============================================================
# Theme — "field almanac": warm paper by day, ink navy by night
# ============================================================
LIGHT = {
    "bg": "#F6F4EF",
    "surface": "#FFFFFF",
    "surface2": "#FBFAF7",
    "text": "#1B2432",
    "muted": "#5F6B7A",
    "muted2": "#8B95A3",
    "border": "rgba(27,36,50,.10)",
    "border2": "rgba(27,36,50,.18)",
    "shadow": "0 14px 40px rgba(27,36,50,.07)",
    "green": "#1E7A55",
    "green_bg": "rgba(30,122,85,.09)",
    "amber": "#A96A0B",
    "amber_bg": "rgba(169,106,11,.09)",
    "coral": "#C24657",
    "coral_bg": "rgba(194,70,87,.08)",
    "blue": "#2F5FA8",
    "blue_bg": "rgba(47,95,168,.08)",
    "meter_green": "#7FBFA2",
    "meter_amber": "#E4C27E",
    "meter_coral": "#DE9AA3",
    "pulse": "rgba(27,36,50,.30)",
}

DARK = {
    "bg": "#0E1522",
    "surface": "#16202F",
    "surface2": "#121A28",
    "text": "#F1EFE9",
    "muted": "#9AA5B4",
    "muted2": "#6E7989",
    "border": "rgba(241,239,233,.10)",
    "border2": "rgba(241,239,233,.20)",
    "shadow": "0 18px 52px rgba(0,0,0,.35)",
    "green": "#4CBE90",
    "green_bg": "rgba(76,190,144,.11)",
    "amber": "#E5AC45",
    "amber_bg": "rgba(229,172,69,.11)",
    "coral": "#EF7E8C",
    "coral_bg": "rgba(239,126,140,.10)",
    "blue": "#7CA6E8",
    "blue_bg": "rgba(124,166,232,.10)",
    "meter_green": "#2E6B51",
    "meter_amber": "#8A6A2A",
    "meter_coral": "#7E4550",
    "pulse": "rgba(241,239,233,.32)",
}


def current_theme():
    return DARK if st.session_state.dark_mode else LIGHT


def inject_css(t):
    st.markdown(
        f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,400;0,9..144,550;0,9..144,650;1,9..144,450&family=Instrument+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@450;600&display=swap');

:root {{ color-scheme: {'dark' if st.session_state.dark_mode else 'light'}; }}

html, body, [class*="css"], .stApp, .stMarkdown, p, span, div, label {{
    font-family: "Instrument Sans", ui-sans-serif, -apple-system, "Segoe UI", sans-serif;
}}

.serif {{ font-family: "Fraunces", Georgia, serif; }}
.mono  {{ font-family: "IBM Plex Mono", ui-monospace, monospace; }}

.stApp {{
    color: {t['text']};
    background: {t['bg']};
}}

[data-testid="stHeader"] {{ background: transparent; }}
[data-testid="stToolbar"], [data-testid="stDecoration"] {{ display: none; }}

.block-container {{
    max-width: 1180px;
    padding-top: 1.0rem;
    padding-bottom: 3rem;
}}

/* ---------- Controls ---------- */
div[data-testid="stButton"] button {{
    height: 38px;
    border: 1px solid {t['border']};
    border-radius: 10px;
    background: {t['surface']};
    color: {t['text']};
    font-weight: 600;
    box-shadow: none;
    transition: border-color .18s ease, transform .18s ease;
}}
div[data-testid="stButton"] button:hover {{
    border-color: {t['border2']};
    transform: translateY(-1px);
}}
div[data-testid="stButton"] button:focus-visible {{
    outline: 2px solid {t['blue']};
    outline-offset: 2px;
}}

.stTabs [data-baseweb="tab-list"] {{
    gap: 6px;
    border-bottom: 1px solid {t['border']};
    padding-bottom: 8px;
}}
.stTabs [data-baseweb="tab"] {{
    height: 40px;
    border-radius: 9px;
    padding: 0 14px;
    color: {t['muted']};
    font-weight: 600;
}}
.stTabs [aria-selected="true"] {{
    color: {t['text']} !important;
    background: {t['surface']} !important;
    border: 1px solid {t['border']} !important;
}}

div[role="radiogroup"] {{ gap: 5px; flex-wrap: wrap; }}
div[role="radiogroup"] label {{
    border: 1px solid {t['border']};
    border-radius: 999px;
    background: {t['surface']};
    padding: 3px 10px;
}}

[data-testid="stExpander"] {{
    border: 1px solid {t['border']};
    border-radius: 14px;
    background: {t['surface']};
}}

/* ---------- Masthead ---------- */
.masthead {{
    display: flex;
    align-items: flex-end;
    justify-content: space-between;
    gap: 24px;
    padding: 10px 2px 6px;
    border-bottom: 2px solid {t['text']};
    margin-bottom: 8px;
}}
.wordmark {{
    font-family: "Fraunces", Georgia, serif;
    font-size: clamp(26px, 3.4vw, 38px);
    font-weight: 650;
    letter-spacing: -0.6px;
    line-height: 1.05;
    color: {t['text']};
}}
.wordmark em {{ font-style: italic; font-weight: 450; }}
.masthead-sub {{
    color: {t['muted']};
    font-size: 13.5px;
    margin-top: 5px;
}}
.freshness {{
    display: flex; flex-wrap: wrap; justify-content: flex-end; gap: 6px;
    padding-bottom: 2px;
}}
.meta-pill {{
    display: inline-flex; align-items: center; gap: 6px;
    color: {t['muted']};
    background: {t['surface']};
    border: 1px solid {t['border']};
    border-radius: 999px;
    padding: 5px 10px;
    font-family: "IBM Plex Mono", monospace;
    font-size: 10.5px;
    white-space: nowrap;
    animation: fadeUp .45s cubic-bezier(.2,.8,.2,1) both;
}}
.freshness .meta-pill:nth-child(1) {{ animation-delay: .05s; }}
.freshness .meta-pill:nth-child(2) {{ animation-delay: .13s; }}
.freshness .meta-pill:nth-child(3) {{ animation-delay: .21s; }}
.freshness .meta-pill:nth-child(4) {{ animation-delay: .29s; }}
.status-dot {{ width: 6px; height: 6px; border-radius: 999px; background: {t['green']}; animation: dotBlink 3.2s ease-in-out 1s 3; }}

/* ---------- Hero: today's report ---------- */
.report-card {{
    background: {t['surface']};
    border: 1px solid {t['border']};
    border-radius: 20px;
    box-shadow: {t['shadow']};
    padding: 34px 36px 30px;
    margin-top: 16px;
    animation: reportIn .6s cubic-bezier(.2,.8,.2,1) both;
}}
.report-grid {{
    display: grid;
    grid-template-columns: minmax(0, 1.05fr) minmax(300px, .95fr);
    gap: 44px;
    align-items: start;
}}
.eyebrow {{
    color: {t['muted']};
    font-family: "IBM Plex Mono", monospace;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 1.4px;
}}
.verdict {{
    font-family: "Fraunces", Georgia, serif;
    font-size: clamp(34px, 4.6vw, 56px);
    font-weight: 550;
    line-height: 1.06;
    letter-spacing: -1.2px;
    color: {t['text']};
    margin-top: 12px;
}}
.verdict .w {{
    display: inline-block;
    animation: wordRise .62s cubic-bezier(.2,.85,.25,1) both;
}}
.verdict .accent {{ font-style: italic; }}
.verdict-copy {{
    color: {t['muted']};
    font-size: 16.5px;
    line-height: 1.55;
    margin-top: 14px;
    max-width: 560px;
    animation: fadeUp .55s cubic-bezier(.2,.8,.2,1) .16s both;
}}
.guardrail {{
    display: inline-flex; align-items: center; gap: 8px;
    margin-top: 18px;
    padding: 9px 12px;
    color: {t['blue']};
    background: {t['blue_bg']};
    border-radius: 10px;
    font-size: 13px;
    font-weight: 600;
    animation: fadeUp .55s cubic-bezier(.2,.8,.2,1) .24s both;
}}

/* ---------- Thermometer panel ---------- */
.thermo-panel {{
    position: relative;
    overflow: hidden;
    border: 1px solid {t['border']};
    border-radius: 16px;
    background: {t['surface2']};
    padding: 22px 22px 18px;
    animation: fadeUp .55s cubic-bezier(.2,.8,.2,1) .14s both;
}}
.thermo-panel::before {{
    content: "";
    position: absolute;
    width: 280px; height: 280px;
    right: -100px; top: -120px;
    border-radius: 999px;
    background: radial-gradient(circle at 50% 50%, var(--glow, transparent), transparent 66%);
    pointer-events: none;
    animation: glowDrift 9s ease-in-out infinite;
}}
.thermo-panel > * {{ position: relative; z-index: 1; }}
.thermo-head {{
    display: flex; align-items: baseline; justify-content: space-between; gap: 14px;
}}
.weather-word {{
    font-family: "Fraunces", Georgia, serif;
    font-size: 30px;
    font-weight: 650;
    color: {t['text']};
    line-height: 1;
}}
.weather-word small {{
    display: block;
    font-family: "Instrument Sans", sans-serif;
    font-size: 12px;
    font-weight: 600;
    color: {t['muted']};
    letter-spacing: .2px;
    margin-bottom: 7px;
}}
.score-reading {{
    font-family: "IBM Plex Mono", monospace;
    font-size: 15px;
    color: {t['muted']};
    text-align: right;
}}
.score-reading b {{
    display: block;
    font-size: 34px;
    font-weight: 600;
    color: {t['text']};
    line-height: 1;
    animation: scorePop .7s cubic-bezier(.16,.9,.3,1.25) .40s both;
}}
.thermo-track {{
    position: relative;
    height: 12px;
    margin-top: 24px;
    border-radius: 999px;
    background: linear-gradient(90deg,
        {t['meter_green']} 0 35%,
        {t['meter_amber']} 35% 65%,
        {t['meter_coral']} 65% 100%);
}}
.thermo-track::after {{
    content: "";
    position: absolute;
    inset: 0;
    border-radius: 999px;
    background: linear-gradient(100deg, transparent 32%, rgba(255,255,255,.32) 50%, transparent 68%);
    background-size: 250% 100%;
    background-repeat: no-repeat;
    pointer-events: none;
    animation: trackSheen 1.1s ease-out .55s 1 both;
}}
.thermo-marker {{
    --pos: 50%;
    position: absolute;
    z-index: 2;
    top: 50%; left: var(--pos);
    width: 18px; height: 18px;
    transform: translate(-50%, -50%);
    border-radius: 999px;
    background: {t['text']};
    border: 3.5px solid {t['surface']};
    box-shadow: 0 3px 12px rgba(0,0,0,.25);
    animation:
        markerGlide .8s cubic-bezier(.2,.85,.25,1) .35s both,
        markerLand 1.5s ease-out 1.25s 2;
}}
.thermo-labels {{
    display: flex; justify-content: space-between;
    margin-top: 10px;
    color: {t['muted']};
    font-size: 11px;
    font-weight: 600;
}}
.thermo-labels span:first-child {{ color: {t['green']}; }}
.thermo-labels span:last-child  {{ color: {t['coral']}; }}
.thermo-meta {{
    display: flex; justify-content: space-between;
    margin-top: 16px;
    color: {t['muted2']};
    font-family: "IBM Plex Mono", monospace;
    font-size: 10.5px;
}}

/* ---------- Plan tiles ---------- */
.plan-grid {{
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 10px;
    margin-top: 26px;
}}
.plan-tile {{
    padding: 16px;
    border-radius: 14px;
    background: {t['surface2']};
    border: 1px solid {t['border']};
    transition: transform .2s ease, border-color .2s ease;
    animation: fadeUp .5s cubic-bezier(.2,.8,.2,1) both;
}}
.plan-tile:nth-child(1) {{ animation-delay: .30s; }}
.plan-tile:nth-child(2) {{ animation-delay: .38s; }}
.plan-tile:nth-child(3) {{ animation-delay: .46s; }}
.plan-tile:hover {{ transform: translateY(-3px); border-color: {t['border2']}; }}
.plan-label {{
    color: {t['muted']};
    font-family: "IBM Plex Mono", monospace;
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 1px;
}}
.plan-value {{
    color: {t['text']};
    font-size: 16.5px;
    line-height: 1.3;
    font-weight: 700;
    margin-top: 7px;
}}
.plan-help {{
    color: {t['muted']};
    font-size: 12px;
    line-height: 1.4;
    margin-top: 6px;
}}

/* ---------- Sections ---------- */
.section-head {{ margin: 34px 0 14px; }}
.section-kicker {{
    color: {t['muted']};
    font-family: "IBM Plex Mono", monospace;
    font-size: 10.5px;
    text-transform: uppercase;
    letter-spacing: 1.4px;
}}
.section-title {{
    font-family: "Fraunces", Georgia, serif;
    color: {t['text']};
    font-size: 25px;
    font-weight: 600;
    letter-spacing: -.4px;
    margin-top: 4px;
}}
.section-copy {{
    color: {t['muted']};
    font-size: 13.5px;
    line-height: 1.5;
    margin-top: 5px;
    max-width: 720px;
}}

/* ---------- Driver cards ---------- */
.driver-card {{
    height: 100%;
    background: {t['surface']};
    border: 1px solid {t['border']};
    border-radius: 14px;
    padding: 16px;
    transition: transform .2s ease, border-color .2s ease;
}}
.driver-card:hover {{ transform: translateY(-3px); border-color: {t['border2']}; }}
.driver-question {{
    color: {t['text']};
    font-size: 14px;
    font-weight: 700;
    line-height: 1.35;
    min-height: 38px;
}}
.driver-answer {{
    font-family: "Fraunces", Georgia, serif;
    font-size: 21px;
    font-weight: 600;
    margin-top: 9px;
    color: {t['text']};
}}
.driver-reading {{
    font-family: "IBM Plex Mono", monospace;
    font-size: 11px;
    color: {t['muted2']};
    margin-top: 4px;
}}
.driver-copy {{
    color: {t['muted']};
    font-size: 12.5px;
    line-height: 1.5;
    margin-top: 9px;
}}
.driver-pill {{
    display: inline-block;
    margin-top: 10px;
    padding: 3px 9px;
    border-radius: 999px;
    font-size: 11px;
    font-weight: 700;
}}
.pill-green {{ color: {t['green']}; background: {t['green_bg']}; }}
.pill-amber {{ color: {t['amber']}; background: {t['amber_bg']}; }}
.pill-coral {{ color: {t['coral']}; background: {t['coral_bg']}; }}
.pill-muted {{ color: {t['muted']}; background: {t['border']}; }}

/* ---------- Index cards ---------- */
.index-grid {{
    display: grid;
    grid-template-columns: repeat(5, minmax(0, 1fr));
    gap: 10px;
}}
.index-card {{
    background: {t['surface']};
    border: 1px solid {t['border']};
    border-radius: 14px;
    padding: 15px;
    transition: transform .2s ease, border-color .2s ease;
}}
.index-card:hover {{ transform: translateY(-3px); border-color: {t['border2']}; }}
.index-ticker {{
    font-family: "IBM Plex Mono", monospace;
    color: {t['text']};
    font-size: 15px;
    font-weight: 600;
}}
.index-name {{ color: {t['muted']}; font-size: 11.5px; margin-top: 3px; min-height: 30px; }}
.index-price {{
    font-family: "IBM Plex Mono", monospace;
    color: {t['text']};
    font-size: 19px;
    font-weight: 600;
    margin-top: 10px;
}}
.index-returns {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 5px; margin-top: 12px; }}
.index-period {{ color: {t['muted2']}; font-size: 9px; font-weight: 700; text-transform: uppercase; letter-spacing: .5px; }}
.index-return {{ font-family: "IBM Plex Mono", monospace; color: {t['text']}; font-size: 11.5px; font-weight: 600; margin-top: 2px; }}
.positive {{ color: {t['green']} !important; }}
.negative {{ color: {t['coral']} !important; }}

/* ---------- Performance ---------- */
.performance-intro {{
    color: {t['muted']};
    font-size: 13px;
    line-height: 1.5;
    margin-bottom: 10px;
}}
.performance-stats {{
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 9px;
    margin: 10px 0 6px;
}}
.summary-card {{
    background: {t['surface']};
    border: 1px solid {t['border']};
    border-radius: 12px;
    padding: 13px 15px;
}}
.summary-label {{ color: {t['muted2']}; font-size: 9.5px; font-weight: 700; text-transform: uppercase; letter-spacing: .8px; }}
.summary-value {{ font-family: "IBM Plex Mono", monospace; color: {t['text']}; font-size: 14px; font-weight: 600; margin-top: 5px; }}

/* ---------- Learn cards ---------- */
.learn-item {{ padding: 6px 0 12px; }}
.learn-q {{
    font-family: "Fraunces", Georgia, serif;
    color: {t['text']};
    font-size: 16.5px;
    font-weight: 600;
}}
.learn-a {{
    color: {t['muted']};
    font-size: 13.5px;
    line-height: 1.55;
    margin-top: 5px;
}}

.footer {{
    color: {t['muted']};
    font-size: 11.5px;
    line-height: 1.55;
    border-top: 1px solid {t['border']};
    padding-top: 16px;
    margin-top: 32px;
}}

/* ---------- Motion ---------- */
@keyframes reportIn {{
    from {{ opacity: 0; transform: translateY(14px); }}
    to   {{ opacity: 1; transform: translateY(0); }}
}}
@keyframes fadeUp {{
    from {{ opacity: 0; transform: translateY(8px); }}
    to   {{ opacity: 1; transform: translateY(0); }}
}}
@keyframes markerGlide {{
    from {{ left: 0%; opacity: 0; }}
    to   {{ left: var(--pos); opacity: 1; }}
}}
@keyframes wordRise {{
    from {{ opacity: 0; transform: translateY(.5em) rotate(1.2deg); filter: blur(3px); }}
    to   {{ opacity: 1; transform: translateY(0) rotate(0); filter: blur(0); }}
}}
@keyframes scorePop {{
    from {{ opacity: 0; transform: translateY(10px) scale(.7); }}
    60%  {{ opacity: 1; transform: translateY(-2px) scale(1.07); }}
    to   {{ opacity: 1; transform: translateY(0) scale(1); }}
}}
@keyframes trackSheen {{
    from {{ background-position: 220% 0; }}
    to   {{ background-position: -120% 0; }}
}}
@keyframes markerLand {{
    0%   {{ box-shadow: 0 3px 12px rgba(0,0,0,.25), 0 0 0 0 {t['pulse']}; }}
    100% {{ box-shadow: 0 3px 12px rgba(0,0,0,.25), 0 0 0 14px rgba(0,0,0,0); }}
}}
@keyframes glowDrift {{
    0%, 100% {{ transform: translate(0, 0) scale(1); opacity: .45; }}
    50%      {{ transform: translate(-20px, 16px) scale(1.12); opacity: .75; }}
}}
@keyframes dotBlink {{
    0%, 100% {{ opacity: 1; }}
    50%      {{ opacity: .3; }}
}}

/* Scroll-triggered reveals — modern browsers only; others show content normally */
@supports (animation-timeline: view()) {{
    .driver-card, .index-card {{
        animation: fadeUp .6s cubic-bezier(.2,.8,.2,1) both;
        animation-timeline: view();
        animation-range: entry 5% entry 40%;
    }}
}}

@media (max-width: 980px) {{
    .masthead {{ flex-direction: column; align-items: flex-start; gap: 10px; }}
    .freshness {{ justify-content: flex-start; }}
    .report-grid {{ grid-template-columns: 1fr; gap: 26px; }}
    .index-grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
}}
@media (max-width: 640px) {{
    .report-card {{ padding: 22px 20px; border-radius: 16px; }}
    .plan-grid, .performance-stats {{ grid-template-columns: 1fr; }}
    .index-grid {{ grid-template-columns: 1fr; }}
}}
@media (prefers-reduced-motion: reduce) {{
    *, *::before, *::after {{
        animation-duration: .001ms !important;
        animation-iteration-count: 1 !important;
        transition-duration: .001ms !important;
    }}
}}
</style>
""",
        unsafe_allow_html=True,
    )


# ============================================================
# Constants
# ============================================================
CORE_INDEXES = {
    "US Large Cap": "SPY",
    "US Total Market": "VTI",
    "Nasdaq 100": "QQQ",
    "International ex-US": "VXUS",
    "US Aggregate Bonds": "BND",
}

MAG7 = {
    "Apple": "AAPL",
    "Microsoft": "MSFT",
    "Alphabet": "GOOGL",
    "Amazon": "AMZN",
    "Nvidia": "NVDA",
    "Meta": "META",
    "Tesla": "TSLA",
}

SP500_SECTORS = {
    "Communication Services": "XLC",
    "Consumer Discretionary": "XLY",
    "Consumer Staples": "XLP",
    "Energy": "XLE",
    "Financials": "XLF",
    "Health Care": "XLV",
    "Industrials": "XLI",
    "Materials": "XLB",
    "Real Estate": "XLRE",
    "Technology": "XLK",
    "Utilities": "XLU",
}

RETURN_PERIODS = ("1D", "1M", "3M", "6M", "YTD", "1Y")
ALL_MARKET_TICKERS = tuple(
    dict.fromkeys(
        ["^GSPC", "^VIX"]
        + list(CORE_INDEXES.values())
        + list(MAG7.values())
        + list(SP500_SECTORS.values())
    )
)

# Plain-language identity for each technical signal.
SIGNAL_PLAIN = {
    "VIX": {
        "name": "Fear gauge",
        "question": "How nervous are investors?",
        "technical": "VIX index",
    },
    "S&P 500 RSI": {
        "name": "Momentum",
        "question": "Has the market run too far, too fast?",
        "technical": "14-day RSI, S&P 500",
    },
    "Distance from 200D": {
        "name": "Trend",
        "question": "Is the market above its long-term path?",
        "technical": "vs. 200-day average",
    },
    "Cboe equity P/C": {
        "name": "Hedging",
        "question": "Are investors paying up for protection?",
        "technical": "Cboe equity put/call",
    },
}


# ============================================================
# General helpers
# ============================================================
def safe_float(value):
    try:
        if value is None:
            return None
        value = float(value)
        if math.isnan(value) or math.isinf(value):
            return None
        return value
    except (TypeError, ValueError):
        return None


def clamp(value, low=0.0, high=100.0):
    value = safe_float(value)
    if value is None:
        return None
    return max(low, min(high, value))


def fmt_number(value, digits=2, suffix=""):
    value = safe_float(value)
    if value is None:
        return "N/A"
    return f"{value:,.{digits}f}{suffix}"


def fmt_return(value):
    value = safe_float(value)
    return "N/A" if value is None else f"{value:+.2f}%"


def return_class(value):
    value = safe_float(value)
    if value is None or value == 0:
        return ""
    return "positive" if value > 0 else "negative"


def score_from_range(value, points):
    value = safe_float(value)
    if value is None:
        return None
    points = sorted(points, key=lambda pair: pair[0])
    if value <= points[0][0]:
        return float(points[0][1])
    if value >= points[-1][0]:
        return float(points[-1][1])
    for (x1, y1), (x2, y2) in zip(points, points[1:]):
        if x1 <= value <= x2:
            portion = (value - x1) / (x2 - x1)
            return y1 + portion * (y2 - y1)
    return None


def period_start_date(latest_date, period):
    latest_date = pd.Timestamp(latest_date).normalize()
    if period == "1M":
        return latest_date - pd.DateOffset(months=1)
    if period == "3M":
        return latest_date - pd.DateOffset(months=3)
    if period == "6M":
        return latest_date - pd.DateOffset(months=6)
    if period == "YTD":
        return pd.Timestamp(year=latest_date.year, month=1, day=1)
    if period == "1Y":
        return latest_date - pd.DateOffset(years=1)
    return latest_date


def calculate_period_return(series, period):
    """Adjusted-close return ending at the latest available observation."""
    series = pd.to_numeric(series, errors="coerce").dropna().sort_index()
    if len(series) < 2:
        return None

    latest_value = safe_float(series.iloc[-1])
    if latest_value is None:
        return None

    if period == "1D":
        base_value = safe_float(series.iloc[-2])
    else:
        start_date = period_start_date(series.index[-1], period)
        prior = series.loc[series.index <= start_date]
        if not prior.empty:
            base_value = safe_float(prior.iloc[-1])
        else:
            later = series.loc[series.index >= start_date]
            base_value = safe_float(later.iloc[0]) if not later.empty else None

    if base_value in (None, 0):
        return None
    return ((latest_value / base_value) - 1.0) * 100.0


# ============================================================
# Data acquisition (unchanged: independent critical fetches + fallbacks)
# ============================================================
def _clean_price_series(series):
    if series is None:
        return pd.Series(dtype="float64")
    clean = pd.to_numeric(series, errors="coerce").dropna().copy()
    if clean.empty:
        return clean
    clean.index = pd.to_datetime(clean.index, errors="coerce")
    clean = clean[~clean.index.isna()]
    if getattr(clean.index, "tz", None) is not None:
        clean.index = clean.index.tz_localize(None)
    clean = clean[~clean.index.duplicated(keep="last")].sort_index()
    return clean


def _extract_close_frame(raw, requested_tickers):
    if raw is None or raw.empty:
        return pd.DataFrame()

    requested = list(requested_tickers)
    close = None

    if isinstance(raw.columns, pd.MultiIndex):
        for level in range(raw.columns.nlevels):
            values = raw.columns.get_level_values(level).astype(str)
            if "Close" in set(values):
                close = raw.xs("Close", axis=1, level=level, drop_level=True).copy()
                break
        if close is None:
            return pd.DataFrame()
    else:
        if "Close" not in raw.columns:
            return pd.DataFrame()
        close = raw[["Close"]].copy()
        if len(requested) == 1:
            close.columns = [requested[0]]

    if isinstance(close, pd.Series):
        name = requested[0] if requested else str(close.name)
        close = close.to_frame(name=name)

    if isinstance(close.columns, pd.MultiIndex):
        flattened = []
        for column in close.columns:
            parts = [str(part) for part in column]
            match = next((ticker for ticker in requested if ticker in parts), parts[-1])
            flattened.append(match)
        close.columns = flattened
    else:
        close.columns = [str(column) for column in close.columns]

    aliases = {ticker.upper(): ticker for ticker in requested}
    renamed = {}
    for column in close.columns:
        normalized = str(column).upper()
        if normalized in aliases:
            renamed[column] = aliases[normalized]
    close = close.rename(columns=renamed)
    close = close.loc[:, [column for column in close.columns if column in requested]]

    close.index = pd.to_datetime(close.index, errors="coerce")
    close = close[~close.index.isna()]
    if getattr(close.index, "tz", None) is not None:
        close.index = close.index.tz_localize(None)
    close = close.loc[:, ~close.columns.duplicated(keep="last")].sort_index()
    return close.dropna(how="all")


def _download_bulk_prices(tickers, period="2y"):
    tickers = list(dict.fromkeys(tickers))
    if not tickers:
        return pd.DataFrame()
    try:
        raw = yf.download(
            tickers=" ".join(tickers),
            period=period,
            interval="1d",
            auto_adjust=True,
            progress=False,
            threads=False,
        )
        return _extract_close_frame(raw, tickers)
    except Exception:
        return pd.DataFrame()


def _download_single_price(ticker, period="2y"):
    try:
        history = yf.Ticker(ticker).history(
            period=period,
            interval="1d",
            auto_adjust=True,
            actions=False,
        )
        if history is None or history.empty or "Close" not in history.columns:
            return pd.Series(dtype="float64", name=ticker)
        series = _clean_price_series(history["Close"])
        series.name = ticker
        return series
    except Exception:
        return pd.Series(dtype="float64", name=ticker)


@st.cache_data(ttl=900, show_spinner=False)
def fetch_market_prices(tickers):
    """Fetch adjusted daily closes with graceful fallbacks.

    Critical index series are fetched independently so one failure cannot
    blank the whole app; ordinary tickers use a bulk request with per-symbol
    fallback fills.
    """
    requested = list(dict.fromkeys(tickers))
    frames = []

    for ticker in ("^GSPC", "SPY", "^VIX"):
        if ticker in requested:
            series = _download_single_price(ticker)
            if not series.empty:
                frames.append(series.to_frame())

    ordinary = [ticker for ticker in requested if ticker not in {"^GSPC", "^VIX", "SPY"}]
    bulk = _download_bulk_prices(ordinary)
    if not bulk.empty:
        frames.append(bulk)

    loaded = set()
    for frame in frames:
        loaded.update(frame.columns)
    for ticker in ordinary:
        if ticker not in loaded:
            series = _download_single_price(ticker)
            if not series.empty:
                frames.append(series.to_frame())

    if not frames:
        return pd.DataFrame()

    prices = pd.concat(frames, axis=1).sort_index()
    prices = prices.loc[:, ~prices.columns.duplicated(keep="last")]
    prices = prices[[ticker for ticker in requested if ticker in prices.columns]]
    return prices.dropna(how="all")


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_cboe_equity_put_call():
    """Latest Cboe equity put/call ratio from Cboe's official daily stats page."""
    url = "https://www.cboe.com/markets/us/options/market-statistics/daily/"
    try:
        response = requests.get(url, timeout=12, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()
        plain = html_lib.unescape(re.sub(r"<[^>]+>", " ", response.text))
        plain = re.sub(r"\s+", " ", plain)
        match = re.search(r"EQUITY PUT/CALL RATIO\s+([0-9]+(?:\.[0-9]+)?)", plain, re.I)
        return safe_float(match.group(1)) if match else None
    except Exception:
        return None


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_treasury_curve():
    """Latest official U.S. Treasury par yield curve. Advanced context only."""
    year = NOW_PT.year
    urls = [
        (
            "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/"
            f"daily-treasury-rates.csv/{year}/all?type=daily_treasury_yield_curve"
            f"&field_tdr_date_value={year}&page&_format=csv"
        ),
        (
            "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/"
            "daily-treasury-rates.csv/all/all?_format=csv&page=&type=daily_treasury_yield_curve"
        ),
    ]
    for url in urls:
        try:
            response = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
            response.raise_for_status()
            frame = pd.read_csv(StringIO(response.text))
            if frame.empty or "Date" not in frame.columns:
                continue
            frame["Date"] = pd.to_datetime(frame["Date"], errors="coerce")
            frame = frame.dropna(subset=["Date"]).sort_values("Date")
            if not frame.empty:
                return frame.iloc[-1].to_dict()
        except Exception:
            continue
    return {}


# ============================================================
# Market model (scoring unchanged; language layer added)
# ============================================================
def build_technical_snapshot(prices):
    if prices.empty:
        return None

    source_ticker = None
    source_label = None
    spx = None
    for ticker, label in (("^GSPC", "S&P 500 Index"), ("SPY", "SPY ETF proxy")):
        if ticker not in prices.columns:
            continue
        candidate = pd.to_numeric(prices[ticker], errors="coerce").dropna()
        if len(candidate) >= 210:
            source_ticker = ticker
            source_label = label
            spx = candidate
            break

    if source_ticker is None:
        return None

    rsi = RSIIndicator(spx, window=14).rsi()
    sma200 = SMAIndicator(spx, window=200).sma_indicator()
    close = safe_float(spx.iloc[-1])
    latest_sma = safe_float(sma200.iloc[-1])

    vix = None
    if "^VIX" in prices.columns:
        vix_series = pd.to_numeric(prices["^VIX"], errors="coerce").dropna()
        vix = safe_float(vix_series.iloc[-1]) if not vix_series.empty else None

    return {
        "close": close,
        "rsi": safe_float(rsi.iloc[-1]),
        "sma200": latest_sma,
        "distance_200d": ((close / latest_sma) - 1) * 100 if close and latest_sma else None,
        "vix": vix,
        "latest_date": pd.Timestamp(spx.index[-1]),
        "history": pd.DataFrame({"Close": spx, "SMA 200": sma200}).reset_index(names="Date"),
        "source_ticker": source_ticker,
        "source_label": source_label,
    }


def signal_description(name, reading):
    value = safe_float(reading)
    if value is None:
        return "Unavailable", "This reading is missing today, so a neutral value is used and confidence goes down."

    if name == "VIX":
        if value < 14:
            return "Very calm", "Investors look relaxed — maybe too relaxed. Calm markets rarely hand out discounts."
        if value < 20:
            return "Calm", "A normal amount of worry. No fear discount, no reason to hold back either."
        if value < 28:
            return "Nervous", "Some fear in the air. Historically, nervous markets have been friendlier to buyers."
        return "Fearful", "Real fear. Uncomfortable to buy into, but usually the opposite of chasing."

    if name == "S&P 500 RSI":
        if value < 30:
            return "Oversold", "The market has fallen hard and fast in the short term."
        if value < 40:
            return "Cooling off", "Short-term prices have pulled back from recent highs."
        if value <= 60:
            return "Steady", "The market isn't stretched in either direction right now."
        if value <= 70:
            return "Running hot", "Prices have climbed quickly. Momentum is strong but getting stretched."
        return "Overheated", "A fast run-up. Buying big after a sprint often means overpaying."

    if name == "Distance from 200D":
        if value < -8:
            return "Well below trend", "Prices are far under their long-term average — historically better entry territory."
        if value < -2:
            return "Below trend", "Prices sit modestly under their long-term average."
        if value <= 8:
            return "On trend", "Prices are within a normal range of their long-term average."
        return "Stretched", "Prices are well above their long-term average. Gravity tends to matter eventually."

    if name == "Cboe equity P/C":
        if value < 0.65:
            return "All-in mood", "Investors are betting on gains, not buying protection. Optimism is running high."
        if value <= 1.10:
            return "Balanced", "A normal mix of optimism and caution in the options market."
        return "Defensive", "Investors are paying up for downside protection — a sign of elevated fear."

    return "Neutral", "No interpretation available."


def build_heat_score(vix, rsi, distance_200d, put_call):
    """Stable rule-based heat index. Missing values get a neutral 50 rather than
    silently reweighting, so the 0–100 scale means the same thing every day."""
    definitions = [
        {
            "Signal": "VIX",
            "Reading": vix,
            "Weight": 0.30,
            "SignalScore": score_from_range(vix, [(12, 88), (18, 62), (25, 36), (35, 15), (50, 5)]),
        },
        {
            "Signal": "S&P 500 RSI",
            "Reading": rsi,
            "Weight": 0.25,
            "SignalScore": score_from_range(rsi, [(25, 8), (35, 24), (50, 50), (65, 72), (75, 90), (85, 100)]),
        },
        {
            "Signal": "Distance from 200D",
            "Reading": distance_200d,
            "Weight": 0.25,
            "SignalScore": score_from_range(distance_200d, [(-20, 7), (-10, 20), (0, 48), (8, 68), (15, 84), (25, 97)]),
        },
        {
            "Signal": "Cboe equity P/C",
            "Reading": put_call,
            "Weight": 0.20,
            "SignalScore": score_from_range(put_call, [(0.50, 94), (0.65, 82), (0.85, 58), (1.10, 34), (1.40, 12)]),
        },
    ]

    rows = []
    for item in definitions:
        available = item["SignalScore"] is not None
        used_score = item["SignalScore"] if available else 50.0
        status, explanation = signal_description(item["Signal"], item["Reading"])
        rows.append(
            {
                **item,
                "Available": available,
                "UsedScore": used_score,
                "WeightedImpact": (used_score - 50.0) * item["Weight"],
                "Status": status,
                "Explanation": explanation,
            }
        )

    frame = pd.DataFrame(rows)
    score = int(round((frame["UsedScore"] * frame["Weight"]).sum()))
    score = int(clamp(score, 0, 100))
    return score, frame


def recommendation(score):
    """One internally consistent buy-sizing policy for extra cash,
    expressed as a weather report a beginner can act on."""
    if score is None:
        return {
            "weather": "Unknown",
            "verdict": "Stick to your normal plan.",
            "copy": "Today's data is incomplete, so the honest answer is the boring one: follow your usual schedule until the numbers refresh.",
            "extra_buy": "100% of your usual extra amount",
            "hold": "No change",
            "avoid": "Guessing from missing data",
        }
    if score <= 20:
        return {
            "weather": "Cold",
            "verdict": "A good day to buy extra.",
            "copy": "The market is fearful, and fear is when long-term buyers historically get better prices. Buying more than usual is reasonable — just don't empty the tank in one day.",
            "extra_buy": "150–200% of your usual extra amount",
            "hold": "Keep some cash for another drop",
            "avoid": "Going all-in at once",
        }
    if score <= 35:
        return {
            "weather": "Cool",
            "verdict": "Lean in a little.",
            "copy": "Conditions look a bit better than normal for buyers. A modestly larger buy makes sense; trying to catch the exact bottom does not.",
            "extra_buy": "125–150% of your usual extra amount",
            "hold": "Save the rest for future buys",
            "avoid": "Trying to time the exact bottom",
        }
    if score <= 65:
        return {
            "weather": "Mild",
            "verdict": "Buy your normal amount.",
            "copy": "Nothing unusual is happening — the market isn't fearful and it isn't overheated. The best move is the boring one: stay on your plan.",
            "extra_buy": "100% of your usual extra amount",
            "hold": "Follow your existing schedule",
            "avoid": "Inventing a clever trade",
        }
    if score <= 80:
        return {
            "weather": "Warm",
            "verdict": "Go easy on extra buys.",
            "copy": "The market has been running warm. Keep your automatic investing exactly as it is, but size any extra buy smaller and spread the rest over coming weeks.",
            "extra_buy": "25–50% of your usual extra amount",
            "hold": "Stage the rest into later buys",
            "avoid": "Chasing a strong run",
        }
    return {
        "weather": "Hot",
        "verdict": "Not the day to chase.",
        "copy": "Prices are stretched and optimism is loud. Your automatic investing keeps going — that never changes — but forcing a big extra buy here is how people overpay.",
        "extra_buy": "0–25% of your usual extra amount",
        "hold": "Wait for scheduled buys or a pullback",
        "avoid": "FOMO-driven lump sums",
    }


def confidence_summary(signal_frame):
    available = signal_frame[signal_frame["Available"]]
    count = len(available)
    if count < 3:
        return "Low", count, "Too many core inputs are unavailable."

    dispersion = float(available["UsedScore"].std(ddof=0)) if count > 1 else 0.0
    if count == 4 and dispersion <= 17:
        return "High", count, "All four inputs are available and broadly agree."
    if dispersion <= 28:
        return "Medium", count, "Most inputs point in a similar direction."
    return "Low", count, "The inputs disagree, so today's signal is less decisive."


def driver_pill(row):
    """Plain direction pill for a signal."""
    impact = row["WeightedImpact"]
    if not row["Available"]:
        return "pill-muted", "No data today"
    if impact > 1:
        return "pill-coral", "Pushes hotter"
    if impact < -1:
        return "pill-green", "Helps buyers"
    return "pill-amber", "Near neutral"


# ============================================================
# Performance helpers
# ============================================================
def build_return_table(prices, assets):
    rows = []
    for name, ticker in assets.items():
        if ticker not in prices.columns:
            continue
        row = {"Name": name, "Ticker": ticker}
        for period in RETURN_PERIODS:
            row[period] = calculate_period_return(prices[ticker], period)
        rows.append(row)
    return pd.DataFrame(rows)


def performance_summary(return_table, period):
    if return_table.empty or period not in return_table.columns:
        return None
    usable = return_table[["Name", "Ticker", period]].dropna()
    if usable.empty:
        return None
    leader = usable.loc[usable[period].idxmax()]
    laggard = usable.loc[usable[period].idxmin()]
    positive = int((usable[period] > 0).sum())
    return {
        "leader": f"{leader['Ticker']} {leader[period]:+.2f}%",
        "laggard": f"{laggard['Ticker']} {laggard[period]:+.2f}%",
        "breadth": f"{positive} of {len(usable)} positive",
    }


def make_return_chart(return_table, period, title, theme, benchmark_return=None):
    if return_table.empty or period not in return_table.columns:
        return None
    chart = return_table[["Name", "Ticker", period]].dropna().copy()
    if chart.empty:
        return None

    chart["Label"] = chart["Name"] + " · " + chart["Ticker"]
    chart = chart.sort_values(period, ascending=True)
    colors = [theme["green"] if value >= 0 else theme["coral"] for value in chart[period]]

    figure = go.Figure(
        go.Bar(
            x=chart[period],
            y=chart["Label"],
            orientation="h",
            marker={"color": colors, "line": {"width": 0}},
            text=[f"{value:+.2f}%" for value in chart[period]],
            textposition="outside",
            cliponaxis=False,
            hovertemplate="<b>%{y}</b><br>Total return: %{x:+.2f}%<extra></extra>",
        )
    )

    if benchmark_return is not None:
        figure.add_vline(
            x=benchmark_return,
            line_width=1.4,
            line_dash="dot",
            line_color=theme["muted"],
            annotation_text=f"SPY {benchmark_return:+.2f}%",
            annotation_position="top",
            annotation_font_color=theme["muted"],
        )

    figure.add_vline(x=0, line_width=1, line_color=theme["border2"])
    figure.update_layout(
        title={"text": title, "x": 0.01, "xanchor": "left", "font": {"size": 15, "family": "Instrument Sans"}},
        height=max(370, 48 * len(chart) + 100),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": theme["text"], "family": "Instrument Sans, sans-serif", "size": 12},
        margin={"l": 10, "r": 76, "t": 52, "b": 20},
        showlegend=False,
        bargap=0.34,
        hoverlabel={"bgcolor": theme["surface"], "font_color": theme["text"]},
        xaxis={"title": None, "ticksuffix": "%", "gridcolor": theme["border"], "zeroline": False},
        yaxis={"title": None, "automargin": True},
    )
    return figure


def render_performance_view(title, copy, assets, prices, key, theme, show_benchmark=True):
    st.markdown(f'<div class="performance-intro"><b>{title}</b> — {copy}</div>', unsafe_allow_html=True)
    period = st.radio(
        f"{title} return period",
        RETURN_PERIODS,
        horizontal=True,
        key=key,
        label_visibility="collapsed",
    )
    table = build_return_table(prices, assets)
    benchmark = None
    if show_benchmark and "SPY" in prices.columns:
        benchmark = calculate_period_return(prices["SPY"], period)

    summary = performance_summary(table, period)
    if summary:
        st.markdown(
            f"""
<div class="performance-stats">
  <div class="summary-card"><div class="summary-label">Best performer</div><div class="summary-value">{summary['leader']}</div></div>
  <div class="summary-card"><div class="summary-label">Worst performer</div><div class="summary-value">{summary['laggard']}</div></div>
  <div class="summary-card"><div class="summary-label">How many are up</div><div class="summary-value">{summary['breadth']}</div></div>
</div>
""",
            unsafe_allow_html=True,
        )

    figure = make_return_chart(table, period, f"{period} adjusted total return", theme, benchmark)
    if figure is None:
        st.warning("Performance data is unavailable right now.")
        return
    st.plotly_chart(figure, use_container_width=True, config={"displayModeBar": False})

    with st.expander("See every return period as a table"):
        display = table.copy()
        for item in RETURN_PERIODS:
            display[item] = display[item].apply(fmt_return)
        st.dataframe(display, use_container_width=True, hide_index=True)


# ============================================================
# UI helpers
# ============================================================
def section_header(kicker, title, copy):
    st.markdown(
        f"""
<div class="section-head">
  <div class="section-kicker">{kicker}</div>
  <div class="section-title">{title}</div>
  <div class="section-copy">{copy}</div>
</div>
""",
        unsafe_allow_html=True,
    )


def render_core_index_cards(prices):
    cards = []
    for name, ticker in CORE_INDEXES.items():
        if ticker not in prices.columns:
            continue
        series = pd.to_numeric(prices[ticker], errors="coerce").dropna()
        if series.empty:
            continue
        price = safe_float(series.iloc[-1])
        one_day = calculate_period_return(series, "1D")
        ytd = calculate_period_return(series, "YTD")
        one_year = calculate_period_return(series, "1Y")
        cards.append(
            f"""
<div class="index-card">
  <div class="index-ticker">{ticker}</div>
  <div class="index-name">{name}</div>
  <div class="index-price">${price:,.2f}</div>
  <div class="index-returns">
    <div><div class="index-period">Today</div><div class="index-return {return_class(one_day)}">{fmt_return(one_day)}</div></div>
    <div><div class="index-period">This yr</div><div class="index-return {return_class(ytd)}">{fmt_return(ytd)}</div></div>
    <div><div class="index-period">1 yr</div><div class="index-return {return_class(one_year)}">{fmt_return(one_year)}</div></div>
  </div>
</div>
"""
        )
    st.markdown(f'<div class="index-grid">{"".join(cards)}</div>', unsafe_allow_html=True)


def reading_text(signal_name, reading):
    if reading is None:
        return "no data"
    if signal_name == "Distance from 200D":
        return fmt_number(reading, 1, "%")
    return fmt_number(reading, 2)


# ============================================================
# Controls and data load
# ============================================================
theme = current_theme()
inject_css(theme)

control_spacer, control_mode, control_refresh = st.columns([0.72, 0.15, 0.13])
with control_mode:
    st.toggle("Dark mode", key="dark_mode")
with control_refresh:
    if st.button("Refresh data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

theme = current_theme()

with st.spinner("Reading today's market weather..."):
    market_prices = fetch_market_prices(ALL_MARKET_TICKERS)
    put_call = fetch_cboe_equity_put_call()
    treasury = fetch_treasury_curve()

technical = build_technical_snapshot(market_prices)
if technical is None:
    loaded_symbols = [ticker for ticker in ALL_MARKET_TICKERS if ticker in market_prices.columns]
    st.markdown(
        """
<div class="masthead">
  <div>
    <div class="wordmark">Should I Buy <em>Today?</em></div>
    <div class="masthead-sub">Market data could not be loaded reliably, so no signal is shown.</div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )
    st.error("The S&P 500 index and its SPY fallback are both unavailable. Yahoo may be rate-limiting this deployment.")
    if loaded_symbols:
        st.caption(f"Other symbols loaded: {', '.join(loaded_symbols)}")
    st.info("Wait a minute and press Refresh data. Critical symbols retry independently, so a temporary failure shouldn't blank the dashboard on the next attempt.")
    st.stop()

score, signal_frame = build_heat_score(
    technical["vix"],
    technical["rsi"],
    technical["distance_200d"],
    put_call,
)
plan = recommendation(score)
confidence, available_count, confidence_reason = confidence_summary(signal_frame)
latest_market_date = technical["latest_date"]
market_age_days = max(0, (NOW_PT.date() - latest_market_date.date()).days)

market_date_label = latest_market_date.strftime("%b %d, %Y")
refresh_label = NOW_PT.strftime("%b %d · %I:%M %p PT")
report_date_label = NOW_PT.strftime("%A, %B %d, %Y")


# ============================================================
# Masthead
# ============================================================
st.markdown(
    f"""
<div class="masthead">
  <div>
    <div class="wordmark">Should I Buy <em>Today?</em></div>
    <div class="masthead-sub">A daily market weather report for long-term index investors. Not a forecast — a sizing guide.</div>
  </div>
  <div class="freshness">
    <span class="meta-pill"><span class="status-dot"></span>prices thru {market_date_label}</span>
    <span class="meta-pill">refreshed {refresh_label}</span>
    <span class="meta-pill">inputs {available_count}/4</span>
    <span class="meta-pill">source: {technical['source_label']}</span>
  </div>
</div>
""",
    unsafe_allow_html=True,
)

if market_age_days > 4:
    st.warning(f"Market prices are {market_age_days} calendar days old. Treat today's report as stale until data refreshes.")


# ============================================================
# Today's report (hero)
# ============================================================
marker = clamp(score, 0, 100) if score is not None else 50

# Word-by-word verdict reveal
verdict_words = " ".join(
    f'<span class="w" style="animation-delay:{0.10 + i * 0.06:.2f}s">{word}</span>'
    for i, word in enumerate(plan["verdict"].split())
)

# Ambient glow tinted by today's weather
weather_hue = {
    "Cold": theme["green"],
    "Cool": theme["green"],
    "Mild": theme["blue"],
    "Warm": theme["amber"],
    "Hot": theme["coral"],
}.get(plan["weather"], theme["blue"])
glow_style = f"--glow: color-mix(in srgb, {weather_hue} 26%, transparent);"

st.markdown(
    f"""
<div class="report-card">
  <div class="report-grid">
    <div>
      <div class="eyebrow">Today's report · {report_date_label}</div>
      <div class="verdict">{verdict_words}</div>
      <div class="verdict-copy">{plan['copy']}</div>
      <div class="guardrail">✓&nbsp; Your automatic investing never changes. This only sizes optional extra cash.</div>
    </div>
    <div class="thermo-panel" style="{glow_style}">
      <div class="thermo-head">
        <div class="weather-word"><small>Market weather</small>{plan['weather']}</div>
        <div class="score-reading"><b>{score}</b>of 100</div>
      </div>
      <div class="thermo-track"><div class="thermo-marker" style="--pos:{marker}%;"></div></div>
      <div class="thermo-labels"><span>Fearful — better prices</span><span>Normal</span><span>Stretched — easy to overpay</span></div>
      <div class="thermo-meta"><span>confidence: {confidence.lower()}</span><span>0–100 heat index</span></div>
    </div>
  </div>
  <div class="plan-grid">
    <div class="plan-tile">
      <div class="plan-label">If you have extra cash</div>
      <div class="plan-value">{plan['extra_buy']}</div>
      <div class="plan-help">100% means whatever you'd normally invest on top of your automatic plan.</div>
    </div>
    <div class="plan-tile">
      <div class="plan-label">What to hold back</div>
      <div class="plan-value">{plan['hold']}</div>
      <div class="plan-help">Spreading buys beats trying to predict one perfect day.</div>
    </div>
    <div class="plan-tile">
      <div class="plan-label">What to avoid</div>
      <div class="plan-value">{plan['avoid']}</div>
      <div class="plan-help">There is never a sell signal here, and never a change to your long-term plan.</div>
    </div>
  </div>
</div>
""",
    unsafe_allow_html=True,
)

# ---------- First-time explainer ----------
with st.expander("🌱 New here? Read this first — it takes 30 seconds"):
    st.markdown(
        """
<div class="learn-item">
  <div class="learn-q">What is this?</div>
  <div class="learn-a">A daily gauge of whether the stock market looks fearful, normal, or overheated — like a weather report. It helps you decide how much <b>extra</b> cash to invest today on top of your regular automatic investing.</div>
</div>
<div class="learn-item">
  <div class="learn-q">What is "automatic investing" (DCA)?</div>
  <div class="learn-a">Dollar-cost averaging: investing the same amount on a schedule (say, every payday) no matter what the market does. It's the backbone of long-term investing, and <b>nothing on this page ever tells you to change it</b>.</div>
</div>
<div class="learn-item">
  <div class="learn-q">Why does "fear" mean better prices?</div>
  <div class="learn-a">When investors are scared, they sell, and prices fall. For someone buying to hold for decades, lower prices are a discount — even though it feels worse to buy on a scary day than a euphoric one.</div>
</div>
<div class="learn-item">
  <div class="learn-q">What is this NOT?</div>
  <div class="learn-a">Not a prediction of tomorrow. Not a stock-picking tool. Not financial advice. It never says "sell." It's a discipline tool that leans slightly against the crowd, sized in percentages of <i>your</i> normal amount.</div>
</div>
""",
        unsafe_allow_html=True,
    )


# ============================================================
# Why today's answer
# ============================================================
section_header(
    "The reasoning",
    "Why today reads " + plan["weather"].lower(),
    f"Four questions, answered by live market data, blended into one score. Confidence is {confidence.lower()}: {confidence_reason}",
)

ordered = signal_frame.reindex(signal_frame["WeightedImpact"].abs().sort_values(ascending=False).index)
columns = st.columns(4)
for column, (_, row) in zip(columns, ordered.iterrows()):
    plain = SIGNAL_PLAIN.get(row["Signal"], {"name": row["Signal"], "question": "", "technical": row["Signal"]})
    pill_class, pill_text = driver_pill(row)
    with column:
        st.markdown(
            f"""
<div class="driver-card">
  <div class="driver-question">{plain['question']}</div>
  <div class="driver-answer">{row['Status']}</div>
  <div class="driver-reading">{plain['technical']}: {reading_text(row['Signal'], row['Reading'])}</div>
  <div class="driver-copy">{row['Explanation']}</div>
  <span class="driver-pill {pill_class}">{pill_text}</span>
</div>
""",
            unsafe_allow_html=True,
        )


# ============================================================
# Core index snapshot
# ============================================================
section_header(
    "The market",
    "Today at a glance",
    "The broad building blocks most long-term portfolios actually own — US stocks, international stocks, and bonds. Returns use adjusted prices.",
)
render_core_index_cards(market_prices)


# ============================================================
# Performance
# ============================================================
section_header(
    "Go deeper",
    "Compare performance",
    "Start with the broad indexes, then see whether a handful of giant companies — or particular sectors — are doing all the work.",
)
index_tab, mag7_tab, sector_tab = st.tabs(["Core indexes", "The Magnificent 7", "S&P 500 sectors"])

with index_tab:
    render_performance_view(
        "Core indexes",
        "US stocks vs. international stocks vs. bonds over the period you pick.",
        CORE_INDEXES,
        market_prices,
        "core_period",
        theme,
        show_benchmark=False,
    )

with mag7_tab:
    render_performance_view(
        "Magnificent 7",
        "The seven biggest US tech companies. The dotted line is the whole S&P 500 (SPY) — anything right of it is beating the market.",
        MAG7,
        market_prices,
        "mag7_period",
        theme,
        show_benchmark=True,
    )

with sector_tab:
    render_performance_view(
        "S&P 500 sector ETFs",
        "Eleven slices of the US economy via the Select Sector SPDR ETFs — investable proxies, not the exact underlying sector indexes.",
        SP500_SECTORS,
        market_prices,
        "sector_period",
        theme,
        show_benchmark=True,
    )


# ============================================================
# Under the hood
# ============================================================
section_header(
    "Trust, but verify",
    "Under the hood",
    "Everything needed to audit today's score — the exact weights, raw readings, and data sources.",
)

with st.expander("Open the full methodology, signal table, and advanced charts"):
    st.markdown(
        """
**How the score works**

The Market Heat Score is a transparent, rule-based index — not a forecast of tomorrow's return. Four inputs: the VIX fear gauge (30%), broad-market momentum via 14-day RSI (25%), distance from the 200-day average (25%), and the Cboe equity put/call ratio (20%). The S&P 500 index is preferred; SPY is a disclosed fallback when the index feed is unavailable. Higher means more stretched; lower means more fearful.

When an input is unavailable, it's replaced with a neutral 50 and confidence drops. The missing weight is **not** silently redistributed, so the score means the same thing every day.
"""
    )

    signal_display = signal_frame[
        ["Signal", "Reading", "Status", "Weight", "UsedScore", "Available", "Explanation"]
    ].copy()
    signal_display.insert(0, "Plain name", signal_display["Signal"].map(lambda s: SIGNAL_PLAIN.get(s, {}).get("name", s)))
    signal_display["Reading"] = signal_display.apply(
        lambda row: reading_text(row["Signal"], row["Reading"]), axis=1
    )
    signal_display["Weight"] = signal_display["Weight"].apply(lambda value: f"{value:.0%}")
    signal_display["UsedScore"] = signal_display["UsedScore"].round(1)
    signal_display["Available"] = signal_display["Available"].map({True: "Yes", False: "No — neutral used"})
    st.dataframe(signal_display, use_container_width=True, hide_index=True)

    trend_tab, treasury_tab, sources_tab = st.tabs(["S&P 500 trend", "Treasury curve", "Data sources"])

    with trend_tab:
        history = technical["history"]
        figure = go.Figure()
        figure.add_trace(go.Scatter(x=history["Date"], y=history["Close"], mode="lines",
                                    name=technical["source_label"], line={"color": theme["blue"], "width": 2}))
        figure.add_trace(go.Scatter(x=history["Date"], y=history["SMA 200"], mode="lines",
                                    name="200-day average", line={"color": theme["muted"], "width": 1.6, "dash": "dot"}))
        figure.update_layout(
            height=400,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font={"color": theme["text"], "family": "Instrument Sans, sans-serif"},
            margin={"l": 10, "r": 10, "t": 20, "b": 10},
            legend={"orientation": "h"},
            hovermode="x unified",
            xaxis={"gridcolor": theme["border"]},
            yaxis={"gridcolor": theme["border"]},
        )
        st.plotly_chart(figure, use_container_width=True, config={"displayModeBar": False})

    with treasury_tab:
        maturity_columns = ["1 Mo", "2 Mo", "3 Mo", "4 Mo", "6 Mo", "1 Yr", "2 Yr", "3 Yr", "5 Yr", "7 Yr", "10 Yr", "20 Yr", "30 Yr"]
        curve_rows = [
            {"Maturity": column, "Yield (%)": safe_float(treasury.get(column))}
            for column in maturity_columns
            if safe_float(treasury.get(column)) is not None
        ]
        if curve_rows:
            curve_frame = pd.DataFrame(curve_rows)
            curve_figure = go.Figure(
                go.Scatter(
                    x=curve_frame["Maturity"],
                    y=curve_frame["Yield (%)"],
                    mode="lines+markers",
                    name="Treasury yield",
                    line={"color": theme["green"]},
                )
            )
            curve_figure.update_layout(
                height=350,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font={"color": theme["text"], "family": "Instrument Sans, sans-serif"},
                margin={"l": 10, "r": 10, "t": 20, "b": 10},
                xaxis={"gridcolor": theme["border"]},
                yaxis={"ticksuffix": "%", "gridcolor": theme["border"]},
            )
            st.plotly_chart(curve_figure, use_container_width=True, config={"displayModeBar": False})
            if treasury.get("Date") is not None:
                st.caption(f"Official U.S. Treasury curve date: {pd.Timestamp(treasury['Date']).strftime('%b %d, %Y')}")
        else:
            st.info("Official Treasury curve data is unavailable right now. It does not affect the heat score.")

    with sources_tab:
        st.markdown(
            """
- **Prices and adjusted returns:** Yahoo Finance via the open-source `yfinance` package. Critical index series are fetched independently, and SPY is a disclosed fallback for the technical signal. Data may be delayed; educational use only.
- **Equity put/call ratio:** Cboe Daily Market Statistics.
- **Treasury curve:** U.S. Department of the Treasury daily par yield curve.
- **Sector view:** the 11 Select Sector SPDR ETFs are investable proxies for S&P 500 sectors; their adjusted returns aren't identical to raw sector-index returns.

Headline sentiment and search trends are deliberately excluded from the core score. They're noisy, fail unpredictably, and made the score unstable from one refresh to the next.
"""
        )

st.markdown(
    """
<div class="footer">
Educational only — not financial advice. Built for long-term index investors deciding how to size <b>optional</b> extra cash. It never recommends selling, never changes an automatic plan, and never predicts the market's next move.
</div>
""",
    unsafe_allow_html=True,
)
