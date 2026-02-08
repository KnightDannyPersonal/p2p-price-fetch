"""Flask web server for P2P Price Fetcher."""

import threading
import time

from flask import Flask, jsonify, render_template
from config import HOST, PORT, REFRESH_INTERVAL
from fetchers import fetch_all

app = Flask(__name__)

# Shared state for latest prices
price_data = {
    "results": [],
    "last_refresh": None,
}
data_lock = threading.Lock()
_fetcher_started = False


def background_fetcher():
    """Continuously fetch P2P prices in the background."""
    while True:
        try:
            results = fetch_all()
            with data_lock:
                price_data["results"] = results
                price_data["last_refresh"] = time.strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{time.strftime('%H:%M:%S')}] Prices refreshed successfully")
        except Exception as e:
            print(f"[{time.strftime('%H:%M:%S')}] Error refreshing prices: {e}")

        time.sleep(REFRESH_INTERVAL)


def start_fetcher():
    """Start background fetcher once (safe to call multiple times)."""
    global _fetcher_started
    if not _fetcher_started:
        _fetcher_started = True
        t = threading.Thread(target=background_fetcher, daemon=True)
        t.start()
        print(f"Background fetcher started (every {REFRESH_INTERVAL}s)")


@app.route("/")
def index():
    return render_template("index.html", refresh_interval=REFRESH_INTERVAL)


@app.route("/api/prices")
def api_prices():
    with data_lock:
        return jsonify(price_data)


# Start fetcher when module loads (works with both gunicorn and python app.py)
start_fetcher()

if __name__ == "__main__":
    print(f"P2P Price Fetcher on http://localhost:{PORT}")
    app.run(host=HOST, port=PORT, debug=False)
