"""Configuration for P2P Price Fetcher."""

import os

# Crypto asset to track
ASSET = "USDT"

# Currency pairs to track: fiat, display label, payment method filters
# Empty pay_filter means fetch all payment methods
PAIRS = [
    {"fiat": "ETB", "label": "USDT/ETB", "pay_filter": []},
    {"fiat": "USD", "label": "USDT/USD", "pay_filter": ["Dukascopy", "Payoneer"]},
    {"fiat": "EUR", "label": "USDT/EUR", "pay_filter": ["Dukascopy", "Payoneer"]},
]

# How often to refresh prices (in seconds)
REFRESH_INTERVAL = 30

# Pagination for exchange API requests
PAGE_SIZE = 20       # Ads per API page request
MAX_PAGES = 10       # Max pages to fetch per side (safety cap)

# Flask server — Render sets PORT via environment variable
HOST = "0.0.0.0"
PORT = int(os.environ.get("PORT", 5000))
