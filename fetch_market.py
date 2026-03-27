#!/usr/bin/env python3
"""
fetch_market.py — Fetches real market data from multiple APIs and writes a
YAML-frontmatter markdown file to Analysis/Market/YYYY-MM-DD.md.
"""

import argparse
import logging
import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import requests

# ---------------------------------------------------------------------------
# API keys — prefer environment variables, fall back to hardcoded values
# ---------------------------------------------------------------------------
FINNHUB_KEY = os.environ.get("FINNHUB_KEY", "d737hnpr01qjjol21cn0d737hnpr01qjjol21cng")
FMP_KEY = os.environ.get("FMP_KEY", "w0Q2UP0Zzzb1A8uLRVPfBmBOlsN4gKe8")

REPO_ROOT = Path(__file__).parent
OUTPUT_DIR = REPO_ROOT / "Analysis" / "Market"

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def safe_get(url: str, headers: dict = None, timeout: int = 10):
    """GET url; return parsed JSON or None on any error."""
    try:
        resp = requests.get(url, headers=headers, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        log.warning("Request failed for %s — %s", url, exc)
        return None


def round2(val):
    """Round to 2 decimal places, or return None."""
    if val is None:
        return None
    try:
        return round(float(val), 2)
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Live data fetchers
# ---------------------------------------------------------------------------

def fetch_finnhub_price(symbol: str) -> float | None:
    data = safe_get(
        f"https://finnhub.io/api/v1/quote?symbol={symbol}&token={FINNHUB_KEY}"
    )
    if data is None:
        return None
    price = data.get("c")
    if not price:
        log.warning("Finnhub: no price for %s (response: %s)", symbol, data)
        return None
    return round2(price)


def fetch_ten_yr_yield() -> float | None:
    data = safe_get(
        f"https://financialmodelingprep.com/stable/treasury-rates?apikey={FMP_KEY}"
    )
    if not data or not isinstance(data, list):
        return None
    try:
        return round2(data[0].get("year10"))
    except (IndexError, KeyError):
        log.warning("FMP: could not parse year10 from %s", data)
        return None


def fetch_yahoo_price(symbol: str) -> float | None:
    """symbol should be URL-encoded already (e.g. %5ENSEI for ^NSEI)."""
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=5d"
    headers = {"User-Agent": "Mozilla/5.0"}
    data = safe_get(url, headers=headers)
    if data is None:
        return None
    try:
        price = data["chart"]["result"][0]["meta"]["regularMarketPrice"]
        return round2(price)
    except (KeyError, IndexError, TypeError):
        log.warning("Yahoo: could not parse price for %s", symbol)
        return None


def fetch_usd_inr() -> float | None:
    data = safe_get("https://open.er-api.com/v6/latest/USD")
    if data is None:
        return None
    try:
        return round2(data["rates"]["INR"])
    except (KeyError, TypeError):
        log.warning("ExchangeRate-API: could not parse INR rate")
        return None


def fetch_crypto_prices() -> tuple[float | None, float | None]:
    data = safe_get(
        "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum&vs_currencies=usd"
    )
    if data is None:
        return None, None
    btc = round2(data.get("bitcoin", {}).get("usd"))
    eth = round2(data.get("ethereum", {}).get("usd"))
    return btc, eth


def fetch_btc_dominance() -> float | None:
    data = safe_get("https://api.coingecko.com/api/v3/global")
    if data is None:
        return None
    try:
        dom = data["data"]["bitcoin_dominance_percentage"]
        return round(float(dom), 1)
    except (KeyError, TypeError, ValueError):
        log.warning("CoinGecko: could not parse bitcoin_dominance_percentage")
        return None


def fetch_fear_greed() -> int | None:
    data = safe_get("https://api.alternative.me/fng/?limit=1")
    if data is None:
        return None
    try:
        return int(data["data"][0]["value"])
    except (KeyError, IndexError, TypeError, ValueError):
        log.warning("Alternative.me: could not parse fear & greed value")
        return None


# ---------------------------------------------------------------------------
# Historical data fetchers (used for --days backfill)
# ---------------------------------------------------------------------------

def fetch_polygon_close(symbol: str, target_date: date) -> float | None:
    """
    Polygon free tier: /v1/open-close/{symbol}/{date}
    Requires a Polygon API key — not available here, so we fall back to None
    and log a warning. Users can set POLYGON_KEY env var if they have one.
    """
    polygon_key = os.environ.get("POLYGON_KEY")
    if not polygon_key:
        log.warning(
            "Polygon key (POLYGON_KEY) not set — cannot fetch historical close for %s on %s",
            symbol, target_date,
        )
        return None
    url = (
        f"https://api.polygon.io/v1/open-close/{symbol}/{target_date}?adjusted=true&apiKey={polygon_key}"
    )
    data = safe_get(url)
    if data is None:
        return None
    return round2(data.get("close"))


def fetch_coingecko_historical(coin_id: str, target_date: date) -> float | None:
    """CoinGecko historical price for a specific date (free, no key)."""
    date_str = target_date.strftime("%d-%m-%Y")
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/history?date={date_str}&localization=false"
    data = safe_get(url)
    if data is None:
        return None
    try:
        price = data["market_data"]["current_price"]["usd"]
        return round2(price)
    except (KeyError, TypeError):
        log.warning("CoinGecko historical: could not parse price for %s on %s", coin_id, target_date)
        return None


# ---------------------------------------------------------------------------
# Build market data dict
# ---------------------------------------------------------------------------

def collect_live_data() -> dict:
    """Fetch all live market data."""
    log.info("Fetching SPY (S&P 500 proxy)...")
    spy = fetch_finnhub_price("SPY")

    log.info("Fetching QQQ (Nasdaq proxy)...")
    qqq = fetch_finnhub_price("QQQ")

    log.info("Fetching GLD (Gold proxy)...")
    gld = fetch_finnhub_price("GLD")

    log.info("Fetching 10-yr treasury yield...")
    ten_yr = fetch_ten_yr_yield()

    log.info("Fetching Nifty 50...")
    nifty = fetch_yahoo_price("%5ENSEI")

    log.info("Fetching Sensex...")
    sensex = fetch_yahoo_price("%5EBSESN")

    log.info("Fetching USD/INR...")
    usd_inr = fetch_usd_inr()

    log.info("Fetching BTC and ETH prices...")
    btc, eth = fetch_crypto_prices()

    log.info("Fetching BTC dominance...")
    btc_dom = fetch_btc_dominance()

    log.info("Fetching Fear & Greed index...")
    fg = fetch_fear_greed()

    return {
        "sp500_close": spy,
        "nasdaq_close": qqq,
        "gold_price": gld,
        "ten_yr_yield": ten_yr,
        "nifty_close": nifty,
        "sensex_close": sensex,
        "usd_inr": usd_inr,
        "btc_price": btc,
        "eth_price": eth,
        "btc_dominance": btc_dom,
        "crypto_fear_greed": fg,
    }


def collect_historical_data(target_date: date) -> dict:
    """Fetch historical market data for a specific past date."""
    log.info("Fetching historical data for %s...", target_date)

    spy = fetch_polygon_close("SPY", target_date)
    qqq = fetch_polygon_close("QQQ", target_date)
    gld = fetch_polygon_close("GLD", target_date)

    # Yahoo Finance historical — not easily available without a key via the v8 endpoint
    # for historical dates; set to None for backfill
    nifty = None
    sensex = None
    log.warning("Yahoo Finance historical data not supported for backfill — nifty/sensex set to null")

    # Treasury yield historical via FMP (same endpoint may return latest, not historical)
    ten_yr = fetch_ten_yr_yield()

    # ExchangeRate-API only provides current rates on free tier
    usd_inr = fetch_usd_inr()
    log.warning("ExchangeRate-API does not support historical rates on free tier — using current rate")

    btc = fetch_coingecko_historical("bitcoin", target_date)
    eth = fetch_coingecko_historical("ethereum", target_date)
    btc_dom = fetch_btc_dominance()

    fg = fetch_fear_greed()
    log.warning("Fear & Greed historical not fetched for backfill — using current value")

    return {
        "sp500_close": spy,
        "nasdaq_close": qqq,
        "gold_price": gld,
        "ten_yr_yield": ten_yr,
        "nifty_close": nifty,
        "sensex_close": sensex,
        "usd_inr": usd_inr,
        "btc_price": btc,
        "eth_price": eth,
        "btc_dominance": btc_dom,
        "crypto_fear_greed": fg,
    }


# ---------------------------------------------------------------------------
# Sentiment
# ---------------------------------------------------------------------------

def derive_sentiment(fg: int | None) -> str:
    if fg is None:
        return "neutral"
    if fg >= 60:
        return "bullish"
    if fg >= 40:
        return "neutral"
    return "bearish"


# ---------------------------------------------------------------------------
# File writer
# ---------------------------------------------------------------------------

def yaml_val(val) -> str:
    """Render a Python value as a YAML scalar (null-safe)."""
    if val is None:
        return "null"
    return str(val)


def write_market_file(target_date: date, market: dict) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / f"{target_date}.md"

    if out_path.exists():
        log.info("Skipping %s — file already exists.", out_path)
        return out_path

    sentiment = derive_sentiment(market.get("crypto_fear_greed"))
    date_str = str(target_date)

    content = f"""---
date: {date_str}
type: daily-market-analysis
sentiment: {sentiment}
sp500_close: {yaml_val(market.get('sp500_close'))}
nasdaq_close: {yaml_val(market.get('nasdaq_close'))}
nifty_close: {yaml_val(market.get('nifty_close'))}
sensex_close: {yaml_val(market.get('sensex_close'))}
btc_price: {yaml_val(market.get('btc_price'))}
eth_price: {yaml_val(market.get('eth_price'))}
gold_price: {yaml_val(market.get('gold_price'))}
usd_inr: {yaml_val(market.get('usd_inr'))}
ten_yr_yield: {yaml_val(market.get('ten_yr_yield'))}
crypto_fear_greed: {yaml_val(market.get('crypto_fear_greed'))}
btc_dominance: {yaml_val(market.get('btc_dominance'))}
tags: [type/analysis, topic/market]
---

# Market Analysis — {date_str}
"""

    out_path.write_text(content, encoding="utf-8")
    return out_path


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(
        description="Fetch real market data and write Analysis/Market/YYYY-MM-DD.md"
    )
    parser.add_argument(
        "--date",
        metavar="YYYY-MM-DD",
        help="Target date (default: today)",
        default=None,
    )
    parser.add_argument(
        "--days",
        metavar="N",
        type=int,
        help="Backfill N days ending on --date (or today)",
        default=None,
    )
    return parser.parse_args()


def main():
    args = parse_args()

    if args.date:
        try:
            base_date = datetime.strptime(args.date, "%Y-%m-%d").date()
        except ValueError:
            log.error("Invalid date format: %s (expected YYYY-MM-DD)", args.date)
            sys.exit(1)
    else:
        base_date = date.today()

    # Build list of dates to process
    if args.days and args.days > 1:
        dates = [base_date - timedelta(days=i) for i in range(args.days - 1, -1, -1)]
    else:
        dates = [base_date]

    written = []
    skipped = []

    for target_date in dates:
        out_path = OUTPUT_DIR / f"{target_date}.md"
        if out_path.exists():
            log.info("Skipping %s — file already exists.", out_path)
            skipped.append(target_date)
            continue

        is_today = (target_date == date.today())
        if is_today or args.days is None:
            market = collect_live_data()
        else:
            market = collect_historical_data(target_date)

        result_path = write_market_file(target_date, market)
        if result_path.exists() and str(target_date) in result_path.name:
            written.append(result_path)

    # Summary
    print()
    for p in written:
        rel = p.relative_to(REPO_ROOT)
        print(f"Written: {rel}")
    for d in skipped:
        rel = OUTPUT_DIR.relative_to(REPO_ROOT) / f"{d}.md"
        print(f"Skipped (exists): {rel}")

    if not written and not skipped:
        log.warning("No files written.")


if __name__ == "__main__":
    main()
