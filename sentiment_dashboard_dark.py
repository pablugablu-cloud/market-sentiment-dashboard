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


# ============================================================
# Theme
# ============================================================
if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = False

LIGHT = {
    "bg": "#f6f8fb",
    "surface": "#ffffff",
    "surface2": "#f9fafb",
    "text": "#111827",
    "muted": "#667085",
    "border": "rgba(17,24,39,.08)",
    "shadow": "0 18px 55px rgba(16,24,40,.08)",
    "green": "#16a34a",
    "yellow": "#f59e0b",
    "red": "#ef4444",
    "blue": "#2563eb",
}
DARK = {
    "bg": "#080b12",
    "surface": "#101622",
    "surface2": "#151c2a",
    "text": "#f8fafc",
    "muted": "#9ca3af",
    "border": "rgba(255,255,255,.09)",
    "shadow": "0 20px 60px rgba(0,0,0,.36)",
    "green": "#22c55e",
    "yellow": "#fbbf24",
    "red": "#fb7185",
    "blue": "#60a5fa",
}
T = DARK if st.session_state.dark_mode else LIGHT


def css(t):
    st.markdown(f"""
<style>
.stApp {{
    background:
      radial-gradient(circle at 0% 0%, rgba(37,99,235,.08), transparent 26%),
      radial-gradient(circle at 100% 0%, rgba(22,163,74,.08), transparent 26%),
      {t["bg"]};
    color: {t["text"]};
}}
[data-testid="stHeader"] {{ background: rgba(0,0,0,0); }}
[data-testid="stToolbar"] {{ display: none; }}
.block-container {{
    padding-top: 1.4rem;
    max-width: 1320px;
}}
div[data-testid="stButton"] button {{
    border-radius: 14px;
    border: 1px solid {t["border"]};
    background: {t["surface"]};
    color: {t["text"]};
    box-shadow: none;
    height: 42px;
}}
.hero {{
    background: {t["surface"]};
    border: 1px solid {t["border"]};
    border-radius: 28px;
    box-shadow: {t["shadow"]};
    padding: 28px 30px;
    margin: 10px 0 18px;
}}
.hero-title {{
    display: flex;
    align-items: center;
    gap: 12px;
    font-size: 40px;
    font-weight: 950;
    letter-spacing: -1.3px;
    color: {t["text"]};
}}
.hero-sub {{
    color: {t["muted"]};
    font-size: 14px;
    margin-top: 10px;
}}
.grid-card {{
    background: {t["surface"]};
    border: 1px solid {t["border"]};
    border-radius: 28px;
    box-shadow: {t["shadow"]};
    padding: 28px;
    min-height: 318px;
}}
.kicker {{
    color: {t["muted"]};
    font-size: 12px;
    font-weight: 900;
    text-transform: uppercase;
    letter-spacing: .75px;
}}
.action-word {{
    font-size: 48px;
    font-weight: 1000;
    letter-spacing: -1.8px;
    color: {t["text"]};
    line-height: 1;
    margin-top: 12px;
}}
.main-copy {{
    color: {t["text"]};
    font-size: 18px;
    line-height: 1.48;
    margin-top: 18px;
}}
.sub-copy {{
    color: {t["muted"]};
    font-size: 14px;
    line-height: 1.45;
    margin-top: 12px;
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
.badge-green {{ color: {t["green"]}; background: rgba(34,197,94,.12); border: 1px solid rgba(34,197,94,.18); }}
.badge-yellow {{ color: {t["yellow"]}; background: rgba(245,158,11,.13); border: 1px solid rgba(245,158,11,.20); }}
.badge-red {{ color: {t["red"]}; background: rgba(239,68,68,.12); border: 1px solid rgba(239,68,68,.18); }}
.badge-blue {{ color: {t["blue"]}; background: rgba(37,99,235,.12); border: 1px solid rgba(37,99,235,.18); }}

.score-card {{
    background: {t["surface"]};
    border: 1px solid {t["border"]};
    border-radius: 28px;
    box-shadow: {t["shadow"]};
    padding: 28px;
    min-height: 318px;
}}
.score-top {{
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 12px;
}}
.score-label {{
    color: {t["muted"]};
    font-size: 12px;
    font-weight: 900;
    text-transform: uppercase;
    letter-spacing: .75px;
}}
.score-number {{
    font-size: 86px;
    line-height: .9;
    font-weight: 1000;
    letter-spacing: -3px;
    color: {t["text"]};
}}
.score-status {{
    color: {t["text"]};
    font-size: 30px;
    font-weight: 950;
    letter-spacing: -1px;
    text-align: right;
}}
.meter {{
    position: relative;
    height: 18px;
    border-radius: 999px;
    overflow: hidden;
    margin-top: 34px;
    background: linear-gradient(90deg, {t["green"]} 0%, {t["green"]} 33%, {t["yellow"]} 33%, {t["yellow"]} 66%, {t["red"]} 66%, {t["red"]} 100%);
}}
.marker {{
    position: relative;
    width: 18px;
    height: 18px;
    border-radius: 999px;
    background: {t["text"]};
    border: 4px solid {t["surface"]};
    box-shadow: 0 8px 22px rgba(0,0,0,.25);
    margin-top: -18px;
}}
.scale {{
    display: flex;
    justify-content: space-between;
    color: {t["muted"]};
    font-size: 12px;
    font-weight: 800;
    margin-top: 11px;
}}
.score-note {{
    color: {t["muted"]};
    font-size: 15px;
    line-height: 1.45;
    margin-top: 26px;
}}
.section {{
    color: {t["text"]};
    font-size: 22px;
    font-weight: 950;
    letter-spacing: -.4px;
    margin: 22px 0 10px;
}}
.metric-card {{
    background: {t["surface"]};
    border: 1px solid {t["border"]};
    border-radius: 22px;
    box-shadow: 0 10px 32px rgba(16,24,40,.06);
    padding: 18px;
    min-height: 134px;
}}
.metric-name {{
    color: {t["muted"]};
    font-size: 12px;
    font-weight: 900;
    text-transform: uppercase;
    letter-spacing: .6px;
}}
.metric-value {{
    color: {t["text"]};
    font-size: 30px;
    font-weight: 950;
    margin-top: 5px;
}}
.metric-help {{
    color: {t["muted"]};
    font-size: 13px;
    line-height: 1.35;
    margin-top: 8px;
}}
.lens-card {{
    background: {t["surface"]};
    border: 1px solid {t["border"]};
    border-radius: 22px;
    box-shadow: 0 10px 32px rgba(16,24,40,.06);
    padding: 20px;
    min-height: 145px;
}}
.lens-head {{
    color: {t["text"]};
    font-size: 20px;
    font-weight: 950;
    margin-top: 4px;
}}
.lens-copy {{
    color: {t["muted"]};
    font-size: 14px;
    line-height: 1.42;
    margin-top: 8px;
}}
.footer {{
    color: {t["muted"]};
    font-size: 12px;
    margin-top: 24px;
    padding-top: 18px;
    border-top: 1px solid {t["border"]};
}}
.driver-card {{
    background: {t["surface"]};
    border: 1px solid {t["border"]};
    border-radius: 22px;
    box-shadow: 0 10px 32px rgba(16,24,40,.06);
    padding: 20px;
    min-height: 148px;
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
    font-size: 22px;
    font-weight: 950;
    margin-top: 7px;
    letter-spacing: -.4px;
}}
.driver-copy {{
    color: {t["muted"]};
    font-size: 14px;
    line-height: 1.42;
    margin-top: 9px;
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
}}
</style>
""", unsafe_allow_html=True)


css(T)


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


def label(score):
    if score is None:
        return "Unknown", "badge-blue"
    if score <= 20:
        return "Extreme Fear", "badge-green"
    if score <= 33:
        return "Fear", "badge-green"
    if score <= 66:
        return "Neutral", "badge-yellow"
    if score <= 80:
        return "Greed", "badge-red"
    return "Extreme Greed", "badge-red"


def action(score):
    if score is None:
        return "WAIT", "Data is incomplete. Use your normal buying plan until signals refresh cleanly.", "badge-blue"
    if score <= 20:
        return "BUY MORE", "Fear is high. This is a good setup to deploy a larger taxable tranche.", "badge-green"
    if score <= 33:
        return "BUY A LITTLE MORE", "Market sentiment is fearful. Slightly increase your scheduled buy.", "badge-green"
    if score <= 66:
        return "BUY NORMALLY", "No major edge. Keep the plan simple and stay consistent.", "badge-yellow"
    if score <= 80:
        return "BUY SMALLER", "Market is getting hot. Keep buying, but avoid a big lump-sum taxable buy.", "badge-red"
    return "DON’T CHASE", "Sentiment is stretched. Keep dry powder and wait for a better setup.", "badge-red"


def mini_class(name, value):
    if name == "VIX":
        if value is None: return "N/A", "badge-blue"
        if value < 14: return "Too Calm", "badge-red"
        if value < 20: return "Calm", "badge-yellow"
        if value < 28: return "Elevated", "badge-yellow"
        return "Fearful", "badge-green"
    if name == "RSI":
        if value is None: return "N/A", "badge-blue"
        if value < 35: return "Oversold", "badge-green"
        if value <= 65: return "Healthy", "badge-yellow"
        return "Hot", "badge-red"
    if name == "Trend":
        if value is None: return "N/A", "badge-blue"
        if value < -3: return "Below Trend", "badge-green"
        if value <= 8: return "Near Trend", "badge-yellow"
        return "Extended", "badge-red"
    if name == "PutCall":
        if value is None: return "N/A", "badge-blue"
        if value < .65: return "Greedy", "badge-red"
        if value <= 1.1: return "Balanced", "badge-yellow"
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


# ============================================================
# Data
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

    bears = ["crash","collapse","meltdown","plunge","sell-off","recession","slowdown","panic","fear","turmoil","bearish","volatility","losses","decline","drop","downgrade"]
    bulls = ["rally","surge","soar","rebound","recovery","growth","momentum","bullish","optimism","confidence","strength","record high","gains","outperform","upgrade"]
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



def human_signal_row(name, reading):
    if name == "VIX":
        if reading is None:
            return ["VIX", "Missing", "Volatility data unavailable", "Ignore for now"]
        if reading < 14:
            return ["VIX", fmt(reading), "Market is too calm", "Leans greedy"]
        if reading < 20:
            return ["VIX", fmt(reading), "Volatility is normal", "Neutral"]
        if reading < 28:
            return ["VIX", fmt(reading), "Some fear is showing up", "Slightly better buy setup"]
        return ["VIX", fmt(reading), "Fear is elevated", "Better buy setup"]

    if name == "RSI":
        if reading is None:
            return ["RSI", "Missing", "Momentum unavailable", "Ignore for now"]
        if reading < 35:
            return ["RSI", fmt(reading), "Market looks oversold", "Better buy setup"]
        if reading <= 65:
            return ["RSI", fmt(reading), "Momentum looks normal", "Neutral"]
        if reading <= 72:
            return ["RSI", fmt(reading), "Momentum is hot", "Buy smaller"]
        return ["RSI", fmt(reading), "Momentum is very hot", "Do not chase"]

    if name == "S&P vs 200D":
        if reading is None:
            return ["S&P vs 200D", "Missing", "Trend distance unavailable", "Ignore for now"]
        if reading < -8:
            return ["S&P vs 200D", fmt(reading, "%"), "Market is well below trend", "Better buy setup"]
        if reading < -2:
            return ["S&P vs 200D", fmt(reading, "%"), "Slightly below trend", "Slightly better buy setup"]
        if reading <= 8:
            return ["S&P vs 200D", fmt(reading, "%"), "Near normal trend", "Neutral"]
        return ["S&P vs 200D", fmt(reading, "%"), "Market looks stretched", "Buy smaller"]

    if name == "Put/Call":
        if reading is None:
            return ["Put/Call", "Missing", "Options sentiment unavailable", "Ignore for now"]
        if reading < 0.65:
            return ["Put/Call", fmt(reading), "Too much call buying / greed", "Buy smaller"]
        if reading <= 1.10:
            return ["Put/Call", fmt(reading), "Options positioning is balanced", "Neutral"]
        return ["Put/Call", fmt(reading), "More hedging / fear", "Better buy setup"]

    if name == "10Y-2Y":
        if reading is None:
            return ["10Y-2Y", "Missing", "Yield curve unavailable", "Ignore for now"]
        if reading < 0:
            return ["10Y-2Y", fmt(reading, "%", 3), "Macro backdrop is cautious", "Small caution"]
        return ["10Y-2Y", fmt(reading, "%", 3), "Macro backdrop is okay", "Small impact"]

    if name == "Google Trends":
        if reading is None:
            return ["Google Trends", "Missing", "Search sentiment unavailable", "Ignore for now"]
        if reading >= 60:
            return ["Google Trends", fmt(reading, "", 0), "Fear searches are rising", "Can improve buy setup"]
        return ["Google Trends", fmt(reading, "", 0), "No fear-search spike", "Small impact"]

    if name == "News":
        if reading is None:
            return ["News", "Missing", "Headline sentiment unavailable", "Ignore for now"]
        if reading > 60:
            return ["News", fmt(reading, "", 0), "Headlines are optimistic", "Slight caution"]
        if reading < 40:
            return ["News", fmt(reading, "", 0), "Headlines are negative", "Can improve buy setup"]
        return ["News", fmt(reading, "", 0), "Headline tone is mixed", "Small impact"]

    return [name, str(reading), "Unknown", "Neutral"]


def driver_severity(action_text):
    if action_text in ["Do not chase", "Buy smaller"]:
        return 4
    if action_text in ["Better buy setup", "Slightly better buy setup"]:
        return 3
    if action_text in ["Leans greedy", "Slight caution", "Small caution"]:
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
    rows = [
        {"Indicator":"VIX", "Reading":fmt(vix), "Score":score_from_range(vix, [(12,85),(18,62),(25,38),(35,15),(50,5)]), "Weight":.24, "Meaning":"Volatility/fear. High VIX usually improves entry points."},
        {"Indicator":"RSI", "Reading":fmt(rsi), "Score":score_from_range(rsi, [(25,10),(35,25),(50,50),(65,72),(75,90),(85,100)]), "Weight":.21, "Meaning":"Momentum temperature. High RSI means hot."},
        {"Indicator":"S&P vs 200D", "Reading":fmt(dist,"%"), "Score":score_from_range(dist, [(-20,8),(-10,20),(0,48),(8,68),(15,84),(25,96)]), "Weight":.21, "Meaning":"Distance from long-term trend."},
        {"Indicator":"Put/Call", "Reading":fmt(pcr), "Score":score_from_range(pcr, [(0.55,90),(.75,70),(.95,52),(1.15,35),(1.4,15)]), "Weight":.15, "Meaning":"Low can mean call chasing. High can mean fear."},
        {"Indicator":"10Y-2Y", "Reading":fmt(curve,"%",3), "Score":score_from_range(curve, [(-1.2,70),(-.5,58),(0,50),(.8,45),(1.5,48)]), "Weight":.07, "Meaning":"Macro context, not the whole decision."},
        {"Indicator":"Google Trends", "Reading":fmt(trends,"",0), "Score":score_from_range(trends, [(0,72),(20,62),(50,45),(80,25),(100,10)]), "Weight":.06, "Meaning":"Crash-search interest. Spikes imply public fear."},
        {"Indicator":"News", "Reading":fmt(news,"",0), "Score":news, "Weight":.06, "Meaning":"Optional headline tone."},
    ]
    df = pd.DataFrame(rows)
    good = df.dropna(subset=["Score"]).copy()
    if good.empty:
        return None, df
    good["AdjWeight"] = good["Weight"] / good["Weight"].sum()
    score = int(round((good["Score"] * good["AdjWeight"]).sum()))
    return int(clamp(score,0,100)), df


# ============================================================
# Controls
# ============================================================
c1, c2, c3 = st.columns([.70, .15, .15])
with c2:
    st.toggle("Dark mode", key="dark_mode")
with c3:
    if st.button("Refresh", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

T = DARK if st.session_state.dark_mode else LIGHT
css(T)

with st.spinner("Loading market read..."):
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
status, status_class = label(score)
act, act_copy, act_class = action(score)
marker_left = 0 if score is None else max(0, min(100, score))

# ============================================================
# UI
# ============================================================
st.markdown(f"""
<div class="hero">
  <div class="hero-title">📊 Market Sentiment Pro</div>
  <div class="hero-sub">A clean taxable-buying signal. One read first, details below. Updated {datetime.now().strftime("%b %d, %Y %I:%M %p")}.</div>
</div>
""", unsafe_allow_html=True)

left, right = st.columns([.52,.48])
with left:
    st.markdown(f"""
<div class="grid-card">
  <div class="kicker">Clear Action Read</div>
  <div class="action-word">{act}</div>
  <div class="badge {act_class}">{status} · {score if score is not None else "N/A"}/100</div>
  <div class="main-copy">{act_copy}</div>
  <div class="sub-copy"><b>Simple rule:</b> this is not a prediction machine. It only tells you whether your next taxable buy should be bigger, normal, smaller, or paused.</div>
</div>
""", unsafe_allow_html=True)

with right:
    st.markdown(f"""
<div class="score-card">
  <div class="score-top">
    <div>
      <div class="score-label">Fear & Greed Score</div>
      <div class="score-number">{score if score is not None else "N/A"}</div>
    </div>
    <div class="score-status">{status}</div>
  </div>
  <div class="meter"></div>
  <div class="marker" style="left: calc({marker_left}% - 9px);"></div>
  <div class="scale"><span>Fear</span><span>Neutral</span><span>Greed</span></div>
  <div class="score-note">Green means better buying conditions. Yellow means stay on plan. Red means avoid chasing large buys.</div>
</div>
""", unsafe_allow_html=True)

st.markdown('<div class="section">Quick Read</div>', unsafe_allow_html=True)
a,b,c,d = st.columns(4)
vix_b, vix_c = mini_class("VIX", vix)
rsi_b, rsi_c = mini_class("RSI", spx["rsi"])
trend_b, trend_c = mini_class("Trend", spx["dist"])
pcr_b, pcr_c = mini_class("PutCall", pcr)
with a:
    metric_card("VIX", fmt(vix), vix_b, vix_c, "Fear gauge. Higher = more fear.")
with b:
    metric_card("RSI", fmt(spx["rsi"]), rsi_b, rsi_c, "Momentum temperature.")
with c:
    metric_card("S&P vs 200D", fmt(spx["dist"], "%"), trend_b, trend_c, "How stretched the market is.")
with d:
    metric_card("Put/Call", fmt(pcr), pcr_b, pcr_c, "Options sentiment.")

st.markdown('<div class="section">Investor Lens</div>', unsafe_allow_html=True)
x,y,z = st.columns(3)
with x:
    st.markdown(f"""<div class="lens-card"><div class="kicker">Buffett Lens</div><div class="lens-head">Do not chase</div><div class="lens-copy">Great investors wait for better pitches. Red means patience. Green means start swinging in tranches.</div></div>""", unsafe_allow_html=True)
with y:
    st.markdown(f"""<div class="lens-card"><div class="kicker">Bogle Lens</div><div class="lens-head">Stay consistent</div><div class="lens-copy">Keep buying broad index funds. This app should size your buys, not turn you into a trader.</div></div>""", unsafe_allow_html=True)
with z:
    st.markdown(f"""<div class="lens-card"><div class="kicker">Tom Lee Lens</div><div class="lens-head">Respect momentum</div><div class="lens-copy">When markets are hot, avoid emotional lump sums. When fear spikes, tactical entry improves.</div></div>""", unsafe_allow_html=True)

st.markdown(f'<div class="section">Why the app says {act}</div>', unsafe_allow_html=True)
tab1, tab2, tab3 = st.tabs(["Why This Signal", "S&P Trend", "Treasury Curve"])
with tab1:
    st.markdown('<div class="clean-note">Plain-English explanation of the signal. The raw math is hidden below so the app feels like a product, not a spreadsheet.</div>', unsafe_allow_html=True)

    signal_df = build_driver_rows(vix, spx["rsi"], spx["dist"], pcr, curve, trends, news_score)
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

    st.markdown("#### All Signals")
    clean_df = signal_df.drop(columns=["_severity"])
    st.dataframe(clean_df, use_container_width=True, hide_index=True)

    with st.expander("Advanced scoring math"):
        raw_df = breakdown.copy()
        raw_df["Score"] = raw_df["Score"].apply(lambda x: "N/A" if pd.isna(x) else round(float(x), 1))
        raw_df["Weight"] = raw_df["Weight"].apply(lambda x: f"{int(round(float(x)*100))}%")
        st.dataframe(raw_df, use_container_width=True, hide_index=True)
with tab2:
    hist = spx["history"]
    fig = go.Figure()
    if "Date" in hist and "Close" in hist:
        fig.add_trace(go.Scatter(x=hist["Date"], y=hist["Close"], mode="lines", name="S&P 500"))
    if "Date" in hist and "SMA_200" in hist:
        fig.add_trace(go.Scatter(x=hist["Date"], y=hist["SMA_200"], mode="lines", name="200D SMA"))
    fig.update_layout(height=390, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font={"color":T["text"]}, margin=dict(l=10,r=10,t=20,b=10), legend=dict(orientation="h"))
    st.plotly_chart(fig, use_container_width=True)
with tab3:
    if yields:
        order = ["US1M","US2M","US3M","US4M","US6M","US1Y","US2Y","US3Y","US5Y","US7Y","US10Y","US20Y","US30Y"]
        ydf = pd.DataFrame([{"Maturity":m, "Yield (%)":yields.get(m)} for m in order if yields.get(m) is not None])
        st.dataframe(ydf, use_container_width=True, hide_index=True)
        if not ydf.empty:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=ydf["Maturity"], y=ydf["Yield (%)"], mode="lines+markers", name="Yield"))
            fig.update_layout(height=350, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font={"color":T["text"]}, margin=dict(l=10,r=10,t=20,b=10))
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Treasury yields unavailable right now.")

st.markdown('<div class="footer">Educational only. Not financial advice. Best use: decide whether to buy more, normally, smaller, or not chase.</div>', unsafe_allow_html=True)
