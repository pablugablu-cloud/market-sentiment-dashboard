import os
import math
import time
from datetime import datetime, timezone

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st
import yfinance as yf
from ta.momentum import RSIIndicator
from ta.trend import SMAIndicator

# Optional dependencies. App works even if these fail.
try:
    from newsapi import NewsApiClient
except Exception:
    NewsApiClient = None

try:
    from pytrends.request import TrendReq
except Exception:
    TrendReq = None


# ------------------------------------------------------------
# Page config
# ------------------------------------------------------------
st.set_page_config(
    page_title="Market Sentiment Pro",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ------------------------------------------------------------
# Styling
# ------------------------------------------------------------
st.markdown(
    """
<style>
    .stApp {
        background:
            radial-gradient(circle at top left, rgba(0, 160, 255, .12), transparent 30%),
            radial-gradient(circle at top right, rgba(0, 255, 170, .10), transparent 28%),
            linear-gradient(135deg, #070b14 0%, #101626 48%, #070b14 100%);
        color: #f6f8fb;
    }
    [data-testid="stHeader"] { background: rgba(0,0,0,0); }
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, rgba(13,18,31,.96), rgba(7,11,20,.96));
        border-right: 1px solid rgba(255,255,255,.08);
    }
    .hero {
        border: 1px solid rgba(255,255,255,.10);
        border-radius: 26px;
        padding: 28px 30px;
        background: linear-gradient(135deg, rgba(255,255,255,.10), rgba(255,255,255,.035));
        box-shadow: 0 18px 60px rgba(0,0,0,.35);
        margin-bottom: 20px;
    }
    .hero h1 {
        font-size: 46px;
        line-height: 1.05;
        margin: 0;
        letter-spacing: -1.2px;
    }
    .muted {
        color: rgba(246,248,251,.72);
        font-size: 15px;
    }
    .card {
        border: 1px solid rgba(255,255,255,.10);
        border-radius: 22px;
        padding: 20px;
        background: rgba(255,255,255,.055);
        box-shadow: 0 10px 34px rgba(0,0,0,.25);
        min-height: 132px;
    }
    .label {
        color: rgba(246,248,251,.66);
        font-size: 13px;
        font-weight: 700;
        letter-spacing: .4px;
        text-transform: uppercase;
    }
    .value {
        color: #ffffff;
        font-size: 34px;
        font-weight: 800;
        margin-top: 5px;
        letter-spacing: -.5px;
    }
    .explain {
        color: rgba(246,248,251,.70);
        font-size: 13px;
        margin-top: 6px;
    }
    .pill {
        display: inline-block;
        padding: 6px 10px;
        border-radius: 999px;
        font-weight: 800;
        font-size: 12px;
        margin-top: 10px;
    }
    .pill-green { background: rgba(0, 194, 123, .18); color: #36e69a; border: 1px solid rgba(54,230,154,.24); }
    .pill-blue { background: rgba(50, 138, 255, .18); color: #7bb4ff; border: 1px solid rgba(123,180,255,.24); }
    .pill-yellow { background: rgba(255, 190, 70, .18); color: #ffd173; border: 1px solid rgba(255,209,115,.24); }
    .pill-red { background: rgba(255, 85, 85, .18); color: #ff8a8a; border: 1px solid rgba(255,138,138,.24); }
    .signal {
        border-radius: 22px;
        padding: 18px 20px;
        margin: 8px 0 14px 0;
        border: 1px solid rgba(255,255,255,.12);
        background: rgba(255,255,255,.06);
    }
    .signal-title {
        font-size: 19px;
        font-weight: 900;
        margin-bottom: 4px;
    }
    .small {
        color: rgba(246,248,251,.68);
        font-size: 13px;
    }
    .footer {
        color: rgba(246,248,251,.55);
        font-size: 12px;
        margin-top: 25px;
        padding-top: 18px;
        border-top: 1px solid rgba(255,255,255,.08);
    }
    div[data-testid="stMetric"] {
        border: 1px solid rgba(255,255,255,.10);
        border-radius: 18px;
        padding: 14px;
        background: rgba(255,255,255,.05);
    }
</style>
    """,
    unsafe_allow_html=True,
)


# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------
def clamp(value, lower=0, upper=100):
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    return max(lower, min(upper, value))


def safe_round(value, digits=2):
    if value is None:
        return None
    try:
        if math.isnan(value):
            return None
        return round(float(value), digits)
    except Exception:
        return None


def score_from_range(value, points):
    """
    Linear interpolation helper.

    points example:
    [(12, 90), (18, 70), (25, 45), (35, 18)]
    X below first point returns first score; above last point returns last score.
    """
    if value is None:
        return None

    value = float(value)
    points = sorted(points, key=lambda x: x[0])

    if value <= points[0][0]:
        return float(points[0][1])
    if value >= points[-1][0]:
        return float(points[-1][1])

    for (x1, y1), (x2, y2) in zip(points, points[1:]):
        if x1 <= value <= x2:
            if x2 == x1:
                return float(y1)
            pct = (value - x1) / (x2 - x1)
            return float(y1 + pct * (y2 - y1))

    return None


def label_for_score(score):
    if score is None:
        return "Unknown", "pill-blue"
    if score <= 24:
        return "Extreme Fear", "pill-green"
    if score <= 44:
        return "Fear", "pill-green"
    if score <= 60:
        return "Neutral", "pill-blue"
    if score <= 75:
        return "Greed", "pill-yellow"
    return "Extreme Greed", "pill-red"


def deployment_guidance(score, mode):
    if score is None:
        return "Data is incomplete. Use your normal planned DCA only until signals are cleaner."

    if mode == "Conservative":
        bands = [
            (24, "Good zone to deploy, but still use tranches. Consider 20–30% of planned taxable cash now, then weekly/biweekly."),
            (44, "Reasonable accumulation zone. Consider 10–20% now and keep the rest on schedule."),
            (60, "Neutral. Stick to your normal plan. No need to force a big lump-sum buy."),
            (75, "Market is leaning greedy. Keep buys small and mechanical."),
            (100, "Overheated zone. I would pause big lump-sum taxable buys and wait for a better setup."),
        ]
    elif mode == "Aggressive":
        bands = [
            (24, "Very attractive fear setup. Consider deploying a larger tranche now while keeping dry powder."),
            (44, "Good buy zone. Deploy meaningfully but avoid pretending you can nail the bottom."),
            (60, "Normal DCA zone. Invest steadily."),
            (75, "Greedy but not automatically dangerous. Smaller buys are fine."),
            (100, "Too hot for aggressive lump-sum buying. Let RSI/valuation pressure cool."),
        ]
    else:
        bands = [
            (24, "Excellent fear setup for disciplined taxable deployment. Deploy in tranches, not all at once."),
            (44, "Good accumulation zone. Start/continue DCA with a slightly larger tranche."),
            (60, "Neutral. Follow your plan and avoid emotional timing."),
            (75, "Greed zone. Continue smaller scheduled buys, but don’t chase."),
            (100, "Extreme greed. Hold cash/SGOV dry powder and wait for better risk/reward."),
        ]

    for cutoff, text in bands:
        if score <= cutoff:
            return text
    return bands[-1][1]


def classify_vix(vix):
    if vix is None:
        return "N/A", "pill-blue"
    if vix < 14:
        return "Complacent", "pill-red"
    if vix < 20:
        return "Calm", "pill-blue"
    if vix < 28:
        return "Elevated", "pill-yellow"
    return "Fear", "pill-green"


def classify_rsi(rsi):
    if rsi is None:
        return "N/A", "pill-blue"
    if rsi < 35:
        return "Oversold", "pill-green"
    if rsi < 45:
        return "Soft", "pill-green"
    if rsi <= 65:
        return "Healthy", "pill-blue"
    if rsi <= 72:
        return "Warm", "pill-yellow"
    return "Overbought", "pill-red"


def classify_pcr(pcr):
    if pcr is None:
        return "N/A", "pill-blue"
    if pcr < 0.65:
        return "Greedy", "pill-red"
    if pcr < 0.85:
        return "Optimistic", "pill-yellow"
    if pcr <= 1.10:
        return "Balanced", "pill-blue"
    return "Fearful", "pill-green"


def classify_ma(distance):
    if distance is None:
        return "N/A", "pill-blue"
    if distance < -10:
        return "Deep Discount", "pill-green"
    if distance < -3:
        return "Below Trend", "pill-green"
    if distance <= 8:
        return "Near Trend", "pill-blue"
    if distance <= 15:
        return "Extended", "pill-yellow"
    return "Very Extended", "pill-red"


def classify_curve(spread):
    if spread is None:
        return "N/A", "pill-blue"
    if spread < -0.50:
        return "Inverted", "pill-yellow"
    if spread < 0:
        return "Slight Inversion", "pill-yellow"
    if spread < 0.75:
        return "Normalizing", "pill-blue"
    return "Steep", "pill-blue"


def metric_card(title, value, label, pill_class, explanation):
    st.markdown(
        f"""
<div class="card">
    <div class="label">{title}</div>
    <div class="value">{value}</div>
    <div class="pill {pill_class}">{label}</div>
    <div class="explain">{explanation}</div>
</div>
        """,
        unsafe_allow_html=True,
    )


# ------------------------------------------------------------
# Data fetchers
# ------------------------------------------------------------
@st.cache_data(ttl=900, show_spinner=False)
def fetch_spx_data():
    df = yf.Ticker("^GSPC").history(period="1y", interval="1d", auto_adjust=False)
    if df.empty:
        return None

    df = df.dropna(subset=["Close"]).copy()
    df["RSI"] = RSIIndicator(df["Close"], window=14).rsi()
    df["SMA_200"] = SMAIndicator(df["Close"], window=200).sma_indicator()
    last = df.iloc[-1]

    close = safe_round(last["Close"], 2)
    rsi = safe_round(last["RSI"], 2)
    sma200 = safe_round(last["SMA_200"], 2)
    ma_distance = safe_round(((close - sma200) / sma200) * 100, 2) if close and sma200 else None

    return {
        "close": close,
        "rsi": rsi,
        "sma200": sma200,
        "ma_distance": ma_distance,
        "history": df.reset_index(),
    }


@st.cache_data(ttl=900, show_spinner=False)
def fetch_vix():
    df = yf.Ticker("^VIX").history(period="1mo", interval="1d")
    if df.empty:
        return None
    return safe_round(df["Close"].dropna().iloc[-1], 2)


@st.cache_data(ttl=900, show_spinner=False)
def fetch_pcr():
    # YCharts endpoint can occasionally block requests. App degrades cleanly.
    url = (
        "https://ycharts.com/charts/fund_data.json"
        "?calcs=&chartId=&chartType=interactive&correlations=&"
        "customGrowthAmount=&dataInLegend=value&dateSelection=range&"
        "format=real&legendOnChart=false&lineAnnotations=&nameInLegend=name_and_ticker&"
        "partner=basic_2000&performanceDisclosure=false&recessions=false&scaleType=linear&"
        "securities=id%3AI%3ACBOEEPCR%2Cinclude%3Atrue%2C%2C&maxPoints=594"
    )
    try:
        r = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        js = r.json()
        return safe_round(js["chart_data"][0][0]["last_value"], 2)
    except Exception:
        return None


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_bond_yields():
    url = (
        "https://quote.cnbc.com/quote-html-webservice/restQuote/"
        "symbolType/symbol?"
        "symbols="
        "US1M%7CUS2M%7CUS3M%7CUS4M%7CUS6M%7CUS1Y%7CUS2Y%7CUS3Y%7CUS5Y%7CUS7Y%7CUS10Y%7CUS20Y%7CUS30Y"
        "&requestMethod=itv&noform=1&partnerId=2&fund=1&exthrs=1&output=json&events=1"
    )
    try:
        r = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        quotes = r.json()["FormattedQuoteResult"]["FormattedQuote"]
        return {q["symbol"]: safe_round(q["last"].strip("%"), 3) for q in quotes}
    except Exception:
        return {}


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_google_trends(term="stock market crash"):
    if TrendReq is None:
        return None
    try:
        py = TrendReq(hl="en-US", tz=360, timeout=(10, 25))
        py.build_payload([term], timeframe="now 7-d", geo="US")
        df = py.interest_over_time()
        if df.empty or term not in df:
            return None
        return int(df[term].dropna().iloc[-1])
    except Exception:
        return None


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_news_sentiment():
    key = os.getenv("NEWSAPI_KEY") or st.secrets.get("NEWSAPI_KEY", None) if hasattr(st, "secrets") else None
    if not key or NewsApiClient is None:
        return None, "Optional"

    bears = [
        "crash", "collapse", "meltdown", "plunge", "sell-off", "recession", "slowdown",
        "downturn", "panic", "fear", "turmoil", "risk-off", "bearish", "volatility",
        "instability", "losses", "decline", "drop", "slump", "downgrade"
    ]
    bulls = [
        "rally", "surge", "soar", "rebound", "recovery", "growth", "momentum",
        "bullish", "optimism", "confidence", "risk-on", "strength", "resilient",
        "record high", "all-time high", "gains", "advance", "outperform", "upgrade"
    ]

    try:
        na = NewsApiClient(api_key=key)
        arts = na.get_everything(q="S&P 500 OR stock market", language="en", page_size=40)["articles"]
        titles = [(a.get("title") or "").lower() for a in arts]
        bear_count = sum(any(word in title for word in bears) for title in titles)
        bull_count = sum(any(word in title for word in bulls) for title in titles)
        score = int(clamp(50 + 3 * (bull_count - bear_count)))
        label = "Bullish" if score > 60 else "Bearish" if score < 40 else "Mixed"
        return score, label
    except Exception:
        return None, "Unavailable"


# ------------------------------------------------------------
# Composite score
# ------------------------------------------------------------
def build_component_scores(vix, rsi, ma_distance, pcr, curve_spread, trends, news_score):
    components = []

    # Fear/Greed score: 0 = fear/opportunity, 100 = greed/overheated.
    components.append({
        "Component": "VIX",
        "Value": vix,
        "Score": score_from_range(vix, [(12, 85), (18, 62), (25, 38), (35, 15), (50, 5)]),
        "Weight": 0.22,
        "Read": "Lower VIX = complacency/greed; higher VIX = fear."
    })
    components.append({
        "Component": "RSI",
        "Value": rsi,
        "Score": score_from_range(rsi, [(25, 10), (35, 25), (50, 50), (65, 72), (75, 90), (85, 100)]),
        "Weight": 0.20,
        "Read": "High RSI = stretched; low RSI = washed out."
    })
    components.append({
        "Component": "S&P vs 200D",
        "Value": ma_distance,
        "Score": score_from_range(ma_distance, [(-20, 8), (-10, 20), (0, 48), (8, 68), (15, 84), (25, 96)]),
        "Weight": 0.20,
        "Read": "Far above trend = greedy; below trend = fear/discount."
    })
    components.append({
        "Component": "Put/Call",
        "Value": pcr,
        "Score": score_from_range(pcr, [(0.55, 90), (0.75, 70), (0.95, 52), (1.15, 35), (1.40, 15)]),
        "Weight": 0.16,
        "Read": "Low put/call = call chasing; high put/call = hedging/fear."
    })
    components.append({
        "Component": "Yield Curve",
        "Value": curve_spread,
        "Score": score_from_range(curve_spread, [(-1.2, 70), (-0.5, 58), (0, 50), (0.8, 45), (1.5, 48)]),
        "Weight": 0.08,
        "Read": "Macro risk modifier. Not a direct buy/sell switch."
    })
    components.append({
        "Component": "Google Trends",
        "Value": trends,
        "Score": score_from_range(trends, [(0, 72), (20, 62), (50, 45), (80, 25), (100, 10)]),
        "Weight": 0.07,
        "Read": "Crash-search spikes usually mean public fear."
    })
    components.append({
        "Component": "News Sentiment",
        "Value": news_score,
        "Score": news_score,
        "Weight": 0.07,
        "Read": "Headline tone. Optional because APIs can be noisy."
    })

    df = pd.DataFrame(components)
    available = df.dropna(subset=["Score"]).copy()
    if available.empty:
        return None, df

    # Reweight available signals so missing optional data doesn't break the app.
    total_weight = available["Weight"].sum()
    available["AdjWeight"] = available["Weight"] / total_weight
    composite = float((available["Score"] * available["AdjWeight"]).sum())
    return int(round(clamp(composite))), df


# ------------------------------------------------------------
# Sidebar controls
# ------------------------------------------------------------
with st.sidebar:
    st.title("⚙️ Controls")
    deploy_mode = st.selectbox(
        "Taxable deployment style",
        ["Balanced", "Conservative", "Aggressive"],
        index=0,
        help="This changes only the wording of the guidance, not the market data."
    )
    trend_term = st.text_input("Google Trends term", value="stock market crash")
    refresh = st.button("🔄 Refresh now", use_container_width=True)

    st.markdown("---")
    st.caption("This app is for education and decision support only. It is not financial advice.")
    st.caption("Tip: add NEWSAPI_KEY in Streamlit secrets to enable headline sentiment.")


if refresh:
    st.cache_data.clear()
    st.rerun()


# ------------------------------------------------------------
# Fetch data
# ------------------------------------------------------------
with st.spinner("Pulling market data..."):
    spx = fetch_spx_data()
    vix = fetch_vix()
    pcr = fetch_pcr()
    yields = fetch_bond_yields()
    trends = fetch_google_trends(trend_term)
    news_score, news_label = fetch_news_sentiment()

if spx is None:
    st.error("Could not load S&P 500 data from Yahoo Finance. Try refreshing in a few minutes.")
    st.stop()

spx_close = spx["close"]
rsi = spx["rsi"]
sma200 = spx["sma200"]
ma_distance = spx["ma_distance"]

us2y = yields.get("US2Y") if yields else None
us10y = yields.get("US10Y") if yields else None
curve_spread = safe_round(us10y - us2y, 3) if us2y is not None and us10y is not None else None

fear_greed_score, comp_df = build_component_scores(vix, rsi, ma_distance, pcr, curve_spread, trends, news_score)
fg_label, fg_class = label_for_score(fear_greed_score)


# ------------------------------------------------------------
# Header
# ------------------------------------------------------------
st.markdown(
    f"""
<div class="hero">
    <h1>Market Sentiment Pro</h1>
    <div class="muted">
        A cleaner taxable-investing dashboard: Fear & Greed, Buffett patience, Bogle discipline, and Tom Lee tactical momentum.
        <br/>Last refreshed: {datetime.now().strftime("%b %d, %Y %I:%M %p")}
    </div>
</div>
    """,
    unsafe_allow_html=True,
)


# ------------------------------------------------------------
# Top section
# ------------------------------------------------------------
left, right = st.columns([1.1, 1])

with left:
    gauge = go.Figure(go.Indicator(
        mode="gauge+number",
        value=fear_greed_score if fear_greed_score is not None else 50,
        number={"font": {"size": 54}},
        title={"text": f"Fear & Greed: {fg_label}", "font": {"size": 22}},
        gauge={
            "axis": {"range": [0, 100], "tickwidth": 1},
            "bar": {"thickness": 0.18},
            "steps": [
                {"range": [0, 25], "color": "rgba(0, 194, 123, .55)"},
                {"range": [25, 45], "color": "rgba(78, 205, 128, .40)"},
                {"range": [45, 60], "color": "rgba(120, 150, 180, .35)"},
                {"range": [60, 75], "color": "rgba(255, 190, 70, .45)"},
                {"range": [75, 100], "color": "rgba(255, 85, 85, .50)"},
            ],
        },
    ))
    gauge.update_layout(
        height=365,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "#f6f8fb"},
        margin=dict(l=20, r=20, t=55, b=10),
    )
    st.plotly_chart(gauge, use_container_width=True)

with right:
    st.markdown("### Clear Action Read")
    st.markdown(
        f"""
<div class="signal">
    <div class="signal-title">Taxable Deployment</div>
    <div>{deployment_guidance(fear_greed_score, deploy_mode)}</div>
</div>
<div class="signal">
    <div class="signal-title">My blunt read</div>
    <div>Use this dashboard to size tranches, not to predict the exact bottom. The edge is discipline, not magic.</div>
</div>
        """,
        unsafe_allow_html=True,
    )

    if fear_greed_score is not None:
        if fear_greed_score <= 44:
            st.success("Market tone is giving you a better buying setup than usual.")
        elif fear_greed_score >= 76:
            st.error("Market tone is hot. Don’t chase just because the chart feels good.")
        elif fear_greed_score >= 61:
            st.warning("Greed is building. Smaller scheduled buys make more sense than hero buys.")
        else:
            st.info("Neutral market. Boring DCA is the correct behavior.")


# ------------------------------------------------------------
# Cards
# ------------------------------------------------------------
st.markdown("## Signal Board")
c1, c2, c3, c4 = st.columns(4)

vix_label, vix_class = classify_vix(vix)
rsi_label, rsi_class = classify_rsi(rsi)
pcr_label, pcr_class = classify_pcr(pcr)
ma_label, ma_class = classify_ma(ma_distance)

with c1:
    metric_card("VIX", vix if vix is not None else "N/A", vix_label, vix_class, "Fear gauge. Higher = more panic.")
with c2:
    metric_card("S&P 500 RSI", rsi if rsi is not None else "N/A", rsi_label, rsi_class, "Momentum temperature.")
with c3:
    metric_card("S&P vs 200D", f"{ma_distance}%" if ma_distance is not None else "N/A", ma_label, ma_class, "Distance from long-term trend.")
with c4:
    metric_card("Put/Call", pcr if pcr is not None else "N/A", pcr_label, pcr_class, "Options sentiment: low = greed, high = fear.")

c5, c6, c7, c8 = st.columns(4)
curve_label, curve_class = classify_curve(curve_spread)

with c5:
    metric_card("10Y - 2Y Spread", f"{curve_spread}%" if curve_spread is not None else "N/A", curve_label, curve_class, "Macro cycle risk modifier.")
with c6:
    metric_card("Google Trends", trends if trends is not None else "N/A", "Fear Search" if trends and trends > 60 else "Normal", "pill-yellow" if trends and trends > 60 else "pill-blue", f"Search term: {trend_term}")
with c7:
    metric_card("News Sentiment", news_score if news_score is not None else "N/A", news_label, "pill-green" if news_score and news_score < 40 else "pill-red" if news_score and news_score > 65 else "pill-blue", "Optional headline tone.")
with c8:
    metric_card("S&P 500", f"{spx_close:,.2f}" if spx_close else "N/A", "Live Market", "pill-blue", f"200D SMA: {sma200:,.2f}" if sma200 else "200D unavailable")


# ------------------------------------------------------------
# Investor lens
# ------------------------------------------------------------
st.markdown("## Investor Lens")

b1, b2, b3 = st.columns(3)

with b1:
    if fear_greed_score is not None and fear_greed_score <= 44:
        buffett_msg = "Be greedy when others are fearful — but only with disciplined tranches."
        b_style = "pill-green"
    elif fear_greed_score is not None and fear_greed_score >= 76:
        buffett_msg = "Do not chase a happy market. Let the pitch come to you."
        b_style = "pill-red"
    else:
        buffett_msg = "Patience is fine. Cash has option value when markets are not offering fear."
        b_style = "pill-blue"
    st.markdown(f"""
<div class="card">
    <div class="label">Buffett Lens</div>
    <div class="value" style="font-size:22px;">Quality + Patience</div>
    <div class="pill {b_style}">Valuation discipline</div>
    <div class="explain">{buffett_msg}</div>
</div>
""", unsafe_allow_html=True)

with b2:
    bogle_msg = "Stay invested. Automate. Do not let a dashboard turn you into a day trader."
    st.markdown(f"""
<div class="card">
    <div class="label">Bogle Lens</div>
    <div class="value" style="font-size:22px;">Own the market</div>
    <div class="pill pill-blue">Keep it simple</div>
    <div class="explain">{bogle_msg}</div>
</div>
""", unsafe_allow_html=True)

with b3:
    if rsi is not None and vix is not None and rsi < 45 and vix > 20:
        tom_msg = "Dip setup detected. Tactical buyers may have a better entry."
        t_style = "pill-green"
    elif rsi is not None and rsi > 70 and vix is not None and vix < 16:
        tom_msg = "Too much comfort. Tactical risk/reward is less attractive."
        t_style = "pill-red"
    else:
        tom_msg = "Trend is not screaming panic or euphoria. Stay invested."
        t_style = "pill-blue"
    st.markdown(f"""
<div class="card">
    <div class="label">Tom Lee Lens</div>
    <div class="value" style="font-size:22px;">Tactical Setup</div>
    <div class="pill {t_style}">Market timing assist</div>
    <div class="explain">{tom_msg}</div>
</div>
""", unsafe_allow_html=True)


# ------------------------------------------------------------
# Charts and tables
# ------------------------------------------------------------
st.markdown("## Market Internals")

tab1, tab2, tab3 = st.tabs(["Component Breakdown", "S&P Trend", "Treasury Yields"])

with tab1:
    show_df = comp_df.copy()
    show_df["Score"] = show_df["Score"].apply(lambda x: None if pd.isna(x) else round(x, 1))
    show_df["Weight"] = (show_df["Weight"] * 100).round(0).astype(int).astype(str) + "%"
    st.dataframe(show_df, use_container_width=True, hide_index=True)

    chart_df = comp_df.dropna(subset=["Score"]).copy()
    if not chart_df.empty:
        fig = go.Figure()
        fig.add_trace(go.Bar(x=chart_df["Component"], y=chart_df["Score"], text=chart_df["Score"].round(0)))
        fig.update_layout(
            height=360,
            yaxis_range=[0, 100],
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font={"color": "#f6f8fb"},
            margin=dict(l=10, r=10, t=20, b=10),
        )
        st.plotly_chart(fig, use_container_width=True)

with tab2:
    hist = spx["history"].copy()
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=hist["Date"], y=hist["Close"], name="S&P 500", mode="lines"))
    fig.add_trace(go.Scatter(x=hist["Date"], y=hist["SMA_200"], name="200D SMA", mode="lines"))
    fig.update_layout(
        height=430,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "#f6f8fb"},
        margin=dict(l=10, r=10, t=20, b=10),
        legend=dict(orientation="h"),
    )
    st.plotly_chart(fig, use_container_width=True)

with tab3:
    if yields:
        order = ["US1M", "US2M", "US3M", "US4M", "US6M", "US1Y", "US2Y", "US3Y", "US5Y", "US7Y", "US10Y", "US20Y", "US30Y"]
        ydf = pd.DataFrame(
            [{"Maturity": k, "Yield (%)": yields.get(k)} for k in order if yields.get(k) is not None]
        )
        st.dataframe(ydf, use_container_width=True, hide_index=True)
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=ydf["Maturity"], y=ydf["Yield (%)"], mode="lines+markers", name="Yield"))
        fig.update_layout(
            height=360,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font={"color": "#f6f8fb"},
            margin=dict(l=10, r=10, t=20, b=10),
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Treasury yields unavailable right now.")


# ------------------------------------------------------------
# Footer
# ------------------------------------------------------------
st.markdown(
    """
<div class="footer">
    Educational only. Not financial advice. Data may be delayed or unavailable depending on provider limits.
    The right use of this dashboard is to guide taxable deployment behavior, not to make emotional all-in/all-out decisions.
</div>
    """,
    unsafe_allow_html=True,
)
