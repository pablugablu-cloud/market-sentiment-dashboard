import os
import streamlit as st
import yfinance as yf
from ta.momentum import RSIIndicator
from pytrends.request import TrendReq
from newsapi import NewsApiClient
import requests
import re
from collections import Counter

# ---- ENV SECRETS HANDLING ----
NEWSAPI_KEY = st.secrets.get("NEWSAPI_KEY", os.getenv("NEWSAPI_KEY", ""))

st.set_page_config(
    page_title="Market Sentiment Dashboard (Buffett & Tom Lee)",
    layout="wide",
)
st.markdown("""
    <style>
    html, body, [class*="css"] { font-family: 'Inter', 'Segoe UI', Arial, sans-serif !important; background: #f7f9fb;}
    .datacard { background: #fff; border-radius: 1.1em; box-shadow: 0 3px 18px 0 rgba(40,55,70,0.06); padding: 1.25em 1.4em 1.1em 1.4em; margin-bottom: 0.7em;}
    .buffett-card { border-left: 7px solid #19bb77;}
    .tomlee-card { border-left: 7px solid #225DF1;}
    .meme-card { border-left: 7px solid #FCAA4A;}
    .big-num { font-size: 2.09rem; font-weight: 800; margin: 0 0 0.09em 0;}
    .caption { color: #a5a7ab; font-size: 0.99em; margin-top: -0.2em;}
    .signal-head { font-weight: 700; font-size: 1.16rem;}
    .ticker-up { color:#19bb77; font-weight:700;}
    .ticker-down { color:#e44b5a; font-weight:700;}
    </style>
""", unsafe_allow_html=True)

st.title("📊 Market Sentiment Dashboard")
st.caption("Buffett & Tom Lee styled risk signals powered by VIX, RSI, Google Trends, News, and Reddit.")

st.markdown("---")

# --- DATA FUNCTIONS ---

def fetch_vix():
    try:
        df = yf.Ticker("^VIX").history(period="5d")
        vix = round(df["Close"].iloc[-1], 2)
        return vix
    except Exception:
        return None

def fetch_rsi():
    try:
        df = yf.Ticker("^GSPC").history(period="2mo", interval="1d")
        df["rsi"] = RSIIndicator(df["Close"]).rsi()
        rsi = round(df["rsi"].iloc[-1], 2)
        return rsi
    except Exception:
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
    if not NEWSAPI_KEY:
        st.warning("No NewsAPI key found. Set NEWSAPI_KEY in Streamlit secrets or .env.")
        return None, "No API Key"
    try:
        na = NewsApiClient(api_key=NEWSAPI_KEY)
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

def fetch_wsb_meme_tickers(limit=50):
    url = f"https://www.reddit.com/r/wallstreetbets/hot/.json?limit={limit}"
    headers = {"User-Agent": "Mozilla/5.0 (compatible; MemeRadarBot/1.0)"}
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code != 200:
            return []
        posts = resp.json()["data"]["children"]
        EXCLUDE = {
            "YOLO", "WSB", "DD", "ETF", "USD", "THE", "ITM", "OTM", "ALL", "OPEN", "GAIN",
            "CALL", "PUT", "BIG", "LOSS", "CASH", "MOON", "ATM", "OUT", "EARN", "NEWS",
            "SPY", "QQQ"  # Optionally exclude indexes; remove if you want them!
        }
        ticker_pat = re.compile(r'\b([A-Z]{2,5})\b')
        mentions = []
        for post in posts:
            data = post.get("data", {})
            for txt in [data.get("title", ""), data.get("selftext", "")]:
                for match in ticker_pat.findall(txt):
                    if match.isupper() and match not in EXCLUDE:
                        mentions.append(match)
        counts = Counter(mentions)
        return counts.most_common(5)
    except Exception as e:
        # For debugging: st.write(f"Reddit fetch error: {e}")
        return []

def get_price_change(ticker):
    try:
        data = yf.Ticker(ticker).history(period="5d")
        if len(data) > 1:
            prev = data['Close'].iloc[-2]
            last = data['Close'].iloc[-1]
            return round((last - prev) / prev * 100, 2)
    except Exception:
        pass
    return None

# --- FETCH DATA ---
vix_val = fetch_vix()
rsi_val = fetch_rsi()
trends_val = fetch_google_trends()
news_val, news_lbl = fetch_news_sentiment()
memes = fetch_wsb_meme_tickers(limit=50)

# --- DISPLAY METRICS ---
cols = st.columns(4)
metrics = [
    ("VIX (Volatility)", vix_val, ">30 = Elevated Fear"),
    ("RSI (S&P 500)", rsi_val, ">70 Overbought / <35 Oversold"),
    ("Google Trends", trends_val, "Search Interest: 'stock market crash'"),
    ("News Sentiment", news_val, f"Headline Tone: {news_lbl}"),
]
for col, (name, val, desc) in zip(cols, metrics):
    with col:
        display_val = val if val is not None else "N/A"
        st.markdown(f"<div class='datacard'><span style='font-size:1.09rem;color:#8592A6;'>{name}</span><br>"
                    f"<span class='big-num'>{display_val}</span>"
                    f"<div class='caption'>{desc}</div></div>", unsafe_allow_html=True)

# --- BUFFETT/TOM LEE SIGNALS ---
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

# --- SIGNAL CARDS ---
st.markdown('<div class="datacard buffett-card" style="margin-top:0.4em;">', unsafe_allow_html=True)
st.markdown('<div class="signal-head">🧭 Buffett-Style Long-Term Investor Signal</div>', unsafe_allow_html=True)
st.markdown(f"<div class='big-num'>{buffett_style_signal(vix_val, rsi_val, trends_val, news_val)}</div>", unsafe_allow_html=True)
st.markdown("<div class='caption'>Buffett: <i>Be fearful when others are greedy, and greedy when others are fearful.</i></div>", unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

st.markdown('<div class="datacard tomlee-card">', unsafe_allow_html=True)
st.markdown('<div class="signal-head">📈 Tom Lee (Fundstrat) Tactical Signal</div>', unsafe_allow_html=True)
st.markdown(f"<div class='big-num'>{tomlee_signal(vix_val, rsi_val, trends_val, news_val)}</div>", unsafe_allow_html=True)
st.markdown("<div class='caption'>Tom Lee: <i>When everyone is cautious, that’s when opportunity strikes.</i></div>", unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# --- MEME STOCK RADAR ---
st.markdown('<div class="datacard meme-card">', unsafe_allow_html=True)
st.markdown('<div class="signal-head">🚀 Meme Stock Radar <span style="font-size:0.97em;color:#225DF1;">(WSB Hotlist)</span></div>', unsafe_allow_html=True)
if memes:
    for ticker, n in memes:
        pct = get_price_change(ticker)
        if pct is not None:
            color = "ticker-up" if pct > 0 else "ticker-down"
            pct_str = f"<span class='{color}'>{pct:+.2f}%</span>"
        else:
            pct_str = ""
        st.markdown(f"<b>{ticker}</b>: {n} mentions {pct_str}", unsafe_allow_html=True)
    st.caption("Top tickers in r/wallstreetbets in the last day. ⚠️ Not investment advice.", unsafe_allow_html=True)
else:
    st.info("No trending meme tickers found (try again soon).")
st.markdown('</div>', unsafe_allow_html=True)

# --- DISCLAIMER & REFRESH ---
st.markdown("---")
with st.expander("⚠️ Disclaimer (Tap to expand)", expanded=False):
    st.markdown("""
    <b>For educational purposes only. Not financial advice. Use at your own risk.</b>
    These signals use sentiment, volatility, and momentum for illustration only — not for trading or portfolio management.<br>
    <b>Legal Notice:</b> This dashboard is for general informational purposes and does not create a client relationship. Always consult your licensed advisor before acting.
    """, unsafe_allow_html=True)

if st.button("🔄 Refresh Data"):
    st.rerun()

