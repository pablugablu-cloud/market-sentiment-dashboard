import os
import streamlit as st
import yfinance as yf
from ta.momentum import RSIIndicator
from pytrends.request import TrendReq
from newsapi import NewsApiClient
from dotenv import load_dotenv
import requests
import re
from collections import Counter

load_dotenv()

st.set_page_config(
    page_title="Market Sentiment Dashboard (Buffett & Tom Lee)",
    layout="wide",
)
st.title("📊 Market Sentiment Dashboard")
st.caption("See how Buffett and Tom Lee might interpret current risk signals. Powered by VIX, RSI, Google Trends, News Sentiment, and Reddit Meme Stock Radar.")
st.markdown("---")

### US TICKER SETUP (for high-confidence meme radar filtering)
@st.cache_data(show_spinner=False)
def load_us_tickers():
    # Use yfinance's built-in tickers; you can also update this to your own CSV if you want
    tickers = set()
    try:
        from yfinance import tickers_sp500, tickers_nasdaq, tickers_dow
        for fetch in [tickers_sp500, tickers_nasdaq, tickers_dow]:
            tickers.update([x.upper() for x in fetch()])
    except Exception:
        # fallback if yfinance changes
        tickers.update(["AAPL","TSLA","MSFT","NVDA","GME","AMC","PLTR","SPY","QQQ","AMD","META","AMZN","GOOG","NFLX","ROKU"])
    return tickers
US_TICKERS = load_us_tickers()

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

def fetch_wsb_meme_tickers(limit=20):
    url = f"https://www.reddit.com/r/wallstreetbets/hot/.json?limit={limit}"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/115.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json"
    }
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code != 200:
            st.warning(f"Reddit returned status code {resp.status_code}. Try again later.")
            return []
        # Reddit will return HTML if rate limited
        if not resp.headers.get("Content-Type", "").startswith("application/json"):
            st.warning("Reddit returned non-JSON (rate limited or blocked). Try again in a few minutes.")
            return []
        posts = resp.json().get("data", {}).get("children", [])
    except Exception as e:
        st.warning(f"Reddit fetch error: {e}")
        return []

    # Heuristic: Only show likely real tickers
    EXCLUDE = {
        "YOLO", "WSB", "DD", "ETF", "USD", "ALL", "GAIN", "LOSS", "PUT", "CALL", "NEWS", "THE", "DAILY", "THREAD",
        "Q", "EPS", "GAAP", "PORT", "AI", "USA", "STOCK", "PORTFOLIO", "STOCKS"
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

# --- Fetch data ---
vix_val = fetch_vix()
rsi_val = fetch_rsi()
trends_val = fetch_google_trends()
news_val, news_lbl = fetch_news_sentiment()
meme_tickers = fetch_wsb_meme_tickers()

# --- Display metrics + meters ---
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

# --- Meme Stock Radar ---
st.markdown("## 🚀 Meme Stock Radar (WSB Hotlist)")
if meme_tickers:
    st.write("Top trending tickers on r/wallstreetbets right now:")
    for i, (tkr, count) in enumerate(meme_tickers, 1):
        st.write(f"**{i}. [{tkr}](https://finance.yahoo.com/quote/{tkr})** &mdash; {count} mentions")
else:
    st.info("No trending meme tickers found (try again soon).")
with st.expander("How are meme stocks detected?"):
    st.write("We scan recent hot posts on r/wallstreetbets for US stock tickers. Only actual tickers are counted, using a filter against S&P500/NASDAQ/DOW listings.")

st.markdown("---")
st.markdown("### ⚠️ Disclaimer")
st.warning(
    "For educational purposes only. Not financial advice. Use at your own risk. These signals use sentiment, volatility, and momentum for illustration only — not for trading or portfolio management."
)

if st.button("🔄 Refresh Data"):
    st.rerun()

