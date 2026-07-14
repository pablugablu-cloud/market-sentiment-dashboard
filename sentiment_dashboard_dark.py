"""
Should I Buy Today? — an immersive market weather report for long-term index investors.

Design principles
-----------------
1. One plain-English answer first. Everything else is optional depth.
2. Weather language everywhere: Cold / Cool / Mild / Warm / Hot.
3. Progressive disclosure: Signal -> Evidence -> Explore -> Audit.
4. The audited score model, data fallbacks, and disclaimers remain unchanged.
5. The presentation is bright, grid-led, kinetic, and intentionally easy to scan.
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
    page_icon="◉",
    layout="wide",
    initial_sidebar_state="collapsed",
)

PACIFIC = ZoneInfo("America/Los_Angeles")
NOW_PT = datetime.now(PACIFIC)

# ============================================================
# Visual system — bright by default, optional dark mode
# ============================================================
LIGHT = {
    "color_scheme": "light",
    "bg": "#EEF1EF",
    "surface": "#F8FAF8",
    "surface2": "#FFFFFF",
    "surface3": "#E6EBE7",
    "text": "#070908",
    "muted": "#4E5752",
    "muted2": "#747D78",
    "border": "#CBD3CE",
    "border2": "#9DAAA3",
    "grid": "rgba(7,20,12,.075)",
    "green": "#008A2E",
    "green2": "#13B84A",
    "green_bg": "rgba(0,138,46,.10)",
    "lime": "#C9F24F",
    "lime_bg": "rgba(201,242,79,.24)",
    "violet": "#6847E8",
    "violet_bg": "rgba(104,71,232,.10)",
    "cyan": "#00A7B7",
    "cyan_bg": "rgba(0,167,183,.10)",
    "blue": "#2864E8",
    "blue_bg": "rgba(40,100,232,.10)",
    "amber": "#B58F00",
    "amber_bg": "rgba(181,143,0,.11)",
    "coral": "#E3552F",
    "coral_bg": "rgba(227,85,47,.10)",
    "pink": "#E7439C",
    "orange": "#D96620",
    "shadow": "0 24px 70px rgba(20,34,25,.12)",
    "button_hover": "#006F25",
    "on_accent": "#FFFFFF",
    "hero_rule_bg": "rgba(255,255,255,.75)",
    "orb_highlight": "rgba(255,255,255,.70)",
    "console_bg": "linear-gradient(135deg, rgba(104,71,232,.11), rgba(255,255,255,.95) 38%, rgba(0,138,46,.07))",
    "marker_ring": "rgba(255,255,255,.74)",
    "soft_shadow": "rgba(7,9,8,.055)",
    "soft_shadow_hover": "rgba(7,9,8,.08)",
    "neutral_pill": "rgba(7,9,8,.06)",
    "signal_viz_bg": "rgba(255,255,255,.45)",
    "action1": "#E7F4CC",
    "action2": "#E7E4FF",
    "action3": "#F7DCD0",
    "signal1": "#EDF7DF",
    "signal2": "#E9F3FF",
    "signal3": "#F0EBFF",
    "signal4": "#FCEDE5",
    "summary1": "#E7F4CC",
    "summary2": "#F7DCD0",
    "summary3": "#E7E4FF",
    "tape1": "#E7F4CC",
    "tape2": "#171426",
    "tape3": "#D8C9FF",
    "tape4": "#F3A9C7",
    "tape5": "#E9A06F",
    "fear_end": "#57E7A1",
    "normal_start": "#55D7E5",
}

DARK = {
    "color_scheme": "dark",
    "bg": "#0D1117",
    "surface": "#11161D",
    "surface2": "#151B23",
    "surface3": "#1B222C",
    "text": "#F4F7F5",
    "muted": "#A7B0AB",
    "muted2": "#7F8A84",
    "border": "#303A34",
    "border2": "#56635B",
    "grid": "rgba(255,255,255,.055)",
    "green": "#3FB950",
    "green2": "#56D364",
    "green_bg": "rgba(63,185,80,.13)",
    "lime": "#B7F34B",
    "lime_bg": "rgba(183,243,75,.14)",
    "violet": "#A78BFA",
    "violet_bg": "rgba(167,139,250,.14)",
    "cyan": "#39C5CF",
    "cyan_bg": "rgba(57,197,207,.13)",
    "blue": "#58A6FF",
    "blue_bg": "rgba(88,166,255,.13)",
    "amber": "#DDBD43",
    "amber_bg": "rgba(221,189,67,.13)",
    "coral": "#FF7B72",
    "coral_bg": "rgba(255,123,114,.13)",
    "pink": "#F778BA",
    "orange": "#FFA657",
    "shadow": "0 24px 70px rgba(0,0,0,.40)",
    "button_hover": "#2EA043",
    "on_accent": "#FFFFFF",
    "hero_rule_bg": "rgba(21,27,35,.88)",
    "orb_highlight": "rgba(255,255,255,.16)",
    "console_bg": "linear-gradient(135deg, rgba(167,139,250,.18), rgba(21,27,35,.96) 40%, rgba(63,185,80,.11))",
    "marker_ring": "rgba(13,17,23,.82)",
    "soft_shadow": "rgba(0,0,0,.24)",
    "soft_shadow_hover": "rgba(0,0,0,.36)",
    "neutral_pill": "rgba(255,255,255,.07)",
    "signal_viz_bg": "rgba(255,255,255,.035)",
    "action1": "#17251A",
    "action2": "#1C1A32",
    "action3": "#2A1D18",
    "signal1": "#15231A",
    "signal2": "#142231",
    "signal3": "#211B35",
    "signal4": "#2B1D19",
    "summary1": "#17251A",
    "summary2": "#2A1D18",
    "summary3": "#1C1A32",
    "tape1": "#17251A",
    "tape2": "#080B10",
    "tape3": "#241E39",
    "tape4": "#35202D",
    "tape5": "#342217",
    "fear_end": "#57E7A1",
    "normal_start": "#55D7E5",
}

if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = False


def current_theme():
    return DARK if st.session_state.dark_mode else LIGHT


def inject_css(t):
    st.markdown(
        f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&family=Space+Grotesk:wght@400;500;600;700&display=swap');

:root {{ color-scheme: {t['color_scheme']}; }}
* {{ box-sizing: border-box; }}
html {{ scroll-behavior: smooth; }}
html, body, [class*="css"], .stApp, .stMarkdown, p, span, div, label {{
    font-family: "DM Sans", ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}}
body {{ background: {t['bg']}; }}
.stApp {{
    color: {t['text']};
    background:
        linear-gradient({t['grid']} 1px, transparent 1px),
        linear-gradient(90deg, {t['grid']} 1px, transparent 1px),
        {t['bg']};
    background-size: 86px 86px;
}}
[data-testid="stHeader"] {{ background: transparent; }}
[data-testid="stToolbar"], [data-testid="stDecoration"], #MainMenu, footer {{ display: none; }}
.block-container {{ max-width: 1380px; padding: 0.6rem 2.2rem 5rem; }}

/* Streamlit controls */
div[data-testid="stButton"] button {{
    min-height: 44px;
    border: 1px solid {t['green']};
    border-radius: 2px;
    background: {t['green']};
    color: {t['on_accent']};
    font-family: "Space Grotesk", sans-serif;
    font-weight: 650;
    letter-spacing: -.01em;
    box-shadow: none;
    transition: transform .18s ease, background .18s ease, box-shadow .18s ease;
}}
div[data-testid="stButton"] button:hover {{
    transform: translateY(-2px);
    background: {t['button_hover']};
    color: {t['on_accent']};
    box-shadow: 0 10px 24px rgba(0,138,46,.18);
}}
div[data-testid="stButton"] button:focus-visible {{ outline: 3px solid {t['lime']}; outline-offset: 3px; }}

/* Native, always-visible theme switch beside Refresh */
.st-key-dark_mode {{
    min-height: 62px;
    display: flex;
    align-items: center;
    padding: 0 14px;
    border: 1px solid {t['border']};
    border-bottom: 0;
    background: {t['surface3']};
}}
.st-key-dark_mode [data-testid="stToggle"] {{
    width: 100%;
    margin: 0;
}}
.st-key-dark_mode label {{
    width: 100%;
    justify-content: space-between;
    gap: 10px;
}}
.st-key-dark_mode label p {{
    color: {t['text']} !important;
    font-family: "IBM Plex Mono", monospace !important;
    font-size: 9px !important;
    font-weight: 700 !important;
    letter-spacing: .08em;
    text-transform: uppercase;
    white-space: nowrap;
}}
.st-key-refresh_market button {{
    min-height: 62px !important;
    border-bottom: 0 !important;
}}

.stTabs [data-baseweb="tab-list"] {{
    gap: 0;
    padding: 0;
    border: 1px solid {t['border']};
    border-radius: 0;
    background: {t['surface2']};
    width: fit-content;
}}
.stTabs [data-baseweb="tab"] {{
    height: 44px;
    border-radius: 0;
    border-right: 1px solid {t['border']};
    padding: 0 18px;
    color: {t['muted']};
    font-family: "Space Grotesk", sans-serif;
    font-weight: 600;
}}
.stTabs [data-baseweb="tab"]:last-child {{ border-right: 0; }}
.stTabs [aria-selected="true"] {{ color: #FFFFFF !important; background: {t['green']} !important; }}
.stTabs [data-baseweb="tab-border"] {{ display: none; }}

div[role="radiogroup"] {{ gap: 7px; flex-wrap: wrap; margin: 12px 0 18px; }}
div[role="radiogroup"] label {{
    border: 1px solid {t['border']};
    border-radius: 999px;
    background: {t['surface2']};
    padding: 5px 11px;
    transition: border-color .18s ease, background .18s ease, transform .18s ease;
}}
div[role="radiogroup"] label:hover {{ transform: translateY(-1px); border-color: {t['green']}; }}
div[role="radiogroup"] label:has(input:checked) {{ background: {t['text']}; color: {t['on_accent']}; border-color: {t['text']}; }}
[data-testid="stExpander"] {{
    border: 1px solid {t['border']} !important;
    border-radius: 0 !important;
    background: {t['surface2']} !important;
    overflow: hidden;
}}
[data-testid="stExpander"] summary {{ font-family: "Space Grotesk", sans-serif; font-weight: 600; }}
[data-testid="stDataFrame"] {{ border: 1px solid {t['border']}; border-radius: 0; overflow: hidden; }}
[data-testid="stPlotlyChart"] {{ margin-top: 10px; padding: 12px; border: 1px solid {t['border']}; border-radius: 0; background: {t['surface2']}; overflow: hidden; }}

/* Top rail */
.top-rail {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 18px;
    min-height: 62px;
    border: 1px solid {t['border']};
    border-bottom: 0;
    background: {t['surface3']};
    padding: 0 18px;
}}
.brand {{ display: flex; align-items: center; gap: 11px; min-width: 0; }}
.brand-mark {{
    width: 25px; height: 25px; border-radius: 50%;
    background: conic-gradient(from 180deg, {t['green']}, {t['lime']}, {t['blue']}, {t['pink']}, {t['green']});
    border: 3px solid {t['text']};
    animation: spinSlow 14s linear infinite;
}}
.brand-name {{ font-family: "Space Grotesk", sans-serif; font-weight: 700; font-size: 14px; letter-spacing: -.02em; }}
.brand-slash {{ color: {t['muted2']}; font-family: "IBM Plex Mono", monospace; font-size: 10px; }}
.top-status {{ display: flex; flex-wrap: wrap; justify-content: flex-end; gap: 0; }}
.micro-pill {{
    display: inline-flex; align-items: center; gap: 7px;
    min-height: 34px; padding: 0 10px;
    border-left: 1px solid {t['border']};
    color: {t['muted']};
    background: transparent;
    font-family: "IBM Plex Mono", monospace;
    font-size: 9px;
    white-space: nowrap;
}}
.live-dot {{ width: 7px; height: 7px; border-radius: 50%; background: {t['green']}; box-shadow: 0 0 0 4px rgba(0,138,46,.10); animation: livePulse 2.2s ease-in-out infinite; }}

/* Hero */
.hero {{
    --weather-a: {t['violet']};
    --weather-b: {t['green']};
    position: relative;
    min-height: 650px;
    overflow: hidden;
    isolation: isolate;
    border: 1px solid {t['border']};
    border-radius: 0;
    background: {t['surface2']};
    box-shadow: {t['shadow']};
}}
.hero::before {{
    content: "";
    position: absolute; inset: 0;
    background-image:
        linear-gradient({t['grid']} 1px, transparent 1px),
        linear-gradient(90deg, {t['grid']} 1px, transparent 1px);
    background-size: 54px 54px;
    pointer-events: none;
}}
.hero::after {{
    content: "";
    position: absolute;
    width: 620px; height: 620px;
    right: -170px; top: -260px;
    border-radius: 50%;
    background:
        radial-gradient(circle at 36% 35%, {t['orb_highlight']}, transparent 14%),
        radial-gradient(circle at 42% 42%, var(--weather-b), var(--weather-a) 46%, transparent 72%);
    filter: blur(4px);
    opacity: .22;
    animation: orbFloat 12s ease-in-out infinite;
    pointer-events: none;
}}
.hero-noise {{
    position: absolute; inset: 0; opacity: .035; pointer-events: none;
    background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 180 180' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='.55'/%3E%3C/svg%3E");
}}
.hero-inner {{
    position: relative; z-index: 2;
    display: grid;
    grid-template-columns: minmax(0, 1.18fr) minmax(420px, .82fr);
    gap: 44px;
    min-height: 650px;
    padding: 54px 54px 42px;
}}
.hero-copy {{ align-self: center; }}
.hero-kicker {{
    display: flex; align-items: center; gap: 12px;
    color: {t['muted']};
    font-family: "IBM Plex Mono", monospace;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: .13em;
}}
.hero-kicker::before {{ content: ""; width: 46px; height: 2px; background: {t['green']}; }}
.hero-title {{
    margin-top: 27px;
    font-family: "Space Grotesk", sans-serif;
    font-size: clamp(68px, 8.6vw, 132px);
    font-weight: 650;
    line-height: .83;
    letter-spacing: -.078em;
    text-transform: uppercase;
    max-width: 830px;
}}
.hero-title .line {{ display: block; animation: titleUp .8s cubic-bezier(.16,1,.3,1) both; }}
.hero-title .line:nth-child(2) {{ animation-delay: .08s; }}
.hero-title .gradient-word {{
    color: transparent;
    background: linear-gradient(90deg, {t['green']} 0%, {t['cyan']} 44%, {t['blue']} 72%, {t['violet']} 100%);
    -webkit-background-clip: text;
    background-clip: text;
    background-size: 165% 100%;
    animation: titleUp .8s cubic-bezier(.16,1,.3,1) .08s both, gradientTravel 7s ease-in-out infinite alternate;
}}
.hero-description {{
    max-width: 660px;
    margin-top: 30px;
    color: {t['muted']};
    font-size: clamp(16px, 1.6vw, 21px);
    line-height: 1.48;
    letter-spacing: -.018em;
    animation: fadeRise .75s ease .24s both;
}}
.hero-rule {{
    display: inline-flex; align-items: center; gap: 11px;
    margin-top: 25px;
    padding: 12px 14px;
    border: 1px solid {t['border']};
    background: {t['hero_rule_bg']};
    color: {t['text']};
    font-size: 13px;
    font-weight: 650;
    animation: fadeRise .75s ease .34s both;
}}
.rule-icon {{
    display: grid; place-items: center;
    flex: 0 0 auto;
    width: 26px; height: 26px;
    border-radius: 50%;
    color: {t['text']};
    background: {t['lime']};
    border: 1px solid {t['text']};
}}

/* Score console — three-stage horizontal heat bar */
.score-console {{
    align-self: center;
    position: relative;
    min-height: 440px;
    padding: 28px;
    border: 1px solid {t['border2']};
    border-radius: 0;
    background: {t['console_bg']};
    box-shadow: 14px 14px 0 {t['lime']};
    animation: consoleIn .9s cubic-bezier(.16,1,.3,1) .18s both;
}}
.score-console::before {{
    content: ""; position: absolute; left: -1px; top: -1px; right: -1px; height: 7px;
    background: linear-gradient(90deg, {t['green']} 0 35%, {t['blue']} 35% 65%, {t['pink']} 65% 100%);
}}
.console-top {{ display: flex; justify-content: space-between; align-items: center; gap: 12px; }}
.console-label {{ color: {t['cyan']}; font-family: "IBM Plex Mono", monospace; font-size: 10px; letter-spacing: .12em; text-transform: uppercase; font-weight: 600; }}
.weather-chip {{
    padding: 7px 11px; border-radius: 999px;
    color: {t['text']}; background: {t['lime']};
    border: 1px solid {t['text']};
    font-family: "IBM Plex Mono", monospace; font-size: 9px; font-weight: 700; text-transform: uppercase;
}}
.heat-summary {{ display: grid; grid-template-columns: auto 1fr; align-items: end; gap: 24px; margin-top: 38px; }}
.score-number {{
    color: {t['text']};
    font-family: "Space Grotesk", sans-serif;
    font-size: clamp(82px, 8vw, 116px);
    font-weight: 560; line-height: .78; letter-spacing: -.085em;
    animation: scoreReveal .85s cubic-bezier(.16,1,.3,1) .55s both;
}}
.score-stage {{ color: var(--weather-a); font-family: "Space Grotesk", sans-serif; font-size: clamp(24px, 2.3vw, 34px); font-weight: 650; line-height: 1; letter-spacing: -.045em; }}
.score-denom {{ color: {t['muted2']}; font-family: "IBM Plex Mono", monospace; font-size: 10px; margin-top: 10px; letter-spacing: .10em; }}
.heat-bar-wrap {{ margin-top: 46px; }}
.heat-track {{
    --score: 50;
    position: relative;
    display: grid;
    grid-template-columns: 35fr 30fr 35fr;
    height: 14px;
    border: 1px solid {t['text']};
    background: {t['surface2']};
}}
.heat-zone {{ min-width: 0; }}
.heat-zone.fear {{ background: linear-gradient(90deg, {t['lime']}, {t['fear_end']}); }}
.heat-zone.normal {{ background: linear-gradient(90deg, {t['normal_start']}, {t['blue']}); border-left: 3px solid {t['surface2']}; border-right: 3px solid {t['surface2']}; }}
.heat-zone.stretched {{ background: linear-gradient(90deg, {t['violet']}, {t['pink']}, {t['coral']}); }}
.heat-marker {{
    position: absolute;
    z-index: 3;
    left: calc(var(--score) * 1%);
    top: 50%;
    width: 4px;
    height: 31px;
    transform: translate(-50%, -50%);
    background: {t['text']};
    box-shadow: 0 0 0 4px {t['marker_ring']};
    animation: markerSlide .9s cubic-bezier(.16,1,.3,1) .45s both;
}}
.heat-marker::before {{
    content: attr(data-score);
    position: absolute;
    left: 50%; bottom: 31px;
    transform: translateX(-50%);
    min-width: 38px;
    padding: 5px 7px;
    border-radius: 999px;
    background: {t['text']};
    color: {t['on_accent']};
    text-align: center;
    font-family: "IBM Plex Mono", monospace;
    font-size: 10px;
    font-weight: 700;
}}
.heat-ticks {{ display: flex; justify-content: space-between; margin-top: 10px; color: {t['muted2']}; font-family: "IBM Plex Mono", monospace; font-size: 9px; }}
.heat-labels {{ display: grid; grid-template-columns: 35fr 30fr 35fr; gap: 15px; margin-top: 18px; }}
.heat-label {{ min-width: 0; }}
.heat-label:nth-child(2) {{ text-align: center; }}
.heat-label:nth-child(3) {{ text-align: right; }}
.heat-label b {{ display: block; font-family: "Space Grotesk", sans-serif; font-size: 14px; letter-spacing: -.02em; }}
.heat-label span {{ display: block; margin-top: 5px; color: {t['muted']}; font-size: 10px; line-height: 1.35; }}
.heat-label.fear b {{ color: {t['green']}; }}
.heat-label.normal b {{ color: {t['blue']}; }}
.heat-label.stretched b {{ color: {t['pink']}; }}
.console-meta {{
    display: flex; justify-content: space-between; gap: 16px;
    margin-top: 24px; padding-top: 15px;
    border-top: 1px solid {t['border']};
    color: {t['muted']}; font-family: "IBM Plex Mono", monospace; font-size: 9px;
}}

/* Action strip */
.action-strip {{
    position: relative; z-index: 3;
    display: grid; grid-template-columns: 1.1fr 1fr 1fr;
    border-top: 1px solid {t['border']};
    background: {t['surface2']};
}}
.action-cell {{
    position: relative;
    padding: 25px 28px;
    border-right: 1px solid {t['border']};
    min-height: 138px;
    transition: transform .2s ease, filter .2s ease;
}}
.action-cell:nth-child(1) {{ background: {t['action1']}; }}
.action-cell:nth-child(2) {{ background: {t['action2']}; }}
.action-cell:nth-child(3) {{ background: {t['action3']}; }}
.action-cell:last-child {{ border-right: 0; }}
.action-cell:hover {{ transform: translateY(-4px); filter: saturate(1.06); z-index: 2; }}
.action-index {{ color: {t['green']}; font-family: "IBM Plex Mono", monospace; font-size: 10px; font-weight: 600; }}
.action-cell:nth-child(2) .action-index {{ color: {t['violet']}; }}
.action-cell:nth-child(3) .action-index {{ color: {t['orange']}; }}
.action-label {{ margin-top: 9px; color: {t['muted']}; font-size: 10px; text-transform: uppercase; letter-spacing: .10em; }}
.action-value {{ margin-top: 8px; color: {t['text']}; font-family: "Space Grotesk", sans-serif; font-size: 19px; font-weight: 650; line-height: 1.22; letter-spacing: -.028em; }}
.action-help {{ margin-top: 7px; color: {t['muted']}; font-size: 11px; line-height: 1.4; }}

/* Moving tape */
.tape-shell {{
    overflow: hidden; margin: 22px 0 0;
    border-top: 1px solid {t['border']}; border-bottom: 1px solid {t['border']};
    background: {t['surface2']};
    mask-image: linear-gradient(90deg, transparent, #000 4%, #000 96%, transparent);
}}
.tape {{ display: flex; width: max-content; animation: tickerMove 34s linear infinite; }}
.tape:hover {{ animation-play-state: paused; }}
.tape-item {{
    display: inline-flex; align-items: center; gap: 9px; padding: 11px 19px;
    border-right: 1px solid {t['border']};
    color: {t['muted']}; font-family: "IBM Plex Mono", monospace; font-size: 10px; white-space: nowrap;
}}
.tape-item:nth-child(5n+1) {{ background: {t['tape1']}; }}
.tape-item:nth-child(5n+2) {{ background: {t['tape2']}; color: {t['on_accent']}; }}
.tape-item:nth-child(5n+3) {{ background: {t['tape3']}; }}
.tape-item:nth-child(5n+4) {{ background: {t['tape4']}; }}
.tape-item:nth-child(5n+5) {{ background: {t['tape5']}; }}
.tape-item:nth-child(5n+2) .tape-ticker {{ color: {t['on_accent']}; }}
.tape-ticker {{ color: {t['text']}; font-weight: 700; }}
.tape-sep {{ color: {t['muted2']}; }}

/* Section typography */
.section-head {{
    display: grid; grid-template-columns: 160px minmax(0, 1fr); gap: 34px;
    align-items: start; margin: 94px 0 26px;
}}
.section-kicker {{ color: {t['green']}; font-family: "IBM Plex Mono", monospace; font-size: 10px; letter-spacing: .13em; text-transform: uppercase; padding-top: 9px; font-weight: 600; }}
.section-title {{
    color: {t['text']}; font-family: "Space Grotesk", sans-serif;
    font-size: clamp(38px, 5.2vw, 70px); font-weight: 570; line-height: .98; letter-spacing: -.055em;
    max-width: 900px;
}}
.section-copy {{ color: {t['muted']}; font-size: 15px; line-height: 1.6; max-width: 760px; margin-top: 16px; }}

/* Signal bento */
.signal-grid {{ display: grid; grid-template-columns: repeat(12, 1fr); gap: 14px; }}
.signal-card {{
    position: relative; overflow: hidden; min-height: 270px; padding: 25px;
    border: 1px solid {t['border']}; border-radius: 0;
    background: {t['surface2']};
    box-shadow: 8px 8px 0 {t['soft_shadow']};
    transition: transform .25s ease, border-color .25s ease, box-shadow .25s ease;
}}
.signal-card:nth-child(1) {{ grid-column: span 5; background: {t['signal1']}; }}
.signal-card:nth-child(2) {{ grid-column: span 7; background: {t['signal2']}; }}
.signal-card:nth-child(3) {{ grid-column: span 7; background: {t['signal3']}; }}
.signal-card:nth-child(4) {{ grid-column: span 5; background: {t['signal4']}; }}
.signal-card:hover {{ transform: translateY(-5px); border-color: {t['border2']}; box-shadow: 12px 12px 0 {t['soft_shadow_hover']}; }}
.signal-card::after {{ content: ""; position: absolute; width: 220px; height: 220px; right: -110px; bottom: -130px; border-radius: 50%; background: var(--signal-color); filter: blur(70px); opacity: .12; }}
.signal-number {{ color: {t['muted2']}; font-family: "IBM Plex Mono", monospace; font-size: 10px; }}
.signal-question {{ margin-top: 35px; color: {t['muted']}; font-size: 13px; }}
.signal-answer {{ margin-top: 9px; color: {t['text']}; font-family: "Space Grotesk", sans-serif; font-size: clamp(29px, 3vw, 43px); font-weight: 620; line-height: 1; letter-spacing: -.045em; }}
.signal-reading {{ margin-top: 13px; color: var(--signal-color); font-family: "IBM Plex Mono", monospace; font-size: 11px; font-weight: 600; }}
.signal-copy {{ margin-top: 18px; color: {t['muted']}; font-size: 13px; line-height: 1.5; max-width: 500px; }}
.signal-pill {{ display: inline-flex; margin-top: 18px; padding: 6px 10px; border-radius: 999px; font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: .08em; }}
.pill-green {{ color: {t['green']}; background: {t['green_bg']}; }}
.pill-amber {{ color: {t['amber']}; background: {t['amber_bg']}; }}
.pill-coral {{ color: {t['coral']}; background: {t['coral_bg']}; }}
.pill-muted {{ color: {t['muted']}; background: {t['neutral_pill']}; }}
.signal-viz {{ position: absolute; right: 22px; top: 22px; width: 84px; height: 84px; border: 1px solid {t['border2']}; border-radius: 50%; background: {t['signal_viz_bg']}; }}
.signal-viz::before, .signal-viz::after {{ content: ""; position: absolute; border-radius: 50%; inset: 12px; border: 1px solid var(--signal-color); opacity: .45; }}
.signal-viz::after {{ inset: 29px; background: var(--signal-color); box-shadow: 0 0 22px color-mix(in srgb, var(--signal-color) 40%, transparent); opacity: .85; animation: livePulse 2.6s ease-in-out infinite; }}

/* Index cards */
.index-grid {{ display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 12px; }}
.index-card {{
    position: relative; min-height: 220px; padding: 20px;
    border: 1px solid {t['border']}; border-radius: 0;
    background: {t['surface2']}; overflow: hidden;
    transition: transform .25s ease, border-color .25s ease, box-shadow .25s ease;
}}
.index-card:hover {{ transform: translateY(-5px); border-color: {t['border2']}; box-shadow: 9px 9px 0 var(--card-accent); }}
.index-card::before {{ content: ""; position: absolute; inset: 0 0 auto 0; height: 6px; background: var(--card-accent); }}
.index-top {{ display: flex; justify-content: space-between; align-items: start; gap: 12px; }}
.index-ticker {{ color: {t['text']}; font-family: "Space Grotesk", sans-serif; font-size: 22px; font-weight: 650; letter-spacing: -.04em; }}
.index-dot {{ width: 10px; height: 10px; border-radius: 0; background: var(--card-accent); }}
.index-name {{ color: {t['muted']}; font-size: 11px; margin-top: 4px; min-height: 32px; }}
.index-price {{ color: {t['text']}; font-family: "Space Grotesk", sans-serif; font-size: 28px; font-weight: 550; letter-spacing: -.05em; margin-top: 23px; }}
.index-returns {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 5px; margin-top: 23px; padding-top: 15px; border-top: 1px solid {t['border']}; }}
.index-period {{ color: {t['muted2']}; font-family: "IBM Plex Mono", monospace; font-size: 8px; text-transform: uppercase; letter-spacing: .08em; }}
.index-return {{ color: {t['text']}; font-family: "IBM Plex Mono", monospace; font-size: 10px; font-weight: 600; margin-top: 4px; }}
.positive {{ color: {t['green']} !important; }}
.negative {{ color: {t['coral']} !important; }}

/* Performance lab */
.performance-shell {{
    margin-top: 18px; padding: 24px;
    border: 1px solid {t['border']}; border-radius: 0;
    background: {t['surface2']};
}}
.performance-intro {{ color: {t['muted']}; font-size: 14px; line-height: 1.55; max-width: 820px; }}
.performance-intro b {{ color: {t['text']}; font-family: "Space Grotesk", sans-serif; }}
.performance-stats {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; margin: 12px 0 6px; }}
.summary-card {{ position: relative; overflow: hidden; min-height: 100px; border: 1px solid {t['border']}; border-radius: 0; padding: 16px; background: {t['surface3']}; }}
.summary-card:nth-child(1) {{ background: {t['summary1']}; }}
.summary-card:nth-child(2) {{ background: {t['summary2']}; }}
.summary-card:nth-child(3) {{ background: {t['summary3']}; }}
.summary-label {{ color: {t['muted2']}; font-family: "IBM Plex Mono", monospace; font-size: 9px; text-transform: uppercase; letter-spacing: .09em; }}
.summary-value {{ color: {t['text']}; font-family: "Space Grotesk", sans-serif; font-size: 18px; font-weight: 650; margin-top: 11px; letter-spacing: -.025em; }}

/* Learn panel */
.learn-grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; }}
.learn-item {{ border: 1px solid {t['border']}; border-radius: 0; padding: 18px; background: {t['surface2']}; }}
.learn-item:nth-child(1) {{ background: {t['signal1']}; }}
.learn-item:nth-child(2) {{ background: {t['signal2']}; }}
.learn-item:nth-child(3) {{ background: {t['signal3']}; }}
.learn-item:nth-child(4) {{ background: {t['signal4']}; }}
.learn-q {{ color: {t['text']}; font-family: "Space Grotesk", sans-serif; font-size: 17px; font-weight: 650; letter-spacing: -.025em; }}
.learn-a {{ color: {t['muted']}; font-size: 13px; line-height: 1.55; margin-top: 8px; }}

.footer {{
    margin-top: 90px; padding: 30px 0 0; border-top: 1px solid {t['border']};
    color: {t['muted2']}; font-size: 11px; line-height: 1.6;
}}
.footer-brand {{ color: {t['text']}; font-family: "Space Grotesk", sans-serif; font-size: clamp(42px, 7vw, 92px); font-weight: 620; letter-spacing: -.07em; line-height: .9; margin-bottom: 28px; }}
.footer-brand span {{ color: {t['green']}; }}

/* Motion */
@keyframes titleUp {{ from {{ opacity: 0; transform: translateY(45px); filter: blur(6px); }} to {{ opacity: 1; transform: translateY(0); filter: blur(0); }} }}
@keyframes fadeRise {{ from {{ opacity: 0; transform: translateY(16px); }} to {{ opacity: 1; transform: translateY(0); }} }}
@keyframes consoleIn {{ from {{ opacity: 0; transform: translateY(22px) rotate(1deg); }} to {{ opacity: 1; transform: translateY(0) rotate(0); }} }}
@keyframes scoreReveal {{ from {{ opacity: 0; transform: scale(.78); }} to {{ opacity: 1; transform: scale(1); }} }}
@keyframes markerSlide {{ from {{ left: 0%; opacity: 0; }} to {{ left: calc(var(--score) * 1%); opacity: 1; }} }}
@keyframes gradientTravel {{ from {{ background-position: 0% 50%; }} to {{ background-position: 100% 50%; }} }}
@keyframes orbFloat {{ 0%,100% {{ transform: translate(0,0) scale(1); }} 50% {{ transform: translate(-48px,62px) scale(1.08); }} }}
@keyframes tickerMove {{ from {{ transform: translateX(0); }} to {{ transform: translateX(-50%); }} }}
@keyframes livePulse {{ 0%,100% {{ opacity: 1; transform: scale(1); }} 50% {{ opacity: .45; transform: scale(.78); }} }}
@keyframes spinSlow {{ to {{ transform: rotate(360deg); }} }}

@supports (animation-timeline: view()) {{
    .signal-card, .index-card, .performance-shell {{
        animation: fadeRise .65s cubic-bezier(.16,1,.3,1) both;
        animation-timeline: view();
        animation-range: entry 5% entry 38%;
    }}
}}

@media (max-width: 1120px) {{
    .hero-inner {{ grid-template-columns: 1fr; padding: 46px 42px 40px; }}
    .score-console {{ max-width: 700px; width: 100%; box-shadow: 10px 10px 0 {t['lime']}; }}
    .hero-title {{ font-size: clamp(68px, 13vw, 118px); }}
    .index-grid {{ grid-template-columns: repeat(3, minmax(0, 1fr)); }}
}}
@media (max-width: 820px) {{
    .block-container {{ padding-left: 1rem; padding-right: 1rem; }}
    .top-rail {{ align-items: flex-start; flex-direction: column; padding: 14px; }}
    .top-status {{ justify-content: flex-start; }}
    .micro-pill:first-child {{ border-left: 0; padding-left: 0; }}
    .hero-inner {{ padding: 36px 24px 30px; min-height: auto; }}
    .hero-title {{ font-size: clamp(56px, 15vw, 90px); }}
    .heat-summary {{ grid-template-columns: 1fr; gap: 14px; align-items: start; }}
    .action-strip {{ grid-template-columns: 1fr; }}
    .action-cell {{ border-right: 0; border-bottom: 1px solid {t['border']}; }}
    .action-cell:last-child {{ border-bottom: 0; }}
    .section-head {{ grid-template-columns: 1fr; gap: 10px; margin-top: 70px; }}
    .section-kicker {{ padding-top: 0; }}
    .signal-card:nth-child(n) {{ grid-column: span 12; }}
    .index-grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
    .performance-stats, .learn-grid {{ grid-template-columns: 1fr; }}
}}
@media (max-width: 540px) {{
    .hero-title {{ font-size: 50px; }}
    .score-console {{ padding: 21px; min-height: auto; box-shadow: 7px 7px 0 {t['lime']}; }}
    .heat-labels {{ gap: 7px; }}
    .heat-label b {{ font-size: 11px; }}
    .heat-label span {{ display: none; }}
    .console-meta {{ flex-direction: column; gap: 7px; }}
    .index-grid {{ grid-template-columns: 1fr; }}
    .stTabs [data-baseweb="tab-list"] {{ width: 100%; overflow-x: auto; }}
}}
@media (prefers-reduced-motion: reduce) {{
    *, *::before, *::after {{ animation-duration: .001ms !important; animation-iteration-count: 1 !important; transition-duration: .001ms !important; scroll-behavior: auto !important; }}
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
    """One consistent buy-sizing policy for optional extra cash.

    The language is intentionally plain: the headline tells a beginner exactly
    what to do, while the underlying thresholds remain unchanged.
    """
    if score is None:
        return {
            "weather": "Unknown",
            "verdict": "Stay with your normal plan.",
            "copy": "Today's data is incomplete. Keep your normal automatic investing schedule and wait for the signal to refresh before changing any optional extra buy.",
            "extra_buy": "100% of your usual extra amount",
            "hold": "No change",
            "avoid": "Guessing from missing data",
        }
    if score <= 20:
        return {
            "weather": "Cold",
            "verdict": "Buy more than usual.",
            "copy": "The market looks fearful and prices are more attractive for a long-term buyer. Adding more than usual can make sense, but keep some cash available in case prices fall further.",
            "extra_buy": "150–200% of your usual extra amount",
            "hold": "Keep some cash for another drop",
            "avoid": "Going all-in at once",
        }
    if score <= 35:
        return {
            "weather": "Cool",
            "verdict": "Buy a little more.",
            "copy": "Conditions look better than normal for buyers. A somewhat larger extra buy is reasonable, while still spreading your money across more than one day.",
            "extra_buy": "125–150% of your usual extra amount",
            "hold": "Save the rest for future buys",
            "avoid": "Trying to catch the exact bottom",
        }
    if score <= 65:
        return {
            "weather": "Mild",
            "verdict": "Buy as usual.",
            "copy": "The market looks balanced—not especially cheap and not especially stretched. Keep your automatic investing and any normal extra buy exactly on schedule.",
            "extra_buy": "100% of your usual extra amount",
            "hold": "Follow your existing schedule",
            "avoid": "Inventing a clever trade",
        }
    if score <= 80:
        return {
            "weather": "Warm",
            "verdict": "Buy a little less.",
            "copy": "The market is running warm. Keep your automatic investing unchanged, but use only part of your optional extra cash today and spread the rest over the coming weeks.",
            "extra_buy": "25–50% of your usual extra amount",
            "hold": "Stage the rest into later buys",
            "avoid": "Chasing a strong run",
        }
    return {
        "weather": "Hot",
        "verdict": "Skip the extra buy today.",
        "copy": "Prices look stretched and optimism is high. Keep your automatic investing unchanged, but wait before putting a large amount of optional extra cash to work.",
        "extra_buy": "0–25% of your usual extra amount",
        "hold": "Wait for scheduled buys or a pullback",
        "avoid": "A FOMO-driven lump sum",
    }


def heat_stage(score):
    """Map the 0–100 score to the three beginner-facing stages."""
    if score is None:
        return "Signal unavailable"
    if score <= 35:
        return "Fear / On Sale"
    if score <= 65:
        return "Normal"
    return "Overstretched"

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

    chart["Label"] = chart["Ticker"] + "  /  " + chart["Name"]
    chart = chart.sort_values(period, ascending=True)
    colors = [theme["green"] if value >= 0 else theme["coral"] for value in chart[period]]

    figure = go.Figure()
    figure.add_trace(
        go.Bar(
            x=chart[period],
            y=chart["Label"],
            orientation="h",
            marker={"color": colors, "line": {"width": 0}},
            text=[f"{value:+.2f}%" for value in chart[period]],
            textposition="outside",
            textfont={"family": "IBM Plex Mono", "size": 11},
            cliponaxis=False,
            hovertemplate="<b>%{y}</b><br>Adjusted return: %{x:+.2f}%<extra></extra>",
        )
    )

    if benchmark_return is not None:
        figure.add_vline(
            x=benchmark_return,
            line_width=1.4,
            line_dash="dot",
            line_color=theme["lime"],
            annotation_text=f"SPY {benchmark_return:+.2f}%",
            annotation_position="top",
            annotation_font_color=theme["lime"],
            annotation_font_family="IBM Plex Mono",
            annotation_font_size=10,
        )

    figure.add_vline(x=0, line_width=1, line_color=theme["border2"])
    figure.update_layout(
        title={"text": title.upper(), "x": 0.01, "xanchor": "left", "font": {"size": 12, "family": "IBM Plex Mono", "color": theme["muted"]}},
        height=max(390, 50 * len(chart) + 110),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": theme["text"], "family": "DM Sans, sans-serif", "size": 12},
        margin={"l": 8, "r": 78, "t": 58, "b": 18},
        showlegend=False,
        bargap=0.42,
        hoverlabel={"bgcolor": theme["surface3"], "bordercolor": theme["border2"], "font_color": theme["text"]},
        xaxis={
            "title": None,
            "ticksuffix": "%",
            "gridcolor": theme["grid"],
            "zeroline": False,
            "tickfont": {"family": "IBM Plex Mono", "size": 10, "color": theme["muted2"]},
        },
        yaxis={
            "title": None,
            "automargin": True,
            "tickfont": {"family": "Space Grotesk", "size": 11, "color": theme["muted"]},
        },
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
  <div class="summary-card"><div class="summary-label">Leader / {period}</div><div class="summary-value">{summary['leader']}</div></div>
  <div class="summary-card"><div class="summary-label">Laggard / {period}</div><div class="summary-value">{summary['laggard']}</div></div>
  <div class="summary-card"><div class="summary-label">Breadth / {period}</div><div class="summary-value">{summary['breadth']}</div></div>
</div>
""",
            unsafe_allow_html=True,
        )

    figure = make_return_chart(table, period, f"{period} adjusted total return", theme, benchmark)
    if figure is None:
        st.warning("Performance data is unavailable right now.")
        return
    st.plotly_chart(figure, use_container_width=True, config={"displayModeBar": False, "scrollZoom": False})

    with st.expander("Open full return matrix"):
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
  <div>
    <div class="section-title">{title}</div>
    <div class="section-copy">{copy}</div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )


def render_core_index_cards(prices, theme):
    accents = [theme["lime"], theme["cyan"], theme["violet"], theme["pink"], theme["amber"]]
    cards = []
    for i, (name, ticker) in enumerate(CORE_INDEXES.items()):
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
<div class="index-card" style="--card-accent:{accents[i % len(accents)]};">
  <div class="index-top"><div><div class="index-ticker">{ticker}</div><div class="index-name">{name}</div></div><span class="index-dot"></span></div>
  <div class="index-price">${price:,.2f}</div>
  <div class="index-returns">
    <div><div class="index-period">1 day</div><div class="index-return {return_class(one_day)}">{fmt_return(one_day)}</div></div>
    <div><div class="index-period">YTD</div><div class="index-return {return_class(ytd)}">{fmt_return(ytd)}</div></div>
    <div><div class="index-period">1 year</div><div class="index-return {return_class(one_year)}">{fmt_return(one_year)}</div></div>
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


def render_ticker_tape(prices):
    items = []
    for name, ticker in CORE_INDEXES.items():
        if ticker not in prices.columns:
            continue
        series = pd.to_numeric(prices[ticker], errors="coerce").dropna()
        if len(series) < 2:
            continue
        change = calculate_period_return(series, "1D")
        css_class = return_class(change)
        items.append(f'<span class="tape-item"><span class="tape-ticker">{ticker}</span><span>{name}</span><span class="{css_class}">{fmt_return(change)}</span><span class="tape-sep">///</span></span>')
    if not items:
        return
    sequence = "".join(items)
    st.markdown(f'<div class="tape-shell"><div class="tape">{sequence}{sequence}</div></div>', unsafe_allow_html=True)

# ============================================================
# Controls and data load
# ============================================================
theme = current_theme()
inject_css(theme)

rail_left, rail_mode, rail_right = st.columns(
    [0.68, 0.15, 0.17],
    gap="small",
    vertical_alignment="center",
)
with rail_mode:
    st.toggle("Dark mode", key="dark_mode")
with rail_right:
    if st.button("↻  Refresh market", key="refresh_market", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

with st.spinner("Syncing market signal..."):
    market_prices = fetch_market_prices(ALL_MARKET_TICKERS)
    put_call = fetch_cboe_equity_put_call()
    treasury = fetch_treasury_curve()

technical = build_technical_snapshot(market_prices)
if technical is None:
    loaded_symbols = [ticker for ticker in ALL_MARKET_TICKERS if ticker in market_prices.columns]
    st.markdown(
        """
<div class="top-rail">
  <div class="brand"><span class="brand-mark"></span><span class="brand-name">SHOULD I BUY TODAY?</span></div>
</div>
<div class="hero" style="min-height:420px;">
  <div class="hero-inner" style="min-height:420px;grid-template-columns:1fr;">
    <div class="hero-copy">
      <div class="hero-kicker">Data link interrupted</div>
      <div class="hero-title" style="font-size:clamp(52px,9vw,108px);"><span class="line">NO SIGNAL.</span></div>
      <div class="hero-description">The S&P 500 index and its SPY fallback are both unavailable. The app is refusing to manufacture an answer from partial data.</div>
    </div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )
    st.error("Yahoo may be rate-limiting this deployment. Refresh once the data feed recovers.")
    if loaded_symbols:
        st.caption(f"Other symbols loaded: {', '.join(loaded_symbols)}")
    st.stop()

score, signal_frame = build_heat_score(
    technical["vix"],
    technical["rsi"],
    technical["distance_200d"],
    put_call,
)
plan = recommendation(score)
stage = heat_stage(score)
confidence, available_count, confidence_reason = confidence_summary(signal_frame)
latest_market_date = technical["latest_date"]
market_age_days = max(0, (NOW_PT.date() - latest_market_date.date()).days)
market_date_label = latest_market_date.strftime("%b %d, %Y")
refresh_label = NOW_PT.strftime("%b %d · %I:%M %p PT")
report_date_label = NOW_PT.strftime("%A / %B %d / %Y")

# ============================================================
# Top rail
# ============================================================
with rail_left:
    st.markdown(
        f"""
<div class="top-rail">
  <div class="brand">
    <span class="brand-mark"></span>
    <span class="brand-name">SHOULD I BUY TODAY?</span>
    <span class="brand-slash">MARKET WEATHER / LONG-TERM INDEX INVESTING</span>
  </div>
  <div class="top-status">
    <span class="micro-pill"><span class="live-dot"></span>LIVE MODEL</span>
    <span class="micro-pill">THEME / {'DARK' if st.session_state.dark_mode else 'LIGHT'}</span>
    <span class="micro-pill">PRICES / {market_date_label}</span>
    <span class="micro-pill">INPUTS / {available_count} OF 4</span>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

if market_age_days > 4:
    st.warning(f"Market prices are {market_age_days} calendar days old. Treat this signal as stale until the feed refreshes.")

# ============================================================
# Bright hero + three-stage score bar
# ============================================================
weather_palette = {
    "Cold": (theme["green"], theme["lime"]),
    "Cool": (theme["cyan"], theme["green2"]),
    "Mild": (theme["blue"], theme["cyan"]),
    "Warm": (theme["violet"], theme["pink"]),
    "Hot": (theme["coral"], theme["orange"]),
}
weather_a, weather_b = weather_palette.get(plan["weather"], (theme["blue"], theme["green"]))

verdict_lines = {
    "Cold": ("BUY", "MORE."),
    "Cool": ("BUY A", "LITTLE MORE."),
    "Mild": ("BUY AS", "USUAL."),
    "Warm": ("BUY A", "LITTLE LESS."),
    "Hot": ("SKIP THE", "EXTRA BUY."),
}.get(plan["weather"], ("STAY", "STEADY."))

st.markdown(
    f"""
<div class="hero" style="--weather-a:{weather_a};--weather-b:{weather_b};">
  <div class="hero-noise"></div>
  <div class="hero-inner">
    <div class="hero-copy">
      <div class="hero-kicker">TODAY'S SIGNAL / {report_date_label}</div>
      <div class="hero-title">
        <span class="line">{verdict_lines[0]}</span>
        <span class="line gradient-word">{verdict_lines[1]}</span>
      </div>
      <div class="hero-description">{plan['copy']}</div>
      <div class="hero-rule"><span class="rule-icon">✓</span><span>Your automatic investing stays unchanged. This only applies to optional extra cash.</span></div>
    </div>
    <div class="score-console">
      <div class="console-top"><span class="console-label">Market heat index</span><span class="weather-chip">{plan['weather']}</span></div>
      <div class="heat-summary">
        <div class="score-number">{score}</div>
        <div><div class="score-stage">{stage}</div><div class="score-denom">OUT OF 100 / HIGHER MEANS MORE STRETCHED</div></div>
      </div>
      <div class="heat-bar-wrap">
        <div class="heat-track" style="--score:{score};">
          <span class="heat-zone fear"></span>
          <span class="heat-zone normal"></span>
          <span class="heat-zone stretched"></span>
          <span class="heat-marker" data-score="{score}"></span>
        </div>
        <div class="heat-ticks"><span>0</span><span>35</span><span>65</span><span>100</span></div>
        <div class="heat-labels">
          <div class="heat-label fear"><b>Fear / On Sale</b><span>Lower prices; better conditions for adding extra cash.</span></div>
          <div class="heat-label normal"><b>Normal</b><span>Balanced conditions; stay with your usual plan.</span></div>
          <div class="heat-label stretched"><b>Overstretched</b><span>Higher risk of overpaying after a strong run.</span></div>
        </div>
      </div>
      <div class="console-meta"><span>CONFIDENCE / {confidence.upper()}</span><span>REFRESHED / {refresh_label}</span></div>
    </div>
  </div>
  <div class="action-strip">
    <div class="action-cell"><div class="action-index">01 / BUY TODAY</div><div class="action-label">Optional extra cash</div><div class="action-value">{plan['extra_buy']}</div><div class="action-help">Relative to the extra amount you would normally invest.</div></div>
    <div class="action-cell"><div class="action-index">02 / KEEP FLEXIBLE</div><div class="action-label">What to do with the rest</div><div class="action-value">{plan['hold']}</div><div class="action-help">Several good decisions are better than one heroic prediction.</div></div>
    <div class="action-cell"><div class="action-index">03 / AVOID</div><div class="action-label">Behavioral trap</div><div class="action-value">{plan['avoid']}</div><div class="action-help">No sell signal, no market prophecy, and no interruption to your automatic plan.</div></div>
  </div>
</div>
""",
    unsafe_allow_html=True,
)

render_ticker_tape(market_prices)

with st.expander("New here? Decode the signal in 30 seconds"):
    st.markdown(
        """
<div class="learn-grid">
  <div class="learn-item"><div class="learn-q">What is this?</div><div class="learn-a">A daily gauge of whether the broad market looks fearful, normal, or overheated. It helps size optional extra cash on top of your regular investing.</div></div>
  <div class="learn-item"><div class="learn-q">What stays constant?</div><div class="learn-a">Your dollar-cost-averaging schedule. This dashboard never tells a long-term investor to pause the habit that matters most.</div></div>
  <div class="learn-item"><div class="learn-q">Why can fear help buyers?</div><div class="learn-a">Fear pushes prices down. For someone buying productive assets for decades, lower prices are useful—even when the headlines feel awful.</div></div>
  <div class="learn-item"><div class="learn-q">What is this not?</div><div class="learn-a">Not a forecast, stock picker, or trading signal. It never says sell. It is a disciplined sizing framework for optional money.</div></div>
</div>
""",
        unsafe_allow_html=True,
    )

# ============================================================
# Signal evidence
# ============================================================
section_header(
    "01 / SIGNAL DNA",
    f"Why the market reads {plan['weather'].lower()}.",
    f"Four live inputs are translated into plain English, then blended using fixed audited weights. Confidence is {confidence.lower()}: {confidence_reason}",
)

ordered = signal_frame.reindex(signal_frame["WeightedImpact"].abs().sort_values(ascending=False).index)
signal_colors = [theme["cyan"], theme["violet"], theme["lime"], theme["amber"]]
signal_cards = []
for i, (_, row) in enumerate(ordered.iterrows(), start=1):
    plain = SIGNAL_PLAIN.get(row["Signal"], {"name": row["Signal"], "question": "", "technical": row["Signal"]})
    pill_class, pill_text = driver_pill(row)
    signal_color = signal_colors[(i - 1) % len(signal_colors)]
    signal_cards.append(
        f"""
<div class="signal-card" style="--signal-color:{signal_color};">
  <div class="signal-number">0{i} / {plain['name'].upper()}</div>
  <div class="signal-viz"></div>
  <div class="signal-question">{plain['question']}</div>
  <div class="signal-answer">{row['Status']}</div>
  <div class="signal-reading">{plain['technical'].upper()} / {reading_text(row['Signal'], row['Reading'])}</div>
  <div class="signal-copy">{row['Explanation']}</div>
  <span class="signal-pill {pill_class}">{pill_text}</span>
</div>
"""
    )
st.markdown(f'<div class="signal-grid">{"".join(signal_cards)}</div>', unsafe_allow_html=True)

# ============================================================
# Core market
# ============================================================
section_header(
    "02 / MARKET PULSE",
    "The building blocks, at a glance.",
    "The broad assets most index investors actually own. Adjusted prices include distributions where the data source provides them.",
)
render_core_index_cards(market_prices, theme)

# ============================================================
# Performance lab
# ============================================================
section_header(
    "03 / PERFORMANCE LAB",
    "See what is carrying the market.",
    "Switch the time horizon. Compare the broad indexes, the Magnificent 7, and all eleven S&P 500 sector ETFs without drowning in a spreadsheet.",
)
index_tab, mag7_tab, sector_tab = st.tabs(["Core indexes", "Magnificent 7", "S&P 500 sectors"])

with index_tab:
    render_performance_view(
        "Core indexes",
        "US stocks, international stocks, and bonds over the period you choose.",
        CORE_INDEXES,
        market_prices,
        "core_period_universe",
        theme,
        show_benchmark=False,
    )

with mag7_tab:
    render_performance_view(
        "Magnificent 7",
        "Seven giant companies versus SPY. The dotted lime line is the S&P 500 benchmark.",
        MAG7,
        market_prices,
        "mag7_period_universe",
        theme,
        show_benchmark=True,
    )

with sector_tab:
    render_performance_view(
        "S&P 500 sector ETFs",
        "Eleven investable slices of the US economy. The dotted lime line is SPY.",
        SP500_SECTORS,
        market_prices,
        "sector_period_universe",
        theme,
        show_benchmark=True,
    )

# ============================================================
# Audit layer
# ============================================================
section_header(
    "04 / AUDIT MODE",
    "Trust the interface. Verify the machinery.",
    "Open the model only when you want it. The recommendation remains simple; the math remains fully inspectable.",
)

with st.expander("Open methodology, raw inputs, and advanced charts"):
    st.markdown(
        """
### How the score works

The Market Heat Score is a transparent, rule-based index—not a forecast of tomorrow's return. Four inputs: the VIX fear gauge (30%), broad-market momentum via 14-day RSI (25%), distance from the 200-day average (25%), and the Cboe equity put/call ratio (20%). The S&P 500 index is preferred; SPY is a disclosed fallback when the index feed is unavailable. Higher means more stretched; lower means more fearful.

When an input is unavailable, it is replaced with a neutral 50 and confidence drops. The missing weight is **not** redistributed, so the 0–100 scale stays consistent from day to day.
"""
    )

    signal_display = signal_frame[["Signal", "Reading", "Status", "Weight", "UsedScore", "Available", "Explanation"]].copy()
    signal_display.insert(0, "Plain name", signal_display["Signal"].map(lambda s: SIGNAL_PLAIN.get(s, {}).get("name", s)))
    signal_display["Reading"] = signal_display.apply(lambda row: reading_text(row["Signal"], row["Reading"]), axis=1)
    signal_display["Weight"] = signal_display["Weight"].apply(lambda value: f"{value:.0%}")
    signal_display["UsedScore"] = signal_display["UsedScore"].round(1)
    signal_display["Available"] = signal_display["Available"].map({True: "Yes", False: "No — neutral used"})
    st.dataframe(signal_display, use_container_width=True, hide_index=True)

    trend_tab, treasury_tab, sources_tab = st.tabs(["S&P 500 trend", "Treasury curve", "Data sources"])

    with trend_tab:
        history = technical["history"]
        figure = go.Figure()
        figure.add_trace(
            go.Scatter(
                x=history["Date"], y=history["Close"], mode="lines", name=technical["source_label"],
                line={"color": theme["cyan"], "width": 2.4}, fill="tozeroy", fillcolor="rgba(0,167,183,.08)"
            )
        )
        figure.add_trace(
            go.Scatter(
                x=history["Date"], y=history["SMA 200"], mode="lines", name="200-day average",
                line={"color": theme["lime"], "width": 1.6, "dash": "dot"}
            )
        )
        figure.update_layout(
            height=430,
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font={"color": theme["text"], "family": "DM Sans, sans-serif"},
            margin={"l": 8, "r": 8, "t": 22, "b": 8}, legend={"orientation": "h", "y": 1.08}, hovermode="x unified",
            xaxis={"gridcolor": theme["grid"], "zeroline": False},
            yaxis={"gridcolor": theme["grid"], "zeroline": False},
            hoverlabel={"bgcolor": theme["surface3"], "font_color": theme["text"]},
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
                    x=curve_frame["Maturity"], y=curve_frame["Yield (%)"], mode="lines+markers", name="Treasury yield",
                    line={"color": theme["violet"], "width": 2.2}, marker={"color": theme["lime"], "size": 7}
                )
            )
            curve_figure.update_layout(
                height=370,
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font={"color": theme["text"], "family": "DM Sans, sans-serif"},
                margin={"l": 8, "r": 8, "t": 22, "b": 8},
                xaxis={"gridcolor": theme["grid"]},
                yaxis={"ticksuffix": "%", "gridcolor": theme["grid"]},
                hoverlabel={"bgcolor": theme["surface3"], "font_color": theme["text"]},
            )
            st.plotly_chart(curve_figure, use_container_width=True, config={"displayModeBar": False})
            if treasury.get("Date") is not None:
                st.caption(f"Official U.S. Treasury curve date: {pd.Timestamp(treasury['Date']).strftime('%b %d, %Y')}")
        else:
            st.info("Official Treasury curve data is unavailable right now. It does not affect the heat score.")

    with sources_tab:
        st.markdown(
            """
- **Prices and adjusted returns:** Yahoo Finance through the open-source `yfinance` package. Critical index series are fetched independently, and SPY is a disclosed fallback for the technical signal. Data may be delayed.
- **Equity put/call ratio:** Cboe Daily Market Statistics.
- **Treasury curve:** U.S. Department of the Treasury daily par yield curve.
- **Sector view:** the eleven Select Sector SPDR ETFs are investable proxies for S&P 500 sectors; their adjusted returns are not identical to raw sector-index returns.

Headline sentiment and search trends remain excluded from the core score because they are noisy and operationally fragile.
"""
        )

st.markdown(
    """
<div class="footer">
  <div class="footer-brand">BUILD THE HABIT.<br><span>IGNORE THE HYPE.</span></div>
  Educational only—not financial advice. Built for long-term index investors deciding how to size optional extra cash. It never recommends selling, never changes an automatic plan, and never predicts the market's next move.
</div>
""",
    unsafe_allow_html=True,
)
