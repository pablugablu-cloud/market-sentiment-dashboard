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
# Page Setup
# ============================================================
st.set_page_config(
    page_title="Market Sentiment Pro",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ============================================================
# CSS
# ============================================================
st.markdown(
    """
<style>
    .stApp {
        background:
            radial-gradient(circle at 8% 5%, rgba(52, 152, 219, .16), transparent 26%),
            radial-gradient(circle at 92% 6%, rgba(46, 204, 113, .13), transparent 28%),
            linear-gradient(135deg, #070b14 0%, #0d1324 52%, #060914 100%);
        color: #f7f9fc;
    }

    [data-testid="stHeader"] { background: rgba(0,0,0,0); }
    [data-testid="stToolbar"] { display: none; }

    .block-container {
        padding-top: 2.0rem;
        padding-bottom: 3rem;
        max-width: 1500px;
    }

    .hero {
        border: 1px solid rgba(255,255,255,.10);
        border-radius: 28px;
        padding: 28px 30px;
        background: linear-gradient(135deg, rgba(255,255,255,.11), rgba(255,255,255,.035));
        box-shadow: 0 22px 70px rgba(0,0,0,.34);
        margin-bottom: 18px;
    }

    .hero h1 {
        font-size: 46px;
        line-height: 1.02;
        margin: 0 0 6px 0;
        letter-spacing: -1.3px;
        color: #ffffff;
    }

    .muted {
        color: rgba(247,249,252,.70);
        font-size: 14px;
    }

    .action {
        border-radius: 28px;
        padding: 26px 28px;
        border: 1px solid rgba(255,255,255,.12);
        background:
            linear-gradient(135deg, rgba(255,255,255,.12), rgba(255,255,255,.05)),
            radial-gradient(circle at top right, rgba(46,204,113,.16), transparent 34%);
        box-shadow: 0 22px 70px rgba(0,0,0,.30);
        min-height: 345px;
    }

    .action-title {
        color: rgba(247,249,252,.72);
        font-size: 13px;
        font-weight: 900;
        letter-spacing: .8px;
        text-transform: uppercase;
        margin-bottom: 8px;
    }

    .action-headline {
        color: #ffffff;
        font-size: 36px;
        font-weight: 950;
        line-height: 1.06;
        letter-spacing: -1px;
        margin-bottom: 10px;
    }

    .action-body {
        color: rgba(247,249,252,.80);
        font-size: 17px;
        line-height: 1.45;
        margin-top: 10px;
    }

    .pill {
        display: inline-block;
        padding: 7px 12px;
        border-radius: 999px;
        font-weight: 900;
        font-size: 12px;
        letter-spacing: .2px;
        margin-top: 8px;
    }

    .pill-green {
        background: rgba(0, 194, 123, .17);
        color: #49e89f;
        border: 1px solid rgba(73,232,159,.25);
    }

    .pill-blue {
        background: rgba(80, 154, 255, .16);
        color: #8dbdff;
        border: 1px solid rgba(141,189,255,.24);
    }

    .pill-yellow {
        background: rgba(255, 190, 70, .18);
        color: #ffd173;
        border: 1px solid rgba(255,209,115,.24);
    }

    .pill-red {
        background: rgba(255, 85, 85, .17);
        color: #ff9292;
        border: 1px solid rgba(255,146,146,.25);
    }

    .card {
        border: 1px solid rgba(255,255,255,.10);
        border-radius: 22px;
        padding: 18px 18px;
        background: rgba(255,255,255,.055);
        box-shadow: 0 12px 34px rgba(0,0,0,.24);
        min-height: 136px;
    }

    .label {
        color: rgba(247,249,252,.62);
        font-size: 12px;
        font-weight: 900;
        letter-spacing: .6px;
        text-transform: uppercase;
    }

    .value {
        color: #ffffff;
        font-size: 31px;
        font-weight: 950;
        margin-top: 3px;
        letter-spacing: -.5px;
    }

    .explain {
        color: rgba(247,249,252,.70);
        font-size: 13px;
        margin-top: 7px;
        line-height: 1.35;
    }

    .lens {
        border: 1px solid rgba(255,255,255,.10);
        border-radius: 22px;
        padding: 19px;
        background: rgba(255,255,255,.055);
        box-shadow: 0 12px 34px rgba(0,0,0,.23);
        min-height: 170px;
    }

    .lens-title {
        color: rgba(247,249,252,.66);
        font-size: 12px;
        font-weight: 950;
        letter-spacing: .6px;
        text-transform: uppercase;
    }

    .lens-head {
        color: #fff;
        font-size: 22px;
        font-weight: 950;
        margin-top: 4px;
        margin-bottom: 7px;
    }

    .lens-body {
        color: rgba(247,249,252,.74);
        font-size: 14px;
        line-height: 1.45;
    }

    .section-title {
        margin-top: 20px;
        margin-bottom: 10px;
        font-size: 24px;
        font-weight: 950;
        color: #ffffff;
        letter-spacing: -.3px;
    }

    .footer {
        color: rgba(247,249,252,.53);
        font-size: 12px;
        margin-top: 28px;
        padding-top: 18px;
        border-top: 1px solid rgba(255,255,255,.08);
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }

    .stTabs [data-baseweb="tab"] {
        border-radius: 999px;
        padding: 8px 16px;
        background: rgba(255,255,255,.06);
        border: 1px solid rgba(255,255,255,.08);
    }

    div[data-testid="stDataFrame"] {
        border-radius: 18px;
        overflow: hidden;
    }
</style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# Utility
# ============================================================
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


def score_from_range(value, points):
    value = safe_float(value)
    if value is None:
        return None

    points = sorted(points, key=lambda item: item[0])

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
    if score <= 24:
        return "Extreme Fear", "pill-green"
    if score <= 44:
        return "Fear", "pill-green"
    if score <= 60:
        return "Neutral", "pill-blue"
    if score <= 75:
        return "Greed", "pill-yellow"
    return "Extreme Greed", "pill-red"


def fmt(value, suffix="", digits=2):
    value = safe_float(value)
    if value is None:
        return "N/A"
    if digits == 0:
        return f"{value:,.0f}{suffix}"
    return f"{value:,.{digits}f}{suffix}"


def card(title, value, status, css_class, explanation):
    st.markdown(
        f"""
<div class="card">
    <div class="label">{title}</div>
    <div class="value">{value}</div>
    <div class="pill {css_class}">{status}</div>
    <div class="explain">{explanation}</div>
</div>
        """,
        unsafe_allow_html=True,
    )


def classify_vix(vix):
    if vix is None:
        return "Unavailable", "pill-blue"
    if vix < 14:
        return "Complacency", "pill-red"
    if vix < 20:
        return "Calm", "pill-blue"
    if vix < 28:
        return "Elevated Fear", "pill-yellow"
    return "High Fear", "pill-green"


def classify_rsi(rsi):
    if rsi is None:
        return "Unavailable", "pill-blue"
    if rsi < 35:
        return "Oversold", "pill-green"
    if rsi < 45:
        return "Soft", "pill-green"
    if rsi <= 65:
        return "Healthy", "pill-blue"
    if rsi <= 72:
        return "Hot", "pill-yellow"
    return "Overbought", "pill-red"


def classify_pcr(pcr):
    if pcr is None:
        return "Unavailable", "pill-blue"
    if pcr < 0.65:
        return "Call Chasing", "pill-red"
    if pcr < 0.85:
        return "Optimistic", "pill-yellow"
    if pcr <= 1.10:
        return "Balanced", "pill-blue"
    return "Fearful", "pill-green"


def classify_distance(distance):
    if distance is None:
        return "Unavailable", "pill-blue"
    if distance < -10:
        return "Deep Discount", "pill-green"
    if distance < -3:
        return "Below Trend", "pill-green"
    if distance <= 8:
        return "Near Trend", "pill-blue"
    if distance <= 15:
        return "Extended", "pill-yellow"
    return "Very Extended", "pill-red"


def classify_curve(spread):
    if spread is None:
        return "Unavailable", "pill-blue"
    if spread < -0.50:
        return "Inverted", "pill-yellow"
    if spread < 0:
        return "Slight Inversion", "pill-yellow"
    return "Normal", "pill-blue"


# ============================================================
# Data Fetchers
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
    sma200 = safe_round(last["SMA_200"], 2)

    distance_200d = None
    if close is not None and sma200 not in [None, 0]:
        distance_200d = safe_round(((close - sma200) / sma200) * 100, 2)

    df = df.reset_index()
    if "Date" not in df.columns:
        df = df.rename(columns={df.columns[0]: "Date"})

    return {
        "close": close,
        "rsi": rsi,
        "sma200": sma200,
        "distance_200d": distance_200d,
        "history": df,
    }


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

    bear_words = [
        "crash", "collapse", "meltdown", "plunge", "sell-off", "recession", "slowdown",
        "downturn", "panic", "fear", "turmoil", "risk-off", "bearish", "volatility",
        "instability", "losses", "decline", "drop", "slump", "downgrade"
    ]
    bull_words = [
        "rally", "surge", "soar", "rebound", "recovery", "growth", "momentum",
        "bullish", "optimism", "confidence", "risk-on", "strength", "resilient",
        "record high", "all-time high", "gains", "advance", "outperform", "upgrade"
    ]

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


# ============================================================
# Scoring
# ============================================================
def build_score(vix, rsi, distance_200d, pcr, curve_spread, trends, news_score):
    # 0 = fear/opportunity, 100 = greed/overheated.
    rows = [
        {
            "Indicator": "VIX",
            "Reading": fmt(vix, "", 2),
            "Score": score_from_range(vix, [(12, 85), (18, 62), (25, 38), (35, 15), (50, 5)]),
            "Weight": 0.24,
            "Why it matters": "Volatility/fear. High VIX usually means better forward entry points."
        },
        {
            "Indicator": "RSI",
            "Reading": fmt(rsi, "", 2),
            "Score": score_from_range(rsi, [(25, 10), (35, 25), (50, 50), (65, 72), (75, 90), (85, 100)]),
            "Weight": 0.21,
            "Why it matters": "Momentum temperature. High RSI means hot; low RSI means washed out."
        },
        {
            "Indicator": "S&P vs 200D",
            "Reading": fmt(distance_200d, "%", 2),
            "Score": score_from_range(distance_200d, [(-20, 8), (-10, 20), (0, 48), (8, 68), (15, 84), (25, 96)]),
            "Weight": 0.21,
            "Why it matters": "How stretched the index is versus its long-term trend."
        },
        {
            "Indicator": "Put/Call Ratio",
            "Reading": fmt(pcr, "", 2),
            "Score": score_from_range(pcr, [(0.55, 90), (0.75, 70), (0.95, 52), (1.15, 35), (1.40, 15)]),
            "Weight": 0.15,
            "Why it matters": "Low ratio can mean call chasing/greed. High ratio can mean hedging/fear."
        },
        {
            "Indicator": "10Y - 2Y Curve",
            "Reading": fmt(curve_spread, "%", 3),
            "Score": score_from_range(curve_spread, [(-1.2, 70), (-0.5, 58), (0, 50), (0.8, 45), (1.5, 48)]),
            "Weight": 0.07,
            "Why it matters": "Macro backdrop. This modifies risk but should not drive the whole decision."
        },
        {
            "Indicator": "Google Trends",
            "Reading": fmt(trends, "", 0),
            "Score": score_from_range(trends, [(0, 72), (20, 62), (50, 45), (80, 25), (100, 10)]),
            "Weight": 0.06,
            "Why it matters": "Public fear proxy. Crash-search spikes usually mean sentiment is fearful."
        },
        {
            "Indicator": "News Sentiment",
            "Reading": fmt(news_score, "", 0),
            "Score": news_score,
            "Weight": 0.06,
            "Why it matters": "Headline tone. Useful, but noisy and optional."
        },
    ]

    df = pd.DataFrame(rows)
    available = df.dropna(subset=["Score"]).copy()

    if available.empty:
        return None, df

    total_weight = available["Weight"].sum()
    available["AdjWeight"] = available["Weight"] / total_weight
    composite = int(round((available["Score"] * available["AdjWeight"]).sum()))
    return int(clamp(composite, 0, 100)), df


def action_read(score, rsi, vix, distance_200d):
    if score is None:
        return (
            "Data incomplete",
            "Do not make a big taxable move from partial data. Stick with your normal DCA until the dashboard refreshes cleanly.",
            "pill-blue",
        )

    if score <= 24:
        return (
            "Really good setup to buy in tranches",
            "Fear is elevated. This is when disciplined long-term investors can put taxable cash to work. I would not go all-in, but I would deploy a meaningful tranche.",
            "pill-green",
        )

    if score <= 44:
        return (
            "Good accumulation zone",
            "Market sentiment is giving you a better-than-normal entry. Continue DCA and consider a slightly larger tranche if this fits your cash plan.",
            "pill-green",
        )

    if score <= 60:
        return (
            "Neutral — follow the plan",
            "Nothing is screaming panic or euphoria. This is a boring DCA environment. Do not overthink it.",
            "pill-blue",
        )

    if score <= 75:
        return (
            "Greed building — slow down big buys",
            "Market is leaning hot. Scheduled buys are fine, but I would avoid a large taxable lump-sum unless you are comfortable ignoring near-term drawdowns.",
            "pill-yellow",
        )

    return (
        "Too hot — do not chase",
        "This is the zone where portfolios feel amazing and discipline gets weak. Keep dry powder, use smaller scheduled buys, and wait for RSI/sentiment to cool.",
        "pill-red",
    )


# ============================================================
# Simple top controls only
# ============================================================
top_left, top_right = st.columns([0.78, 0.22])
with top_right:
    if st.button("🔄 Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()


# ============================================================
# Fetch Data
# ============================================================
with st.spinner("Loading clean market read..."):
    spx = fetch_sp500()
    vix = fetch_vix()
    pcr = fetch_pcr()
    yields = fetch_yields()
    trends = fetch_google_trends("stock market crash")
    news_score, news_label = fetch_news_sentiment()

if spx is None:
    st.error("Could not load S&P 500 data from Yahoo Finance. Refresh in a few minutes.")
    st.stop()

spx_close = spx["close"]
rsi = spx["rsi"]
sma200 = spx["sma200"]
distance_200d = spx["distance_200d"]

us2y = yields.get("US2Y") if yields else None
us10y = yields.get("US10Y") if yields else None
curve_spread = safe_round(us10y - us2y, 3) if us2y is not None and us10y is not None else None

score, components = build_score(vix, rsi, distance_200d, pcr, curve_spread, trends, news_score)
sentiment_label, sentiment_class = score_label(score)
headline, guidance, action_class = action_read(score, rsi, vix, distance_200d)


# ============================================================
# Header
# ============================================================
st.markdown(
    f"""
<div class="hero">
    <h1>📊 Market Sentiment Pro</h1>
    <div class="muted">
        Clean taxable-investing dashboard using Fear & Greed, valuation stretch, volatility, options sentiment, macro, and trend.
        Last refreshed: {datetime.now().strftime("%b %d, %Y %I:%M %p")}
    </div>
</div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# Clear Action Read at Top
# ============================================================
left, right = st.columns([0.55, 0.45])

with left:
    st.markdown(
        f"""
<div class="action">
    <div class="action-title">Clear Action Read</div>
    <div class="action-headline">{headline}</div>
    <div class="pill {action_class}">{sentiment_label} · Score {score if score is not None else "N/A"}/100</div>
    <div class="action-body">{guidance}</div>
    <div class="action-body">
        <b>Plain English:</b> Use this to size taxable tranches, not to predict the exact bottom.
        The winning behavior is disciplined deployment, not emotional all-in/all-out moves.
    </div>
</div>
        """,
        unsafe_allow_html=True,
    )

with right:
    gauge = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=score if score is not None else 50,
            number={"font": {"size": 58}},
            title={"text": f"Fear & Greed: {sentiment_label}", "font": {"size": 22}},
            gauge={
                "axis": {"range": [0, 100], "tickwidth": 1},
                "bar": {"thickness": 0.18},
                "steps": [
                    {"range": [0, 25], "color": "rgba(0, 194, 123, .55)"},
                    {"range": [25, 45], "color": "rgba(78, 205, 128, .40)"},
                    {"range": [45, 60], "color": "rgba(120, 150, 180, .35)"},
                    {"range": [60, 75], "color": "rgba(255, 190, 70, .45)"},
                    {"range": [75, 100], "color": "rgba(255, 85, 85, .50)"},
                ],
            },
        )
    )
    gauge.update_layout(
        height=345,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "#f7f9fc"},
        margin=dict(l=16, r=16, t=54, b=10),
    )
    st.plotly_chart(gauge, use_container_width=True)


# ============================================================
# Signal Cards
# ============================================================
st.markdown('<div class="section-title">Signal Board</div>', unsafe_allow_html=True)

c1, c2, c3, c4, c5 = st.columns(5)

vix_label, vix_class = classify_vix(vix)
rsi_label, rsi_class = classify_rsi(rsi)
dist_label, dist_class = classify_distance(distance_200d)
pcr_label, pcr_class = classify_pcr(pcr)
news_css = "pill-red" if news_score is not None and news_score > 65 else "pill-green" if news_score is not None and news_score < 40 else "pill-blue"

with c1:
    card("VIX", fmt(vix), vix_label, vix_class, "Higher VIX = more fear. Fear can improve forward buying odds.")
with c2:
    card("RSI", fmt(rsi), rsi_label, rsi_class, "Momentum temperature. Over 70 is hot; under 35 is washed out.")
with c3:
    card("S&P vs 200D", fmt(distance_200d, "%"), dist_label, dist_class, "Shows whether the index is stretched above trend.")
with c4:
    card("Put/Call", fmt(pcr), pcr_label, pcr_class, "Low = call chasing. High = hedging/fear.")
with c5:
    card("News Sentiment", fmt(news_score, "", 0), news_label, news_css, "Optional. Works when NEWSAPI_KEY is set.")


# ============================================================
# Investor Lenses
# ============================================================
st.markdown('<div class="section-title">Investor Lens</div>', unsafe_allow_html=True)

l1, l2, l3 = st.columns(3)

if score is not None and score <= 44:
    buffett_text = "Be greedy when others are fearful — but with tranches, not hero moves."
    buffett_class = "pill-green"
elif score is not None and score >= 76:
    buffett_text = "Do not chase a market that is already celebrating. Wait for a better pitch."
    buffett_class = "pill-red"
else:
    buffett_text = "Patience is acceptable. You do not need to swing at every market."
    buffett_class = "pill-blue"

with l1:
    st.markdown(
        f"""
<div class="lens">
    <div class="lens-title">Buffett Lens</div>
    <div class="lens-head">Patience + Price</div>
    <div class="pill {buffett_class}">Valuation discipline</div>
    <div class="lens-body">{buffett_text}</div>
</div>
        """,
        unsafe_allow_html=True,
    )

with l2:
    st.markdown(
        """
<div class="lens">
    <div class="lens-title">Bogle Lens</div>
    <div class="lens-head">Stay Invested</div>
    <div class="pill pill-blue">Process beats timing</div>
    <div class="lens-body">Keep buying broad index funds. This dashboard should guide tranche sizing, not turn you into a trader.</div>
</div>
        """,
        unsafe_allow_html=True,
    )

if rsi is not None and vix is not None and rsi < 45 and vix > 20:
    tom_text = "Dip setup detected. Tactical buying has a better risk/reward."
    tom_class = "pill-green"
elif rsi is not None and rsi > 70 and vix is not None and vix < 16:
    tom_text = "Momentum is hot and fear is low. Tactical risk/reward is less attractive."
    tom_class = "pill-red"
else:
    tom_text = "Stay invested. No screaming panic, no screaming euphoria."
    tom_class = "pill-blue"

with l3:
    st.markdown(
        f"""
<div class="lens">
    <div class="lens-title">Tom Lee Lens</div>
    <div class="lens-head">Tactical Read</div>
    <div class="pill {tom_class}">Momentum setup</div>
    <div class="lens-body">{tom_text}</div>
</div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# Charts / Tables
# ============================================================
st.markdown('<div class="section-title">Data Details</div>', unsafe_allow_html=True)
tab1, tab2, tab3 = st.tabs(["Score Breakdown", "S&P 500 Trend", "Treasury Curve"])

with tab1:
    display_components = components.copy()
    display_components["Score"] = display_components["Score"].apply(lambda x: "N/A" if pd.isna(x) else round(float(x), 1))
    display_components["Weight"] = display_components["Weight"].apply(lambda x: f"{int(round(float(x) * 100))}%")
    st.dataframe(display_components, use_container_width=True, hide_index=True)

    chart_components = components.copy()
    chart_components["Score"] = pd.to_numeric(chart_components["Score"], errors="coerce")
    chart_components = chart_components.dropna(subset=["Score"])

    if not chart_components.empty:
        fig = go.Figure()
        fig.add_trace(
            go.Bar(
                x=chart_components["Indicator"],
                y=chart_components["Score"],
                text=chart_components["Score"].round(0),
                textposition="outside",
                name="Greed Score",
            )
        )
        fig.update_layout(
            height=390,
            yaxis=dict(range=[0, 105], title="0 = Fear / 100 = Greed"),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font={"color": "#f7f9fc"},
            margin=dict(l=12, r=12, t=24, b=12),
        )
        st.plotly_chart(fig, use_container_width=True)

with tab2:
    history = spx["history"].copy()
    fig = go.Figure()

    if "Date" in history.columns and "Close" in history.columns:
        fig.add_trace(go.Scatter(x=history["Date"], y=history["Close"], mode="lines", name="S&P 500"))

    if "Date" in history.columns and "SMA_200" in history.columns:
        fig.add_trace(go.Scatter(x=history["Date"], y=history["SMA_200"], mode="lines", name="200D SMA"))

    fig.update_layout(
        height=440,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "#f7f9fc"},
        margin=dict(l=12, r=12, t=24, b=12),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    st.plotly_chart(fig, use_container_width=True)

with tab3:
    if yields:
        order = ["US1M", "US2M", "US3M", "US4M", "US6M", "US1Y", "US2Y", "US3Y", "US5Y", "US7Y", "US10Y", "US20Y", "US30Y"]
        rows = []
        for maturity in order:
            y = yields.get(maturity)
            if y is not None:
                rows.append({"Maturity": maturity, "Yield (%)": y})

        ydf = pd.DataFrame(rows)

        if not ydf.empty and "Maturity" in ydf.columns and "Yield (%)" in ydf.columns:
            st.dataframe(ydf, use_container_width=True, hide_index=True)

            fig = go.Figure()
            fig.add_trace(
                go.Scatter(
                    x=ydf["Maturity"],
                    y=ydf["Yield (%)"],
                    mode="lines+markers",
                    name="Yield",
                )
            )
            fig.update_layout(
                height=390,
                yaxis_title="Yield (%)",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font={"color": "#f7f9fc"},
                margin=dict(l=12, r=12, t=24, b=12),
            )
            st.plotly_chart(fig, use_container_width=True)

            curve_status, curve_class = classify_curve(curve_spread)
            st.markdown(
                f"""
<div class="card">
    <div class="label">Yield Curve Read</div>
    <div class="value">{fmt(curve_spread, "%", 3)}</div>
    <div class="pill {curve_class}">{curve_status}</div>
    <div class="explain">10Y minus 2Y spread. Useful macro context, but not a standalone buy/sell signal.</div>
</div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.warning("Treasury yield table loaded empty. Refresh later.")
    else:
        st.warning("Treasury yields unavailable right now. The dashboard still works without this input.")


# ============================================================
# Footer
# ============================================================
st.markdown(
    """
<div class="footer">
    Educational only. Not financial advice. Data can be delayed, missing, or temporarily blocked by providers.
    Best use: decide whether to deploy taxable cash in small, normal, or larger tranches.
</div>
    """,
    unsafe_allow_html=True,
)
