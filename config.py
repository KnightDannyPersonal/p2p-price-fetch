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

# Optional: restrict tracked pairs via FIATS env var, e.g. FIATS=ETB or FIATS=ETB,USD.
# Unset means all pairs above are tracked.
_enabled_fiats = [f.strip().upper() for f in os.environ.get("FIATS", "").split(",") if f.strip()]
if _enabled_fiats:
    _known = [p["fiat"] for p in PAIRS]
    _unknown = [f for f in _enabled_fiats if f not in _known]
    if _unknown:
        raise ValueError(f"FIATS contains unknown fiat(s) {_unknown}; known: {_known}")
    PAIRS = [p for p in PAIRS if p["fiat"] in _enabled_fiats]

# How often to refresh prices (in seconds). Override with REFRESH_INTERVAL env var.
REFRESH_INTERVAL = int(os.environ.get("REFRESH_INTERVAL", 30))

# Pagination for exchange API requests
PAGE_SIZE = 20       # Ads per API page request
MAX_PAGES = 10       # Max pages to fetch per side (safety cap)

# Flask server. Render sets PORT via environment variable.
HOST = "0.0.0.0"
PORT = int(os.environ.get("PORT", 5000))
