import streamlit as st
import yfinance as yf
from ta.momentum import RSIIndicator
import requests
import praw
import re
from collections import Counter

# --- Load secrets securely from Streamlit's secrets system ---
REDDIT_CLIENT_ID = st.secrets.get("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = st.secrets.get("REDDIT_CLIENT_SECRET")
REDDIT_USER_AGENT = st.secrets.get("REDDIT_USER_AGENT")

st.set_page_config(
    page_title="Market Sentiment Dashboard (Minimalist)",
    layout="wide",
)

# --- Minimalist, Modern CSS ---
st.markdown("""
    <style>
    html, body, [class*="css"]  { font-family: 'Inter', 'Segoe UI', Arial, sans-serif !important; background: #f7f9fb; }
    .big-num { font-size: 2.4rem !important; font-weight: 800; margin: 0 0 0.06em 0;}
    .small-label { font-size: 1.13rem !important; color: #76839B; }
    .datacard { background: #fff; border-radius: 1.15em; box-shadow: 0 3px 18px 0 rgba(40,55,70,0.08);
        padding: 1.15em 1.5em 1em 1.35em; margin-bottom: 0.8em;}
    .buffett-card { border-left: 7px solid #16BF6C; }
    .tomlee-card { border-left: 7px solid #225DF1; }
    .meme-card { border-left: 7px solid #FCAA4A;}
    .bar {height: 14px; background: #e8ecf2; border-radius: 7px; margin: 0.3em 0 1em 0; overflow: hidden;}
    .bar-inner {height: 100%; border-radius: 7px;}
    .badge { display:inline-block; font-size:0.97em; font-weight:600; padding:0.17em 0.78em; border-radius:1em; }
    .badge-green { background: #e4faef; color: #19bb77;}
    .badge-yellow { background: #FFF4DC; color: #F6B100;}
    .badge-red { background: #ffefef; color: #e44b5a;}
    .badge-blue { background: #e5f1ff; color: #225DF1;}
    .caption { color: #a5a7ab; font-size: 0.99em; margin-top: -0.18em; }
    .signal-head { font-weight: 800; font-size: 1.25rem; margin-bottom:0.15em;}
    .signal-main { font-size:2rem;font-weight:900;margin-top:.15em;line-height:1.13;}
    .signal-detail {color:#425073;font-size:1.12em;}
    </style>
""", unsafe_allow_html=True)

# ---- Page Title ----
st.markdown("""
    <div style="display:flex;align-items:center;">
        <img src="https://img.icons8.com/color/40/000000/combo-chart--v2.png" width="33" style="margin-right: 11px;"/>
        <span style="font-size:1.45rem;font-weight:900;letter-spacing:-1px;">Market Sentiment Dashboard</span>
    </div>
    <div style="font-size:1.08rem;color:#546480;margin-top:0.18em;">
        Minimalist real-world snapshot inspired by Buffett & Tom Lee.<br>
        <span style="color:#A5AEBC;font-size:0.98rem;">
            Powered by VIX, RSI, and live WSB Meme Stock Radar.
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

def fetch_reddit_meme_tickers(limit=200):
    try:
        reddit = praw.Reddit(
            client_id=REDDIT_CLIENT_ID,
            client_secret=REDDIT_CLIENT_SECRET,
            user_agent=REDDIT_USER_AGENT,
        )
        posts = []
        for submission in reddit.subreddit("wallstreetbets").hot(limit=limit):
            posts.append(submission.title + " " + (submission.selftext or ""))
        pat = re.compile(r'\$?([A-Z]{2,5})\b')
        exclude = {"USD", "WSB", "ETF", "IPO", "SPAC", "CEO", "DD", "FOMO", "ATH", "LOL", "TOS"}
        mentions = []
        for text in posts:
            for match in pat.findall(text):
                if match not in exclude and match.isalpha():
                    mentions.append(match)
        counts = Counter(mentions)
        return counts.most_common(5)
    except Exception as e:
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

# --- Helper for colored badges ---
def colored_badge(value, label):
    if value is None:
        return f"<span class='badge badge-red'>N/A</span>"
    if label.lower() == "vix":
        if value > 30: return f"<span class='badge badge-red'>High</span>"
        elif value > 20: return f"<span class='badge badge-yellow'>Elevated</span>"
        else: return f"<span class='badge badge-green'>Calm</span>"
    if label.lower() == "rsi":
        if value > 70: return f"<span class='badge badge-red'>Overbought</span>"
        elif value < 35: return f"<span class='badge badge-blue'>Oversold</span>"
        else: return f"<span class='badge badge-green'>Normal</span>"
    return ""

# --- Display Data as Cards ---
with st.container():
    c1, c2 = st.columns(2)
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

# --- Buffett-Style Signal Logic ---
def buffett_style_signal(vix, rsi):
    fear_count = 0
    if vix is not None and vix > 28: fear_count += 1
    if rsi is not None and rsi < 35: fear_count += 1
    if rsi is not None and rsi < 35 and fear_count >= 2:
        return "🟢 Buffett: Really Good Time to Buy (Be Greedy When Others Are Fearful)"
    if rsi is not None and rsi < 40 and fear_count >= 1:
        return "🟡 Buffett: Good Time to Accumulate, Be Patient"
    if (rsi is not None and 40 <= rsi <= 60 and vix is not None and 16 < vix < 28):
        return "⚪ Buffett: Wait, Stay Patient (No Edge)"
    if (rsi is not None and rsi > 70):
        return "🔴 Buffett: Market Overheated, Wait for Pullback"
    return "🔴 Buffett: Hold Off (No Opportunity Detected)"

# --- Tom Lee (Fundstrat) Signal Logic ---
def tomlee_signal(vix, rsi):
    bullish_score = 0
    if vix is not None and vix > 22: bullish_score += 1
    if rsi is not None and rsi < 45: bullish_score += 1
    if bullish_score >= 2:
        return "🟢 Tom Lee: Good Time to Buy (Buy the Dip Mentality)"
    if vix is not None and vix < 14 and rsi is not None and rsi > 70:
        return "🔴 Tom Lee: Even Tom Lee says: Hold Off, Too Hot!"
    return "⚪ Tom Lee: Stay Invested or Accumulate Slowly"

# --- Buffett Card ---
st.markdown('<div class="datacard buffett-card" style="margin-top:0.8em;">', unsafe_allow_html=True)
st.markdown('<div class="signal-head">🧭 Buffett-Style Long-Term Investor Signal</div>', unsafe_allow_html=True)
st.markdown(f"<div class='signal-main'>{buffett_style_signal(vix_val, rsi_val)}</div>", unsafe_allow_html=True)
st.markdown("<div class='signal-detail'>Buffett: <i>Be fearful when others are greedy, and greedy when others are fearful.</i></div>", unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# --- Tom Lee Card ---
st.markdown('<div class="datacard tomlee-card">', unsafe_allow_html=True)
st.markdown('<div class="signal-head">📈 Tom Lee (Fundstrat) Tactical Signal</div>', unsafe_allow_html=True)
st.markdown(f"<div class='signal-main'>{tomlee_signal(vix_val, rsi_val)}</div>", unsafe_allow_html=True)
st.markdown("<div class='signal-detail'>Tom Lee: <i>When everyone is cautious, that's when opportunity strikes.</i></div>", unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# --- Meme Stock Radar Card ---
st.markdown('<div class="datacard meme-card">', unsafe_allow_html=True)
st.markdown('<div class="signal-head">🚀 Meme Stock Radar <span class="badge badge-blue">(WSB Hotlist)</span></div>', unsafe_allow_html=True)
memes = fetch_reddit_meme_tickers(limit=250)
if memes:
    for i, (ticker, n) in enumerate(memes):
        pct = get_price_change(ticker)
        change = f"<span style='color:{'#19bb77' if pct and pct>0 else '#e44b5a'}; font-weight:700;'>{pct:+.2f}%</span>" if pct is not None else ""
        fire = "🔥" if i==0 and pct and pct > 10 else ""
        st.markdown(f"<b>{ticker}</b>: {n} mentions {change} {fire}", unsafe_allow_html=True)
    st.caption("Top tickers in r/wallstreetbets now. ⚠️ Not investment advice.", unsafe_allow_html=True)
else:
    st.caption("No trending meme tickers found (try again soon).", unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# --- Disclaimer Collapsible ---
with st.expander("⚠️ Disclaimer (Tap to expand)", expanded=False):
    st.markdown("""
    <div class='disclaimer-pro'>
    <b>For educational purposes only. Not financial advice. Use at your own risk.</b>
    These signals use sentiment and volatility for illustration only — not for trading or portfolio management.<br>
    <b>Legal Notice:</b> This dashboard is for general informational purposes and does not create a client relationship. Always consult your licensed advisor before acting.
    </div>
    """, unsafe_allow_html=True)

# --- Refresh Button ---
if st.button("🔄 Refresh Data"):
    st.rerun()

