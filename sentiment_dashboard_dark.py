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


st.set_page_config(
    page_title="Market Sentiment Pro",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

LIGHT_THEME = {
    "name": "light",
    "bg": "#f5f7fb",
    "bg2": "#ffffff",
    "text": "#111827",
    "muted": "#6b7280",
    "border": "rgba(17,24,39,.08)",
    "card": "rgba(255,255,255,.90)",
    "card2": "rgba(255,255,255,.96)",
    "shadow": "0 12px 34px rgba(15,23,42,.08)",
    "green": "#16a34a",
    "yellow": "#f59e0b",
    "red": "#ef4444",
    "blue": "#2563eb",
    "accent": "#0f172a",
    "hero_grad_1": "rgba(37,99,235,.10)",
    "hero_grad_2": "rgba(22,163,74,.10)",
}

DARK_THEME = {
    "name": "dark",
    "bg": "#070b14",
    "bg2": "#0d1324",
    "text": "#f8fafc",
    "muted": "rgba(248,250,252,.72)",
    "border": "rgba(255,255,255,.09)",
    "card": "rgba(255,255,255,.05)",
    "card2": "rgba(255,255,255,.06)",
    "shadow": "0 14px 40px rgba(0,0,0,.28)",
    "green": "#22c55e",
    "yellow": "#fbbf24",
    "red": "#f87171",
    "blue": "#60a5fa",
    "accent": "#f8fafc",
    "hero_grad_1": "rgba(37,99,235,.15)",
    "hero_grad_2": "rgba(22,163,74,.12)",
}

if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = False

theme = DARK_THEME if st.session_state.dark_mode else LIGHT_THEME


def apply_css(theme_dict):
    st.markdown(
        f"""
<style>
    .stApp {{
        background:
            radial-gradient(circle at 8% 5%, {theme_dict["hero_grad_1"]}, transparent 26%),
            radial-gradient(circle at 92% 6%, {theme_dict["hero_grad_2"]}, transparent 28%),
            linear-gradient(135deg, {theme_dict["bg"]} 0%, {theme_dict["bg2"]} 54%, {theme_dict["bg"]} 100%);
        color: {theme_dict["text"]};
    }}
    [data-testid="stHeader"] {{ background: rgba(0,0,0,0); }}
    [data-testid="stToolbar"] {{ display: none; }}
    .block-container {{
        padding-top: 1.6rem;
        padding-bottom: 3rem;
        max-width: 1500px;
    }}
    .hero {{
        border: 1px solid {theme_dict["border"]};
        border-radius: 28px;
        padding: 26px 28px;
        background: linear-gradient(135deg, {theme_dict["card2"]}, {theme_dict["card"]});
        box-shadow: {theme_dict["shadow"]};
        margin-bottom: 16px;
    }}
    .hero h1 {{
        font-size: 42px;
        line-height: 1.04;
        margin: 0;
        letter-spacing: -1.1px;
        color: {theme_dict["text"]};
    }}
    .muted {{
        color: {theme_dict["muted"]};
        font-size: 14px;
        margin-top: 6px;
    }}
    .hook-card {{
        border-radius: 28px;
        padding: 28px 28px;
        border: 1px solid {theme_dict["border"]};
        background: linear-gradient(135deg, {theme_dict["card2"]}, {theme_dict["card"]});
        box-shadow: {theme_dict["shadow"]};
        min-height: 360px;
    }}
    .hook-title {{
        color: {theme_dict["muted"]};
        font-size: 12px;
        font-weight: 900;
        letter-spacing: .7px;
        text-transform: uppercase;
        margin-bottom: 8px;
    }}
    .hook-headline {{
        color: {theme_dict["text"]};
        font-size: 40px;
        font-weight: 950;
        line-height: 1.02;
        letter-spacing: -1.2px;
        margin-bottom: 12px;
    }}
    .hook-body {{
        color: {theme_dict["text"]};
        font-size: 17px;
        line-height: 1.45;
        margin-top: 12px;
    }}
    .hook-sub {{
        color: {theme_dict["muted"]};
        font-size: 15px;
        line-height: 1.45;
        margin-top: 12px;
    }}
    .pill {{
        display: inline-block;
        padding: 7px 12px;
        border-radius: 999px;
        font-weight: 900;
        font-size: 12px;
        letter-spacing: .2px;
        margin-top: 8px;
    }}
    .pill-green {{
        background: rgba(34,197,94,.12);
        color: {theme_dict["green"]};
        border: 1px solid rgba(34,197,94,.18);
    }}
    .pill-yellow {{
        background: rgba(245,158,11,.12);
        color: {theme_dict["yellow"]};
        border: 1px solid rgba(245,158,11,.18);
    }}
    .pill-red {{
        background: rgba(239,68,68,.12);
        color: {theme_dict["red"]};
        border: 1px solid rgba(239,68,68,.18);
    }}
    .pill-blue {{
        background: rgba(37,99,235,.12);
        color: {theme_dict["blue"]};
        border: 1px solid rgba(37,99,235,.18);
    }}
    .small-card {{
        border: 1px solid {theme_dict["border"]};
        border-radius: 22px;
        padding: 18px 18px;
        background: {theme_dict["card"]};
        box-shadow: {theme_dict["shadow"]};
        min-height: 135px;
    }}
    .small-title {{
        color: {theme_dict["muted"]};
        font-size: 12px;
        font-weight: 900;
        letter-spacing: .55px;
        text-transform: uppercase;
    }}
    .small-value {{
        color: {theme_dict["text"]};
        font-size: 30px;
        font-weight: 950;
        letter-spacing: -.5px;
        margin-top: 4px;
    }}
    .small-copy {{
        color: {theme_dict["muted"]};
        font-size: 13px;
        line-height: 1.35;
        margin-top: 6px;
    }}
    .section-title {{
        color: {theme_dict["text"]};
        font-size: 24px;
        font-weight: 950;
        letter-spacing: -.3px;
        margin-top: 18px;
        margin-bottom: 10px;
    }}
    .lens {{
        border: 1px solid {theme_dict["border"]};
        border-radius: 22px;
        padding: 18px;
        background: {theme_dict["card"]};
        box-shadow: {theme_dict["shadow"]};
        min-height: 156px;
    }}
    .lens-title {{
        color: {theme_dict["muted"]};
        font-size: 12px;
        font-weight: 900;
        letter-spacing: .55px;
        text-transform: uppercase;
    }}
    .lens-head {{
        color: {theme_dict["text"]};
        font-size: 22px;
        font-weight: 950;
        margin-top: 5px;
        margin-bottom: 7px;
    }}
    .lens-copy {{
        color: {theme_dict["muted"]};
        font-size: 14px;
        line-height: 1.42;
    }}
    .footer {{
        color: {theme_dict["muted"]};
        font-size: 12px;
        margin-top: 28px;
        padding-top: 18px;
        border-top: 1px solid {theme_dict["border"]};
    }}
    .stTabs [data-baseweb="tab-list"] {{
        gap: 8px;
    }}
    .stTabs [data-baseweb="tab"] {{
        border-radius: 999px;
        padding: 8px 16px;
        background: {theme_dict["card"]};
        border: 1px solid {theme_dict["border"]};
        color: {theme_dict["text"]};
    }}
    div[data-testid="stDataFrame"] {{
        border-radius: 18px;
        overflow: hidden;
    }}
</style>
        """,
        unsafe_allow_html=True,
    )


apply_css(theme)


def safe_float(value):
    try:
        if value is None:
            return None
        value = float(value)
        if math.isnan(value):
            return None
        return value
    except Exception:
        return None


def safe_round(value, digits=2):
    value = safe_float(value)
    if value is None:
        return None
    return round(value, digits)


def clamp(value, low=0, high=100):
    value = safe_float(value)
    if value is None:
        return None
    return max(low, min(high, value))


def fmt(value, suffix="", digits=2):
    value = safe_float(value)
    if value is None:
        return "N/A"
    if digits == 0:
        return f"{value:,.0f}{suffix}"
    return f"{value:,.{digits}f}{suffix}"


def score_from_range(value, points):
    value = safe_float(value)
    if value is None:
        return None

    points = sorted(points, key=lambda x: x[0])

    if value <= points[0][0]:
        return float(points[0][1])
    if value >= points[-1][0]:
        return float(points[-1][1])

    for (x1, y1), (x2, y2) in zip(points, points[1:]):
        if x1 <= value <= x2:
            pct = (value - x1) / (x2 - x1)
            return float(y1 + pct * (y2 - y1))
    return None


def score_label(score):
    if score is None:
        return "Unknown", "pill-blue"
    if score <= 33:
        return "Fear", "pill-green"
    if score <= 66:
        return "Neutral", "pill-yellow"
    return "Greed", "pill-red"


def detailed_label(score):
    if score is None:
        return "Unknown", "pill-blue"
    if score <= 20:
        return "Extreme Fear", "pill-green"
    if score <= 33:
        return "Fear", "pill-green"
    if score <= 50:
        return "Slight Fear", "pill-yellow"
    if score <= 66:
        return "Neutral", "pill-yellow"
    if score <= 80:
        return "Greed", "pill-red"
    return "Extreme Greed", "pill-red"


def simple_action(score):
    if score is None:
        return ("WAIT", "Data is incomplete right now. Stick with your normal investing plan.", "pill-blue")
    if score <= 20:
        return ("BUY MORE", "Fear is high. This is one of the better times to add in tranches.", "pill-green")
    if score <= 33:
        return ("BUY A LITTLE MORE", "Sentiment is fearful. Good setup for a slightly bigger buy than normal.", "pill-green")
    if score <= 66:
        return ("KEEP BUYING NORMALLY", "Nothing special. Just stay disciplined and keep buying on schedule.", "pill-yellow")
    if score <= 80:
        return ("BUY SMALLER", "Market is getting hot. Keep buying, but size down large taxable buys.", "pill-red")
    return ("DON'T CHASE", "Sentiment is stretched. Keep dry powder and avoid oversized buys.", "pill-red")


def card(title, value, status, css_class, explanation):
    st.markdown(
        f"""
<div class="small-card">
    <div class="small-title">{title}</div>
    <div class="small-value">{value}</div>
    <div class="pill {css_class}">{status}</div>
    <div class="small-copy">{explanation}</div>
</div>
        """,
        unsafe_allow_html=True,
    )


def classify_vix(vix):
    if vix is None:
        return "Unavailable", "pill-blue"
    if vix < 14:
        return "Very Calm", "pill-red"
    if vix < 20:
        return "Calm", "pill-yellow"
    if vix < 28:
        return "Elevated", "pill-yellow"
    return "Fearful", "pill-green"


def classify_rsi(rsi):
    if rsi is None:
        return "Unavailable", "pill-blue"
    if rsi < 35:
        return "Oversold", "pill-green"
    if rsi < 45:
        return "Soft", "pill-green"
    if rsi <= 65:
        return "Healthy", "pill-yellow"
    if rsi <= 72:
        return "Hot", "pill-red"
    return "Overbought", "pill-red"


def classify_distance(dist):
    if dist is None:
        return "Unavailable", "pill-blue"
    if dist < -8:
        return "Cheap vs Trend", "pill-green"
    if dist < -2:
        return "Below Trend", "pill-green"
    if dist <= 8:
        return "Near Trend", "pill-yellow"
    return "Extended", "pill-red"


def classify_pcr(pcr):
    if pcr is None:
        return "Unavailable", "pill-blue"
    if pcr < 0.65:
        return "Call Chasing", "pill-red"
    if pcr <= 1.10:
        return "Balanced", "pill-yellow"
    return "Fearful", "pill-green"


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
    sma200 = safe_round(last["SMA_200"], 2)
    dist_200d = None
    if close is not None and sma200 not in [None, 0]:
        dist_200d = safe_round(((close - sma200) / sma200) * 100, 2)
    df = df.reset_index()
    if "Date" not in df.columns:
        df = df.rename(columns={df.columns[0]: "Date"})
    return {"close": close, "rsi": rsi, "sma200": sma200, "dist_200d": dist_200d, "history": df}


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
        response = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()
        data = response.json()
        return safe_round(data["chart_data"][0][0]["last_value"], 2)
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
        response = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()
        quotes = response.json()["FormattedQuoteResult"]["FormattedQuote"]
        yields = {}
        for q in quotes:
            symbol = q.get("symbol")
            last = q.get("last")
            if symbol and last:
                yields[symbol] = safe_round(str(last).strip("%"), 3)
        return yields
    except Exception:
        return {}


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_google_trends(term="stock market crash"):
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
def fetch_news_sentiment():
    key = None
    try:
        key = st.secrets.get("NEWSAPI_KEY", None)
    except Exception:
        key = None
    if not key:
        key = os.getenv("NEWSAPI_KEY")
    if not key or NewsApiClient is None:
        return None, "Optional"

    bear_words = ["crash","collapse","meltdown","plunge","sell-off","recession","slowdown","downturn","panic","fear","turmoil","risk-off","bearish","volatility","instability","losses","decline","drop","slump","downgrade"]
    bull_words = ["rally","surge","soar","rebound","recovery","growth","momentum","bullish","optimism","confidence","risk-on","strength","resilient","record high","all-time high","gains","advance","outperform","upgrade"]
    try:
        client = NewsApiClient(api_key=key)
        articles = client.get_everything(q="S&P 500 OR stock market", language="en", page_size=40).get("articles", [])
        titles = [(article.get("title") or "").lower() for article in articles]
        bear_count = sum(any(word in title for word in bear_words) for title in titles)
        bull_count = sum(any(word in title for word in bull_words) for title in titles)
        score = int(clamp(50 + 3 * (bull_count - bear_count), 0, 100))
        label = "Bullish" if score > 60 else "Bearish" if score < 40 else "Mixed"
        return score, label
    except Exception:
        return None, "Unavailable"


def build_score(vix, rsi, dist_200d, pcr, curve_spread, trends, news_score):
    rows = [
        {"Indicator":"VIX","Reading":fmt(vix),"Score":score_from_range(vix, [(12, 85), (18, 62), (25, 38), (35, 15), (50, 5)]),"Weight":0.24,"Why it matters":"Higher VIX means more fear. Fear often improves entry points."},
        {"Indicator":"RSI","Reading":fmt(rsi),"Score":score_from_range(rsi, [(25, 10), (35, 25), (50, 50), (65, 72), (75, 90), (85, 100)]),"Weight":0.21,"Why it matters":"Momentum temperature. High RSI usually means the market is hot."},
        {"Indicator":"S&P vs 200D","Reading":fmt(dist_200d, "%"),"Score":score_from_range(dist_200d, [(-20, 8), (-10, 20), (0, 48), (8, 68), (15, 84), (25, 96)]),"Weight":0.21,"Why it matters":"Tells you if the index is cheap or stretched vs long-term trend."},
        {"Indicator":"Put/Call Ratio","Reading":fmt(pcr),"Score":score_from_range(pcr, [(0.55, 90), (0.75, 70), (0.95, 52), (1.15, 35), (1.40, 15)]),"Weight":0.15,"Why it matters":"Low ratio can mean options-driven greed. High ratio can mean fear."},
        {"Indicator":"10Y - 2Y Curve","Reading":fmt(curve_spread, "%", 3),"Score":score_from_range(curve_spread, [(-1.2, 70), (-0.5, 58), (0, 50), (0.8, 45), (1.5, 48)]),"Weight":0.07,"Why it matters":"Macro backdrop. Helpful context, but not the main signal."},
        {"Indicator":"Google Trends","Reading":fmt(trends, "", 0),"Score":score_from_range(trends, [(0, 72), (20, 62), (50, 45), (80, 25), (100, 10)]),"Weight":0.06,"Why it matters":"Crash-search spikes are a simple public fear signal."},
        {"Indicator":"News Sentiment","Reading":fmt(news_score, "", 0),"Score":news_score,"Weight":0.06,"Why it matters":"Headline tone. Useful, but optional and noisy."},
    ]
    df = pd.DataFrame(rows)
    available = df.dropna(subset=["Score"]).copy()
    if available.empty:
        return None, df
    total_weight = available["Weight"].sum()
    available["AdjWeight"] = available["Weight"] / total_weight
    composite = int(round((available["Score"] * available["AdjWeight"]).sum()))
    return int(clamp(composite, 0, 100)), df


def fear_greed_donut(score, theme_dict):
    score = 50 if score is None else score
    label, _ = score_label(score)
    fig = go.Figure(
        data=[
            go.Pie(
                values=[33, 33, 34],
                labels=["Fear", "Neutral", "Greed"],
                hole=0.76,
                sort=False,
                direction="clockwise",
                marker=dict(
                    colors=[theme_dict["green"], theme_dict["yellow"], theme_dict["red"]],
                    line=dict(color=theme_dict["bg"], width=7)
                ),
                textinfo="label",
                textfont=dict(size=15, color=theme_dict["text"]),
                hovertemplate="%{label}<extra></extra>",
            )
        ]
    )
    fig.add_annotation(
        text=f"<b>{score}</b><br><span style='font-size:16px'>{label}</span>",
        x=0.5, y=0.50, showarrow=False,
        font=dict(size=34, color=theme_dict["text"]),
    )
    fig.update_layout(
        title=dict(text="Fear & Greed", x=0.5, y=0.96, font=dict(size=24, color=theme_dict["text"])),
        showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=360,
        margin=dict(l=10, r=10, t=40, b=20),
    )
    return fig


c1, c2, c3 = st.columns([0.72, 0.12, 0.16])
with c2:
    st.toggle("🌙 Dark mode", key="dark_mode")
with c3:
    if st.button("🔄 Refresh", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

theme = DARK_THEME if st.session_state.dark_mode else LIGHT_THEME
apply_css(theme)

with st.spinner("Loading market read..."):
    spx = fetch_sp500()
    vix = fetch_vix()
    pcr = fetch_pcr()
    yields = fetch_yields()
    trends = fetch_google_trends("stock market crash")
    news_score, news_label = fetch_news_sentiment()

if spx is None:
    st.error("Could not load S&P 500 data from Yahoo Finance. Please refresh in a few minutes.")
    st.stop()

spx_close = spx["close"]
rsi = spx["rsi"]
sma200 = spx["sma200"]
dist_200d = spx["dist_200d"]
us2y = yields.get("US2Y") if yields else None
us10y = yields.get("US10Y") if yields else None
curve_spread = safe_round(us10y - us2y, 3) if us2y is not None and us10y is not None else None

score, breakdown = build_score(vix, rsi, dist_200d, pcr, curve_spread, trends, news_score)
main_label, main_pill = score_label(score)
full_label, full_pill = detailed_label(score)
action_title, action_text, action_pill = simple_action(score)

st.markdown(
    f"""
<div class="hero">
    <h1>📊 Market Sentiment Pro</h1>
    <div class="muted">
        Super simple investing read for taxable buys. Light mode by default, clean design, and one clear answer first.
        Last updated: {datetime.now().strftime("%b %d, %Y %I:%M %p")}
    </div>
</div>
    """,
    unsafe_allow_html=True,
)

left, right = st.columns([0.56, 0.44])
with left:
    st.markdown(
        f"""
<div class="hook-card">
    <div class="hook-title">Clear Action Read</div>
    <div class="hook-headline">{action_title}</div>
    <div class="pill {action_pill}">{full_label} · Score {score if score is not None else "N/A"}/100</div>
    <div class="hook-body"><b>What it means:</b> {action_text}</div>
    <div class="hook-sub"><b>Keep it simple:</b> use this app to decide whether to buy <b>more</b>, <b>normal</b>, or <b>smaller</b>. Do not use it to guess the exact bottom.</div>
    <div class="hook-sub"><b>Right now:</b> sentiment says <b>{main_label.lower()}</b>, so the app is telling you to <b>{action_title.lower()}</b>.</div>
</div>
        """,
        unsafe_allow_html=True,
    )
with right:
    st.plotly_chart(fear_greed_donut(score, theme), use_container_width=True)

st.markdown('<div class="section-title">Quick Read</div>', unsafe_allow_html=True)
q1, q2, q3, q4 = st.columns(4)
vix_label, vix_css = classify_vix(vix)
rsi_label, rsi_css = classify_rsi(rsi)
dist_label, dist_css = classify_distance(dist_200d)
pcr_label, pcr_css = classify_pcr(pcr)
with q1:
    card("VIX", fmt(vix), vix_label, vix_css, "Fear gauge. Higher usually means more fear.")
with q2:
    card("RSI", fmt(rsi), rsi_label, rsi_css, "Momentum read. Hot market = more caution.")
with q3:
    card("S&P vs 200D", fmt(dist_200d, "%"), dist_label, dist_css, "Shows if price is stretched vs long-term trend.")
with q4:
    card("Put/Call", fmt(pcr), pcr_label, pcr_css, "Options positioning. Low can mean greed; high can mean fear.")

st.markdown('<div class="section-title">Simple Investor Lens</div>', unsafe_allow_html=True)
l1, l2, l3 = st.columns(3)
buffett_copy = "Best setups usually come when fear is obvious. Be patient when markets are hot." if score is not None and score > 66 else "Fear is your friend if you are buying quality assets for the long term."
tom_copy = "Momentum is hot. Tactical buyers should avoid chasing." if rsi is not None and rsi > 70 else "No extreme momentum signal right now. Stay measured."
with l1:
    st.markdown(f"""<div class="lens"><div class="lens-title">Buffett Lens</div><div class="lens-head">Be patient</div><div class="lens-copy">{buffett_copy}</div></div>""", unsafe_allow_html=True)
with l2:
    st.markdown("""<div class="lens"><div class="lens-title">Bogle Lens</div><div class="lens-head">Keep buying</div><div class="lens-copy">Stay invested in broad index funds. Use this score to size tranches, not to become a trader.</div></div>""", unsafe_allow_html=True)
with l3:
    st.markdown(f"""<div class="lens"><div class="lens-title">Tom Lee Lens</div><div class="lens-head">Watch momentum</div><div class="lens-copy">{tom_copy}</div></div>""", unsafe_allow_html=True)

st.markdown('<div class="section-title">Why the Score Looks This Way</div>', unsafe_allow_html=True)
tab1, tab2, tab3 = st.tabs(["Score Breakdown", "S&P Trend", "Treasury Curve"])
with tab1:
    df = breakdown.copy()
    df["Score"] = df["Score"].apply(lambda x: "N/A" if pd.isna(x) else round(float(x), 1))
    df["Weight"] = df["Weight"].apply(lambda x: f"{int(round(float(x) * 100))}%")
    st.dataframe(df, use_container_width=True, hide_index=True)
with tab2:
    history = spx["history"].copy()
    fig = go.Figure()
    if "Date" in history.columns and "Close" in history.columns:
        fig.add_trace(go.Scatter(x=history["Date"], y=history["Close"], mode="lines", name="S&P 500"))
    if "Date" in history.columns and "SMA_200" in history.columns:
        fig.add_trace(go.Scatter(x=history["Date"], y=history["SMA_200"], mode="lines", name="200D SMA"))
    fig.update_layout(height=430, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font={"color": theme["text"]}, margin=dict(l=12, r=12, t=20, b=12), legend=dict(orientation="h", yanchor="bottom", y=1.02))
    st.plotly_chart(fig, use_container_width=True)
with tab3:
    if yields:
        order = ["US1M", "US2M", "US3M", "US4M", "US6M", "US1Y", "US2Y", "US3Y", "US5Y", "US7Y", "US10Y", "US20Y", "US30Y"]
        rows = [{"Maturity": m, "Yield (%)": yields.get(m)} for m in order if yields.get(m) is not None]
        ydf = pd.DataFrame(rows)
        if not ydf.empty and "Maturity" in ydf.columns and "Yield (%)" in ydf.columns:
            st.dataframe(ydf, use_container_width=True, hide_index=True)
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=ydf["Maturity"], y=ydf["Yield (%)"], mode="lines+markers", name="Yield Curve"))
            fig.update_layout(height=360, yaxis_title="Yield (%)", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font={"color": theme["text"]}, margin=dict(l=12, r=12, t=20, b=12))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Treasury data loaded empty. Please refresh later.")
    else:
        st.warning("Treasury yields unavailable right now.")

st.markdown("""<div class="footer">Educational only. Not financial advice. Best use: decide whether to buy more, normal, or smaller with taxable cash.</div>""", unsafe_allow_html=True)
