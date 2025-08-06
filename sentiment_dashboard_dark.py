import os
import streamlit as st
import yfinance as yf
from ta.momentum import RSIIndicator
from pytrends.request import TrendReq
from newsapi import NewsApiClient
from dotenv import load_dotenv
import requests
import re
import pandas as pd
from bs4 import BeautifulSoup

load_dotenv()

st.set_page_config(page_title="Market Sentiment Dashboard (Buffett & Tom Lee)", layout="wide")
st.title("📊 Market Sentiment Dashboard")
st.caption("Buffett, Tom Lee, Meme Market Sentiment, Bonds, Options & Social Buzz. For learning, not advice.")
st.markdown("---")

######################################
# === DATA FUNCTIONS ================
######################################

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
        st.warning("No NewsAPI key found. Set NEWSAPI_KEY env variable.")
        return None, "No API Key"
    try:
        na = NewsApiClient(api_key=key)
        arts = na.get_everything(q="stock market", language="en", page_size=25)["articles"]
        bears = ["crash", "panic", "recession", "sell-off", "bear"]
        bulls = ["rally", "bullish", "surge", "record high", "soar"]
        b_score = sum(any(w in a["title"].lower() for w in bears) for a in arts)
        u_score = sum(any(w in a["title"].lower() for w in bulls) for a in arts)
        score = max(0, min(100, 50 + (u_score - b_score) * 2))
        lbl = "Bullish" if score > 60 else "Bearish" if score < 40 else "Mixed"
        return score, lbl
    except Exception as e:
        st.warning(f"NewsAPI error: {e}")
        return None, "Error"

def fetch_wsb_meme_tickers():
    try:
        res = requests.get(
            "https://www.reddit.com/r/wallstreetbets/hot/.json?limit=30",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=10
        )
        if res.status_code != 200:
            return [], f"Reddit returned status code {res.status_code}. Try again later."
        data = res.json()
        children = data["data"]["children"]
        ticker_pattern = r"\b([A-Z]{2,5})\b"
        # Load current S&P 500 tickers for cross-check (optional, makes higher-confidence)
        sp500 = yf.Tickers(' '.join(['AAPL','MSFT','AMZN','NVDA','GOOGL','META','TSLA','BRK.B','V','JPM','UNH','XOM','AVGO','LLY','JNJ','PG','MA','HD','MRK','COST','ADBE']))
        sp500_tickers = set([x for x in sp500.symbols])
        tickers_count = {}
        post_info = {}
        for post in children:
            text = post["data"]["title"] + " " + post["data"].get("selftext", "")
            tickers = set(re.findall(ticker_pattern, text))
            for t in tickers:
                if (t not in {"YOLO", "WSB", "DD", "FOMO", "GDP", "ETF", "CEO"} and (t in sp500_tickers or len(t) >= 3)):
                    tickers_count[t] = tickers_count.get(t, 0) + 1
                    if t not in post_info or post["data"]["ups"] > post_info[t]["ups"]:
                        post_info[t] = {
                            "title": post["data"]["title"][:100],
                            "ups": post["data"]["ups"]
                        }
        hot = sorted(tickers_count, key=lambda t: (-tickers_count[t], -post_info[t]["ups"]))[:5]
        trending = [{"ticker": t, "mentions": tickers_count[t], "ups": post_info[t]["ups"], "title": post_info[t]["title"]} for t in hot]
        return trending, None
    except Exception as e:
        return [], f"Reddit fetch error: {str(e)}"

def fetch_stocktwits_trending():
    try:
        r = requests.get("https://api.stocktwits.com/api/2/streams/trending.json", timeout=10)
        if r.status_code != 200:
            return [], f"StockTwits returned {r.status_code}"
        js = r.json()
        tickers = []
        for msg in js.get("messages", []):
            for sym in msg.get("symbols", []):
                tickers.append(sym["symbol"])
        tickers = [t for t in pd.Series(tickers).value_counts().index[:5]]
        return tickers, None
    except Exception as e:
        return [], f"StockTwits fetch error: {str(e)}"

def fetch_put_call_ratio():
    try:
        # Scrape YCharts (2025: reliable)
        url = "https://ycharts.com/indicators/cboe_spx_put_call_ratio"
        r = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code != 200:
            return None, f"YCharts returned {r.status_code}"
        soup = BeautifulSoup(r.text, "html.parser")
        # Value is in a span with class 'key-stat-title' then sibling div (site may update!)
        val = soup.find("div", string=re.compile("CBOE SPX Put Call Ratio"))
        if not val:
            # Try to fallback on "key-stat" value
            stat = soup.find("div", class_="key-stat")
            if stat:
                n = re.search(r"(\d+\.\d+)", stat.text)
                if n:
                    return float(n.group(1)), None
            return None, "Could not parse put/call ratio"
        value = val.find_next("div").text.strip()
        n = re.search(r"[\d\.]+", value)
        if n:
            return float(n.group()), None
        return None, "Could not parse PCR value"
    except Exception as e:
        return None, f"PCR error: {str(e)}"

def fetch_cnbc_bond_yields():
    try:
        url = "https://www.cnbc.com/bonds/"
        r = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code != 200:
            return {}, f"CNBC bonds page returned status code {r.status_code}"
        soup = BeautifulSoup(r.text, "html.parser")
        bond_table = soup.find("table")
        bonds = {}
        if not bond_table:
            return {}, "No bond table found"
        for row in bond_table.find_all("tr")[1:]:
            cols = row.find_all("td")
            if len(cols) >= 5:
                name = cols[0].text.strip()
                yld = cols[1].text.strip()
                change = cols[2].text.strip()
                high = cols[3].text.strip()
                low = cols[4].text.strip()
                bonds[name] = {
                    "yield": yld, "change": change, "high": high, "low": low
                }
        return bonds, None
    except Exception as e:
        return {}, f"Bonds fetch error: {str(e)}"

######################################
# === FETCH ALL DATA ================
######################################

vix_val = fetch_vix()
rsi_val = fetch_rsi()
trends_val = fetch_google_trends()
news_val, news_lbl = fetch_news_sentiment()
wsb_hot, wsb_err = fetch_wsb_meme_tickers()
twits_trend, twits_err = fetch_stocktwits_trending()
put_call, pcr_err = fetch_put_call_ratio()
bonds, bonds_err = fetch_cnbc_bond_yields()

######################################
# === DISPLAY METRICS ===============
######################################

cols = st.columns(6)
metrics = [
    ("VIX (Volatility)", vix_val, None, ">30 = Elevated Fear"),
    ("RSI (S&P 500)", rsi_val, None, ">70 Overbought / <35 Oversold"),
    ("Google Trends", trends_val, None, "Interest for 'stock market crash'"),
    ("News Sentiment", news_val, news_lbl, "Headline tone: bull vs bear"),
    ("Put/Call Ratio", put_call, None, "<0.7 Greed, >1.2 Fear (Equity PCR)"),
    ("10Y Treasury Yield", bonds.get("U.S. 10 Year Treasury")['yield'] if bonds and "U.S. 10 Year Treasury" in bonds else None, None, "Long-term rate (risk/recession)")
]
for col, (name, val, lbl, desc) in zip(cols, metrics):
    with col:
        display_val = val if val is not None else "N/A"
        display_delta = lbl or ""
        st.metric(f"**{name}**", value=display_val, delta=display_delta)
        if isinstance(val, (int, float)):
            st.progress(min(max(float(val) / 100, 0.0), 1.0))
        with st.expander(f"ℹ️ What is {name}?"):
            st.write(desc)

if bonds:
    bond_str = " | ".join([f"{b}: {v['yield']}" for b, v in bonds.items() if "Year" in b or "Week" in b][:6])
    st.markdown(f"**Yield Curve Snapshot:** {bond_str}")

######################################
# === BUFFETT & TOM LEE SIGNALS =====
######################################

def buffett_style_signal(vix, rsi, trends, news, pcr, bonds):
    fear_count = 0
    if vix is not None and vix > 28: fear_count += 1
    if trends is not None and trends > 80: fear_count += 1
    if news is not None and news < 35: fear_count += 1
    if pcr is not None and pcr > 1.1: fear_count += 1
    ten = None
    two = None
    for b in bonds:
        if "10 Year" in b: ten = bonds[b]['yield'].replace("%","")
        if "2 Year" in b: two = bonds[b]['yield'].replace("%","")
    try:
        if ten and two and float(two) > float(ten): fear_count += 1
    except: pass
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

def tomlee_signal(vix, rsi, trends, news, pcr, bonds):
    bullish_score = 0
    if vix is not None and vix > 22: bullish_score += 1
    if rsi is not None and rsi < 45: bullish_score += 1
    if trends is not None and trends > 60: bullish_score += 1
    if news is not None and news < 50: bullish_score += 1
    if pcr is not None and pcr > 1.0: bullish_score += 1
    ten = None
    two = None
    for b in bonds:
        if "10 Year" in b: ten = bonds[b]['yield'].replace("%","")
        if "2 Year" in b: two = bonds[b]['yield'].replace("%","")
    try:
        if ten and two and float(two) > float(ten): bullish_score += 1
    except: pass
    if bullish_score >= 2:
        return "🟢 Tom Lee: Good Time to Buy (Buy the Dip Mentality)"
    if vix is not None and vix < 14 and rsi is not None and rsi > 70 and news is not None and news > 60:
        return "🔴 Tom Lee: Even Tom Lee says: Hold Off, Too Hot!"
    return "⚪ Tom Lee: Stay Invested or Accumulate Slowly"

st.markdown("## 🧭 Buffett-Style Long-Term Investor Signal")
st.success(buffett_style_signal(vix_val, rsi_val, trends_val, news_val, put_call, bonds))
with st.expander("Buffett Philosophy"):
    st.markdown("> *Be fearful when others are greedy, and greedy when others are fearful.*  \n— Warren Buffett")

st.markdown("## 📈 Tom Lee (Fundstrat) Tactical Signal")
st.info(tomlee_signal(vix_val, rsi_val, trends_val, news_val, put_call, bonds))
with st.expander("Tom Lee Style"):
    st.markdown("> *When everyone is cautious, that’s when opportunity strikes. The market often climbs a wall of worry.*  \n— Tom Lee (Fundstrat, paraphrased)")

######################################
# === MEME RADAR + SOCIAL TRENDS ====
######################################

st.markdown("## 🚀 Meme Stock Radar (WSB Hotlist)")
if wsb_err:
    st.warning(wsb_err)
elif wsb_hot:
    st.markdown("**Top tickers from recent /r/wallstreetbets hot posts (auto-detected):**")
    for d in wsb_hot:
        st.markdown(f"**{d['ticker']}** — Mentioned {d['mentions']} times | 🔺Upvotes: {d['ups']}\n\n_{d['title']}_\n")
else:
    st.info("No trending meme tickers found (try again soon).")

st.markdown("## 💬 Twitter/X (StockTwits) Trending Tickers")
if twits_err:
    st.warning(twits_err)
elif twits_trend:
    st.markdown("Top trending tickers: " + ", ".join(f"`{t}`" for t in twits_trend))
else:
    st.info("No trending tickers on StockTwits right now.")

st.markdown("---")
st.markdown("### ⚠️ Disclaimer")
st.warning(
    "For educational purposes only. Not financial advice. Use at your own risk. These signals use sentiment, volatility, and momentum for illustration only — not for trading or portfolio management."
)

if st.button("🔄 Refresh Data"):
    st.rerun()

