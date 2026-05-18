import os
import math
import time
from datetime import datetime
from zoneinfo import ZoneInfo

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

.command-grid {{
    display: grid;
    grid-template-columns: 1.15fr .85fr;
    gap: 18px;
    align-items: stretch;
    margin-bottom: 8px;
}}

.command-left, .command-right {{
    background: linear-gradient(180deg, {t["surface"]} 0%, {t["surface2"]} 100%);
    border: 1px solid {t["border"]};
    border-radius: 30px;
    box-shadow: {t["shadow"]};
    padding: 30px;
}}

.command-header {{
    display: flex;
    justify-content: space-between;
    gap: 18px;
    align-items: flex-start;
}}

.command-score {{
    text-align: right;
    min-width: 110px;
}}

.command-score-num {{
    font-size: 64px;
    line-height: .88;
    font-weight: 950;
    letter-spacing: -2.5px;
    color: {t["text"]};
}}

.command-score-label {{
    margin-top: 7px;
    color: {t["muted"]};
    font-size: 12px;
    font-weight: 900;
    text-transform: uppercase;
    letter-spacing: .6px;
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

.left-score-mini {{
    text-align: left !important;
    margin-top: 7px;
    margin-bottom: 28px;
}}

.heat-explainer {{
    margin-top: 24px;
    border-radius: 18px;
    padding: 14px 15px;
    background: {t["surface"]};
    border: 1px solid {t["border"]};
    color: {t["muted"]};
    font-size: 14px;
    line-height: 1.45;
}}

.hero-updated {{
    color: {t["muted"]};
    font-size: 13px;
    margin-top: 16px;
    font-weight: 700;
}}

@keyframes floatUp {{
    from {{ opacity: 0; transform: translateY(12px); }}
    to {{ opacity: 1; transform: translateY(0); }}
}}

@keyframes pulseMarker {{
    0% {{ box-shadow: 0 0 0 0 rgba(255,255,255,.22), 0 10px 26px rgba(0,0,0,.28); }}
    70% {{ box-shadow: 0 0 0 10px rgba(255,255,255,0), 0 10px 26px rgba(0,0,0,.28); }}
    100% {{ box-shadow: 0 0 0 0 rgba(255,255,255,0), 0 10px 26px rgba(0,0,0,.28); }}
}}

@keyframes shine {{
    0% {{ transform: translateX(-120%); }}
    100% {{ transform: translateX(220%); }}
}}

.hero, .card, .buy-tile {{
    animation: floatUp .55s ease both;
}}

.hero {{
    animation-delay: .05s;
}}

.card {{
    transition: transform .22s ease, border-color .22s ease, box-shadow .22s ease;
}}

.card:hover, .buy-tile:hover {{
    transform: translateY(-3px);
    border-color: {t["border2"]};
}}

.hero-meter-card {{
    overflow: hidden;
}}

.hero-meter-card .meter {{
    position: relative;
}}

.hero-meter-card .meter::after {{
    content: "";
    position: absolute;
    inset: 0;
    width: 34%;
    background: linear-gradient(90deg, rgba(255,255,255,0), rgba(255,255,255,.18), rgba(255,255,255,0));
    animation: shine 3.8s linear infinite;
}}

.hero-meter-card .marker {{
    animation: pulseMarker 2.4s ease-out infinite;
}}

.hero-sub {{
    font-size: 17px;
    line-height: 1.45;
    max-width: 900px;
}}

.today-summary {{
    padding: 8px 12px;
    font-size: 13px;
}}

.compact-action-card {{
    min-height: 210px;
}}

.compact-action {{
    font-size: 48px;
    margin-top: 10px;
}}

.compact-copy {{
    font-size: 22px;
    line-height: 1.3;
    max-width: 320px;
}}

.meter-subtitle {{
    font-size: 18px;
    line-height: 1.35;
    margin-top: 12px;
    margin-bottom: 28px;
}}

.meter-verdict {{
    margin-top: 26px;
}}

.meter-verdict-value {{
    font-size: 24px;
}}

.buy-tile {{
    transition: transform .2s ease, border-color .2s ease, box-shadow .2s ease;
}}

.buy-value {{
    font-size: 22px;
}}

.avoid-tile .buy-value {{
    font-size: 18px;
}}

@media (max-width: 900px) {{
    .big-heat-score {{ font-size: 78px; }}
    .meter-title {{ font-size: 36px; }}
    .meter-verdict {{ flex-direction: column; align-items: flex-start; }}
    .command-grid {{ grid-template-columns: 1fr; }}
    .command-header {{ flex-direction: column; }}
    .command-score {{ text-align: left; }}
    .decision-row {{ flex-direction: column; align-items: flex-start; }}
    .decision-value {{ text-align: left; }}
    .hero-title {{ font-size: 34px; }}
    .action-word {{ font-size: 43px; }}
    .score-number {{ font-size: 72px; }}
    .buy-plan {{ grid-template-columns: 1fr; }}
    .signal-row {{ grid-template-columns: 1fr; gap: 6px; }}
    .signal-do {{ text-align: left; }}
}}

.hero-meter-card {{
    min-height: 410px;
    padding: 34px;
    background:
        radial-gradient(circle at 100% 0%, rgba(239,68,68,.12), transparent 38%),
        linear-gradient(180deg, {t["surface"]} 0%, {t["surface2"]} 100%);
}}

.meter-head {{
    display: flex;
    justify-content: space-between;
    gap: 20px;
    align-items: flex-start;
}}

.meter-title {{
    color: {t["text"]};
    font-size: 44px;
    font-weight: 950;
    letter-spacing: -1.5px;
    margin-top: 8px;
}}

.big-heat-score {{
    color: {t["text"]};
    font-size: 104px;
    line-height: .82;
    font-weight: 950;
    letter-spacing: -5px;
}}

.meter-subtitle {{
    color: {t["muted"]};
    font-size: 16px;
    line-height: 1.45;
    margin-top: 18px;
    margin-bottom: 34px;
    max-width: 560px;
}}

.hero-meter-card .meter {{
    height: 24px;
}}

.hero-meter-card .marker {{
    width: 26px;
    height: 26px;
    margin-top: -25px;
    border-width: 5px;
}}

.hero-meter-card .scale {{
    font-size: 13px;
    margin-top: 14px;
}}

.meter-verdict {{
    margin-top: 32px;
    border-radius: 22px;
    padding: 18px 20px;
    background: {t["red_bg"]};
    border: 1px solid rgba(239,68,68,.18);
    display: flex;
    justify-content: space-between;
    gap: 18px;
    align-items: center;
}}

.meter-verdict-label {{
    color: {t["muted"]};
    font-size: 12px;
    font-weight: 900;
    text-transform: uppercase;
    letter-spacing: .7px;
}}

.meter-verdict-value {{
    color: {t["red"]};
    font-size: 26px;
    font-weight: 950;
    letter-spacing: -.7px;
}}

.compact-action-card {{
    min-height: 235px;
}}

.compact-action {{
    font-size: 46px;
}}

.avoid-tile {{
    margin-top: 12px;
}}


/* ============================================================
   Ultra-modern motion layer
   ============================================================ */

@keyframes auroraMove {{
    0% {{ transform: translate3d(-4%, -3%, 0) scale(1); opacity: .58; }}
    35% {{ transform: translate3d(5%, 2%, 0) scale(1.08); opacity: .85; }}
    70% {{ transform: translate3d(2%, 6%, 0) scale(.98); opacity: .7; }}
    100% {{ transform: translate3d(-4%, -3%, 0) scale(1); opacity: .58; }}
}}

@keyframes heroGlow {{
    0%, 100% {{ box-shadow: 0 24px 70px rgba(15,23,42,.08), inset 0 0 0 rgba(96,165,250,0); }}
    50% {{ box-shadow: 0 32px 90px rgba(37,99,235,.20), inset 0 0 48px rgba(96,165,250,.08); }}
}}

@keyframes cardRise {{
    0% {{ opacity: 0; transform: translateY(22px) scale(.985); filter: blur(5px); }}
    100% {{ opacity: 1; transform: translateY(0) scale(1); filter: blur(0); }}
}}

@keyframes scorePop {{
    0% {{ opacity: 0; transform: translateY(14px) scale(.82); filter: blur(3px); }}
    60% {{ opacity: 1; transform: translateY(-4px) scale(1.04); filter: blur(0); }}
    100% {{ transform: translateY(0) scale(1); }}
}}

@keyframes meterSweep {{
    0% {{ transform: translateX(-130%); opacity: 0; }}
    12% {{ opacity: .95; }}
    60% {{ opacity: .9; }}
    100% {{ transform: translateX(260%); opacity: 0; }}
}}

@keyframes markerPulseHeavy {{
    0% {{
        transform: scale(1);
        box-shadow:
            0 0 0 0 rgba(255,255,255,.34),
            0 0 0 0 rgba(251,113,133,.26),
            0 12px 30px rgba(0,0,0,.35);
    }}
    45% {{
        transform: scale(1.08);
        box-shadow:
            0 0 0 10px rgba(255,255,255,0),
            0 0 0 20px rgba(251,113,133,.08),
            0 18px 42px rgba(0,0,0,.42);
    }}
    100% {{
        transform: scale(1);
        box-shadow:
            0 0 0 0 rgba(255,255,255,0),
            0 0 0 0 rgba(251,113,133,0),
            0 12px 30px rgba(0,0,0,.35);
    }}
}}

@keyframes verdictGlow {{
    0%, 100% {{ transform: scale(1); box-shadow: 0 0 0 rgba(251,113,133,0); }}
    50% {{ transform: scale(1.012); box-shadow: 0 0 36px rgba(251,113,133,.22); }}
}}

@keyframes pillPulse {{
    0%, 100% {{ transform: scale(1); }}
    50% {{ transform: scale(1.025); }}
}}

@keyframes subtleDrift {{
    0%, 100% {{ transform: translateY(0); }}
    50% {{ transform: translateY(-5px); }}
}}

.stApp::before {{
    content: "";
    position: fixed;
    inset: -20%;
    pointer-events: none;
    z-index: 0;
    background:
        radial-gradient(circle at 20% 20%, rgba(96,165,250,.18), transparent 28%),
        radial-gradient(circle at 80% 10%, rgba(34,197,94,.13), transparent 26%),
        radial-gradient(circle at 60% 90%, rgba(251,113,133,.13), transparent 30%);
    filter: blur(24px);
    animation: auroraMove 13s ease-in-out infinite;
}}

.block-container {{
    position: relative;
    z-index: 1;
}}

.hero {{
    animation: cardRise .7s cubic-bezier(.2,.9,.2,1) both, heroGlow 5.5s ease-in-out infinite;
}}

.hero::after {{
    animation: auroraMove 9s ease-in-out infinite;
}}

.today-summary {{
    animation: pillPulse 2.6s ease-in-out infinite;
}}

.card, .buy-tile, .driver-card, .metric-card, .lens-card {{
    animation: cardRise .72s cubic-bezier(.2,.9,.2,1) both;
    will-change: transform;
}}

.card:nth-of-type(1) {{ animation-delay: .08s; }}
.card:nth-of-type(2) {{ animation-delay: .16s; }}

.hero-meter-card {{
    position: relative;
    animation-delay: .10s;
}}

.compact-action-card {{
    animation-delay: .18s;
}}

.big-heat-score {{
    animation: scorePop .85s cubic-bezier(.2,.9,.2,1) both, subtleDrift 4.2s ease-in-out infinite .9s;
}}

.meter-title {{
    animation: scorePop .8s cubic-bezier(.2,.9,.2,1) both;
}}

.hero-meter-card .meter {{
    position: relative;
    box-shadow: 0 0 28px rgba(251,113,133,.16);
}}

.hero-meter-card .meter::before {{
    content: "";
    position: absolute;
    inset: 0;
    width: 36%;
    background: linear-gradient(90deg, rgba(255,255,255,0), rgba(255,255,255,.36), rgba(255,255,255,0));
    animation: meterSweep 2.2s ease-in-out infinite;
}}

.hero-meter-card .meter::after {{
    content: "";
    position: absolute;
    inset: 0;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,.08), transparent);
    animation: meterSweep 4.8s linear infinite reverse;
}}

.hero-meter-card .marker {{
    animation: markerPulseHeavy 1.9s ease-out infinite;
    z-index: 2;
}}

.meter-verdict {{
    animation: verdictGlow 2.5s ease-in-out infinite;
}}

.meter-verdict-value {{
    text-shadow: 0 0 22px rgba(251,113,133,.32);
}}

.buy-tile {{
    animation-delay: .24s;
}}

.buy-tile:hover, .card:hover, .driver-card:hover, .metric-card:hover, .lens-card:hover {{
    transform: translateY(-7px) scale(1.012);
    box-shadow: 0 26px 70px rgba(0,0,0,.24);
}}

.action-word {{
    animation: scorePop .7s cubic-bezier(.2,.9,.2,1) both;
}}

@media (prefers-reduced-motion: reduce) {{
    *, *::before, *::after {{
        animation-duration: .001ms !important;
        animation-iteration-count: 1 !important;
        scroll-behavior: auto !important;
    }}
}}


/* ============================================================
   Premium animation pack: clear, simple, impressive
   ============================================================ */

@keyframes livePulse {{
    0% {{
        transform: scale(.95);
        box-shadow: 0 0 0 0 rgba(34,197,94,.55);
        opacity: .8;
    }}
    70% {{
        transform: scale(1.12);
        box-shadow: 0 0 0 9px rgba(34,197,94,0);
        opacity: 1;
    }}
    100% {{
        transform: scale(.95);
        box-shadow: 0 0 0 0 rgba(34,197,94,0);
        opacity: .85;
    }}
}}

@keyframes scoreRollIn {{
    0% {{
        opacity: 0;
        transform: translateY(18px) scale(.72) rotateX(34deg);
        filter: blur(7px);
    }}
    55% {{
        opacity: 1;
        transform: translateY(-5px) scale(1.08) rotateX(0deg);
        filter: blur(0);
    }}
    100% {{
        opacity: 1;
        transform: translateY(0) scale(1);
        filter: blur(0);
    }}
}}

@keyframes markerGlide {{
    0% {{
        left: calc(0% - 10px);
        transform: scale(.86);
    }}
    65% {{
        left: calc(var(--target-left) - 10px);
        transform: scale(1.14);
    }}
    100% {{
        left: calc(var(--target-left) - 10px);
        transform: scale(1);
    }}
}}

@keyframes heatZoneGlow {{
    0%, 100% {{
        opacity: .18;
        transform: scaleX(.96);
        filter: blur(10px);
    }}
    50% {{
        opacity: .42;
        transform: scaleX(1.02);
        filter: blur(16px);
    }}
}}

@keyframes signalStagger {{
    from {{
        opacity: 0;
        transform: translateY(18px) scale(.985);
        filter: blur(5px);
    }}
    to {{
        opacity: 1;
        transform: translateY(0) scale(1);
        filter: blur(0);
    }}
}}

@keyframes verdictSweep {{
    0% {{ transform: translateX(-130%); opacity: 0; }}
    18% {{ opacity: .75; }}
    55% {{ opacity: .55; }}
    100% {{ transform: translateX(250%); opacity: 0; }}
}}

.live-dot {{
    width: 9px;
    height: 9px;
    border-radius: 999px;
    background: {t["green"]};
    display: inline-block;
    margin-right: 2px;
    animation: livePulse 1.65s ease-out infinite;
}}

.score-count {{
    animation:
        scoreRollIn .9s cubic-bezier(.18,.9,.22,1) both,
        subtleDrift 4.2s ease-in-out infinite 1s;
    transform-origin: center;
}}

.hero-meter-card .marker {{
    animation:
        markerGlide 1.15s cubic-bezier(.16,.9,.2,1) both,
        markerPulseHeavy 1.9s ease-out infinite 1.2s;
}}

.hero-meter-card .meter {{
    isolation: isolate;
}}

.hero-meter-card .meter::before {{
    z-index: 2;
}}

.hero-meter-card .meter::after {{
    z-index: 1;
}}

.hero-meter-card::before {{
    content: "";
    position: absolute;
    right: 22px;
    top: 112px;
    width: 43%;
    height: 96px;
    border-radius: 999px;
    background: radial-gradient(circle, rgba(251,113,133,.42), rgba(251,113,133,.02) 67%, transparent 72%);
    pointer-events: none;
    animation: heatZoneGlow 2.8s ease-in-out infinite;
}}

.meter-verdict {{
    position: relative;
    overflow: hidden;
}}

.meter-verdict::after {{
    content: "";
    position: absolute;
    top: 0;
    bottom: 0;
    width: 34%;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,.18), transparent);
    animation: verdictSweep 3.1s ease-in-out infinite;
}}

.driver-card, .metric-card, .lens-card, .signal-row {{
    opacity: 0;
    animation: signalStagger .64s cubic-bezier(.2,.9,.2,1) both;
}}

.driver-card:nth-of-type(1), .metric-card:nth-of-type(1), .lens-card:nth-of-type(1), .signal-row:nth-of-type(1) {{
    animation-delay: .08s;
}}
.driver-card:nth-of-type(2), .metric-card:nth-of-type(2), .lens-card:nth-of-type(2), .signal-row:nth-of-type(2) {{
    animation-delay: .16s;
}}
.driver-card:nth-of-type(3), .metric-card:nth-of-type(3), .lens-card:nth-of-type(3), .signal-row:nth-of-type(3) {{
    animation-delay: .24s;
}}
.driver-card:nth-of-type(4), .metric-card:nth-of-type(4), .lens-card:nth-of-type(4), .signal-row:nth-of-type(4) {{
    animation-delay: .32s;
}}

@media (prefers-reduced-motion: reduce) {{
    .live-dot,
    .score-count,
    .hero-meter-card .marker,
    .hero-meter-card::before,
    .meter-verdict::after,
    .driver-card,
    .metric-card,
    .lens-card,
    .signal-row {{
        animation-duration: .001ms !important;
        animation-iteration-count: 1 !important;
    }}
}}


/* ============================================================
   Benchmark motion layer: scan → score → meter → decision → reasons
   ============================================================ */

@property --scoreNum {{
    syntax: "<integer>";
    initial-value: 0;
    inherits: false;
}}

@keyframes trueCountUp {{
    from {{ --scoreNum: 0; }}
    to {{ --scoreNum: var(--scoreTarget); }}
}}

@keyframes meterFill {{
    from {{ clip-path: inset(0 100% 0 0 round 999px); }}
    to {{ clip-path: inset(0 0 0 0 round 999px); }}
}}

@keyframes lockIn {{
    0% {{ opacity: 0; transform: translateY(16px) scale(.94); filter: blur(5px); }}
    55% {{ opacity: 1; transform: translateY(-3px) scale(1.035); filter: blur(0); }}
    100% {{ opacity: 1; transform: translateY(0) scale(1); }}
}}

@keyframes checkPulse {{
    0%, 100% {{ transform: scale(1); box-shadow: 0 0 0 0 rgba(34,197,94,.30); }}
    50% {{ transform: scale(1.08); box-shadow: 0 0 0 9px rgba(34,197,94,0); }}
}}

@keyframes dotReveal {{
    from {{ opacity: 0; transform: translateY(8px) scale(.82); }}
    to {{ opacity: 1; transform: translateY(0) scale(1); }}
}}

@keyframes dotPulse {{
    0%, 100% {{ transform: scale(1); opacity: .82; }}
    50% {{ transform: scale(1.18); opacity: 1; }}
}}

@keyframes scanLine {{
    0% {{ transform: translateX(-120%); opacity: 0; }}
    12% {{ opacity: 1; }}
    85% {{ opacity: .8; }}
    100% {{ transform: translateX(130%); opacity: 0; }}
}}

@keyframes scanProgress {{
    from {{ width: 0%; }}
    to {{ width: 100%; }}
}}

@keyframes chartReveal {{
    from {{ opacity: 0; transform: translateY(18px) scale(.99); filter: blur(6px); }}
    to {{ opacity: 1; transform: translateY(0) scale(1); filter: blur(0); }}
}}

@keyframes magneticGlow {{
    0%, 100% {{ background-position: 0% 50%; }}
    50% {{ background-position: 100% 50%; }}
}}

.scan-shell {{
    position: relative;
    overflow: hidden;
    border-radius: 28px;
    border: 1px solid {t["border"]};
    background:
        radial-gradient(circle at 20% 20%, rgba(96,165,250,.16), transparent 32%),
        radial-gradient(circle at 85% 15%, rgba(34,197,94,.12), transparent 30%),
        linear-gradient(180deg, {t["surface"]}, {t["surface2"]});
    box-shadow: {t["shadow"]};
    padding: 26px 28px;
    margin: 8px 0 18px;
}}

.scan-shell::after {{
    content: "";
    position: absolute;
    inset: 0;
    width: 38%;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,.13), transparent);
    animation: scanLine 1.25s ease-in-out infinite;
}}

.scan-title {{
    color: {t["text"]};
    font-size: 23px;
    font-weight: 950;
    letter-spacing: -.5px;
}}

.scan-steps {{
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
    margin-top: 14px;
}}

.scan-chip {{
    border-radius: 999px;
    padding: 8px 11px;
    color: {t["muted"]};
    background: {t["surface"]};
    border: 1px solid {t["border"]};
    font-size: 12px;
    font-weight: 850;
    animation: dotReveal .55s ease both;
}}

.scan-chip:nth-child(1) {{ animation-delay: .04s; }}
.scan-chip:nth-child(2) {{ animation-delay: .18s; }}
.scan-chip:nth-child(3) {{ animation-delay: .32s; }}
.scan-chip:nth-child(4) {{ animation-delay: .46s; }}

.scan-bar {{
    height: 8px;
    border-radius: 999px;
    background: {t["surface3"]};
    margin-top: 18px;
    overflow: hidden;
}}

.scan-fill {{
    height: 100%;
    border-radius: 999px;
    background: linear-gradient(90deg, {t["green"]}, {t["yellow"]}, {t["red"]});
    animation: scanProgress 1.05s cubic-bezier(.2,.8,.2,1) both;
}}

.score-count {{
    color: transparent !important;
    position: relative;
    --scoreNum: 0;
    animation:
        trueCountUp 1.15s cubic-bezier(.16,.9,.2,1) forwards,
        subtleDrift 4.2s ease-in-out infinite 1.2s !important;
}}

.score-count::after {{
    content: counter(scoreCounter);
    counter-reset: scoreCounter var(--scoreNum);
    color: {t["text"]};
    position: absolute;
    inset: 0;
}}

.hero-meter-card .meter {{
    animation: meterFill 1.05s cubic-bezier(.16,.9,.2,1) both;
    transform-origin: left center;
}}

.signal-dots {{
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 9px;
    margin-top: 22px;
}}

.signal-dot-card {{
    border: 1px solid {t["border"]};
    background: rgba(255,255,255,.035);
    border-radius: 17px;
    padding: 10px 9px;
    display: flex;
    align-items: center;
    gap: 8px;
    min-width: 0;
    opacity: 0;
    animation: dotReveal .52s cubic-bezier(.2,.9,.2,1) both;
}}

.signal-dot-card:nth-child(1) {{ animation-delay: .05s; }}
.signal-dot-card:nth-child(2) {{ animation-delay: .10s; }}
.signal-dot-card:nth-child(3) {{ animation-delay: .15s; }}
.signal-dot-card:nth-child(4) {{ animation-delay: .20s; }}
.signal-dot-card:nth-child(5) {{ animation-delay: .25s; }}
</style>
""", unsafe_allow_html=True)

# ============================================================
# Main Application Content Logic Wrapper Example
# ============================================================
# Setting up theme and styles
theme = current_theme()
inject_css(theme)

# Get current time localized cleanly to PST/PDT zone
pst_zone = ZoneInfo("America/Los_Angeles")
pst_now = datetime.now(pst_zone)
formatted_time = pst_now.strftime("%b %d, %Y %I:%M %p")

# Rendering hero block safely with target timezone format string
st.markdown(f"""
<div class="hero">
    <div class="hero-title">📈 Should I Buy Today?</div>
    <div class="hero-sub">Real-time systemic marketplace heat mapping and modern automated entry point analysis.</div>
    <div class="hero-updated">Updated {formatted_time} PST</div>
</div>
""", unsafe_allow_html=True)
