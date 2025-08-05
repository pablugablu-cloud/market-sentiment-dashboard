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
    page_title="Market Sentiment Dashboard (Minimalist)",
    layout="wide",
)

# --- Custom CSS ---
st.markdown("""
    <style>
    html, body, [class*="css"]  { font-family: 'Inter', 'Segoe UI', Arial, sans-serif !important; background: #f7f9fb; }
    .big-num { font-size: 2.2rem !important; font-weight: 800; margin: 0 0 0.06em 0;}
    .small-label { font-size: 1.09rem !important; color: #8592A6; }
    .datacard { background: #fff; border-radius: 1.1em; box-shadow: 0 3px 18px 0 rgba(40,55,70,0.06);
        padding: 1.2em 1.5em 1.1em 1.4em; margin-bottom: 0.7em;}
    .buffett-card { border-left: 7px solid #16BF6C; }
    .tomlee-card { border-left: 7px solid #225DF1; }
    .meme-card { border-left: 7px solid #FCAA4A;}
    .bar {height: 13px; background: #e8ecf2; border-radius: 7px; margin: 0.3em 0 1em 0; overflow: hidden;}
    .bar-inner {height: 100%; border-radius: 7px;}
    .badge { display:inline-block; font-size:0.95em; font-weight:600; padding:0.19em 0.8em; border-radius:1em; }
    .badge-green { background: #e4faef; color: #19bb77;}
    .badge-yellow { background: #FFF4DC; color: #F6B100;}
    .badge-red { background: #ffefef; color: #e44b5a;}
    .badge-blue { background: #e5f1ff; color: #225DF1;}
    .badge-gray { background: #f3f4f6; color: #a5a7ab;}
    .caption { color: #a5a7ab; font-size: 0.99em; margin-top: -0.2em; }
    .signal-head { font-weight: 700; font-size: 1.13rem; }
    .msg { font-size:1em; color:#a5a7ab; margin: 0.1em 0 0.7em 0;}
    </style>
""", unsafe_allow_html=True)

# ---- Page Title ----
st.markdown("""
    <div style="display:flex;align-items:center;">
        <img src="https://img.icons8.com/color/40/000000/combo-chart--v2.png" width="33" style="margin-right: 11px;"/>
        <span style="font-size:1.47rem;font-weight:900;letter-spacing:-1px;">Market Sentiment Dashboard</span>
    </div>
    <div style="font-size:1.01rem;color:#6d7893;margin-top:0.18em;">
        Minimalist market snapshot inspired by Buffett & Tom Lee.<br>
        <span style="color:#A5AEBC;font-size:0.97rem;">
            Powered by VIX, RSI, Google Trends, News.
        </span>
    </div>
""", unsafe_allow_html=True)

# --- Data Functions ---
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
    except Exception:
        return None  # No error text; just show N/A as neutral

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
        msg = str(e)
        if "rateLimited" in msg or "Too Many Requests" in msg:
            return None, "Rate Limited"
        return None, "Unavailable"

def fetch_pushshift_wsb_tickers(limit=500):
    url = f"https://api.pushshift.io/reddit/search/submission/?subreddit=wallstreetbets&size={limit}&fields=title,selftext"
    try:
        r = requests.get(url, timeout=10)
        data = r.json().get('data', [])
        texts = [d.get('title', '') + " " + d.get('selftext', '') for d in data]
        pat = re.compile(r'\$?([A-Z]{2,5})\b')
        exclude = {"USD", "WSB", "ETF", "IPO", "SPAC", "CEO", "DD", "FOMO", "ATH", "LOL", "TOS"}
        mentions = []
        for text in texts:
            for match in pat.findall(text):
                if match not in exclude and match.isalpha():
                    mentions.append(match)
        counts = Counter(mentions)
        return counts.most_common(5)
    except Exception:
        return []

def get_price_change(ticker):
    try:
        data = yf.Ticker(ticker).history(period="5d")
        if len(data) > 1:
            prev = data['Close'].iloc[-2]
            last = data['Close'].iloc[-1]
            return round((last - prev)/prev * 100, 2)
    except: pass
    return None

# --- Fetch data ---
vix_val = fetch_vix()
rsi_val = fetch_rsi()
trends_val = fetch_google_trends()
news_val, news_lbl = fetch_news_sentiment()

# --- Mini Helper for colored badges ---
def colored_badge(value, label):
    if value is None:
        return f"<span class='badge badge-gray'>N/A</span>"
    if label.lower() == "vix":
        if value > 30: return f"<span class='badge badge-red'>High</span>"
        elif value > 20: return f"<span class='badge badge-yellow'>Elevated</span>"
        else: return f"<span class='badge badge-green'>Calm</span>"
    if label.lower() == "rsi":
        if value > 70: return f"<span class='badge badge-red'>Overbought</span>"
        elif value < 35: return f"<span class='badge badge-blue'>Oversold</span>"
        else: return f"<span class='badge badge-green'>Normal</span>"
    if label.lower() == "google":
        if value is None: return "<span class='badge badge-gray'>N/A</span>"
        if value > 70: return f"<span class='badge badge-red'>High Search</span>"
        elif value > 30: return f"<span class='badge badge-yellow'>Moderate</span>"
        else: return f"<span class='badge badge-green'>Low</span>"
    if label.lower() == "news":
        if value is None or news_lbl in ["No API Key", "Rate Limited", "Unavailable"]:
            return "<span class='badge badge-gray'>N/A</span>"
        if news_lbl == "Bullish": return f"<span class='badge badge-green'>Bullish</span>"
        if news_lbl == "Bearish": return f"<span class='badge badge-red'>Bearish</span>"
        return f"<span class='badge badge-yellow'>Mixed</span>"
    return ""

# --- Display Data as Cards ---
with st.container():
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown("<div class='datacard'><span class='small-label'>VIX (Volatility)</span><br>"
                    f"<span class='big-num'>{vix_val if vix_val is not None else '--'}</span> "
                    f"{colored_badge(vix_val, 'vix')}"
                    "<div class='caption'>30+ = High Fear</div></div>", unsafe_allow_html=True)
        if vix_val is not None:
            pct = int(min(max((vix_val-10)/(40-10)*100, 0), 100))
            st.markdown(f"<div class='bar'><div class='bar-inner' style='width:{pct}%;background:#19bb77;'></div></div>", unsafe_allow_html=True)
    with c2:
        st.markdown("<div class='datacard'><span class='small-label'>RSI (S&P 500)</span><br>"
                    f"<span class='big-num'>{rsi_val if rsi_val is not None else '--'}</span> "
                    f"{colored_badge(rsi_val, 'rsi')}"
                    "<div class='caption'>&gt;70 Overbought / &lt;35 Oversold</div></div>", unsafe_allow_html=True)
        if rsi_val is not None:
            pct = int(min(max((rsi_val-10)/(90-10)*100, 0), 100))
            st.markdown(f"<div class='bar'><div class='bar-inner' style='width:{pct}%;background:#225DF1;'></div></div>", unsafe_allow_html=True)
    with c3:
        st.markdown("<div class='datacard'><span class='small-label'>Google Trends</span><br>"
                    f"<span class='big-num'>{trends_val if trends_val is not None else '--'}</span> "
                    f"{colored_badge(trends_val, 'google')}"
                    "<div class='caption'>Search: 'market crash'</div></div>", unsafe_allow_html=True)
        if trends_val is not None:
            pct = int(min(max(trends_val, 0), 100))
            st.markdown(f"<div class='bar'><div class='bar-inner' style='width:{pct}%;background:#FCAA4A;'></div></div>", unsafe_allow_html=True)
        elif trends_val is None:
            st.markdown(f"<span class='msg'>Google Trends data is not available (rate limited, or no connection).</span>", unsafe_allow_html=True)
    with c4:
        st.markdown("<div class='datacard'><span class='small-label'>News Sentiment</span><br>"
                    f"<span class='big-num'>{news_val if news_val is not None else '--'}</span> "
                    f"{colored_badge(news_val, 'news')}"
                    "<div class='caption'>Headline Tone</div></div>", unsafe_allow_html=True)
        if news_val is not None:
            pct = int(min(max(news_val, 0), 100))
            st.markdown(f"<div class='bar'><div class='bar-inner' style='width:{pct}%;background:#FFD700;'></div></div>", unsafe_allow_html=True)
        elif news_lbl:
            st.markdown(f"<span class='msg'>News sentiment not available ({news_lbl}).</span>", unsafe_allow_html=True)

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
    if (rsi is not None and 40 <= rsi <= 60 and vix is not None and 16 < vix < 28 and news is not None and 35 <= news <= 65):
        return "⚪ Buffett: Wait, Stay Patient (No Edge)"
    if (rsi is not None and rsi > 70 and news is not None and news > 60 and trends is not None and trends < 20):
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

# --- Buffett Card ---
st.markdown('<div class="datacard buffett-card" style="margin-top:0.6em;">', unsafe_allow_html=True)
st.markdown('<div class="signal-head">🧭 Buffett-Style Long-Term Investor Signal</div>', unsafe_allow_html=True)
st.markdown(f"<div class='big-num'>{buffett_style_signal(vix_val, rsi_val, trends_val, news_val)}</div>", unsafe_allow_html=True)
st.markdown("<div class='caption'>Buffett: <i>Be fearful when others are greedy, and greedy when others are fearful.</i></div>", unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# --- Tom Lee Card ---
st.markdown('<div class="datacard tomlee-card">', unsafe_allow_html=True)
st.markdown('<div class="signal-head">📈 Tom Lee (Fundstrat) Tactical Signal</div>', unsafe_allow_html=True)
st.markdown(f"<div class='big-num'>{tomlee_signal(vix_val, rsi_val, trends_val, news_val)}</div>", unsafe_allow_html=True)
st.markdown("<div class='caption'>Tom Lee: <i>When everyone is cautious, that's when opportunity strikes.</i></div>", unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# --- Meme Stock Radar Card ---
st.markdown('<div class="datacard meme-card">', unsafe_allow_html=True)
st.markdown('<div class="signal-head">🚀 Meme Stock Radar <span class="badge badge-blue">(WSB Hotlist)</span></div>', unsafe_allow_html=True)
memes = fetch_pushshift_wsb_tickers(limit=700)
if memes:
    for i, (ticker, n) in enumerate(memes):
        pct = get_price_change(ticker)
        change = f"<span style='color:{'#19bb77' if pct and pct>0 else '#e44b5a'}; font-weight:700;'>{pct:+.2f}%</span>" if pct is not None else ""
        fire = "🔥" if i==0 and pct and pct > 10 else ""
        st.markdown(f"<b>{ticker}</b>: {n} mentions {change} {fire}", unsafe_allow_html=True)
    st.caption("Top tickers in r/wallstreetbets in the last day. ⚠️ Not investment advice.", unsafe_allow_html=True)
else:
    st.caption("No trending meme tickers found. Either r/WSB is quiet, API is slow, or it's just a boring day. 😉", unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html

