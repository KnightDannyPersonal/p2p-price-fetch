<div align="center">

# 📈 P2P Price Tracker

**A real-time USDT P2P price aggregator across four major exchanges.**
Fetches live buy/sell ads from **MEXC**, **Binance**, **Bybit**, and **OKX**, compares them side by side, and exposes a simple API for tools like Google Sheets.

<p>
  <img alt="Python" src="https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white">
  <img alt="Flask" src="https://img.shields.io/badge/Flask-2.3-000000?logo=flask&logoColor=white">
  <img alt="Requests" src="https://img.shields.io/badge/requests-2.32-2CA5E0">
  <img alt="Gunicorn" src="https://img.shields.io/badge/Gunicorn-21.2-499848?logo=gunicorn&logoColor=white">
  <img alt="Docker" src="https://img.shields.io/badge/Docker-ready-2496ED?logo=docker&logoColor=white">
  <img alt="Render" src="https://img.shields.io/badge/Render-deployed-46E3B7?logo=render&logoColor=white">
</p>

[![Live Demo](https://img.shields.io/badge/🌐_Live_Demo-p2p--price--fetch.onrender.com-2EA043?style=for-the-badge)](https://p2p-price-fetch.onrender.com)

[Features](#-features) · [API](#-api-endpoints) · [Configuration](#%EF%B8%8F-configuration) · [Exchange Notes](#-exchange-specific-notes) · [Run Locally](#-running-locally) · [Deploy](#-deployment-render)

</div>

> Built to compare USDT/ETB (and USD/EUR) P2P rates across exchanges in one place, since each platform only shows its own market. A background worker keeps prices fresh, and a plain-text endpoint lets a Google Sheet pull a single live price with `IMPORTDATA`.

---

## ✨ Features

- **🔀 Multi-exchange aggregation**: buy/sell ads from MEXC, Binance, Bybit, and OKX in a single view
- **💱 Multi-currency pairs**: tracks USDT/ETB, USDT/USD, and USDT/EUR
- **📄 Multi-page fetching**: paginates through all available ads per exchange, not just the first page
- **🔄 Auto-refresh**: a background thread fetches fresh data on a configurable interval (30 seconds by default)
- **📊 Exchange comparison table**: side-by-side best/average prices and spread across exchanges
- **🧾 Individual ad cards**: sortable by price, showing merchant, limits, and payment methods
- **🎚️ Filters**: toggle exchanges on/off, multi-select payment methods (CBE, Tele Birr, Dukascopy…), and filter by trade amount
- **🧮 Arbitrage guard**: drops impossible buy ads priced below the best sell price, so comparisons stay realistic
- **🔌 Simple API**: plain-text endpoint for Google Sheets `IMPORTDATA`
- **🧱 JSON API**: full ad data for programmatic use
- **📱 Responsive design**: dark-themed dashboard that works on desktop and mobile

---

## 🧰 Tech Stack

| Layer | Technology |
|---|---|
| 🐍 **Language** | Python 3.11 |
| 🌶️ **Web framework** | Flask |
| 🌐 **HTTP client** | requests |
| 🧵 **Concurrency** | Background daemon thread + thread-safe shared state |
| 🚀 **Server** | Gunicorn (1 worker, 4 threads) |
| 🐳 **Container** | Docker (`python:3.11-slim`) |
| ☁️ **Hosting** | Render (free tier) |

---

## 📁 Project Structure

```
P2P Price Fetch/
├── app.py                  # Flask server, routes, background fetcher thread
├── config.py               # Configuration (asset, pairs, refresh interval, pagination)
├── fetchers.py             # Exchange-specific P2P API fetchers + normalization
├── templates/
│   └── index.html          # Single-page dashboard (HTML/CSS/JS)
├── test_fetchers.py        # Smoke tests for the fetchers
├── requirements.txt        # Python dependencies
├── Dockerfile              # Container image for deployment
├── render.yaml             # Render deployment config
└── GOOGLE_SHEETS_GUIDE.md  # Google Sheets integration guide
```

---

## 🔌 API Endpoints

### `GET /`
Web dashboard.

### `GET /api/prices?fiat=ETB`
Full JSON for a given fiat: every exchange's best/average prices plus the individual ads.

| Parameter | Default | Description |
|---|---|---|
| `fiat` | `ETB` | Currency code: `ETB`, `USD`, or `EUR` |

```json
{
  "last_refresh": "2026-02-08 21:39:27",
  "results": [
    {
      "exchange": "MEXC",
      "best_buy_price": 191.0,
      "best_sell_price": 191.69,
      "avg_buy_price": 193.21,
      "avg_sell_price": 191.04,
      "buy_count": 46,
      "sell_count": 50,
      "buy_ads": [ /* ... */ ],
      "sell_ads": [ /* ... */ ],
      "last_updated": "2026-02-08 21:39:15",
      "error": null
    }
  ]
}
```

### `GET /api/price/simple`
A single plain-text price value, built for Google Sheets `IMPORTDATA`.

| Parameter | Default | Description |
|---|---|---|
| `fiat` | `ETB` | Currency code |
| `exchange` | *(best across all)* | `MEXC`, `Binance`, `Bybit`, or `OKX` |
| `field` | `best_sell` | `best_buy`, `best_sell`, `avg_buy`, or `avg_sell` |

```
GET /api/price/simple?fiat=ETB&exchange=Binance&field=best_sell
→ 191.02
```

With no `exchange`, it returns the best across all exchanges (max for sell, min for buy), or `N/A` if no data is available yet. See **[GOOGLE_SHEETS_GUIDE.md](GOOGLE_SHEETS_GUIDE.md)** for full `IMPORTDATA` usage.

---

## ⚙️ Configuration

Everything lives in [config.py](config.py). Settings marked *env* can be overridden with an environment variable of the same name, so on Render you can change them from the dashboard without touching code.

| Setting | Default | Description |
|---|---|---|
| `ASSET` | `"USDT"` | Crypto asset to track |
| `PAIRS` | ETB, USD, EUR | Currency pairs with optional payment-method filters |
| `FIATS` *(env)* | *(all pairs)* | Comma-separated allowlist of fiats to track, e.g. `ETB` or `ETB,USD`. Unlisted pairs are not fetched or shown |
| `REFRESH_INTERVAL` *(env)* | `30` | Seconds between background fetches. `render.yaml` sets `300` |
| `PAGE_SIZE` | `20` | Ads per API page (Binance/Bybit) |
| `MAX_PAGES` | `10` | Max pages to fetch per side per exchange (safety cap) |
| `HOST` | `"0.0.0.0"` | Flask bind host |
| `PORT` *(env)* | `5000` | Flask port (Render sets this) |

### Currency pair filters

Each pair can restrict which payment methods are fetched and shown via `pay_filter`:

```python
PAIRS = [
    {"fiat": "ETB", "label": "USDT/ETB", "pay_filter": []},                          # all methods
    {"fiat": "USD", "label": "USDT/USD", "pay_filter": ["Dukascopy", "Payoneer"]},   # filtered
    {"fiat": "EUR", "label": "USDT/EUR", "pay_filter": ["Dukascopy", "Payoneer"]},   # filtered
]
```

An empty `pay_filter` shows all methods. When set, only matching methods appear in the dropdown, and on Binance/OKX/MEXC the API request itself is filtered to those methods (prefix matching bridges naming differences across exchanges).

---

## 🏦 Exchange-Specific Notes

| Exchange | Method | Pagination | Notes |
|---|---|---|---|
| **MEXC** | `GET` `/platform/p2p/api/market` | 10/page, up to 5 pages (50 ads) | Payment method IDs resolved via a separate `/payment/method` call |
| **Binance** | `POST` `/c2c/adv/search` | 20/page, up to 10 pages | Methods mapped via `BINANCE_PAY_METHODS` (e.g. `Dukascopy → DukascopyBank`) |
| **Bybit** | `POST` `/fiat/otc/item/online` | 20/page, up to 10 pages | Skips ineligible ads (`hasUnPostAd`); IDs resolved via `BYBIT_PAYMENT_NAMES` |
| **OKX** | `GET` `/c2c/tradingOrders/books` | single response | Payment methods passed as comma-separated identifiers |

All fetchers normalize results into a common shape and reconcile maker/taker perspective so "buy" and "sell" mean the same thing across exchanges.

---

## 🚀 Running Locally

**Prerequisites:** Python 3.11+

```bash
git clone https://github.com/KnightDanny/p2p-price-fetch.git
cd p2p-price-fetch
pip install -r requirements.txt
python app.py
```

The server starts on http://localhost:5000. The background fetcher begins immediately and refreshes every 30 seconds unless `REFRESH_INTERVAL` is set.

### With Docker

```bash
docker build -t p2p-price-tracker .
docker run -p 5000:5000 p2p-price-tracker
```

---

## ☁️ Deployment (Render)

Configured for Render's free tier via Docker:

1. Push to GitHub.
2. Render auto-deploys from [render.yaml](render.yaml), which builds the [Dockerfile](Dockerfile).
3. `render.yaml` sets `PORT=5000` and `REFRESH_INTERVAL=300`. Add `FIATS=ETB` in the Render dashboard to track only ETB.
4. Gunicorn runs with **1 worker and 4 threads**.

### Why one worker?

The background fetcher thread starts when the Flask module loads. With multiple Gunicorn workers, each would spawn its own fetcher and make redundant calls to the exchanges. A single worker with multiple threads handles concurrent HTTP requests while keeping exactly one fetcher running.

---

## 🧪 Tests

```bash
python test_fetchers.py
```

Smoke-tests the exchange fetchers against the live P2P endpoints.

---

## 📄 License

Personal project, built for portfolio demonstration and personal use.