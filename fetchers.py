"""P2P price fetchers for Binance, Bybit, OKX, and MEXC."""

import json
import time
import requests
from curl_cffi import requests as curl_requests
from config import ASSET, FIAT, ADS_PER_PAGE


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Content-Type": "application/json",
}

# MEXC coin IDs
MEXC_COIN_IDS = {
    "USDT": "128f589271cb4951b03e71e6323eb7be",
    "BTC": "febc9973be4d4d53bb374476239eb219",
    "ETH": "93c38b0169214f8689763ce9a63a73ff",
    "USDC": "34309140878b4ae99f195ac091d49bab",
}

# MEXC payment method ID -> name mapping (loaded on first fetch)
MEXC_PAYMENT_METHODS = {}
_mexc_session = curl_requests.Session(impersonate="chrome120")


def _safe_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _build_result(exchange, buy_ads, sell_ads):
    """Build a standardized result dict from raw ad lists."""
    buy_prices = [a["price"] for a in buy_ads if a["price"] > 0]
    sell_prices = [a["price"] for a in sell_ads if a["price"] > 0]

    return {
        "exchange": exchange,
        "buy_ads": buy_ads,
        "sell_ads": sell_ads,
        "best_buy_price": min(buy_prices) if buy_prices else None,
        "best_sell_price": max(sell_prices) if sell_prices else None,
        "avg_buy_price": round(sum(buy_prices) / len(buy_prices), 2) if buy_prices else None,
        "avg_sell_price": round(sum(sell_prices) / len(sell_prices), 2) if sell_prices else None,
        "buy_count": len(buy_prices),
        "sell_count": len(sell_prices),
        "last_updated": time.strftime("%Y-%m-%d %H:%M:%S"),
        "error": None,
    }


def _error_result(exchange, error_msg):
    return {
        "exchange": exchange,
        "buy_ads": [],
        "sell_ads": [],
        "best_buy_price": None,
        "best_sell_price": None,
        "avg_buy_price": None,
        "avg_sell_price": None,
        "buy_count": 0,
        "sell_count": 0,
        "last_updated": time.strftime("%Y-%m-%d %H:%M:%S"),
        "error": str(error_msg),
    }


# ---------------------------------------------------------------------------
# MEXC (Most Important) — uses curl_cffi for browser-like TLS fingerprint
# ---------------------------------------------------------------------------
def _load_mexc_payment_methods():
    """Load MEXC payment method names once."""
    global MEXC_PAYMENT_METHODS
    if MEXC_PAYMENT_METHODS:
        return
    try:
        resp = _mexc_session.get(
            "https://www.mexc.com/api/platform/p2p/api/payment/method",
            headers={"Accept": "application/json", "Referer": "https://www.mexc.com/buy-crypto/p2p"},
            timeout=10,
        )
        data = resp.json()
        if isinstance(data, dict) and "data" in data:
            for pm in data["data"]:
                if isinstance(pm, dict):
                    pm_id = str(pm.get("id", ""))
                    pm_name = pm.get("nameEn") or pm.get("name") or pm.get("nameCn") or pm_id
                    MEXC_PAYMENT_METHODS[pm_id] = pm_name
            print(f"[MEXC] Loaded {len(MEXC_PAYMENT_METHODS)} payment methods")
    except Exception as e:
        print(f"[MEXC] Payment method load error: {e}")


def fetch_mexc():
    """Fetch P2P ads from MEXC."""
    exchange = "MEXC"

    try:
        _load_mexc_payment_methods()

        coin_id = MEXC_COIN_IDS.get(ASSET, MEXC_COIN_IDS["USDT"])
        base_url = "https://www.mexc.com/api/platform/p2p/api/market"
        all_ads = {"buy": [], "sell": []}

        for trade_type, side_name in [("BUY", "buy"), ("SELL", "sell")]:
            params = {
                "adsType": "1",
                "allowTrade": "false",
                "amount": "",
                "blockTrade": "false",
                "certifiedMerchant": "false",
                "coinId": coin_id,
                "countryCode": "",
                "currency": FIAT,
                "follow": "false",
                "haveTrade": "false",
                "page": "1",
                "payMethod": "",
                "tradeType": trade_type,
            }

            resp = _mexc_session.get(base_url, params=params, headers={
                "Accept": "application/json, text/plain, */*",
                "Referer": "https://www.mexc.com/buy-crypto/p2p",
            }, timeout=15)
            data = resp.json()

            ads_list = []
            items = data.get("data", []) if isinstance(data, dict) else []

            for item in items[:ADS_PER_PAGE]:
                price = _safe_float(item.get("price"))
                amount = _safe_float(item.get("availableQuantity"))
                min_amount = _safe_float(item.get("minTradeLimit"))
                max_amount = _safe_float(item.get("maxTradeLimit"))

                merchant_info = item.get("merchant", {})
                merchant = merchant_info.get("nickName", "Unknown") if isinstance(merchant_info, dict) else "Unknown"

                pay_ids = str(item.get("payMethod", "")).split(",")
                payments = [
                    MEXC_PAYMENT_METHODS.get(pid.strip(), f"Method {pid.strip()}")
                    for pid in pay_ids if pid.strip()
                ]

                ads_list.append({
                    "price": price,
                    "available_amount": amount,
                    "min_amount": min_amount,
                    "max_amount": max_amount,
                    "merchant": merchant,
                    "payment_methods": payments,
                })

            all_ads[side_name] = ads_list

        return _build_result(exchange, all_ads["buy"], all_ads["sell"])

    except Exception as e:
        return _error_result(exchange, e)


# ---------------------------------------------------------------------------
# Binance
# ---------------------------------------------------------------------------
def fetch_binance():
    """Fetch P2P ads from Binance."""
    url = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"
    exchange = "Binance"

    try:
        all_ads = {"buy": [], "sell": []}

        for trade_type in ["BUY", "SELL"]:
            payload = {
                "fiat": FIAT,
                "page": 1,
                "rows": ADS_PER_PAGE,
                "tradeType": trade_type,
                "asset": ASSET,
                "countries": [],
                "proMerchantAds": False,
                "shieldMerchantAds": False,
                "publisherType": None,
                "payTypes": [],
                "classifies": ["mass", "profession"],
            }

            resp = requests.post(url, json=payload, headers=HEADERS, timeout=15)
            data = resp.json()

            ads_list = []
            for item in data.get("data", []):
                adv = item.get("adv", {})
                advertiser = item.get("advertiser", {})
                price = _safe_float(adv.get("price"))
                amount = _safe_float(adv.get("surplusAmount") or adv.get("tradableQuantity"))
                min_amount = _safe_float(adv.get("minSingleTransAmount"))
                max_amount = _safe_float(adv.get("maxSingleTransAmount"))
                merchant = advertiser.get("nickName", "Unknown")
                payments = [
                    m.get("tradeMethodName", m.get("identifier", ""))
                    for m in adv.get("tradeMethods", [])
                ]

                ads_list.append({
                    "price": price,
                    "available_amount": amount,
                    "min_amount": min_amount,
                    "max_amount": max_amount,
                    "merchant": merchant,
                    "payment_methods": payments,
                })

            side = "buy" if trade_type == "BUY" else "sell"
            all_ads[side] = ads_list

        return _build_result(exchange, all_ads["buy"], all_ads["sell"])

    except Exception as e:
        return _error_result(exchange, e)


# ---------------------------------------------------------------------------
# Bybit — payment ID to name mapping for Ethiopian methods
# ---------------------------------------------------------------------------
BYBIT_PAYMENT_NAMES = {
    "629": "CBE", "630": "Tele Birr", "631": "Awash Bank",
    "632": "Bank of Abyssinia", "633": "Dashen Bank", "634": "Wegagen Bank",
    "635": "Hibret Bank", "636": "Nib Bank", "637": "Oromia Bank",
    "638": "Ebirr", "639": "Amole", "6": "Bank Transfer",
    "14": "Bank Transfer", "40": "Mobile Money", "41": "Mobile Money",
    "97": "Mobile Money", "178": "Bank Transfer",
}


def fetch_bybit():
    """Fetch P2P ads from Bybit."""
    url = "https://api2.bybit.com/fiat/otc/item/online"
    exchange = "Bybit"

    try:
        all_ads = {"buy": [], "sell": []}

        for side_code, side_name in [("1", "buy"), ("0", "sell")]:
            payload = {
                "userId": "",
                "tokenId": ASSET,
                "currencyId": FIAT,
                "payment": [],
                "side": side_code,
                "size": str(ADS_PER_PAGE),
                "page": "1",
                "amount": "",
                "authMaker": False,
                "canTrade": True,
            }

            resp = requests.post(url, json=payload, headers=HEADERS, timeout=15)
            data = resp.json()

            ads_list = []
            items = data.get("result", {}).get("items", [])
            for item in items:
                price = _safe_float(item.get("price"))
                amount = _safe_float(item.get("lastQuantity") or item.get("quantity"))
                min_amount = _safe_float(item.get("minAmount"))
                max_amount = _safe_float(item.get("maxAmount"))
                merchant = item.get("nickName", "Unknown")

                # Bybit payments are string IDs, not dicts
                raw_payments = item.get("payments", [])
                payments = []
                for p in raw_payments:
                    if isinstance(p, dict):
                        payments.append(p.get("paymentName", p.get("paymentType", str(p))))
                    else:
                        pid = str(p)
                        payments.append(BYBIT_PAYMENT_NAMES.get(pid, f"Method {pid}"))

                ads_list.append({
                    "price": price,
                    "available_amount": amount,
                    "min_amount": min_amount,
                    "max_amount": max_amount,
                    "merchant": merchant,
                    "payment_methods": payments,
                })

            all_ads[side_name] = ads_list

        return _build_result(exchange, all_ads["buy"], all_ads["sell"])

    except Exception as e:
        return _error_result(exchange, e)


# ---------------------------------------------------------------------------
# OKX
# ---------------------------------------------------------------------------
def fetch_okx():
    """Fetch P2P ads from OKX."""
    base_url = "https://www.okx.com/v3/c2c/tradingOrders/books"
    exchange = "OKX"

    try:
        all_ads = {"buy": [], "sell": []}

        for side in ["buy", "sell"]:
            params = {
                "quoteCurrency": FIAT.lower(),
                "baseCurrency": ASSET.lower(),
                "side": side,
                "paymentMethod": "all",
                "userType": "all",
                "showTrade": "false",
                "showFollow": "false",
                "showAlreadyTraded": "false",
                "isAbleFilter": "false",
                "receivingAds": "false",
            }

            get_headers = {
                "User-Agent": HEADERS["User-Agent"],
                "Accept": "application/json",
            }

            resp = requests.get(base_url, params=params, headers=get_headers, timeout=15)
            data = resp.json()

            ads_list = []
            # OKX returns data.buy[] for buy requests, data.sell[] for sell
            items = data.get("data", {}).get(side, [])

            for item in items[:ADS_PER_PAGE]:
                price = _safe_float(item.get("price"))
                amount = _safe_float(item.get("availableAmount"))
                min_amount = _safe_float(item.get("quoteMinAmountPerOrder"))
                max_amount = _safe_float(item.get("quoteMaxAmountPerOrder"))
                merchant = item.get("nickName", "Unknown")

                # OKX paymentMethods is a list of strings
                payments = []
                for p in item.get("paymentMethods", []):
                    if isinstance(p, str):
                        payments.append(p)
                    elif isinstance(p, dict):
                        payments.append(p.get("paymentMethod", ""))

                ads_list.append({
                    "price": price,
                    "available_amount": amount,
                    "min_amount": min_amount,
                    "max_amount": max_amount,
                    "merchant": merchant,
                    "payment_methods": payments,
                })

            # OKX side is from maker's perspective: "buy" = makers buying YOUR usdt
            mapped_side = "sell" if side == "buy" else "buy"
            all_ads[mapped_side] = ads_list

        return _build_result(exchange, all_ads["buy"], all_ads["sell"])

    except Exception as e:
        return _error_result(exchange, e)


# ---------------------------------------------------------------------------
# Fetch all exchanges
# ---------------------------------------------------------------------------
ALL_FETCHERS = [
    ("MEXC", fetch_mexc),
    ("Binance", fetch_binance),
    ("Bybit", fetch_bybit),
    ("OKX", fetch_okx),
]


def fetch_all():
    """Fetch P2P data from all exchanges. Returns list of result dicts."""
    results = []
    for name, fetcher in ALL_FETCHERS:
        print(f"  Fetching {name}...")
        results.append(fetcher())
    return results
