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

# ---- Custom CSS ----
st.markdown("""
    <style>
    html, body, [class*="css"]  {
        font-family: 'Inter', 'Segoe UI', Arial, sans-serif !important;
        background: #FAFBFC;
    }
    .big-metric {
        font-size: 2.7rem !important;
        font-weight: 800;
        margin: 0.35em 0 0.2em 0;
    }
    .signal-card {
        background: #FFFFFF;
        border-radius: 1.1em;
        box-shadow: 0 6px 24px 0 rgba(40,55,70,0.08);
        padding: 2em 2em 1.2em 2em;
        margin-bottom: 2em;
        border: 1.5px solid #f1f1f1;
    }
    .tomlee-card { border-left: 7px solid #3664F6; }
    .buffett-card { border-left: 7px solid #16BF6C; }
    .signal-label {
        font-size: 1.18rem;
        font-weight: 700;
        letter-spacing: .01em;
        margin-bottom: 0.3em;
    }
    .refresh-button button {
        background: #3664F6 !important;
        color: white !important;
        font-weight: 700 !important;
        border-radius: 1.3em !important;
        padding: 0.4em 2em !important;
        margin-top: 0.8em;
        margin-bottom: 1em;
    }
    .metric-title {
        font-size: 1.07rem !important;
        color: #6B7683;
        margin-bottom: -0.7em;
        margin-top: 1.4em;
    }
    .stProgress .st-bo {
        height: 22px !important;
        border-radius: 8px !important;
    }
    </style>
""", unsafe_allow_html=True)

# ---- Page Title ----
st.markdown("""
    <div style="display:flex;align-items:center;">
        <img src="https://img.icons8.com/color/48/000000/combo-chart--v2.png" width="40" style="margin-right: 13px;"/>
        <span style="font-size:2.1rem;font-weight:900;letter-spacing:-1px;">Market Sentiment Dashboard</span>
    </div>
    <div style="font-size:1.07rem;color:#83899C;margin-top:0.18em;">
        See how Buffett and Tom Lee might interpret current risk signals.<br>
        <span style="color:#B8BAC7;font-size:1rem;">
            Powered by VIX, RSI, Google Trends, News Sentiment.
        </span>
    </div>
""", unsafe_allow_html=True)

st.markdown("")

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

# --- Beautiful Meters: Plotly dials for each metric ---
def dial_gauge(title, value, minval, maxval, color, thresholds):
    if value is None:
        value = 0
    fig = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = value,
        domain = {'x': [0, 1], 'y': [0, 1]},
        title = {'text': title, 'font': {'size': 17}},
        gauge = {
            'axis': {'range': [minval, maxval], 'tickwidth': 1, 'tickcolor': "darkgray"},
            'bar': {'color': color, 'thickness': 0.23},
            'steps': [
                {'range': [minval, thresholds[0]], 'color': "#F65164"},
                {'range': [thresholds[0], thresholds[1]], 'color': "#FFA539"},
                {'range': [thresholds[1], thresholds[2]], 'color': "#49C586"},
                {'range': [thresholds[2], maxval], 'color': "#10E6BC"},
            ],
        }
    ))
    fig.update_layout(margin=dict(l=8, r=8, b=3, t=40), height=210)
    return fig

cols = st.columns(4)
with cols[0]:
    st.plotly_chart(
        dial_gauge("VIX (Volatility)", vix_val, 10, 40, "#7D57FF", [18, 25, 32]),
        use_container_width=True
    )
    st.caption(">30 = Elevated Fear")
with cols[1]:
    st.plotly_chart(
        dial_gauge("RSI (S&P 500)", rsi_val, 10, 90, "#16BF6C", [30, 50, 70]),
        use_container_width=True
    )
    st.caption(">70 Overbought / <35 Oversold")
with cols[2]:
    st.plotly_chart(
        dial_gauge("Google Trends", trends_val, 0, 100, "#FCAA4A", [30, 60, 80]),
        use_container_width=True
    )
    st.caption("Search interest for 'stock market crash'")
with cols[3]:
    st.plotly_chart(
        dial_gauge("News Sentiment", news_val, 0, 100, "#3664F6", [30, 50, 70]),
        use_container_width=True
    )
    st.caption("Headline tone: bull vs bear")

st.markdown("")

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
st.markdown('<div style="font-size:0.98rem;color:#5A6174;padding-top:0.7em;">'
            'Buffett Philosophy: <i>Be fearful when others are greedy, and greedy when others are fearful.</i></div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# --- Tom Lee Card ---
st.markdown('<div class="signal-card tomlee-card">', unsafe_allow_html=True)
st.markdown('<div class="signal-label">📈 Tom Lee (Fundstrat) Tactical Signal</div>', unsafe_allow_html=True)
st.markdown(f'<div class="big-metric">{tomlee_signal(vix_val, rsi_val, trends_val, news_val)}</div>', unsafe_allow_html=True)
st.markdown('<div style="font-size:0.98rem;color:#5A6174;padding-top:0.7em;">'
            "Tom Lee Style: <i>When everyone is cautious, that's when opportunity strikes. The market often climbs a wall of worry.</i></div>", unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# --- Disclaimer ---
st.markdown("### ⚠️ Disclaimer")
st.warning(
    "For educational purposes only. Not financial advice. Use at your own risk. "
    "These signals use sentiment, volatility, and momentum for illustration only — not for trading or portfolio management."
)

# --- Refresh Button (Styled) ---
st.markdown('<div class="refresh-button">', unsafe_allow_html=True)
if st.button("🔄 Refresh Data"):
    st.rerun()
st.markdown('</div>', unsafe_allow_html=True)
