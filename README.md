# FinCopilot Dashboard

[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/streamlit-1.x-FF4B4B.svg)](https://streamlit.io/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Data Pipeline](https://img.shields.io/badge/data%20pipeline-GitHub%20Actions-2088FF.svg)](https://github.com/features/actions)

A personal finance intelligence dashboard built for my own use as an NRI investor tracking US markets, India markets, crypto, and retirement accounts — all in one terminal-style interface.

**Live demo:** https://fincopilot-dashboard.streamlit.app _(auth-protected — access by invite)_

---

## Overview

Managing finances across two countries means juggling S&P 500 performance, Nifty 50 movements, USD/INR exchange rates, crypto positions, and US real estate decisions simultaneously. Most dashboards handle one of these well. This one handles all of them together.

FinCopilot pulls live market data daily via a GitHub Actions pipeline and surfaces it through three focused tabs: real estate analysis, market overview, and portfolio tracking. The underlying data lives in plain markdown files with YAML frontmatter — human-readable, git-versioned, and queryable by the same Obsidian PKM setup I use for notes.

No database. No server. No ongoing infrastructure cost.

---

## Features

### 🏠 Real Estate Tab
- Mortgage rate tracking (30-year fixed, 15-year fixed)
- Rental yield and price-to-rent ratio analysis
- Neighborhood scoring across Austin, Dallas, Hyderabad, and Guntur
- Buy vs. rent breakeven analysis with customizable assumptions

### 📊 Market Analysis Tab
- US equities: S&P 500 (SPY), Nasdaq (QQQ), Gold (GLD)
- India equities: Nifty 50, Sensex
- Crypto: BTC, ETH with dominance metrics
- Treasury yield curve (2Y / 10Y)
- USD/INR exchange rate history
- CNN Fear & Greed Index
- Historical trend charts for all major indices

### 💼 Portfolio Tab
- 401(k) allocation tracker (T. Rowe Price 2055, JHancock JLKYX)
- Crypto holdings: SOL, DOGE, AVAX, WIF
- Cost basis and unrealized P&L per position
- Allocation breakdown — donut and polar radar charts
- Overall portfolio performance vs. benchmarks

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     DATA SOURCES                            │
│                                                             │
│  Finnhub      FMP Stable     Yahoo Finance    CoinGecko     │
│  (SPY/QQQ/    (treasury      (Nifty/Sensex)   (BTC/ETH/     │
│   GLD)         yields)                         dominance)   │
│                                                             │
│  ExchangeRate-API            Alternative.me                 │
│  (USD/INR)                   (Fear & Greed)                 │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│               GITHUB ACTIONS CRON (9PM ET daily)            │
│                                                             │
│   fetch_market_data.py                                      │
│   → writes YAML frontmatter into .md files                  │
│   → commits data files to repo                              │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                  DATA LAYER (markdown files)                 │
│                                                             │
│   data/market/spy.md          data/market/nifty.md          │
│   data/market/crypto.md       data/market/fear_greed.md     │
│   data/real_estate/austin.md  data/portfolio/401k.md        │
│                                                             │
│   Each file: YAML frontmatter + human-readable notes        │
│   Also readable directly in Obsidian                        │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                  DASHBOARD (dashboard.py)                    │
│                                                             │
│   PyYAML + regex parse frontmatter                          │
│   pandas transforms and aggregates                          │
│   Plotly renders charts (bar / line / donut / radar)        │
│   Streamlit handles layout, tabs, and auth                  │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│          STREAMLIT COMMUNITY CLOUD                          │
│                                                             │
│   Auto-deploys on push to main                              │
│   Viewer auth via email whitelist                           │
│   Zero server management                                    │
└─────────────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| Dashboard framework | Streamlit | UI, layout, tab routing, auth |
| Charts | Plotly | Bar, line, scatter, pie/donut, polar radar |
| Data parsing | PyYAML + regex | Read YAML frontmatter from markdown files |
| Data manipulation | pandas | Aggregation, time-series prep, P&L calculations |
| Automation | GitHub Actions | Daily data pipeline, cron scheduling |
| Deployment | Streamlit Community Cloud | Hosting, auto-deploy on push |
| Data format | Markdown + YAML frontmatter | Human-readable, git-versioned, Obsidian-compatible |

---

## Data Pipeline

Market data is fetched daily at 9PM ET via a GitHub Actions workflow. Each source feeds a specific set of data files:

| Source | Data | Files Updated |
|---|---|---|
| Finnhub | SPY, QQQ, GLD prices and history | `data/market/us_equities.md` |
| FMP Stable | 2Y / 10Y treasury yields | `data/market/yields.md` |
| Yahoo Finance | Nifty 50, Sensex | `data/market/india_equities.md` |
| CoinGecko | BTC, ETH, market dominance | `data/market/crypto.md` |
| ExchangeRate-API | USD/INR rate | `data/market/forex.md` |
| Alternative.me | Fear & Greed Index | `data/market/fear_greed.md` |

Portfolio data (401k balances, crypto positions, cost basis) is updated manually — these are personal records, not something an API can provide.

The YAML frontmatter schema looks like this:

```yaml
---
ticker: SPY
price: 542.18
change_pct: 0.73
week_52_high: 613.23
week_52_low: 491.50
updated: 2026-03-27
---
```

The dashboard reads these files at startup, parses the frontmatter with regex, and hands the data off to pandas. If a file is missing or malformed, the affected section degrades gracefully rather than crashing the whole app.

---

## Local Setup

```bash
# Clone the repo
git clone https://github.com/sakethGT/fincopilot-dashboard.git
cd fincopilot-dashboard

# Install dependencies
pip install -r requirements.txt

# Run the dashboard
streamlit run dashboard.py
```

The app will open at `http://localhost:8501`. Without the data files present, most panels will show empty states — run the pipeline script manually to populate them:

```bash
python scripts/fetch_market_data.py
```

This requires API keys for Finnhub, FMP, ExchangeRate-API, and CoinGecko. Add them to a `.env` file (see `.env.example`).

---

## Project Structure

```
fincopilot-dashboard/
├── dashboard.py                 # Main Streamlit app, tab routing
├── requirements.txt
├── .env.example
│
├── tabs/
│   ├── real_estate.py           # Real estate tab — mortgage, rental yield, breakeven
│   ├── market_analysis.py       # Market tab — equities, crypto, Fear & Greed
│   └── portfolio.py             # Portfolio tab — 401k, crypto, P&L
│
├── utils/
│   ├── data_loader.py           # YAML frontmatter parser, file readers
│   ├── charts.py                # Reusable Plotly chart builders
│   └── formatters.py            # Number formatting, color scales
│
├── scripts/
│   └── fetch_market_data.py     # Data pipeline — fetches all sources, writes .md files
│
├── data/
│   ├── market/
│   │   ├── us_equities.md
│   │   ├── india_equities.md
│   │   ├── crypto.md
│   │   ├── yields.md
│   │   ├── forex.md
│   │   └── fear_greed.md
│   ├── real_estate/
│   │   ├── austin.md
│   │   ├── dallas.md
│   │   ├── hyderabad.md
│   │   └── guntur.md
│   └── portfolio/
│       ├── 401k.md              # Manual — 401k balances and allocations
│       └── crypto.md            # Manual — positions, cost basis
│
└── .github/
    └── workflows/
        └── fetch_data.yml       # Cron job: daily at 9PM ET
```

---

## Design Decisions

**Dark terminal aesthetic.** Background color `#080c14`, monospace-adjacent fonts, high-contrast chart colors. Financial data reads better against dark backgrounds — this is a tool I look at every day, so it needed to feel right.

**Markdown as the data layer.** Storing data as YAML frontmatter in `.md` files was a deliberate choice. The same files that feed the dashboard are readable in Obsidian, diff cleanly in git, and require no schema migrations. For a personal project with stable data shapes, this is more practical than a database.

**No backend server.** Streamlit Community Cloud handles hosting. GitHub Actions handles the data pipeline. The total infrastructure footprint is zero managed servers and zero ongoing cost beyond API rate limits, all of which fall within free tiers.

**NRI-first scope.** The specific market combinations here — US equities alongside Nifty/Sensex, USD/INR tracking, real estate analysis that includes both US cities and Indian cities — reflect the actual financial decisions I navigate. There's no general-purpose configurability because this tool isn't trying to be one.

---

## License

MIT — see [LICENSE](LICENSE).
