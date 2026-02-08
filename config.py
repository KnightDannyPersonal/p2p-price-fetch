"""Configuration for P2P Price Fetcher."""

import os

# Crypto asset to track
ASSET = "USDT"

# Fiat currency
FIAT = "ETB"

# How often to refresh prices (in seconds)
REFRESH_INTERVAL = 30

# Number of ads to fetch per exchange per side
ADS_PER_PAGE = 10

# Flask server — Render sets PORT via environment variable
HOST = "0.0.0.0"
PORT = int(os.environ.get("PORT", 5000))
