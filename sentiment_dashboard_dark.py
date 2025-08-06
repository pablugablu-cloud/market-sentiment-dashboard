import os
import streamlit as st
import yfinance as yf
from ta.momentum import RSIIndicator
from pytrends.request import TrendReq
from newsapi import NewsApiClient
from dotenv import load_dotenv
import requests

load_dotenv()

st.set_page_config(page_title="Market Sentiment Dashboard (API-Only)", layout="wide")
st.title("📊 Market Sentiment Dashboard (API-Only, Reliable)")
st.caption("Buffett, Tom Lee, Meme Market Sentiment. For learning, not advice.")
st.markdown("---")

##########################
# Data Functions
##########################

def fetch_vix():
    try:
        df = yf.Ticker("^VIX").history(period="5d")
        vix = round(df["Close"].iloc[-1], 2)
        return vix
    except Exception as e:
        st.warning(f"VIX unavailable: {e}")
        return None

def fetch_rsi():
    try:
        df = yf.Ticker("^GSPC").history(period="2mo", interval="1d")
        df["rsi"] = RSIIndicator(df["Close"]).rsi()
        rsi = round(df["rsi"].iloc[-1], 2)
        return rsi
    except Exception as e:
        st.warning(f"RSI unavailable: {e}")
        return None

def fetch_google_trends(term="stock market crash"):
    try:
        py = TrendReq(hl="en-US", tz=360)
        py.build_payload([term], timeframe="now 7-d")
        df = py.interest_over_time()
        if len(df) > 0:
            val = int(df[term].iloc[-1])
            return val
        else:
            return None
    except Exception as e:
        st.warning(f"Google Trends unavailable: {e}")
        return None

def fetch_news_sentiment():
    key = os.getenv("NEWSAPI_KEY", "")
    if not key:
        st.warning("No NewsAPI key found. Set NEWSAPI_KEY env variable.")
        return None, "No API Key"
    try:
        na = NewsApiClient(api_key=key)
        arts = na.get_everything(q="stock market", language="en", page_size=25)["articles"]
        bears = ["crash", "panic", "recession", "sell-off", "bear market"]
        bulls = ["rally", "bullish", "surge", "record high", "soar"]
        b_score = sum(any(w in a["title"].lower() for w in bears) for a in arts)
        u_score = sum(any(w in a["title"].lower() for w in bulls) for a in arts)
        score = max(0, min(100, 50 + (u_score - b_score) * 2))
        lbl = "Bullish" if score > 60 else "Bearish" if score < 40 else "Mixed"
        return score, lbl
    except Exception as e:
        st.warning(f"NewsAPI error: {e}")
        return None, "Error"

##############################
# Main Metrics - Only APIs!
##############################
vix_val = fetch_vix()
rsi_val = fetch_rsi()
trends_val = fetch_google_trends()
news_val, news_lbl = fetch_news_sentiment()

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
        with st.expander(f"ℹ️ What is {name}?"):
            st.write(desc)

##############################
# Buffett & Tom Lee Signals
##############################
def buffett_signal(vix, rsi, trends, news):
    # Only use available data!
    fear = 0
    if vix is not None and vix > 28: fear += 1
    if trends is not None and trends > 80: fear += 1
    if news is not None and news < 35: fear += 1
    if rsi is not None and rsi < 35 and fear >= 2:
        return "🟢 Buffett: Really Good Time to Buy (Be Greedy When Others Are Fearful)"
    if rsi is not None and rsi < 40 and fear >= 1:
        return "🟡 Buffett: Good Time to Accumulate, Be Patient"
    if (
        rsi is not None and 40 <= rsi <= 60
        and vix is not None and 16 < vix < 28
        and news is not None and 35 <= news <= 65
    ):
        return "⚪ Buffett: Wait, Stay Patient (No Edge)"
    if (
        rsi is not None and rsi > 70
        and news is not None and news > 60
        and trends is not None and trends < 20
    ):
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

st.markdown("## 🧭 Buffett-Style Long-Term Investor Signal")
st.success(buffett_signal(vix_val, rsi_val, trends_val, news_val))
with st.expander("Buffett Philosophy"):
    st.markdown("> *Be fearful when others are greedy, and greedy when others are fearful.*  \n— Warren Buffett")

st.markdown("## 📈 Tom Lee (Fundstrat) Tactical Signal")
st.info(tomlee_signal(vix_val, rsi_val, trends_val, news_val))
with st.expander("Tom Lee Style"):
    st.markdown("> *When everyone is cautious, that’s when opportunity strikes. The market often climbs a wall of worry.*  \n— Tom Lee (paraphrased)")

##############################
# Social/Meme/Bond/Options Data (Read Me!)
##############################
st.markdown("---")
st.markdown("### 🚀 Meme & Social Trends")
st.warning("Reddit, Stocktwits, and meme stock APIs require OAuth/authentication as of 2025. \n"
           "**Add your own API credentials to enable this. Free unauthenticated access is now forbidden or unreliable.**")

st.markdown("### 🏦 Bonds & Put/Call Ratio")
st.warning("US Treasury and CBOE data APIs are now mostly paid, gated, or require authentication. For professional dashboards, use a market data API like Barchart, Intrinio, Refinitiv, or similar.")

with st.expander("How To Add More (Reddit/Stocktwits/Options/Bonds)"):
    st.markdown("""
- **Reddit:** Register for an API key [here](https://www.reddit.com/prefs/apps), use PRAW or requests with OAuth.
- **Stocktwits:** [API Docs](https://api.stocktwits.com/developers/docs/api).
- **Put/Call Ratio:** Use a paid data vendor, or scrape YCharts (when possible).
- **Bond Yields:** Use [FRED API](https://fred.stlouisfed.org/docs/api/fred/) or a paid market data provider.
- **Production/Trading Use:** For reliable signals, use institutional-grade data feeds!
    """)

st.markdown("---")
st.warning("For educational purposes only. Not financial advice. Most 'retail' meme/option/bond APIs are now paid or require login. For robust dashboards, register for API access or use paid data feeds.")

if st.button("🔄 Refresh Data"):
    st.rerun()

