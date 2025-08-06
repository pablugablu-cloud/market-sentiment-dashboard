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

# ─── Custom CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* container padding */
.block-container { padding: 2rem 3rem; }

/* Card style for metrics */
.metric-card {
  background: #FFFFFF;
  border-radius: 12px;
  padding: 1rem 1.2rem;
  box-shadow: 0 2px 6px rgba(0,0,0,0.05);
  margin-bottom: 1rem;
}
.metric-label { font-size: 0.95rem; color: #666666; }
.metric-value { font-size: 1.8rem; font-weight: 600; margin-top: 0.2rem; }
.metric-delta { font-size: 0.9rem; }

/* Section headers */
.section-header {
  font-size: 1.4rem;
  margin: 1.8rem 0 0.6rem 0;
  font-weight: 600;
  color: #333333;
}

/* Treasury yield grid */
.yield-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 1rem;
}
.yield-item {
  background: #FFF;
  border-radius: 8px;
  padding: 0.6rem;
  text-align: center;
  box-shadow: 0 1px 4px rgba(0,0,0,0.04);
}
.yield-symbol { font-weight: 500; color: #444; }
.yield-value { font-size: 1.2rem; margin-top: 0.2rem; color: #111; }
</style>
""", unsafe_allow_html=True)

# ─── Title ───────────────────────────────────────────────────────────────────
st.markdown("## 📊 Market Sentiment Dashboard")
st.caption("Buffett & Tom Lee Signals + Put/Call Ratio & Bond Yields. For learning, not advice.")
st.markdown("---")


# ─── Data Fetchers ────────────────────────────────────────────────────────────
def fetch_vix():
    try:
        df = yf.Ticker("^VIX").history(period="5d")
        return round(df["Close"].iloc[-1], 2)
    except:
        return None

def fetch_rsi():
    try:
        df = yf.Ticker("^GSPC").history(period="2mo", interval="1d")
        df["rsi"] = RSIIndicator(df["Close"]).rsi()
        return round(df["rsi"].iloc[-1], 2)
    except:
        return None

def fetch_google_trends(term="stock market crash"):
    try:
        py = TrendReq(hl="en-US", tz=360)
        py.build_payload([term], timeframe="now 7-d")
        df = py.interest_over_time()
        return int(df[term].iloc[-1]) if not df.empty else None
    except:
        return None

def fetch_news_sentiment():
    key = os.getenv("NEWSAPI_KEY","")
    if not key: return None, "No Key"
    na = NewsApiClient(api_key=key)
    arts = na.get_everything(q="stock market", language="en", page_size=25)["articles"]
    bears = ["crash","panic","recession","sell-off"]
    bulls = ["rally","bullish","surge","record high"]
    b = sum(any(w in a["title"].lower() for w in bears) for a in arts)
    u = sum(any(w in a["title"].lower() for w in bulls) for a in arts)
    score = max(0, min(100, 50 + 2*(u-b)))
    lbl = "Bullish" if score>60 else "Bearish" if score<40 else "Mixed"
    return score, lbl

def fetch_pcr():
    url = (
      "https://ycharts.com/charts/fund_data.json"
      "?securities=id%3AI%3ACBOEEPCR%2Cinclude%3Atrue&format=real&maxPoints=1"
    )
    r = requests.get(url, headers={"User-Agent":"Mozilla/5.0"}, timeout=10)
    r.raise_for_status()
    return float(r.json()["chart_data"][0][0]["last_value"]), None

def fetch_bond_yields():
    url = (
      "https://quote.cnbc.com/quote-html-webservice/restQuote/"
      "symbolType/symbol?"
      "symbols=US1M%7CUS2M%7CUS3M%7CUS4M%7CUS6M%7CUS1Y%7CUS2Y%7CUS3Y%7CUS5Y%7CUS7Y%7CUS10Y%7CUS20Y%7CUS30Y"
      "&requestMethod=itv&noform=1&partnerId=2&fund=1&exthrs=1&output=json&events=1"
    )
    r = requests.get(url, headers={"User-Agent":"Mozilla/5.0"}, timeout=10)
    r.raise_for_status()
    data = r.json()["FormattedQuoteResult"]["FormattedQuote"]
    return {q["symbol"]: float(q["last"].strip("%")) for q in data}, None

# ―― Fetch everything ――
vix = fetch_vix()
rsi = fetch_rsi()
trd = fetch_google_trends()
ns, nsl = fetch_news_sentiment()
pcr, pcr_err = fetch_pcr()
yields, yerr = fetch_bond_yields()


# ─── Top-Line Metrics ─────────────────────────────────────────────────────────
def render_metric(col, label, val, delta=None, desc=""):
    with col:
        col.markdown(f"<div class='metric-card'>", unsafe_allow_html=True)
        col.markdown(f"<div class='metric-label'>{label}</div>", unsafe_allow_html=True)
        display = val if val is not None else "N/A"
        col.markdown(f"<div class='metric-value'>{display}</div>", unsafe_allow_html=True)
        if delta:
            col.markdown(f"<div class='metric-delta'>{delta}</div>", unsafe_allow_html=True)
        if desc:
            with col.expander(f"ℹ️ What is {label}?"):
                col.write(desc)
        col.markdown("</div>", unsafe_allow_html=True)

cols = st.columns(5)
render_metric(cols[0], "VIX (Vol)",    vix,    None, ">30 = Elevated Fear")
render_metric(cols[1], "RSI (S&P 500)",rsi,    None, ">70 Overbought / <35 Oversold")
render_metric(cols[2], "Google Trends",trd,    None, "Search interest last 7d")
render_metric(cols[3], "News Sentiment",ns, nsl, "Bull vs. Bear headlines")
render_metric(cols[4], "Put/Call Ratio",pcr,  None, "<0.7 Greed · >1.2 Fear")

st.markdown("---")


# ─── Bond Yield Grid ──────────────────────────────────────────────────────────
st.markdown("<div class='section-header'>🏦 U.S. Treasury Yields</div>", unsafe_allow_html=True)
if yields:
    items = "".join(
        f"<div class='yield-item'>"
        f"<div class='yield-symbol'>{sym}</div>"
        f"<div class='yield-value'>{yields[sym]:.2f}%</div>"
        f"</div>"
        for sym in sorted(yields)
    )
    st.markdown(f"<div class='yield-grid'>{items}</div>", unsafe_allow_html=True)
else:
    st.warning(yerr)

st.markdown("---")


# ─── Signals ─────────────────────────────────────────────────────────────────
def buffett(vix, rsi, trd, ns, pcr, yd):
    fcount = sum([
      (vix>28 if vix else False),
      (trd>80 if trd else False),
      (ns<35  if ns  else False),
      (pcr>1.1 if pcr else False),
      (yd.get("US2Y",0)>yd.get("US10Y",0))
    ])
    if rsi<35 and fcount>=2: return "🟢 Really Good Time to Buy"
    if rsi<40 and fcount>=1: return "🟡 Good Time to Accumulate"
    if 40<=rsi<=60 and 16<vix<28 and 35<=ns<=65: return "⚪ Wait, Stay Patient"
    if rsi>70 and ns>60 and trd<20: return "🔴 Market Overheated"
    return "🔴 Hold Off"

def tomlee(vix, rsi, trd, ns, pcr, yd):
    score = sum([
      vix>22, rsi<45, trd>60, ns<50,
      (pcr>1.0 if pcr else False),
      yd.get("US2Y",0)>yd.get("US10Y",0)
    ])
    if score>=2: return "🟢 Buy the Dip"
    if vix<14 and rsi>70 and ns>60: return "🔴 Too Hot"
    return "⚪ Stay Invested"

st.markdown("<div class='section-header'>🧭 Buffett-Style Signal</div>", unsafe_allow_html=True)
st.success(buffett(vix, rsi, trd, ns, pcr, yields))
with st.expander("Buffett Philosophy"):
    st.markdown("> *Be fearful when others are greedy, and greedy when others are fearful.* — Warren Buffett")

st.markdown("<div class='section-header'>📈 Tom Lee Tactical Signal</div>", unsafe_allow_html=True)
st.info(tomlee(vix, rsi, trd, ns, pcr, yields))
with st.expander("Tom Lee Style"):
    st.markdown("> *When everyone is cautious, that’s when opportunity strikes.* — Tom Lee")

st.markdown("---")
st.warning("⚠️ For educational purposes only. Not financial advice.")
if st.button("🔄 Refresh Data"):
    st.experimental_rerun()

