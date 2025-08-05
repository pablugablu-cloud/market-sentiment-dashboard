import os
import requests
import streamlit as st
import yfinance as yf
from ta.momentum import RSIIndicator
from pytrends.request import TrendReq
from newsapi import NewsApiClient
from dotenv import load_dotenv
from collections import Counter
import re

load_dotenv()

# --------------- US Ticker Loading ---------------

@st.cache_data(show_spinner=False, persist="disk")
def load_all_us_tickers():
    # Download once from NASDAQ FTP, or load static lists. Fast enough for Streamlit
    urls = [
        "https://data.nasdaq.com/api/v3/datasets/WIKI/prices.csv?api_key=demo",  # placeholder, not exhaustive
        "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt",
        "https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt",
        # fallback, see also https://old.nasdaq.com/screening/companies-by-name.aspx?letter=0&exchange=nasdaq
    ]
    tickers = set()
    # Parse NASDAQ and NYSE tickers
    for url in urls[1:]:
        try:
            resp = requests.get(url, timeout=10)
            lines = resp.text.splitlines()
            for line in lines[1:]:
                symbol = line.split('|')[0]
                if symbol.isalpha() and 1 < len(symbol) <= 5:
                    tickers.add(symbol)
        except Exception:
            continue
    # Add S&P 500 (hardcoded as backup)
    sp500_tickers = [
        "AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA", "BRK.B", "AVGO", "LLY", "JPM", "V", "UNH", "XOM", "MA",
        "PG", "JNJ", "GOOG", "HD", "MRK", "CVX", "COST", "ABBV", "MCD", "ADBE", "PEP", "CRM", "BAC", "WMT", "NFLX",
        "KO", "LIN", "DIS", "AMD", "T", "VZ", "PYPL", "ORCL", "PFE", "SBUX", "NKE", "INTC", "BA", "CMCSA"
    ]
    tickers.update(sp500_tickers)
    return tickers

US_TICKERS = load_all_us_tickers()

# --------------- Streamlit UI Setup ---------------

st.set_page_config(
    page_title="Market Sentiment Dashboard (Buffett & Tom Lee)",
    layout="wide",
)
st.title("📊 Market Sentiment Dashboard")
st.caption("Buffett & Tom Lee sentiment signals + Real-Time Meme Stock Radar (WSB)")
st.markdown("---")

# --------------- Core Data Functions ---------------

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

# ----------- Production-Grade Meme Radar -----------

def fetch_wsb_meme_tickers(limit=20):
    url = f"https://www.reddit.com/r/wallstreetbets/hot/.json?limit={limit}"
    headers = {"User-Agent": "Mozilla/5.0 (compatible; MemeRadarBot/1.0)"}
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        posts = resp.json().get("data", {}).get("children", [])
    except Exception as e:
        st.warning(f"Reddit fetch error: {e}")
        return []
    EXCLUDE = {
        "YOLO", "WSB", "DD", "ETF", "USD", "ALL", "GAIN", "LOSS", "PUT", "CALL", "NEWS", "THE", "DAILY", "THREAD",
        "Q", "EPS", "GAAP", "PORT", "AI", "SPY", "PORTFOLIO", "STOCK", "USA", "AMAZON", "GAIN", "LOSS"
    }
    ticker_pat = re.compile(r'\$?([A-Za-z]{2,5})\b')
    mentions = []
    for post in posts:
        data = post.get("data", {})
        text = f"{data.get('title','')} {data.get('selftext','')}"
        found = ticker_pat.findall(text)
        for match in found:
            tkr = match.upper()
            if tkr in US_TICKERS and tkr not in EXCLUDE:
                mentions.append(tkr)
    counts = Counter(mentions)
    return counts.most_common(7) if counts else []

# ----------- Data Fetch Section -----------
with st.spinner("Loading market sentiment..."):
    vix_val = fetch_vix()
    rsi_val = fetch_rsi()
    trends_val = fetch_google_trends()
    news_val, news_lbl = fetch_news_sentiment()
    meme_tickers = fetch_wsb_meme_tickers()

# ----------- UI Layout -----------

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

# ----------- Meme Stock Radar UI -----------
st.markdown("## 🚀 Meme Stock Radar (WSB Hotlist)")
if meme_tickers:
    for tkr, cnt in meme_tickers:
        st.markdown(f"- **{tkr}**  — mentioned `{cnt}` times in WSB hot posts")
else:
    st.info("No trending meme tickers found (try again soon).")
with st.expander("How is this calculated?"):
    st.write("We scan WSB hot post titles & bodies for US stock tickers (validated against NASDAQ/NYSE lists). Shows what's getting the most WSB attention today!")

# ----------- Buffett & Tom Lee Signals -----------
def buffett_style_signal(vix, rsi, trends, news):
    fear_count = 0
    if vix is not None and vix > 28: fear_count += 1
    if trends is not None and trends > 80: fear_count += 1
    if news is not None and news < 35: fear_count += 1

    if rsi is not None and rsi < 35 and fear_count >= 2:
        return "🟢 Buffett: Really Good Time to Buy (Be Greedy When Others Are Fearful)"

    if rsi is not None and rsi < 40 and fear_count >= 1:
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

# --- Buffett Tracker ---
st.markdown("## 🧭 Buffett-Style Long-Term Investor Signal")
st.success(buffett_style_signal(vix_val, rsi_val, trends_val, news_val))
with st.expander("Buffett Philosophy"):
    st.markdown("> *Be fearful when others are greedy, and greedy when others are fearful.*  \n— Warren Buffett")

# --- Tom Lee Tracker ---
st.markdown("## 📈 Tom Lee (Fundstrat) Tactical Signal")
st.info(tomlee_signal(vix_val, rsi_val, trends_val, news_val))
with st.expander("Tom Lee Style"):
    st.markdown("> *When everyone is cautious, that’s when opportunity strikes. The market often climbs a wall of worry.*  \n— Tom Lee (Fundstrat, paraphrased)")

# --- Footer ---
st.markdown("---")
st.markdown("### ⚠️ Disclaimer")
st.warning(
    "For educational purposes only. Not financial advice. Use at your own risk. These signals use sentiment, volatility, and momentum for illustration only — not for trading or portfolio management."
)
if st.button("🔄 Refresh Data"):
    st.rerun()

