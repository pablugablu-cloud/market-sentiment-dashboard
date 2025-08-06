import os
import streamlit as st
import yfinance as yf
from ta.momentum import RSIIndicator
from pytrends.request import TrendReq
from newsapi import NewsApiClient
from dotenv import load_dotenv
import requests
import pandas as pd
from io import StringIO

load_dotenv()

st.set_page_config(page_title="Market Sentiment Dashboard (API-Only)", layout="wide")
st.title("📊 Market Sentiment Dashboard")
st.caption("Buffett, Tom Lee, Put/Call Ratio & Bond Yields. For learning, not advice.")
st.markdown("---")

# --- 1. VIX ---
def fetch_vix():
    try:
        df = yf.Ticker("^VIX").history(period="5d")
        return round(df["Close"].iloc[-1], 2)
    except Exception as e:
        st.warning(f"VIX unavailable: {e}")
        return None

# --- 2. RSI (S&P 500) ---
def fetch_rsi():
    try:
        df = yf.Ticker("^GSPC").history(period="2mo", interval="1d")
        df["rsi"] = RSIIndicator(df["Close"]).rsi()
        return round(df["rsi"].iloc[-1], 2)
    except Exception as e:
        st.warning(f"RSI unavailable: {e}")
        return None

# --- 3. Google Trends ---
def fetch_google_trends(term="stock market crash"):
    try:
        py = TrendReq(hl="en-US", tz=360)
        py.build_payload([term], timeframe="now 7-d")
        df = py.interest_over_time()
        return int(df[term].iloc[-1]) if not df.empty else None
    except Exception as e:
        st.warning(f"Google Trends unavailable: {e}")
        return None

# --- 4. News Sentiment ---
def fetch_news_sentiment():
    key = os.getenv("NEWSAPI_KEY", "")
    if not key:
        st.warning("Set NEWSAPI_KEY in env")
        return None, "No Key"
    try:
        na = NewsApiClient(api_key=key)
        arts = na.get_everything(q="stock market", language="en", page_size=25)["articles"]
        bears = ["crash","panic","recession","sell-off"]
        bulls = ["rally","bullish","surge","record high"]
        b = sum(any(w in a["title"].lower() for w in bears) for a in arts)
        u = sum(any(w in a["title"].lower() for w in bulls) for a in arts)
        score = max(0, min(100, 50 + 2*(u-b)))
        lbl = "Bullish" if score>60 else "Bearish" if score<40 else "Mixed"
        return score, lbl
    except Exception as e:
        st.warning(f"NewsAPI error: {e}")
        return None, "Error"

# --- 5. Put/Call Ratio from MacroMicro CSV (fallback) ---
def fetch_pcr():
    csv_url = "https://en.macromicro.me/charts/449/us-cboe-options-put-call-ratio.csv"
    try:
        r = requests.get(csv_url, timeout=10)
        r.raise_for_status()
        df = pd.read_csv(StringIO(r.text))
        if "value" in df.columns:
            return float(df["value"].iloc[-1]), None
        else:
            return None, "No 'value' column"
    except Exception as e:
        return None, f"PCR error: {e}"

# --- 6. Bond Yields from CNBC ---
def fetch_bond_yields():
    url = (
        "https://quote.cnbc.com/quote-html-webservice/restQuote/"
        "symbolType/symbol?"
        "symbols="
        "US1M%7CUS2M%7CUS3M%7CUS4M%7CUS6M%7CUS1Y%7CUS2Y%7CUS3Y%7CUS5Y%7CUS7Y%7CUS10Y%7CUS20Y%7CUS30Y"
        "&requestMethod=itv&noform=1&partnerId=2&fund=1&exthrs=1&output=json&events=1"
    )
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        quotes = r.json()["FormattedQuoteResult"]["FormattedQuote"]
        yd = {q["symbol"]: float(q["last"].strip("%")) for q in quotes}
        return yd, None
    except Exception as e:
        return {}, f"Bond fetch error: {e}"

# --- Fetch everything ---
vix = fetch_vix()
rsi = fetch_rsi()
trends = fetch_google_trends()
news, news_lbl = fetch_news_sentiment()
pcr, pcr_err = fetch_pcr()
yields, yields_err = fetch_bond_yields()

# --- Display top-row metrics ---
cols = st.columns(5)
for col, (name, val, lbl, desc) in zip(cols, [
    ("VIX (Vol)", vix, None, ">30 = Elevated Fear"),
    ("RSI (S&P)", rsi, None, ">70 Overbought / <35 Oversold"),
    ("Google Trends", trends, None, "Search interest"),
    ("News Sentiment", news, news_lbl, "Bull vs. Bear headlines"),
    ("Put/Call Ratio", pcr, None, "<0.7 Greed, >1.2 Fear"),
]):
    with col:
        dv = val if val is not None else "N/A"
        st.metric(f"**{name}**", value=dv, delta=lbl or "")
        with st.expander(f"ℹ️ What is {name}?"):
            st.write(desc)

# --- Bond yields table ---
st.markdown("### 🏦 U.S. Treasury Yields")
if yields:
    df_y = pd.DataFrame.from_dict(yields, orient="index", columns=["Yield (%)"])
    st.table(df_y)
else:
    st.warning(yields_err)

st.markdown("---")

# --- Buffett & Tom Lee signals ---
def buffett_sig(vix, rsi, trends, news, pcr, yds):
    fear = sum([
        vix>28 if vix is not None else False,
        trends>80 if trends is not None else False,
        news<35 if news is not None else False,
        pcr>1.1 if pcr is not None else False,
        (yds.get("US2Y",0)>yds.get("US10Y",0)) if yds else False,
    ])
    if rsi is not None and rsi<35 and fear>=2:
        return "🟢 Buffett: Really Good Time to Buy"
    if rsi is not None and rsi<40 and fear>=1:
        return "🟡 Buffett: Good Time to Accumulate"
    if rsi and 40<=rsi<=60 and vix and 16<vix<28 and news and 35<=news<=65:
        return "⚪ Buffett: Wait, Stay Patient"
    if rsi and rsi>70 and news and news>60 and trends and trends<20:
        return "🔴 Buffett: Market Overheated"
    return "🔴 Buffett: Hold Off"

def tomlee_sig(vix, rsi, trends, news, pcr, yds):
    score = sum([
        vix>22 if vix is not None else False,
        rsi<45 if rsi is not None else False,
        trends>60 if trends is not None else False,
        news<50 if news is not None else False,
        pcr>1.0 if pcr is not None else False,
        (yds.get("US2Y",0)>yds.get("US10Y",0)) if yds else False,
    ])
    if score>=2:
        return "🟢 Tom Lee: Buy the Dip"
    if vix<14 and rsi>70 and news>60:
        return "🔴 Tom Lee: Too Hot"
    return "⚪ Tom Lee: Stay Invested"

st.markdown("## 🧭 Buffett-Style Signal")
st.success(buffett_sig(vix, rsi, trends, news, pcr, yields))
with st.expander("Buffett Philosophy"):
    st.markdown("> *Be fearful when others are greedy, and greedy when others are fearful.* — Warren Buffett")

st.markdown("## 📈 Tom Lee Tactical Signal")
st.info(tomlee_sig(vix, rsi, trends, news, pcr, yields))
with st.expander("Tom Lee Style"):
    st.markdown("> *When everyone is cautious, that’s when opportunity strikes.* — Tom Lee")

st.markdown("---")
st.warning("For educational purposes only. Not financial advice.")

if st.button("🔄 Refresh Data"):
    st.rerun()

