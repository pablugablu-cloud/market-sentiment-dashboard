import os
import streamlit as st
import yfinance as yf
from ta.momentum import RSIIndicator
from pytrends.request import TrendReq
from newsapi import NewsApiClient
from dotenv import load_dotenv
import plotly.graph_objects as go

load_dotenv()
st.set_page_config(
    page_title="Market Sentiment Dashboard (Pro)",
    layout="wide",
)

# --- Modern Minimal CSS ---
st.markdown("""
    <style>
    html, body, [class*="css"]  { font-family: 'Inter', 'Segoe UI', Arial, sans-serif !important; background: #f7f9fb; }
    .big-metric { font-size: 2.15rem !important; font-weight: 800; margin: 0.18em 0 0.2em 0;}
    .signal-card { background: #fff; border-radius: 1.1em; box-shadow: 0 3px 20px 0 rgba(40,55,70,0.06);
        padding: 1.2em 1.2em 0.5em 1.5em; margin-bottom: 1.3em; border-left: 7px solid #cfd8df;}
    .tomlee-card { border-left: 7px solid #225DF1; }
    .buffett-card { border-left: 7px solid #19bb77; }
    .signal-label { font-size: 1.07rem; font-weight: 700; color: #33465f; margin-bottom: 0.18em;}
    .refresh-button button { background: #225DF1 !important; color: white !important; font-weight: 700 !important;
        border-radius: 1.3em !important; padding: 0.4em 2.2em !important; margin-top: 0.5em; margin-bottom: 1em;}
    .metric-title { font-size: 1rem !important; color: #6B7683; margin-bottom: -0.45em; margin-top: 1.3em; }
    .stProgress .st-bo { height: 20px !important; border-radius: 8px !important;}
    .stPlotlyChart { margin-bottom: -1.4em !important; }
    .disclaimer-pro { font-size: 0.99rem; color: #b08911; background: #fff7e6;
        border-radius: 0.7em; margin-top: 1.6em; padding: 0.55em 1em 0.55em 1.1em; border: 1px solid #f5e4c6;}
    .stExpanderHeader { font-weight: 700; color: #b08911; font-size:1.05rem;}
    </style>
""", unsafe_allow_html=True)

# ---- Page Title ----
st.markdown("""
    <div style="display:flex;align-items:center;">
        <img src="https://img.icons8.com/color/40/000000/combo-chart--v2.png" width="34" style="margin-right: 11px;"/>
        <span style="font-size:1.52rem;font-weight:900;letter-spacing:-1px;">Market Sentiment Dashboard</span>
    </div>
    <div style="font-size:1.01rem;color:#6d7893;margin-top:0.18em;">
        Modern risk snapshot inspired by Buffett and Tom Lee.<br>
        <span style="color:#A5AEBC;font-size:0.97rem;">
            Powered by VIX, RSI, Google Trends, News.
        </span>
    </div>
""", unsafe_allow_html=True)

# --- Data Functions ---
def fetch_vix():
    try:
        df = yf.Ticker("^VIX").history(period="5d")
        vix = round(df["Close"].iloc[-1], 2)
        return vix
    except Exception as e:
        st.error(f"VIX data unavailable: {e}")
        return None

def fetch_rsi():
    try:
        df = yf.Ticker("^GSPC").history(period="2mo", interval="1d")
        df["rsi"] = RSIIndicator(df["Close"]).rsi()
        rsi = round(df["rsi"].iloc[-1], 2)
        return rsi
    except Exception as e:
        st.error(f"RSI data unavailable: {e}")
        return None

def fetch_google_trends(term="stock market crash"):
    try:
        py = TrendReq(hl="en-US", tz=360)
        py.build_payload([term], timeframe="now 7-d")
        df = py.interest_over_time()
        val = int(df[term].iloc[-1])
        return val
    except Exception as e:
        st.warning(f"Google Trends not available: {e}")
        return None

def fetch_news_sentiment():
    key = os.getenv("NEWSAPI_KEY", "")
    if not key:
        st.warning("No NewsAPI key found. Set NEWSAPI_KEY environment variable.")
        return None, "No API Key"
    try:
        na = NewsApiClient(api_key=key)
        arts = na.get_everything(q="stock market", language="en", page_size=25)["articles"]
        bears = ["crash", "panic", "recession", "sell-off"]
        bulls = ["rally", "bullish", "surge", "record high"]
        b_score = sum(any(w in a["title"].lower() for w in bears) for a in arts)
        u_score = sum(any(w in a["title"].lower() for w in bulls) for a in arts)
        score = max(0, min(100, 50 + (u_score - b_score) * 2))
        lbl = "Bullish" if score > 60 else "Bearish" if score < 40 else "Mixed"
        return score, lbl
    except Exception as e:
        st.warning(f"NewsAPI error: {e}")
        return None, "Error"

# --- Fetch data ---
vix_val = fetch_vix()
rsi_val = fetch_rsi()
trends_val = fetch_google_trends()
news_val, news_lbl = fetch_news_sentiment()

# --- Minimalist Modern Plotly Dials ---
def modern_gauge(title, value, minval, maxval, thresholds, colorbands, maincolor="#1967D2"):
    # colorbands: list of (range, color)
    # value: if None, show '--'
    if value is None:
        value = minval
        number = {'prefix': '-- '}
    else:
        number = {'valueformat': '.1f'}
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        number=number,
        title={'text': title, 'font': {'size': 16, 'color': '#344055'}},
        gauge={
            'axis': {'range': [minval, maxval], 'tickwidth': 1.1, 'tickcolor': "#aaa", 'tickfont': {'size': 13}},
            'bar': {'color': maincolor, 'thickness': 0.22},
            'bgcolor': "#f7f9fb",
            'steps': [{'range': rng, 'color': col} for rng, col in colorbands],
            'threshold': {'line': {'color': maincolor, 'width': 2.4}, 'thickness': 0.7, 'value': value},
        }
    ))
    fig.update_layout(margin=dict(l=6, r=6, t=35, b=10), height=190)
    return fig

cols = st.columns(4)
with cols[0]:
    st.plotly_chart(modern_gauge(
        "VIX (Volatility)", vix_val, 10, 40,
        thresholds=[18, 25, 32],
        colorbands=[
            ([10, 18], "#ffe7eb"),
            ([18, 25], "#FFF6C7"),
            ([25, 32], "#E3F9D3"),
            ([32, 40], "#c8e8fa")
        ],
        maincolor="#6043ff"
    ), use_container_width=True)
    st.caption("<span style='color:#83899c;'>30+ = Elevated Fear</span>", unsafe_allow_html=True)
with cols[1]:
    st.plotly_chart(modern_gauge(
        "RSI (S&P 500)", rsi_val, 10, 90,
        thresholds=[30, 50, 70],
        colorbands=[
            ([10, 30], "#FFE9DC"),
            ([30, 50], "#F3F7F5"),
            ([50, 70], "#DEF8ED"),
            ([70, 90], "#f4e1e8")
        ],
        maincolor="#16bf6c"
    ), use_container_width=True)
    st.caption("<span style='color:#83899c;'>&gt;70 Overbought / &lt;35 Oversold</span>", unsafe_allow_html=True)
with cols[2]:
    st.plotly_chart(modern_gauge(
        "Google Trends", trends_val, 0, 100,
        thresholds=[30, 60, 80],
        colorbands=[
            ([0, 30], "#FFF3C1"),
            ([30, 60], "#F2F8FE"),
            ([60, 80], "#DEF8ED"),
            ([80, 100], "#FFE7E7")
        ],
        maincolor="#FCAA4A"
    ), use_container_width=True)
    st.caption("<span style='color:#83899c;'>Search: 'market crash'</span>", unsafe_allow_html=True)
with cols[3]:
    st.plotly_chart(modern_gauge(
        "News Sentiment", news_val, 0, 100,
        thresholds=[30, 50, 70],
        colorbands=[
            ([0, 30], "#FFE3D8"),
            ([30, 50], "#D4F0FF"),
            ([50, 70], "#E3F9D3"),
            ([70, 100], "#FDEBF9")
        ],
        maincolor="#3664F6"
    ), use_container_width=True)
    st.caption("<span style='color:#83899c;'>Headline Tone</span>", unsafe_allow_html=True)

# --- Buffett-Style Signal Logic ---
def buffett_style_signal(vix, rsi, trends, news):
    fear_count = 0
    if vix is not None and vix > 28: fear_count += 1
    if trends is not None and trends > 80: fear_count += 1
    if news is not None and news < 35: fear_count += 1
    if rsi is not None and rsi < 35 and fear_count >= 2:
        return "🟢 Buffett: Really Good Time to Buy (Be Greedy When Others Are Fearful)"
    if rsi is not None and rsi < 40 and fear_count >= 1:
        return "🟡 Buffett: Good Time to Accumulate, Be Patient"
    if (rsi is not None and 40 <= rsi <= 60 and vix is not None and 16 < vix < 28 and news is not None and 35 <= news <= 65):
        return "⚪ Buffett: Wait, Stay Patient (No Edge)"
    if (rsi is not None and rsi > 70 and news is not None and news > 60 and trends is not None and trends < 20):
        return "🔴 Buffett: Market Overheated, Wait for Pullback"
    return "🔴 Buffett: Hold Off (No Opportunity Detected)"

# --- Tom Lee (Fundstrat) Signal Logic ---
def tomlee_signal(vix, rsi, trends, news):
    bullish_score = 0
    if vix is not None and vix > 22: bullish_score += 1
    if rsi is not None and rsi < 45: bullish_score += 1
    if trends is not None and trends > 60: bullish_score += 1
    if news is not None and news < 50: bullish_score += 1
    if bullish_score >= 2:
        return "🟢 Tom Lee: Good Time to Buy (Buy the Dip Mentality)"
    if vix is not None and vix < 14 and rsi is not None and rsi > 70 and news is not None and news > 60:
        return "🔴 Tom Lee: Even Tom Lee says: Hold Off, Too Hot!"
    return "⚪ Tom Lee: Stay Invested or Accumulate Slowly"

# --- Buffett Card ---
st.markdown('<div class="signal-card buffett-card">', unsafe_allow_html=True)
st.markdown('<div class="signal-label">🧭 Buffett-Style Long-Term Investor Signal</div>', unsafe_allow_html=True)
st.markdown(f'<div class="big-metric">{buffett_style_signal(vix_val, rsi_val, trends_val, news_val)}</div>', unsafe_allow_html=True)
st.markdown('<div style="font-size:0.98rem;color:#5A6174;padding-top:0.58em;">'
            'Buffett Philosophy: <i>Be fearful when others are greedy, and greedy when others are fearful.</i></div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# --- Tom Lee Card ---
st.markdown('<div class="signal-card tomlee-card">', unsafe_allow_html=True)
st.markdown('<div class="signal-label">📈 Tom Lee (Fundstrat) Tactical Signal</div>', unsafe_allow_html=True)
st.markdown(f'<div class="big-metric">{tomlee_signal(vix_val, rsi_val, trends_val, news_val)}</div>', unsafe_allow_html=True)
st.markdown('<div style="font-size:0.98rem;color:#5A6174;padding-top:0.58em;">'
            "Tom Lee Style: <i>When everyone is cautious, that's when opportunity strikes. The market often climbs a wall of worry.</i></div>", unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# --- Disclaimer Collapsible ---
with st.expander("⚠️ Disclaimer (Tap to expand)", expanded=False):
    st.markdown("""
    <div class='disclaimer-pro'>
    <b>For educational purposes only. Not financial advice. Use at your own risk.</b>
    These signals use sentiment, volatility, and momentum for illustration only — not for trading or portfolio management.<br>
    <b>Legal Notice:</b> This dashboard is for general informational purposes and does not create a client relationship. Always consult your licensed advisor before acting.
    </div>
    """, unsafe_allow_html=True)

# --- Refresh Button ---
st.markdown('<div class="refresh-button">', unsafe_allow_html=True)
if st.button("🔄 Refresh Data"):
    st.rerun()
st.markdown('</div>', unsafe_allow_html=True)

