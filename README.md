# P2P Price Tracker

A real-time P2P (peer-to-peer) USDT price aggregator that fetches and displays buy/sell ads from four major cryptocurrency exchanges: **MEXC**, **Binance**, **Bybit**, and **OKX**.

Built with Flask (Python) and deployed on Render. Provides a web dashboard with live price comparison and a simple API for integration with tools like Google Sheets.

**Live URL:** https://p2p-price-fetch.onrender.com

## Features

- **Multi-exchange aggregation** — Fetches P2P ads from MEXC, Binance, Bybit, and OKX in a single view
- **Multi-currency pairs** — Tracks USDT/ETB, USDT/USD, and USDT/EUR
- **Multi-page fetching** — Paginates through all available ads on each exchange (not just the first page)
- **Auto-refresh** — Background thread fetches fresh data every 30 seconds
- **Exchange comparison table** — Side-by-side best/average prices and spread across exchanges
- **Individual ad cards** — Sortable by price, showing merchant name, limits, and payment methods
- **Exchange filter** — Toggle specific exchanges on/off in the ads view
- **Payment method filter** — Multi-select dropdown to filter ads by payment method (e.g., CBE, Tele Birr, Dukascopy). Uses prefix matching to handle naming differences across exchanges
- **Amount filter** — Enter a trade amount to only see ads whose min/max limits include that amount
- **Pagination** — Paginated ads grid with page controls
- **Simple API** — Plain-text endpoint for Google Sheets `IMPORTDATA` integration
- **JSON API** — Full ad data as JSON for programmatic use
- **Responsive design** — Dark-themed dashboard that works on desktop and mobile

## Project Structure

```
P2P Price Fetch/
├── app.py              # Flask server, routes, background fetcher thread
├── config.py           # Configuration (pairs, refresh interval, pagination)
├── fetchers.py         # Exchange-specific P2P API fetchers
├── templates/
│   └── index.html      # Single-page dashboard (HTML/CSS/JS)
├── requirements.txt    # Python dependencies
├── Dockerfile          # Docker image for deployment
├── render.yaml         # Render deployment config
├── GOOGLE_SHEETS_GUIDE.md  # Google Sheets integration guide
└── .gitignore
```

## Configuration

All configuration is in `config.py`:

| Setting | Default | Description |
|---------|---------|-------------|
| `ASSET` | `"USDT"` | Crypto asset to track |
| `PAIRS` | ETB, USD, EUR | Currency pairs with optional payment method filters |
| `REFRESH_INTERVAL` | `30` | Seconds between background fetches |
| `PAGE_SIZE` | `20` | Ads per API page (Binance/Bybit) |
| `MAX_PAGES` | `10` | Max pages to fetch per side per exchange |
| `HOST` | `"0.0.0.0"` | Flask bind host |
| `PORT` | `5000` | Flask port (overridden by `PORT` env var on Render) |

### Currency Pair Configuration

Each pair in `PAIRS` can specify a `pay_filter` list to restrict which payment methods are fetched and shown:

```python
PAIRS = [
    {"fiat": "ETB", "label": "USDT/ETB", "pay_filter": []},           # All payment methods
    {"fiat": "USD", "label": "USDT/USD", "pay_filter": ["Dukascopy", "Payoneer"]},  # Filtered
    {"fiat": "EUR", "label": "USDT/EUR", "pay_filter": ["Dukascopy", "Payoneer"]},  # Filtered
]
```

An empty `pay_filter` means all payment methods are shown. When specified, only matching methods appear in the dropdown, and on Binance/OKX/MEXC the API request itself is filtered to those methods.

## API Endpoints

### `GET /`

Web dashboard.

### `GET /api/prices?fiat=ETB`

Returns full JSON data for a given fiat currency, including all exchange results with individual ads.

**Parameters:**

| Parameter | Default | Description |
|-----------|---------|-------------|
| `fiat` | `ETB` | Currency code: `ETB`, `USD`, or `EUR` |

**Response structure:**
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
      "buy_ads": [ ... ],
      "sell_ads": [ ... ],
      "last_updated": "2026-02-08 21:39:15",
      "error": null
    },
    ...
  ]
}
```

### `GET /api/price/simple`

Returns a single plain-text price value. Designed for Google Sheets `IMPORTDATA`.

**Parameters:**

| Parameter | Default | Description |
|-----------|---------|-------------|
| `fiat` | `ETB` | Currency code |
| `exchange` | *(best across all)* | Exchange name: `MEXC`, `Binance`, `Bybit`, `OKX` |
| `field` | `best_sell` | Price field: `best_buy`, `best_sell`, `avg_buy`, `avg_sell` |

**Example:**
```
GET /api/price/simple?fiat=ETB&exchange=Binance&field=best_sell
→ 191.02
```

When no exchange is specified, returns the best value across all exchanges (max for sell, min for buy). Returns `N/A` if no data is available.

See [GOOGLE_SHEETS_GUIDE.md](GOOGLE_SHEETS_GUIDE.md) for detailed usage with `IMPORTDATA`.

## Exchange-Specific Notes

### MEXC
- Uses GET requests to `mexc.com/api/platform/p2p/api/market`
- Returns 10 ads per page; fetches up to 5 pages per side (50 ads max)
- Payment method IDs are resolved via a separate API call to `/api/payment/method`
- Filters out ads where merchant trade is disabled (`merchantTradeEnable: false`)

### Binance
- Uses POST requests to `p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search`
- 20 ads per page, up to 10 pages
- Payment methods mapped via `BINANCE_PAY_METHODS` dict (e.g., `"Dukascopy"` -> `"DukascopyBank"`)

### Bybit
- Uses POST requests to `api2.bybit.com/fiat/otc/item/online`
- 20 ads per page, up to 10 pages
- Filters out ineligible ads (merchants requiring taker to have posted their own ad via `hasUnPostAd`)
- Payment method IDs resolved via `BYBIT_PAYMENT_NAMES` mapping

### OKX
- Uses GET requests to `okx.com/v3/c2c/tradingOrders/books`
- Returns all ads in a single response (no pagination needed)
- Payment methods passed as comma-separated identifiers

## Running Locally

### Prerequisites

- Python 3.11+

### Setup

```bash
git clone https://github.com/KnightDannyPersonal/p2p-price-fetch.git
cd p2p-price-fetch
pip install -r requirements.txt
python app.py
```

The server starts on http://localhost:5000. The background fetcher begins immediately and refreshes every 30 seconds.

### With Docker

```bash
docker build -t p2p-price-tracker .
docker run -p 5000:5000 p2p-price-tracker
```

## Deployment (Render)

The project is configured for Render's free tier using Docker:

1. Push to the GitHub repository
2. Render auto-deploys from `render.yaml` which uses the `Dockerfile`
3. The `PORT` environment variable is set to `5000` in `render.yaml`
4. Gunicorn runs with 1 worker and 4 threads (single worker ensures the background fetcher runs once)

### Why 1 Worker?

The background fetcher thread is started when the Flask app module loads. With multiple Gunicorn workers, each worker would spawn its own fetcher thread, making redundant API calls to the exchanges. A single worker with multiple threads handles concurrent HTTP requests while keeping one fetcher.

## Dependencies

| Package | Purpose |
|---------|---------|
| `flask` | Web framework |
| `requests` | HTTP client for exchange APIs |
| `gunicorn` | Production WSGI server (deployment) |
