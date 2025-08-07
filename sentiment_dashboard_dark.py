import os
import streamlit as st
import yfinance as yf
from ta.momentum import RSIIndicator
from pytrends.request import TrendReq
from newsapi import NewsApiClient
from dotenv import load_dotenv
import requests
import pandas as pd

load_dotenv()

st.set_page_config(page_title="Market Sentiment Dashboard", layout="wide")
st.title("📊 Market Sentiment Dashboard")
st.caption("Buffett & Tom Lee Signals + Put/Call Ratio & Bond Yields. For learning, not advice.")
st.markdown("---")

# 1. VIX
def fetch_vix():
    try:
        df = yf.Ticker("^VIX").history(period="5d")
        return round(df["Close"].iloc[-1], 2)
    except Exception as e:
        st.warning(f"VIX unavailable: {e}")
        return None

# 2. RSI (S&P 500)
def fetch_rsi():
    try:
        df = yf.Ticker("^GSPC").history(period="2mo", interval="1d")
        df["rsi"] = RSIIndicator(df["Close"]).rsi()
        return round(df["rsi"].iloc[-1], 2)
    except Exception as e:
        st.warning(f"RSI unavailable: {e}")
        return None

# 3. Google Trends
def fetch_google_trends(term="stock market crash"):
    try:
        py = TrendReq(hl="en-US", tz=360)
        py.build_payload([term], timeframe="now 7-d")
        df = py.interest_over_time()
        return int(df[term].iloc[-1]) if not df.empty else None
    except Exception as e:
        st.warning(f"Google Trends unavailable: {e}")
        return None

# 4. News Sentiment
def fetch_news_sentiment():
    key = os.getenv("NEWSAPI_KEY", "")
    if not key:
        st.warning("Set NEWSAPI_KEY in env")
        return None, "No Key"
    try:
        na = NewsApiClient(api_key=key)
        arts = na.get_everything(q="stock market", language="en", page_size=25)["articles"]
        bears = [
    # Market crashes and collapses
    "crash", "collapse", "meltdown", "plunge", "freefall", "bloodbath", "nosedive", "sell-off",

    # Economic stress
    "recession", "slowdown", "downturn", "stagflation", "deflation", "default", "credit crunch",

    # Investor emotions / fear signals
    "panic", "fear", "uncertainty", "turmoil", "concern", "risk-off", "bearish", "pessimism", "jitters",

    # Volatility and instability
    "volatility", "instability", "turbulence", "shock", "chaos", "fragile",

    # Market losses / negatives
    "losses", "decline", "drop", "slump", "dip", "red", "cut", "plummeting", "downgrade", "underperform"
]

        bulls = [
    # Market gains and breakouts
    "rally", "surge", "soar", "jump", "bounce", "run-up", "breakout", "rebound", "uptrend", "green",

    # Economic growth / optimism
    "recovery", "comeback", "expansion", "growth", "stimulus", "boom", "momentum", "tailwinds",

    # Investor emotions / bullish tone
    "bullish", "optimism", "confidence", "buying", "risk-on", "support", "strength", "resilient",

    # Records and highs
    "record high", "all-time high", "new peak", "historic high", "milestone", "breakthrough", "beating estimates",

    # Market performance terms
    "gains", "up", "advance", "outperform", "upgrade", "bull market", "ripping", "winning streak"
]


        b = sum(any(w in a["title"].lower() for w in bears) for a in arts)
        u = sum(any(w in a["title"].lower() for w in bulls) for a in arts)
        score = max(0, min(100, 50 + 2*(u-b)))
        lbl = "Bullish" if score>60 else "Bearish" if score<40 else "Mixed"
        return score, lbl
    except Exception as e:
        st.warning(f"NewsAPI error: {e}")
        return None, "Error"

# 5. Put/Call Ratio from YCharts
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
        r = requests.get(url, timeout=10, headers={"User-Agent":"Mozilla/5.0"})
        r.raise_for_status()
        js = r.json()
        # navigate into chart_data → first series → last_value
        last = js["chart_data"][0][0]["last_value"]
        return float(last), None
    except Exception as e:
        return None, f"PCR error: {e}"

# 6. U.S. Treasury Yields from CNBC
def fetch_bond_yields():
    url = (
        "https://quote.cnbc.com/quote-html-webservice/restQuote/"
        "symbolType/symbol?"
        "symbols="
        "US1M%7CUS2M%7CUS3M%7CUS4M%7CUS6M%7CUS1Y%7CUS2Y%7CUS3Y%7CUS5Y%7CUS7Y%7CUS10Y%7CUS20Y%7CUS30Y"
        "&requestMethod=itv&noform=1&partnerId=2&fund=1&exthrs=1&output=json&events=1"
    )
    try:
        r = requests.get(url, timeout=10, headers={"User-Agent":"Mozilla/5.0"})
        r.raise_for_status()
        quotes = r.json()["FormattedQuoteResult"]["FormattedQuote"]
        return {q["symbol"]: float(q["last"].strip("%")) for q in quotes}, None
    except Exception as e:
        return {}, f"Bond fetch error: {e}"

# ――― Fetch all data ―――
vix   = fetch_vix()
rsi   = fetch_rsi()
trds  = fetch_google_trends()
news, nlbl = fetch_news_sentiment()
pcr, pcr_err   = fetch_pcr()
yields, y_err  = fetch_bond_yields()

# ――― Top-line metrics ―――
cols = st.columns(5)
for col, (name, val, lbl, desc) in zip(cols, [
    ("VIX (Vol)",   vix,    None, ">30 = Elevated Fear"),
    ("RSI (S&P)",   rsi,    None, ">70 Overbought / <35 Oversold"),
    ("GoogleTrends",trds,   None, "Search interest: market crash"),
    ("NewsSent",    news,   nlbl, "Bull vs. Bear headlines"),
    ("Put/CallRatio",pcr,   None, "<0.7 Greed, >1.2 Fear"),
]):
    with col:
        dv = val if val is not None else "N/A"
        st.metric(f"**{name}**", value=dv, delta=lbl or "")
        with st.expander(f"ℹ️ What is {name}?"):
            st.write(desc)

# ――― Bond yields table ―――
st.markdown("### 🏦 U.S. Treasury Yields")
if yields:
    df_y = pd.DataFrame.from_dict(yields, orient="index", columns=["Yield (%)"])
    st.table(df_y)
else:
    st.warning(y_err)

st.markdown("---")

# ――― Buffett & Tom Lee signals ―――
def buffett_sig(vix, rsi, tr, ns, pcr, yd):
    fear = sum([
        vix>28  if vix else False,
        tr>80   if tr else False,
        ns<35   if ns else False,
        pcr>1.1 if pcr else False,
        yd.get("US2Y",0)>yd.get("US10Y",0)
    ])
    if rsi<35 and fear>=2: return "🟢 Buffett: Really Good Time to Buy"
    if rsi<40 and fear>=1: return "🟡 Buffett: Good Time to Accumulate"
    if 40<=rsi<=60 and 16<vix<28 and 35<=ns<=65: return "⚪ Buffett: Wait, Stay Patient"
    if rsi>70 and ns>60 and tr<20: return "🔴 Buffett: Market Overheated"
    return "🔴 Buffett: Hold Off"

def tomlee_sig(vix, rsi, tr, ns, pcr, yd):
    score = sum([
        vix>22, rsi<45, tr>60, ns<50,
        pcr>1.0, yd.get("US2Y",0)>yd.get("US10Y",0)
    ])
    if score>=2: return "🟢 Tom Lee: Buy the Dip"
    if vix<14 and rsi>70 and ns>60: return "🔴 Tom Lee: Too Hot"
    return "⚪ Tom Lee: Stay Invested"

st.markdown("## 🧭 Buffett-Style Signal")
st.success(buffett_sig(vix, rsi, trds, news, pcr or 0, yields))
with st.expander("Buffett Philosophy"):
    st.markdown("> *Be fearful when others are greedy, and greedy when others are fearful.* — Warren Buffett")

st.markdown("## 📈 Tom Lee Tactical Signal")
st.info(tomlee_sig(vix, rsi, trds, news, pcr or 0, yields))
with st.expander("Tom Lee Style"):
    st.markdown("> *When everyone is cautious, that’s when opportunity strikes.* — Tom Lee")

st.markdown("---")
st.warning("For educational purposes only. Not financial advice.")

if st.button("🔄 Refresh Data"):
    st.rerun()

