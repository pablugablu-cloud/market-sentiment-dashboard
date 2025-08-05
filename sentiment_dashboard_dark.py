import os
import re
import requests
import streamlit as st
import yfinance as yf
from ta.momentum import RSIIndicator
from pytrends.request import TrendReq
from newsapi import NewsApiClient
from dotenv import load_dotenv

# ----------- LOAD ENV VARIABLES -----------
load_dotenv()

# ----------- STREAMLIT SETUP -----------
st.set_page_config(
    page_title="Market Sentiment Dashboard (Buffett & Tom Lee)",
    layout="wide",
    initial_sidebar_state="auto"
)

st.title("📊 Market Sentiment Dashboard")
st.caption("Buffett & Tom Lee signals + Market Volatility, Google Trends, News, and WSB Meme Radar")
st.markdown("---")

# ----------- DATA FUNCTIONS -----------

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
        bears = ["crash", "panic", "recession", "sell-off", "fear", "collapse"]
        bulls = ["rally", "bullish", "surge", "record high", "optimism"]
        b_score = sum(any(w in a["title"].lower() for w in bears) for a in arts)
        u_score = sum(any(w in a["title"].lower() for w in bulls) for a in arts)
        score = max(0, min(100, 50 + (u_score - b_score) * 2))
        lbl = "Bullish" if score > 60 else "Bearish" if score < 40 else "Mixed"
        return score, lbl
    except Exception as e:
        st.warning(f"NewsAPI error: {e}")
        return None, "Error"

def fetch_wsb_meme_tickers():
    """
    Scrapes /r/wallstreetbets 'hot' posts and returns most mentioned tickers in the last 25 posts.
    Returns a list of (ticker, post title, upvotes).
    """
    url = "https://www.reddit.com/r/wallstreetbets/hot/.json?limit=25"
    headers = {
        "User-Agent": "Mozilla/5.0 (MarketSentimentDashboard/1.0; +https://github.com/your-repo)"
    }

    # Get US stock tickers set for robust matching
    @st.cache_resource
    def load_all_tickers():
        try:
            tickers = yf.tickers_sp500()
            all_tickers = set(tickers)
            # Add some common meme tickers missed from S&P500
            all_tickers.update(["GME", "AMC", "PLTR", "TSLA", "BBBY", "NVDA", "HOOD", "BB", "ROKU", "CLOV", "AAPL", "SPY"])
            return all_tickers
        except Exception:
            # Fallback: Just use popular meme tickers if Yahoo fails
            return set(["GME", "AMC", "PLTR", "TSLA", "BBBY", "NVDA", "HOOD", "BB", "ROKU", "CLOV", "AAPL", "SPY"])

    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 429:
            return "rate_limit"
        if resp.status_code != 200:
            return f"error:{resp.status_code}"
        data = resp.json()
        posts = data["data"]["children"]
        all_titles = [p["data"]["title"] for p in posts if "title" in p["data"]]
        all_selftexts = [p["data"]["selftext"] for p in posts if "selftext" in p["data"]]
        combined = all_titles + all_selftexts
        text = " ".join(combined)

        tickers = load_all_tickers()
        ticker_pat = re.compile(r"\b([A-Z]{2,5})\b")
        found = ticker_pat.findall(text)
        freq = {}
        for t in found:
            if t in tickers:
                freq[t] = freq.get(t, 0) + 1
        if not freq:
            return []
        sorted_tickers = sorted(freq.items(), key=lambda x: -x[1])[:10]

        # Find post titles mentioning those tickers (for display)
        ticker_to_title = {}
        for p in posts:
            title = p["data"]["title"]
            upvotes = p["data"]["ups"]
            for t, _ in sorted_tickers:
                if t in title:
                    ticker_to_title[t] = (title, upvotes)
        result = []
        for t, count in sorted_tickers:
            title, upvotes = ticker_to_title.get(t, ("N/A", 0))
            result.append((t, count, title, upvotes))
        return result
    except requests.exceptions.RequestException as e:
        st.warning(f"Reddit fetch error: {e}")
        return "network_error"
    except Exception as e:
        st.warning(f"Reddit parsing error: {e}")
        return "parse_error"

# ----------- FETCH DATA -----------
vix_val = fetch_vix()
rsi_val = fetch_rsi()
trends_val = fetch_google_trends()
news_val, news_lbl = fetch_news_sentiment()
wsb_meme = fetch_wsb_meme_tickers()

# ----------- DISPLAY METRICS -----------

cols = st.columns(4)
metrics = [
    ("VIX (Volatility)", vix_val, None, ">30 = Elevated Fear"),
    ("RSI (S&P 500)", rsi_val, None, ">70 Overbought / <35 Oversold"),
    ("Google Trends", trends_val, None, "Interest for 'stock market crash' (last 7d)"),
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

# ----------- BUFFETT SIGNAL -----------
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

# ----------- TOM LEE SIGNAL -----------
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

# ----------- BUFFETT & TOM LEE UI -----------
st.markdown("## 🧭 Buffett-Style Long-Term Investor Signal")
st.success(buffett_style_signal(vix_val, rsi_val, trends_val, news_val))
with st.expander("Buffett Philosophy"):
    st.markdown("> *Be fearful when others are greedy, and greedy when others are fearful.*  \n— Warren Buffett")

st.markdown("## 📈 Tom Lee (Fundstrat) Tactical Signal")
st.info(tomlee_signal(vix_val, rsi_val, trends_val, news_val))
with st.expander("Tom Lee Style"):
    st.markdown("> *When everyone is cautious, that’s when opportunity strikes. The market often climbs a wall of worry.*  \n— Tom Lee (Fundstrat, paraphrased)")

# ----------- WSB MEME RADAR UI -----------
st.markdown("## 🚀 Meme Stock Radar (WSB Hotlist)")
if wsb_meme == "rate_limit":
    st.warning("Reddit API Rate Limited (Try again in 1-2 minutes).")
elif isinstance(wsb_meme, str) and wsb_meme.startswith("error"):
    code = wsb_meme.split(":")[1]
    st.warning(f"Reddit returned status code {code}. Try again later.")
elif wsb_meme == "network_error":
    st.warning("Could not fetch Reddit posts (Network Error).")
elif wsb_meme == "parse_error":
    st.warning("Could not parse Reddit response. Format may have changed.")
elif not wsb_meme or (isinstance(wsb_meme, list) and len(wsb_meme) == 0):
    st.info("No trending meme tickers found (try again soon).")
else:
    st.write("Top tickers from recent /r/wallstreetbets hot posts (auto-detected):")
    for t, count, title, upvotes in wsb_meme:
        st.write(f"**{t}** — Mentioned {count} times | 🔺Upvotes: {upvotes}\n> _{title}_")

with st.expander("ℹ️ How Meme Stock Radar works"):
    st.write(
        "Scrapes hot posts from r/wallstreetbets and auto-detects all valid US tickers mentioned. Only tickers that match official exchanges or common meme tickers are counted for high confidence."
    )

# ----------- DISCLAIMER -----------

st.markdown("---")
st.markdown("### ⚠️ Disclaimer")
st.warning(
    "For educational purposes only. Not financial advice. Use at your own risk. These signals use sentiment, volatility, and momentum for illustration only — not for trading or portfolio management."
)

if st.button("🔄 Refresh Data"):
    st.rerun()

