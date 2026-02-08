"""Flask web server for P2P Price Fetcher."""

import threading
import time

from flask import Flask, jsonify, render_template, request
from config import HOST, PORT, REFRESH_INTERVAL, PAIRS
from fetchers import fetch_all_pairs, _now

app = Flask(__name__)

# Shared state: keyed by fiat currency code
price_data = {p["fiat"]: {"results": [], "last_refresh": None} for p in PAIRS}
data_lock = threading.Lock()
_fetcher_started = False


def background_fetcher():
    """Continuously fetch P2P prices for all pairs in the background."""
    while True:
        try:
            all_data = fetch_all_pairs()
            with data_lock:
                for fiat, data in all_data.items():
                    price_data[fiat] = data
            print(f"[{_now('%H:%M:%S')}] All pairs refreshed successfully")
        except Exception as e:
            print(f"[{_now('%H:%M:%S')}] Error refreshing prices: {e}")

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
    return render_template(
        "index.html",
        refresh_interval=REFRESH_INTERVAL,
        pairs=PAIRS,
    )


@app.route("/api/price/simple")
def api_price_simple():
    fiat = request.args.get("fiat", PAIRS[0]["fiat"]).upper()
    exchange = request.args.get("exchange", "").lower()
    field = request.args.get("field", "best_sell")
    with data_lock:
        data = price_data.get(fiat, {"results": []})
        for r in data.get("results", []):
            if r.get("exchange", "").lower() == exchange or not exchange:
                val = r.get(f"{field}_price", r.get(field))
                if val is not None:
                    return str(val), 200, {"Content-Type": "text/plain"}
        return "N/A", 200, {"Content-Type": "text/plain"}


@app.route("/api/prices")
def api_prices():
    fiat = request.args.get("fiat", PAIRS[0]["fiat"]).upper()
    with data_lock:
        data = price_data.get(fiat, {"results": [], "last_refresh": None})
        return jsonify(data)


# Start fetcher when module loads (works with both gunicorn and python app.py)
start_fetcher()

if __name__ == "__main__":
    print(f"P2P Price Fetcher on http://localhost:{PORT}")
    app.run(host=HOST, port=PORT, debug=False)
