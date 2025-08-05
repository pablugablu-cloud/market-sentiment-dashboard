import os
import streamlit as st
import yfinance as yf
from ta.momentum import RSIIndicator
from pytrends.request import TrendReq
from newsapi import NewsApiClient
import requests
import re
from collections import Counter

# ---- Streamlit config ----
st.set_page_config(
    page_title="Market Sentiment Dashboard (Buffett & Tom Lee)",
    layout="wide",
)
st.title("📊 Market Sentiment Dashboard")
st.caption("Minimalist real-world snapshot inspired by Buffett & Tom Lee. Powered by VIX, RSI, Google Trends, News, and live WSB Meme Stock Radar.")
st.markdown("---")

# ---- Data Functions ----

def fetch_vix():
    try:
        df = yf.Ticker("^VIX").history(period="5d")
        vix = round(df["Close"].iloc[-1], 2)
        return vix
    except Exception as e:
        return None

def fetch_rsi():
    try:
        df = yf.Ticker("^GSPC").history(period="2mo", interval="1d")
        df["rsi"] = RSIIndicator(df["Close"]).rsi()
        rsi = round(df["rsi"].iloc[-1], 2)
        return rsi
    except Exception as e:
        return None

def fetch_google_trends(term="stock market crash"):
    try:
        py = TrendReq(hl="en-US", tz=360)
        py.build_payload([term], timeframe="now 7-d")
        df = py.interest_over_time()
        val = int(df[term].iloc[-1])
        return val
    except Exception as e:
        return None

def fetch_news_sentiment():
    key = os.getenv("NEWSAPI_KEY", "")
    if not key:
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
        return None, "Error"

# --- Reddit Meme Stock Radar ---
def fetch_wsb_meme_tickers(limit=50):
    """
    Fetch top hot posts from wallstreetbets and extract ticker mentions from titles.
    """
    url = f"https://www.reddit.com/r/wallstreetbets/hot/.json?limit={limit}"
    headers = {"User-Agent": "Mozilla/5.0 (compatible; MemeRadarBot/1.0)"}
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        posts = resp.json()["data"]["children"]
        ticker_pat = re.compile(r'\b([A-Z]{2,5})\b')
        EXCLUDE = {"YOLO", "WSB", "DD", "ETF", "USD", "THE", "ITM", "OTM", "ALL", "OPEN", "GAIN", "CALL", "PUT", "BIG", "LOSS", "CASH", "MOON"}
        mentions = []
        for post in posts:
            title = post["data"].get("title", "")
            for match in ticker_pat.findall(title):
                if match.isupper() and match not in EXCLUDE:
                    mentions.append(match)
        if not mentions:
            return []
        counts = Counter(mentions)
        return counts.most_common(5)
    except Exception as e:
        return []

# ---- Fetch Data ----
vix_val = fetch_vix()
rsi_val = fetch_rsi()
trends_val = fetch_google_trends()
news_val, news_lbl = fetch_news_sentiment()
meme_tickers = fetch_wsb_meme_tickers()

# ---- Display Metrics ----
cols = st.columns(4)
metrics = [
    ("VIX (Volatility)", vix_val, None, ">30 = Elevated Fear"),
    ("RSI (S&P 500)", rsi_val, None, ">70 Overbought / <35 Oversold"),
    ("Google Trends", trends_val, None, "Interest for 'stock market crash'"),
    ("News Sentiment", news_val, news_lbl, "Headline tone: bull vs bear"),
]
for col, (name, val, lbl, desc) in zip(cols, metrics):
    with col:
        display_val = val if val is not None else "N/A"
        display_delta = lbl or ""
        st.metric(f"**{name}**", value=display_val, delta=display_delta)
        if isinstance(val, (int, float)):
            st.progress(min(max(val / 100, 0.0), 1.0))
        with st.expander(f"ℹ️ What is {name}?"):
            st.write(desc)

# ---- Buffett Signal ----
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

# ---- Buffett Decision ----
st.markdown("## 🧭 Buffett-Style Long-Term Investor Signal")
buffett_decision = buffett_style_signal(vix_val, rsi_val, trends_val, news_val)
st.markdown(f"""
<div style="font-size:1.35em; font-weight:800; margin-top:-0.5em; margin-bottom:0.3em;">
    {buffett_decision}
</div>""", unsafe_allow_html=True)
with st.expander("Buffett Philosophy"):
    st.markdown("> *Be fearful when others are greedy, and greedy when others are fearful.*  \n— Warren Buffett")

# ---- Tom Lee Decision ----
st.markdown("## 📈 Tom Lee (Fundstrat) Tactical Signal")
tomlee_decision = tomlee_signal(vix_val, rsi_val, trends_val, news_val)
st.markdown(f"""
<div style="font-size:1.35em; font-weight:800; margin-top:-0.5em; margin-bottom:0.3em;">
    {tomlee_decision}
</div>""", unsafe_allow_html=True)
with st.expander("Tom Lee Style"):
    st.markdown("> *When everyone is cautious, that’s when opportunity strikes. The market often climbs a wall of worry.*  \n— Tom Lee (Fundstrat, paraphrased)")

# ---- Meme Stock Radar ----
st.markdown("## 🚀 Meme Stock Radar ([WSB Hotlist](https://www.reddit.com/r/wallstreetbets/hot/))")
if meme_tickers:
    st.markdown("**Top mentioned tickers in r/wallstreetbets hot posts:**")
    for rank, (ticker, count) in enumerate(meme_tickers, 1):
        st.markdown(f"- `{ticker}` &nbsp; <span style='color:#ffb900;font-weight:bold;'>{count} mentions</span>", unsafe_allow_html=True)
    st.caption("⚠️ These are *not* investment advice, just what's trending with the crowd.")
else:
    st.caption("No trending meme tickers found (try again soon).")

# ---- Disclaimer ----
st.markdown("---")
with st.expander("⚠️ Disclaimer (Tap to expand)", expanded=False):
    st.markdown("""
    <b>For educational purposes only. Not financial advice. Use at your own risk.</b><br>
    These signals use sentiment, volatility, and momentum for illustration only — not for trading or portfolio management.<br>
    <b>Legal Notice:</b> This dashboard is for general informational purposes and does not create a client relationship. Always consult your licensed advisor before acting.
    """, unsafe_allow_html=True)

if st.button("🔄 Refresh Data"):
    st.rerun()

