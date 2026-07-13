import html as html_lib
import math
import re
from datetime import datetime
from io import StringIO
from zoneinfo import ZoneInfo

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st
import yfinance as yf
from ta.momentum import RSIIndicator
from ta.trend import SMAIndicator


# ============================================================
# App configuration
# ============================================================
st.set_page_config(
    page_title="Should I Buy Today?",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

PACIFIC = ZoneInfo("America/Los_Angeles")
NOW_PT = datetime.now(PACIFIC)

if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = True


# ============================================================
# Theme
# ============================================================
LIGHT = {
    "bg": "#f5f7fb",
    "surface": "#ffffff",
    "surface2": "#f8fafc",
    "surface3": "#edf2f7",
    "text": "#111827",
    "muted": "#64748b",
    "muted2": "#94a3b8",
    "border": "rgba(15,23,42,.09)",
    "border2": "rgba(15,23,42,.15)",
    "shadow": "0 18px 52px rgba(15,23,42,.08)",
    "green": "#16a34a",
    "green_bg": "rgba(22,163,74,.11)",
    "yellow": "#d97706",
    "yellow_bg": "rgba(217,119,6,.11)",
    "red": "#e11d48",
    "red_bg": "rgba(225,29,72,.10)",
    "blue": "#2563eb",
    "blue_bg": "rgba(37,99,235,.10)",
}

DARK = {
    "bg": "#080d16",
    "surface": "#111827",
    "surface2": "#151f30",
    "surface3": "#0d1421",
    "text": "#f8fafc",
    "muted": "#a8b2c1",
    "muted2": "#748094",
    "border": "rgba(255,255,255,.09)",
    "border2": "rgba(255,255,255,.16)",
    "shadow": "0 22px 64px rgba(0,0,0,.32)",
    "green": "#22c55e",
    "green_bg": "rgba(34,197,94,.12)",
    "yellow": "#fbbf24",
    "yellow_bg": "rgba(251,191,36,.12)",
    "red": "#fb7185",
    "red_bg": "rgba(251,113,133,.12)",
    "blue": "#60a5fa",
    "blue_bg": "rgba(96,165,250,.12)",
}


def current_theme():
    return DARK if st.session_state.dark_mode else LIGHT


def inject_css(t):
    st.markdown(
        f"""
<style>
:root {{ color-scheme: {'dark' if st.session_state.dark_mode else 'light'}; }}

* {{
    font-family: Inter, ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}}

.stApp {{
    color: {t['text']};
    background:
        radial-gradient(circle at 5% 0%, rgba(37,99,235,.08), transparent 28%),
        radial-gradient(circle at 96% 2%, rgba(34,197,94,.06), transparent 26%),
        {t['bg']};
}}

[data-testid="stHeader"] {{ background: transparent; }}
[data-testid="stToolbar"], [data-testid="stDecoration"] {{ display: none; }}

.block-container {{
    max-width: 1240px;
    padding-top: 1.1rem;
    padding-bottom: 3rem;
}}

/* Controls */
div[data-testid="stButton"] button {{
    height: 40px;
    border: 1px solid {t['border']};
    border-radius: 12px;
    background: {t['surface']};
    color: {t['text']};
    font-weight: 750;
    box-shadow: none;
}}

div[data-testid="stButton"] button:hover {{
    border-color: {t['border2']};
    transform: translateY(-1px);
}}

.stTabs [data-baseweb="tab-list"] {{
    gap: 8px;
    border-bottom: 1px solid {t['border']};
    padding-bottom: 8px;
}}

.stTabs [data-baseweb="tab"] {{
    height: 42px;
    border-radius: 11px;
    padding: 0 15px;
    color: {t['muted']};
    font-weight: 800;
}}

.stTabs [aria-selected="true"] {{
    color: {t['text']} !important;
    background: {t['surface']} !important;
    border: 1px solid {t['border']} !important;
}}

div[role="radiogroup"] {{ gap: 5px; flex-wrap: wrap; }}
div[role="radiogroup"] label {{
    border: 1px solid {t['border']};
    border-radius: 999px;
    background: {t['surface']};
    padding: 4px 10px;
}}

/* Header */
.app-header {{
    display: flex;
    align-items: flex-end;
    justify-content: space-between;
    gap: 24px;
    padding: 14px 2px 20px;
}}

.app-title {{
    color: {t['text']};
    font-size: clamp(31px, 4vw, 46px);
    line-height: 1;
    font-weight: 930;
    letter-spacing: -1.8px;
}}

.app-subtitle {{
    color: {t['muted']};
    margin-top: 10px;
    font-size: 15px;
    line-height: 1.45;
}}

.freshness {{
    display: flex;
    flex-wrap: wrap;
    justify-content: flex-end;
    gap: 7px;
}}

.meta-pill {{
    display: inline-flex;
    align-items: center;
    gap: 7px;
    color: {t['muted']};
    background: {t['surface']};
    border: 1px solid {t['border']};
    border-radius: 999px;
    padding: 8px 11px;
    font-size: 11px;
    font-weight: 800;
    white-space: nowrap;
}}

.status-dot {{
    width: 7px;
    height: 7px;
    border-radius: 999px;
    background: {t['green']};
}}

/* Decision card */
.decision-card {{
    position: relative;
    overflow: hidden;
    background:
        radial-gradient(circle at 100% 0%, rgba(251,113,133,.10), transparent 35%),
        linear-gradient(145deg, {t['surface']} 0%, {t['surface2']} 100%);
    border: 1px solid {t['border']};
    border-radius: 28px;
    box-shadow: {t['shadow']};
    padding: 30px;
    animation: rise .55s cubic-bezier(.2,.8,.2,1) both;
}}

.decision-grid {{
    display: grid;
    grid-template-columns: minmax(0, 1.15fr) minmax(280px, .85fr);
    gap: 32px;
    align-items: start;
}}

.eyebrow {{
    color: {t['muted']};
    font-size: 11px;
    font-weight: 900;
    text-transform: uppercase;
    letter-spacing: .72px;
}}

.action-title {{
    color: {t['text']};
    font-size: clamp(39px, 5vw, 61px);
    font-weight: 950;
    line-height: .96;
    letter-spacing: -2.2px;
    margin-top: 10px;
}}

.action-copy {{
    color: {t['muted']};
    font-size: 17px;
    line-height: 1.5;
    margin-top: 15px;
    max-width: 650px;
}}

.guardrail {{
    display: inline-flex;
    align-items: center;
    gap: 8px;
    margin-top: 17px;
    padding: 10px 12px;
    color: {t['blue']};
    background: {t['blue_bg']};
    border: 1px solid rgba(96,165,250,.16);
    border-radius: 12px;
    font-size: 13px;
    font-weight: 800;
}}

.score-panel {{
    background: rgba(255,255,255,.025);
    border: 1px solid {t['border']};
    border-radius: 22px;
    padding: 20px;
}}

.score-row {{
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 18px;
}}

.temperature {{
    color: {t['text']};
    font-size: 25px;
    font-weight: 900;
    margin-top: 5px;
}}

.score-number {{
    color: {t['text']};
    font-size: 70px;
    font-weight: 950;
    line-height: .82;
    letter-spacing: -3px;
    animation: scoreIn .7s cubic-bezier(.2,.9,.2,1) both;
}}

.heat-meter {{
    position: relative;
    height: 14px;
    margin-top: 26px;
    border-radius: 999px;
    background: linear-gradient(90deg, {t['green']} 0 34%, {t['yellow']} 34% 66%, {t['red']} 66% 100%);
}}

.heat-marker {{
    --marker: 50%;
    position: absolute;
    top: 50%;
    left: var(--marker);
    width: 20px;
    height: 20px;
    transform: translate(-50%, -50%);
    border-radius: 999px;
    background: {t['text']};
    border: 4px solid {t['surface']};
    box-shadow: 0 5px 18px rgba(0,0,0,.28);
    animation: markerIn .8s cubic-bezier(.2,.9,.2,1) both;
}}

.heat-scale {{
    display: flex;
    justify-content: space-between;
    color: {t['muted']};
    font-size: 10px;
    font-weight: 850;
    margin-top: 9px;
}}

.score-meta {{
    display: flex;
    justify-content: space-between;
    gap: 12px;
    margin-top: 18px;
    color: {t['muted']};
    font-size: 12px;
    font-weight: 750;
}}

.plan-grid {{
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 10px;
    margin-top: 24px;
}}

.plan-tile {{
    min-height: 106px;
    padding: 15px;
    border-radius: 17px;
    background: {t['surface']};
    border: 1px solid {t['border']};
}}

.plan-label {{
    color: {t['muted']};
    font-size: 10px;
    font-weight: 900;
    text-transform: uppercase;
    letter-spacing: .6px;
}}

.plan-value {{
    color: {t['text']};
    font-size: 18px;
    line-height: 1.25;
    font-weight: 900;
    margin-top: 7px;
}}

.plan-help {{
    color: {t['muted']};
    font-size: 11px;
    line-height: 1.35;
    margin-top: 6px;
}}

/* Sections */
.section-head {{ margin: 30px 0 13px; }}
.section-title {{
    color: {t['text']};
    font-size: 23px;
    font-weight: 920;
    letter-spacing: -.55px;
}}
.section-copy {{
    color: {t['muted']};
    font-size: 13px;
    line-height: 1.45;
    margin-top: 4px;
}}

.driver-card, .index-card, .summary-card {{
    height: 100%;
    background: linear-gradient(180deg, {t['surface']}, {t['surface2']});
    border: 1px solid {t['border']};
    border-radius: 18px;
    padding: 17px;
    animation: rise .5s cubic-bezier(.2,.8,.2,1) both;
}}

.driver-top {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
}}
.driver-name {{ color: {t['muted']}; font-size: 11px; font-weight: 900; text-transform: uppercase; letter-spacing: .55px; }}
.driver-reading {{ color: {t['text']}; font-size: 12px; font-weight: 900; }}
.driver-status {{ color: {t['text']}; font-size: 20px; font-weight: 920; margin-top: 9px; }}
.driver-copy {{ color: {t['muted']}; font-size: 12px; line-height: 1.45; margin-top: 7px; }}

.index-grid {{
    display: grid;
    grid-template-columns: repeat(5, minmax(0, 1fr));
    gap: 10px;
}}
.index-ticker {{ color: {t['text']}; font-size: 18px; font-weight: 950; }}
.index-name {{ color: {t['muted']}; font-size: 11px; margin-top: 2px; min-height: 31px; }}
.index-price {{ color: {t['text']}; font-size: 20px; font-weight: 900; margin-top: 11px; }}
.index-returns {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 5px; margin-top: 12px; }}
.index-period {{ color: {t['muted']}; font-size: 9px; font-weight: 800; text-transform: uppercase; }}
.index-return {{ color: {t['text']}; font-size: 11px; font-weight: 900; margin-top: 2px; }}
.positive {{ color: {t['green']} !important; }}
.negative {{ color: {t['red']} !important; }}

.performance-intro {{
    color: {t['muted']};
    font-size: 13px;
    line-height: 1.45;
    margin-bottom: 10px;
}}

.performance-stats {{
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 9px;
    margin: 10px 0 6px;
}}
.summary-label {{ color: {t['muted']}; font-size: 9px; font-weight: 900; text-transform: uppercase; letter-spacing: .55px; }}
.summary-value {{ color: {t['text']}; font-size: 15px; font-weight: 920; margin-top: 5px; }}

.source-note {{
    color: {t['muted']};
    font-size: 11px;
    line-height: 1.5;
    padding: 12px 0 0;
}}

.footer {{
    color: {t['muted']};
    font-size: 11px;
    line-height: 1.5;
    border-top: 1px solid {t['border']};
    padding-top: 17px;
    margin-top: 28px;
}}

@keyframes rise {{ from {{ opacity: 0; transform: translateY(10px); }} to {{ opacity: 1; transform: translateY(0); }} }}
@keyframes scoreIn {{ from {{ opacity: 0; transform: scale(.84); }} to {{ opacity: 1; transform: scale(1); }} }}
@keyframes markerIn {{ from {{ left: 0%; }} to {{ left: var(--marker); }} }}

@media (max-width: 960px) {{
    .app-header {{ align-items: flex-start; flex-direction: column; }}
    .freshness {{ justify-content: flex-start; }}
    .decision-grid {{ grid-template-columns: 1fr; }}
    .index-grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
}}

@media (max-width: 680px) {{
    .decision-card {{ padding: 21px; border-radius: 22px; }}
    .plan-grid, .performance-stats {{ grid-template-columns: 1fr; }}
    .index-grid {{ grid-template-columns: 1fr; }}
    .score-number {{ font-size: 59px; }}
}}

@media (prefers-reduced-motion: reduce) {{
    *, *::before, *::after {{
        animation-duration: .001ms !important;
        animation-iteration-count: 1 !important;
        transition-duration: .001ms !important;
    }}
}}
</style>
""",
        unsafe_allow_html=True,
    )


# ============================================================
# Constants
# ============================================================
CORE_INDEXES = {
    "US Large Cap": "SPY",
    "US Total Market": "VTI",
    "Nasdaq 100": "QQQ",
    "International ex-US": "VXUS",
    "US Aggregate Bonds": "BND",
}

MAG7 = {
    "Apple": "AAPL",
    "Microsoft": "MSFT",
    "Alphabet": "GOOGL",
    "Amazon": "AMZN",
    "Nvidia": "NVDA",
    "Meta": "META",
    "Tesla": "TSLA",
}

SP500_SECTORS = {
    "Communication Services": "XLC",
    "Consumer Discretionary": "XLY",
    "Consumer Staples": "XLP",
    "Energy": "XLE",
    "Financials": "XLF",
    "Health Care": "XLV",
    "Industrials": "XLI",
    "Materials": "XLB",
    "Real Estate": "XLRE",
    "Technology": "XLK",
    "Utilities": "XLU",
}

RETURN_PERIODS = ("1D", "1M", "3M", "6M", "YTD", "1Y")
ALL_MARKET_TICKERS = tuple(
    dict.fromkeys(
        ["^GSPC", "^VIX"]
        + list(CORE_INDEXES.values())
        + list(MAG7.values())
        + list(SP500_SECTORS.values())
    )
)


# ============================================================
# General helpers
# ============================================================
def safe_float(value):
    try:
        if value is None:
            return None
        value = float(value)
        if math.isnan(value) or math.isinf(value):
            return None
        return value
    except (TypeError, ValueError):
        return None


def clamp(value, low=0.0, high=100.0):
    value = safe_float(value)
    if value is None:
        return None
    return max(low, min(high, value))


def fmt_number(value, digits=2, suffix=""):
    value = safe_float(value)
    if value is None:
        return "N/A"
    return f"{value:,.{digits}f}{suffix}"


def fmt_return(value):
    value = safe_float(value)
    return "N/A" if value is None else f"{value:+.2f}%"


def return_class(value):
    value = safe_float(value)
    if value is None or value == 0:
        return ""
    return "positive" if value > 0 else "negative"


def score_from_range(value, points):
    value = safe_float(value)
    if value is None:
        return None
    points = sorted(points, key=lambda pair: pair[0])
    if value <= points[0][0]:
        return float(points[0][1])
    if value >= points[-1][0]:
        return float(points[-1][1])
    for (x1, y1), (x2, y2) in zip(points, points[1:]):
        if x1 <= value <= x2:
            portion = (value - x1) / (x2 - x1)
            return y1 + portion * (y2 - y1)
    return None


def period_start_date(latest_date, period):
    latest_date = pd.Timestamp(latest_date).normalize()
    if period == "1M":
        return latest_date - pd.DateOffset(months=1)
    if period == "3M":
        return latest_date - pd.DateOffset(months=3)
    if period == "6M":
        return latest_date - pd.DateOffset(months=6)
    if period == "YTD":
        return pd.Timestamp(year=latest_date.year, month=1, day=1)
    if period == "1Y":
        return latest_date - pd.DateOffset(years=1)
    return latest_date


def calculate_period_return(series, period):
    """Adjusted-close return ending at the latest available observation."""
    series = pd.to_numeric(series, errors="coerce").dropna().sort_index()
    if len(series) < 2:
        return None

    latest_value = safe_float(series.iloc[-1])
    if latest_value is None:
        return None

    if period == "1D":
        base_value = safe_float(series.iloc[-2])
    else:
        start_date = period_start_date(series.index[-1], period)
        prior = series.loc[series.index <= start_date]
        if not prior.empty:
            base_value = safe_float(prior.iloc[-1])
        else:
            later = series.loc[series.index >= start_date]
            base_value = safe_float(later.iloc[0]) if not later.empty else None

    if base_value in (None, 0):
        return None
    return ((latest_value / base_value) - 1.0) * 100.0


# ============================================================
# Data acquisition
# ============================================================
def _clean_price_series(series):
    """Normalize one Yahoo price series into a timezone-naive daily series."""
    if series is None:
        return pd.Series(dtype="float64")
    clean = pd.to_numeric(series, errors="coerce").dropna().copy()
    if clean.empty:
        return clean
    clean.index = pd.to_datetime(clean.index, errors="coerce")
    clean = clean[~clean.index.isna()]
    if getattr(clean.index, "tz", None) is not None:
        clean.index = clean.index.tz_localize(None)
    clean = clean[~clean.index.duplicated(keep="last")].sort_index()
    return clean


def _extract_close_frame(raw, requested_tickers):
    """Handle the different column layouts returned by yfinance versions."""
    if raw is None or raw.empty:
        return pd.DataFrame()

    requested = list(requested_tickers)
    close = None

    if isinstance(raw.columns, pd.MultiIndex):
        for level in range(raw.columns.nlevels):
            values = raw.columns.get_level_values(level).astype(str)
            if "Close" in set(values):
                close = raw.xs("Close", axis=1, level=level, drop_level=True).copy()
                break
        if close is None:
            return pd.DataFrame()
    else:
        if "Close" not in raw.columns:
            return pd.DataFrame()
        close = raw[["Close"]].copy()
        if len(requested) == 1:
            close.columns = [requested[0]]

    if isinstance(close, pd.Series):
        name = requested[0] if requested else str(close.name)
        close = close.to_frame(name=name)

    if isinstance(close.columns, pd.MultiIndex):
        flattened = []
        for column in close.columns:
            parts = [str(part) for part in column]
            match = next((ticker for ticker in requested if ticker in parts), parts[-1])
            flattened.append(match)
        close.columns = flattened
    else:
        close.columns = [str(column) for column in close.columns]

    # yfinance can occasionally reverse or alter column order; keep only requested names.
    aliases = {ticker.upper(): ticker for ticker in requested}
    renamed = {}
    for column in close.columns:
        normalized = str(column).upper()
        if normalized in aliases:
            renamed[column] = aliases[normalized]
    close = close.rename(columns=renamed)
    close = close.loc[:, [column for column in close.columns if column in requested]]

    close.index = pd.to_datetime(close.index, errors="coerce")
    close = close[~close.index.isna()]
    if getattr(close.index, "tz", None) is not None:
        close.index = close.index.tz_localize(None)
    close = close.loc[:, ~close.columns.duplicated(keep="last")].sort_index()
    return close.dropna(how="all")


def _download_bulk_prices(tickers, period="2y"):
    """Minimal-argument bulk request for compatibility across yfinance releases."""
    tickers = list(dict.fromkeys(tickers))
    if not tickers:
        return pd.DataFrame()
    try:
        raw = yf.download(
            tickers=" ".join(tickers),
            period=period,
            interval="1d",
            auto_adjust=True,
            progress=False,
            threads=False,
        )
        return _extract_close_frame(raw, tickers)
    except Exception:
        return pd.DataFrame()


def _download_single_price(ticker, period="2y"):
    """Independent fallback so one Yahoo failure cannot blank the whole app."""
    try:
        history = yf.Ticker(ticker).history(
            period=period,
            interval="1d",
            auto_adjust=True,
            actions=False,
        )
        if history is None or history.empty or "Close" not in history.columns:
            return pd.Series(dtype="float64", name=ticker)
        series = _clean_price_series(history["Close"])
        series.name = ticker
        return series
    except Exception:
        return pd.Series(dtype="float64", name=ticker)


@st.cache_data(ttl=900, show_spinner=False)
def fetch_market_prices(tickers):
    """
    Fetch adjusted daily closes with graceful fallbacks.

    The old implementation used one all-or-nothing Yahoo request. Any exception —
    including a version-specific keyword or one failed symbol — returned an empty
    frame and stopped the app. Critical index series are now fetched independently,
    while ordinary stocks and ETFs use a smaller bulk request.
    """
    requested = list(dict.fromkeys(tickers))
    frames = []

    # These series power the score, so do not make them depend on a 20+ ticker batch.
    for ticker in ("^GSPC", "SPY", "^VIX"):
        if ticker in requested:
            series = _download_single_price(ticker)
            if not series.empty:
                frames.append(series.to_frame())

    # Stocks and ETFs are more reliable in a batch than when mixed with index symbols.
    ordinary = [ticker for ticker in requested if ticker not in {"^GSPC", "^VIX", "SPY"}]
    bulk = _download_bulk_prices(ordinary)
    if not bulk.empty:
        frames.append(bulk)

    # Fill any missing ordinary symbols individually. Partial data is better than a blank page.
    loaded = set()
    for frame in frames:
        loaded.update(frame.columns)
    for ticker in ordinary:
        if ticker not in loaded:
            series = _download_single_price(ticker)
            if not series.empty:
                frames.append(series.to_frame())

    if not frames:
        return pd.DataFrame()

    prices = pd.concat(frames, axis=1).sort_index()
    prices = prices.loc[:, ~prices.columns.duplicated(keep="last")]
    prices = prices[[ticker for ticker in requested if ticker in prices.columns]]
    return prices.dropna(how="all")


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_cboe_equity_put_call():
    """Latest Cboe equity put/call ratio from Cboe's official daily statistics page."""
    url = "https://www.cboe.com/markets/us/options/market-statistics/daily/"
    try:
        response = requests.get(url, timeout=12, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()
        plain = html_lib.unescape(re.sub(r"<[^>]+>", " ", response.text))
        plain = re.sub(r"\s+", " ", plain)
        match = re.search(r"EQUITY PUT/CALL RATIO\s+([0-9]+(?:\.[0-9]+)?)", plain, re.I)
        return safe_float(match.group(1)) if match else None
    except Exception:
        return None


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_treasury_curve():
    """Latest official U.S. Treasury par yield curve. Advanced context only."""
    year = NOW_PT.year
    urls = [
        (
            "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/"
            f"daily-treasury-rates.csv/{year}/all?type=daily_treasury_yield_curve"
            f"&field_tdr_date_value={year}&page&_format=csv"
        ),
        (
            "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/"
            "daily-treasury-rates.csv/all/all?_format=csv&page=&type=daily_treasury_yield_curve"
        ),
    ]
    for url in urls:
        try:
            response = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
            response.raise_for_status()
            frame = pd.read_csv(StringIO(response.text))
            if frame.empty or "Date" not in frame.columns:
                continue
            frame["Date"] = pd.to_datetime(frame["Date"], errors="coerce")
            frame = frame.dropna(subset=["Date"]).sort_values("Date")
            if not frame.empty:
                return frame.iloc[-1].to_dict()
        except Exception:
            continue
    return {}


# ============================================================
# Market model
# ============================================================
def build_technical_snapshot(prices):
    """Build the score from the S&P 500 index, falling back to SPY when needed."""
    if prices.empty:
        return None

    source_ticker = None
    source_label = None
    for ticker, label in (("^GSPC", "S&P 500 Index"), ("SPY", "SPY ETF proxy")):
        if ticker not in prices.columns:
            continue
        candidate = pd.to_numeric(prices[ticker], errors="coerce").dropna()
        if len(candidate) >= 210:
            source_ticker = ticker
            source_label = label
            spx = candidate
            break

    if source_ticker is None:
        return None

    rsi = RSIIndicator(spx, window=14).rsi()
    sma200 = SMAIndicator(spx, window=200).sma_indicator()
    close = safe_float(spx.iloc[-1])
    latest_sma = safe_float(sma200.iloc[-1])

    vix = None
    if "^VIX" in prices.columns:
        vix_series = pd.to_numeric(prices["^VIX"], errors="coerce").dropna()
        vix = safe_float(vix_series.iloc[-1]) if not vix_series.empty else None

    return {
        "close": close,
        "rsi": safe_float(rsi.iloc[-1]),
        "sma200": latest_sma,
        "distance_200d": ((close / latest_sma) - 1) * 100 if close and latest_sma else None,
        "vix": vix,
        "latest_date": pd.Timestamp(spx.index[-1]),
        "history": pd.DataFrame({"Close": spx, "SMA 200": sma200}).reset_index(names="Date"),
        "source_ticker": source_ticker,
        "source_label": source_label,
    }


def signal_description(name, reading):
    value = safe_float(reading)
    if value is None:
        return "Unavailable", "Data is missing; a neutral value is used and confidence is reduced."

    if name == "VIX":
        if value < 14:
            return "Very calm", "Low volatility can signal complacency, so large extra buys deserve restraint."
        if value < 20:
            return "Calm", "Volatility is normal; there is no meaningful fear discount."
        if value < 28:
            return "Elevated fear", "Some fear is present, improving the setup for incremental buying."
        return "High fear", "Volatility is elevated, which generally makes chasing less of a concern."

    if name == "S&P 500 RSI":
        if value < 30:
            return "Oversold", "The index is stretched lower in the short term."
        if value < 40:
            return "Near oversold", "Short-term conditions are becoming more favorable."
        if value <= 60:
            return "Neutral", "The index is not meaningfully stretched in either direction."
        if value <= 70:
            return "Elevated", "Momentum is strong, but the index is approaching an overbought zone."
        return "Overbought", "Short-term momentum is stretched; avoid chasing a large extra buy."

    if name == "Distance from 200D":
        if value < -8:
            return "Well below trend", "The market is far below its long-term trend, improving valuation discipline."
        if value < -2:
            return "Below trend", "The market is modestly below its long-term trend."
        if value <= 8:
            return "Near trend", "The market is within a normal range around its long-term trend."
        return "Extended", "The market is stretched above its 200-day average."

    if name == "Cboe equity P/C":
        if value < 0.65:
            return "Call-heavy", "Equity options activity is leaning optimistic or speculative."
        if value <= 1.10:
            return "Balanced", "Equity options positioning is within a broadly normal range."
        return "Put-heavy", "More defensive option activity suggests elevated investor fear."

    return "Neutral", "No interpretation available."


def build_heat_score(vix, rsi, distance_200d, put_call):
    """
    Stable rule-based heat index.

    Missing values receive a neutral 50 rather than silently reweighting the model,
    so the meaning of the 0-100 scale stays consistent from day to day.
    """
    definitions = [
        {
            "Signal": "VIX",
            "Reading": vix,
            "Weight": 0.30,
            "SignalScore": score_from_range(vix, [(12, 88), (18, 62), (25, 36), (35, 15), (50, 5)]),
        },
        {
            "Signal": "S&P 500 RSI",
            "Reading": rsi,
            "Weight": 0.25,
            "SignalScore": score_from_range(rsi, [(25, 8), (35, 24), (50, 50), (65, 72), (75, 90), (85, 100)]),
        },
        {
            "Signal": "Distance from 200D",
            "Reading": distance_200d,
            "Weight": 0.25,
            "SignalScore": score_from_range(distance_200d, [(-20, 7), (-10, 20), (0, 48), (8, 68), (15, 84), (25, 97)]),
        },
        {
            "Signal": "Cboe equity P/C",
            "Reading": put_call,
            "Weight": 0.20,
            "SignalScore": score_from_range(put_call, [(0.50, 94), (0.65, 82), (0.85, 58), (1.10, 34), (1.40, 12)]),
        },
    ]

    rows = []
    for item in definitions:
        available = item["SignalScore"] is not None
        used_score = item["SignalScore"] if available else 50.0
        status, explanation = signal_description(item["Signal"], item["Reading"])
        rows.append(
            {
                **item,
                "Available": available,
                "UsedScore": used_score,
                "WeightedImpact": (used_score - 50.0) * item["Weight"],
                "Status": status,
                "Explanation": explanation,
            }
        )

    frame = pd.DataFrame(rows)
    score = int(round((frame["UsedScore"] * frame["Weight"]).sum()))
    score = int(clamp(score, 0, 100))
    return score, frame


def recommendation(score):
    """One internally consistent buy-sizing policy for extra cash."""
    if score is None:
        return {
            "action": "BUY NORMALLY",
            "temperature": "Data incomplete",
            "extra_buy": "100% of your normal extra-buy amount",
            "hold": "No tactical change",
            "copy": "Use your normal plan until the data refreshes.",
            "avoid": "Guessing from incomplete data",
        }
    if score <= 20:
        return {
            "action": "BUY MORE",
            "temperature": "Deep fear",
            "extra_buy": "150%–200% of your normal extra-buy amount",
            "hold": "Keep some cash for another leg down",
            "copy": "Fear is elevated. A larger incremental buy is reasonable without trying to call the bottom.",
            "avoid": "Going all-in at once",
        }
    if score <= 35:
        return {
            "action": "BUY A LITTLE MORE",
            "temperature": "Fear",
            "extra_buy": "125%–150% of your normal extra-buy amount",
            "hold": "Reserve the remainder for future buys",
            "copy": "Conditions are more favorable than normal, but discipline still matters.",
            "avoid": "Trying to pick the exact bottom",
        }
    if score <= 65:
        return {
            "action": "BUY NORMALLY",
            "temperature": "Balanced",
            "extra_buy": "100% of your normal extra-buy amount",
            "hold": "Follow your existing schedule",
            "copy": "The market is not meaningfully fearful or stretched. Stay on plan.",
            "avoid": "Inventing a tactical trade",
        }
    if score <= 80:
        return {
            "action": "BUY SMALLER",
            "temperature": "Warm",
            "extra_buy": "25%–50% of your normal extra-buy amount",
            "hold": "Stage the remainder into later buys",
            "copy": "The market is warm. Use a smaller extra-cash buy and keep your recurring plan unchanged.",
            "avoid": "Chasing after a strong run",
        }
    return {
        "action": "DON’T CHASE",
        "temperature": "Hot",
        "extra_buy": "0%–25% of your normal extra-buy amount",
        "hold": "Wait for scheduled buys or a pullback",
        "copy": "The market is stretched. Keep automatic investing active, but do not force a large extra buy.",
        "avoid": "FOMO-driven lump sums",
    }


def confidence_summary(signal_frame):
    available = signal_frame[signal_frame["Available"]]
    count = len(available)
    if count < 3:
        return "Low", count, "Too many core inputs are unavailable."

    dispersion = float(available["UsedScore"].std(ddof=0)) if count > 1 else 0.0
    if count == 4 and dispersion <= 17:
        return "High", count, "All core inputs are available and broadly agree."
    if dispersion <= 28:
        return "Medium", count, "Most core inputs point in a similar direction."
    return "Low", count, "Core inputs disagree, so the buy-sizing signal is less decisive."


# ============================================================
# Performance helpers
# ============================================================
def build_return_table(prices, assets):
    rows = []
    for name, ticker in assets.items():
        if ticker not in prices.columns:
            continue
        row = {"Name": name, "Ticker": ticker}
        for period in RETURN_PERIODS:
            row[period] = calculate_period_return(prices[ticker], period)
        rows.append(row)
    return pd.DataFrame(rows)


def performance_summary(return_table, period):
    if return_table.empty or period not in return_table.columns:
        return None
    usable = return_table[["Name", "Ticker", period]].dropna()
    if usable.empty:
        return None
    leader = usable.loc[usable[period].idxmax()]
    laggard = usable.loc[usable[period].idxmin()]
    positive = int((usable[period] > 0).sum())
    return {
        "leader": f"{leader['Ticker']} {leader[period]:+.2f}%",
        "laggard": f"{laggard['Ticker']} {laggard[period]:+.2f}%",
        "breadth": f"{positive} of {len(usable)} positive",
    }


def make_return_chart(return_table, period, title, theme, benchmark_return=None):
    if return_table.empty or period not in return_table.columns:
        return None
    chart = return_table[["Name", "Ticker", period]].dropna().copy()
    if chart.empty:
        return None

    chart["Label"] = chart["Name"] + " · " + chart["Ticker"]
    chart = chart.sort_values(period, ascending=True)
    colors = [theme["green"] if value >= 0 else theme["red"] for value in chart[period]]

    figure = go.Figure(
        go.Bar(
            x=chart[period],
            y=chart["Label"],
            orientation="h",
            marker={"color": colors, "line": {"width": 0}},
            text=[f"{value:+.2f}%" for value in chart[period]],
            textposition="outside",
            cliponaxis=False,
            hovertemplate="<b>%{y}</b><br>Total return: %{x:+.2f}%<extra></extra>",
        )
    )

    if benchmark_return is not None:
        figure.add_vline(
            x=benchmark_return,
            line_width=1.4,
            line_dash="dot",
            line_color=theme["muted"],
            annotation_text=f"SPY {benchmark_return:+.2f}%",
            annotation_position="top",
            annotation_font_color=theme["muted"],
        )

    figure.add_vline(x=0, line_width=1, line_color=theme["border2"])
    figure.update_layout(
        title={"text": title, "x": 0.01, "xanchor": "left", "font": {"size": 16}},
        height=max(370, 48 * len(chart) + 100),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": theme["text"], "family": "Inter, sans-serif"},
        margin={"l": 10, "r": 76, "t": 55, "b": 20},
        showlegend=False,
        bargap=0.34,
        hoverlabel={"bgcolor": theme["surface"], "font_color": theme["text"]},
        xaxis={
            "title": None,
            "ticksuffix": "%",
            "gridcolor": theme["border"],
            "zeroline": False,
        },
        yaxis={"title": None, "automargin": True},
    )
    return figure


def render_performance_view(title, copy, assets, prices, key, theme, show_benchmark=True):
    st.markdown(f'<div class="performance-intro"><b>{title}</b> — {copy}</div>', unsafe_allow_html=True)
    period = st.radio(
        f"{title} return period",
        RETURN_PERIODS,
        horizontal=True,
        key=key,
        label_visibility="collapsed",
    )
    table = build_return_table(prices, assets)
    benchmark = None
    if show_benchmark and "SPY" in prices.columns:
        benchmark = calculate_period_return(prices["SPY"], period)

    summary = performance_summary(table, period)
    if summary:
        st.markdown(
            f"""
<div class="performance-stats">
  <div class="summary-card"><div class="summary-label">Leader</div><div class="summary-value">{summary['leader']}</div></div>
  <div class="summary-card"><div class="summary-label">Laggard</div><div class="summary-value">{summary['laggard']}</div></div>
  <div class="summary-card"><div class="summary-label">Breadth</div><div class="summary-value">{summary['breadth']}</div></div>
</div>
""",
            unsafe_allow_html=True,
        )

    figure = make_return_chart(table, period, f"{period} adjusted total return", theme, benchmark)
    if figure is None:
        st.warning("Performance data is unavailable right now.")
        return
    st.plotly_chart(figure, use_container_width=True, config={"displayModeBar": False})

    with st.expander("View all return periods"):
        display = table.copy()
        for item in RETURN_PERIODS:
            display[item] = display[item].apply(fmt_return)
        st.dataframe(display, use_container_width=True, hide_index=True)


# ============================================================
# UI helpers
# ============================================================
def section_header(title, copy):
    st.markdown(
        f'<div class="section-head"><div class="section-title">{title}</div><div class="section-copy">{copy}</div></div>',
        unsafe_allow_html=True,
    )


def render_core_index_cards(prices):
    cards = []
    for name, ticker in CORE_INDEXES.items():
        if ticker not in prices.columns:
            continue
        series = pd.to_numeric(prices[ticker], errors="coerce").dropna()
        if series.empty:
            continue
        price = safe_float(series.iloc[-1])
        one_day = calculate_period_return(series, "1D")
        ytd = calculate_period_return(series, "YTD")
        one_year = calculate_period_return(series, "1Y")
        cards.append(
            f"""
<div class="index-card">
  <div class="index-ticker">{ticker}</div>
  <div class="index-name">{name}</div>
  <div class="index-price">${price:,.2f}</div>
  <div class="index-returns">
    <div><div class="index-period">1D</div><div class="index-return {return_class(one_day)}">{fmt_return(one_day)}</div></div>
    <div><div class="index-period">YTD</div><div class="index-return {return_class(ytd)}">{fmt_return(ytd)}</div></div>
    <div><div class="index-period">1Y</div><div class="index-return {return_class(one_year)}">{fmt_return(one_year)}</div></div>
  </div>
</div>
"""
        )
    st.markdown(f'<div class="index-grid">{"".join(cards)}</div>', unsafe_allow_html=True)


def reading_text(signal_name, reading):
    if reading is None:
        return "N/A"
    if signal_name == "Distance from 200D":
        return fmt_number(reading, 2, "%")
    return fmt_number(reading, 2)


# ============================================================
# Controls and data load
# ============================================================
theme = current_theme()
inject_css(theme)

control_spacer, control_mode, control_refresh = st.columns([0.72, 0.15, 0.13])
with control_mode:
    st.toggle("Dark mode", key="dark_mode")
with control_refresh:
    if st.button("Refresh", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# Toggle changes cause a rerun, so one theme injection is sufficient per render.
theme = current_theme()

with st.spinner("Loading the latest available market data..."):
    market_prices = fetch_market_prices(ALL_MARKET_TICKERS)
    put_call = fetch_cboe_equity_put_call()
    treasury = fetch_treasury_curve()

technical = build_technical_snapshot(market_prices)
if technical is None:
    loaded_symbols = [ticker for ticker in ALL_MARKET_TICKERS if ticker in market_prices.columns]
    st.markdown(
        """
<div class="app-header">
  <div>
    <div class="app-title">📈 Should I Buy Today?</div>
    <div class="app-subtitle">Market data could not be loaded reliably, so the app is withholding a buy-sizing signal.</div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )
    st.error("The S&P 500 index and SPY fallback are both unavailable. Yahoo may be rate-limiting this deployment.")
    if loaded_symbols:
        st.caption(f"Other symbols loaded: {', '.join(loaded_symbols)}")
    st.info("Wait a minute and press Refresh. The app now retries critical symbols independently, so a temporary failure should no longer blank the full dashboard on the next successful request.")
    st.stop()

score, signal_frame = build_heat_score(
    technical["vix"],
    technical["rsi"],
    technical["distance_200d"],
    put_call,
)
plan = recommendation(score)
confidence, available_count, confidence_reason = confidence_summary(signal_frame)
latest_market_date = technical["latest_date"]
market_age_days = max(0, (NOW_PT.date() - latest_market_date.date()).days)

market_date_label = latest_market_date.strftime("%b %d, %Y")
refresh_label = NOW_PT.strftime("%b %d · %I:%M %p PT")


# ============================================================
# Header
# ============================================================
st.markdown(
    f"""
<div class="app-header">
  <div>
    <div class="app-title">📈 Should I Buy Today?</div>
    <div class="app-subtitle">A calm buy-sizing guide for long-term index investors — not a market-timing forecast.</div>
  </div>
  <div class="freshness">
    <span class="meta-pill"><span class="status-dot"></span>Prices through {market_date_label}</span>
    <span class="meta-pill">Refreshed {refresh_label}</span>
    <span class="meta-pill">Core data {available_count}/4</span>
    <span class="meta-pill">Signal source: {technical['source_label']}</span>
  </div>
</div>
""",
    unsafe_allow_html=True,
)

if market_age_days > 4:
    st.warning(f"Market prices are {market_age_days} calendar days old. Treat the signal as stale until data refreshes.")


# ============================================================
# Primary decision
# ============================================================
marker = clamp(score, 0, 100) if score is not None else 50
st.markdown(
    f"""
<div class="decision-card">
  <div class="decision-grid">
    <div>
      <div class="eyebrow">Today’s extra-cash plan</div>
      <div class="action-title">{plan['action']}</div>
      <div class="action-copy">{plan['copy']}</div>
      <div class="guardrail">✓ Automatic DCA stays unchanged. This signal only sizes optional extra cash.</div>
    </div>
    <div class="score-panel">
      <div class="score-row">
        <div>
          <div class="eyebrow">Market temperature</div>
          <div class="temperature">{plan['temperature']}</div>
        </div>
        <div class="score-number">{score}</div>
      </div>
      <div class="heat-meter"><div class="heat-marker" style="--marker:{marker}%;"></div></div>
      <div class="heat-scale"><span>More attractive</span><span>Normal</span><span>More stretched</span></div>
      <div class="score-meta"><span>Confidence: {confidence}</span><span>0–100 heat index</span></div>
    </div>
  </div>
  <div class="plan-grid">
    <div class="plan-tile">
      <div class="plan-label">Optional extra buy</div>
      <div class="plan-value">{plan['extra_buy']}</div>
      <div class="plan-help">100% means your usual discretionary extra-buy amount.</div>
    </div>
    <div class="plan-tile">
      <div class="plan-label">Remaining cash</div>
      <div class="plan-value">{plan['hold']}</div>
      <div class="plan-help">Stage capital instead of trying to predict one perfect day.</div>
    </div>
    <div class="plan-tile">
      <div class="plan-label">Avoid</div>
      <div class="plan-value">{plan['avoid']}</div>
      <div class="plan-help">No sell signal. No change to long-term allocation.</div>
    </div>
  </div>
</div>
""",
    unsafe_allow_html=True,
)


# ============================================================
# Why this result
# ============================================================
section_header(
    "What is driving today’s result",
    f"The three inputs with the largest weighted effect on the heat score. Confidence is {confidence.lower()}: {confidence_reason}",
)

top_drivers = signal_frame.reindex(signal_frame["WeightedImpact"].abs().sort_values(ascending=False).index).head(3)
columns = st.columns(3)
for column, (_, row) in zip(columns, top_drivers.iterrows()):
    direction = "Pushes hotter" if row["WeightedImpact"] > 1 else "Improves the setup" if row["WeightedImpact"] < -1 else "Near neutral"
    with column:
        st.markdown(
            f"""
<div class="driver-card">
  <div class="driver-top">
    <div class="driver-name">{row['Signal']}</div>
    <div class="driver-reading">{reading_text(row['Signal'], row['Reading'])}</div>
  </div>
  <div class="driver-status">{row['Status']}</div>
  <div class="driver-copy"><b>{direction}.</b> {row['Explanation']}</div>
</div>
""",
            unsafe_allow_html=True,
        )


# ============================================================
# Core index snapshot
# ============================================================
section_header(
    "Core index snapshot",
    "A fast read on the broad building blocks most long-term investors actually own. Returns use adjusted prices.",
)
render_core_index_cards(market_prices)


# ============================================================
# Performance
# ============================================================
section_header(
    "Performance",
    "Explore broad indexes first, then market leadership. One chart is shown at a time to keep the page readable.",
)
index_tab, mag7_tab, sector_tab = st.tabs(["Core Indexes", "Magnificent 7", "S&P 500 Sectors"])

with index_tab:
    render_performance_view(
        "Core indexes",
        "Compare US stocks, international stocks and bonds across the selected period.",
        CORE_INDEXES,
        market_prices,
        "core_period",
        theme,
        show_benchmark=False,
    )

with mag7_tab:
    render_performance_view(
        "Magnificent 7",
        "See whether mega-cap leadership is broad or concentrated. The dotted line is SPY total return.",
        MAG7,
        market_prices,
        "mag7_period",
        theme,
        show_benchmark=True,
    )

with sector_tab:
    render_performance_view(
        "S&P 500 sector ETFs",
        "Investable Select Sector SPDR ETF total returns. These are ETF proxies, not the exact underlying sector-index returns.",
        SP500_SECTORS,
        market_prices,
        "sector_period",
        theme,
        show_benchmark=True,
    )


# ============================================================
# Methodology and advanced detail
# ============================================================
section_header(
    "Methodology & deeper detail",
    "Everything needed to audit the result is available here, without crowding the main experience.",
)

with st.expander("Open methodology, all signals and advanced charts"):
    st.markdown(
        """
**How to read the score**

The Market Heat Score is a transparent rule-based index, not a forecast of tomorrow’s return. It uses four core inputs: VIX (30%), broad-market RSI (25%), distance from the 200-day average (25%), and the Cboe equity put/call ratio (20%). The S&P 500 index is preferred; SPY is used only as a transparent fallback when the index feed is unavailable. Higher means more stretched; lower means more fearful.

When a core input is unavailable, the model uses a neutral value of 50 and lowers confidence. It does **not** silently redistribute the missing weight, which keeps the score comparable across days.
"""
    )

    signal_display = signal_frame[
        ["Signal", "Reading", "Status", "Weight", "UsedScore", "Available", "Explanation"]
    ].copy()
    signal_display["Reading"] = signal_display.apply(
        lambda row: reading_text(row["Signal"], row["Reading"]), axis=1
    )
    signal_display["Weight"] = signal_display["Weight"].apply(lambda value: f"{value:.0%}")
    signal_display["UsedScore"] = signal_display["UsedScore"].round(1)
    signal_display["Available"] = signal_display["Available"].map({True: "Yes", False: "No — neutral used"})
    st.dataframe(signal_display, use_container_width=True, hide_index=True)

    trend_tab, treasury_tab, sources_tab = st.tabs(["S&P 500 Trend", "Treasury Curve", "Data Sources"])

    with trend_tab:
        history = technical["history"]
        figure = go.Figure()
        figure.add_trace(go.Scatter(x=history["Date"], y=history["Close"], mode="lines", name=technical["source_label"]))
        figure.add_trace(go.Scatter(x=history["Date"], y=history["SMA 200"], mode="lines", name="200-day average"))
        figure.update_layout(
            height=400,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font={"color": theme["text"]},
            margin={"l": 10, "r": 10, "t": 20, "b": 10},
            legend={"orientation": "h"},
            hovermode="x unified",
            xaxis={"gridcolor": theme["border"]},
            yaxis={"gridcolor": theme["border"]},
        )
        st.plotly_chart(figure, use_container_width=True, config={"displayModeBar": False})

    with treasury_tab:
        maturity_columns = ["1 Mo", "2 Mo", "3 Mo", "4 Mo", "6 Mo", "1 Yr", "2 Yr", "3 Yr", "5 Yr", "7 Yr", "10 Yr", "20 Yr", "30 Yr"]
        curve_rows = [
            {"Maturity": column, "Yield (%)": safe_float(treasury.get(column))}
            for column in maturity_columns
            if safe_float(treasury.get(column)) is not None
        ]
        if curve_rows:
            curve_frame = pd.DataFrame(curve_rows)
            curve_figure = go.Figure(
                go.Scatter(
                    x=curve_frame["Maturity"],
                    y=curve_frame["Yield (%)"],
                    mode="lines+markers",
                    name="Treasury yield",
                )
            )
            curve_figure.update_layout(
                height=350,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font={"color": theme["text"]},
                margin={"l": 10, "r": 10, "t": 20, "b": 10},
                xaxis={"gridcolor": theme["border"]},
                yaxis={"ticksuffix": "%", "gridcolor": theme["border"]},
            )
            st.plotly_chart(curve_figure, use_container_width=True, config={"displayModeBar": False})
            if treasury.get("Date") is not None:
                st.caption(f"Official U.S. Treasury curve date: {pd.Timestamp(treasury['Date']).strftime('%b %d, %Y')}")
        else:
            st.info("Official Treasury curve data is unavailable right now. It does not affect the heat score.")

    with sources_tab:
        st.markdown(
            """
- **Prices and adjusted returns:** Yahoo Finance through the open-source `yfinance` package. Critical index series are fetched independently, and SPY is a disclosed fallback for the technical signal. Data may be delayed and is intended here for educational use.
- **Equity put/call ratio:** Cboe Daily Market Statistics.
- **Treasury curve:** U.S. Department of the Treasury daily par yield curve.
- **Sector view:** the 11 Select Sector SPDR ETFs are investable proxies for S&P 500 sectors. Their adjusted returns are not identical to raw sector-index returns.

The app deliberately excludes headline sentiment and Google search trends from the core score. Those inputs are noisy, can fail unpredictably, and made the old score less stable from one refresh to the next.
"""
        )

st.markdown(
    """
<div class="footer">
Educational only — not financial advice. Designed for long-term index investors deciding how to size optional extra cash. It does not recommend selling, changing an automatic DCA, or predicting the next market move.
</div>
""",
    unsafe_allow_html=True,
)
