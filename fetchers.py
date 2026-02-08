"""P2P price fetchers for Binance, Bybit, OKX, and MEXC."""

import json
import time
from datetime import datetime, timezone, timedelta
import requests
from curl_cffi import requests as curl_requests
from config import ASSET, ADS_PER_PAGE, PAIRS

TZ_OFFSET = timezone(timedelta(hours=3))


def _now(fmt="%Y-%m-%d %H:%M:%S"):
    return datetime.now(TZ_OFFSET).strftime(fmt)


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

# Bybit payment ID -> name mapping
BYBIT_PAYMENT_NAMES = {
    "629": "CBE", "630": "Tele Birr", "631": "Awash Bank",
    "632": "Bank of Abyssinia", "633": "Dashen Bank", "634": "Wegagen Bank",
    "635": "Hibret Bank", "636": "Nib Bank", "637": "Oromia Bank",
    "638": "Ebirr", "639": "Amole", "6": "Bank Transfer",
    "14": "Bank Transfer", "40": "Mobile Money", "41": "Mobile Money",
    "97": "Mobile Money", "178": "Bank Transfer",
    "582": "Payoneer", "62": "Payoneer",
}

# Payment method name mappings per exchange (generic name -> exchange-specific identifier)
BINANCE_PAY_METHODS = {
    "Dukascopy": "DukascopyBank",
    "Payoneer": "Payoneer",
}

OKX_PAY_METHODS = {
    "Dukascopy": "Dukascopy",
    "Payoneer": "Payoneer",
}


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
        "last_updated": _now(),
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
        "last_updated": _now(),
        "error": str(error_msg),
    }


# ---------------------------------------------------------------------------
# MEXC — uses curl_cffi for browser-like TLS fingerprint
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


def _mexc_pay_filter_ids(pay_filter):
    """Find MEXC payment method IDs matching filter names."""
    if not pay_filter or not MEXC_PAYMENT_METHODS:
        return ""
    matching_ids = []
    for pm_id, pm_name in MEXC_PAYMENT_METHODS.items():
        for f in pay_filter:
            if f.lower() in pm_name.lower():
                matching_ids.append(pm_id)
                break
    return ",".join(matching_ids)


def fetch_mexc(fiat="ETB", pay_filter=None):
    """Fetch P2P ads from MEXC."""
    exchange = "MEXC"
    pay_filter = pay_filter or []

    try:
        _load_mexc_payment_methods()

        coin_id = MEXC_COIN_IDS.get(ASSET, MEXC_COIN_IDS["USDT"])
        base_url = "https://www.mexc.com/api/platform/p2p/api/market"
        all_ads = {"buy": [], "sell": []}
        pay_method_param = _mexc_pay_filter_ids(pay_filter)

        # MEXC tradeType is from maker perspective: BUY = maker buying = we sell
        for trade_type, side_name in [("BUY", "sell"), ("SELL", "buy")]:
            params = {
                "adsType": "0",
                "allowTrade": "true",
                "amount": "",
                "blockTrade": "false",
                "certifiedMerchant": "false",
                "coinId": coin_id,
                "countryCode": "",
                "currency": fiat,
                "follow": "false",
                "haveTrade": "false",
                "page": "1",
                "payMethod": pay_method_param,
                "tradeType": trade_type,
            }

            resp = _mexc_session.get(base_url, params=params, headers={
                "Accept": "application/json, text/plain, */*",
                "Referer": "https://www.mexc.com/buy-crypto/p2p",
            }, timeout=15)
            data = resp.json()

            ads_list = []
            raw_items = data.get("data", []) if isinstance(data, dict) else []
            # Skip ads where merchant trade is disabled (shows "Limited")
            items = [i for i in raw_items if i.get("merchantTradeEnable", True)]

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
def fetch_binance(fiat="ETB", pay_filter=None):
    """Fetch P2P ads from Binance."""
    url = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"
    exchange = "Binance"
    pay_filter = pay_filter or []

    # Map generic names to Binance-specific identifiers
    pay_types = [BINANCE_PAY_METHODS.get(p, p) for p in pay_filter] if pay_filter else []

    try:
        all_ads = {"buy": [], "sell": []}

        for trade_type in ["BUY", "SELL"]:
            payload = {
                "fiat": fiat,
                "page": 1,
                "rows": ADS_PER_PAGE,
                "tradeType": trade_type,
                "asset": ASSET,
                "countries": [],
                "proMerchantAds": False,
                "shieldMerchantAds": False,
                "publisherType": None,
                "payTypes": pay_types,
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
# Bybit
# ---------------------------------------------------------------------------
def fetch_bybit(fiat="ETB", pay_filter=None):
    """Fetch P2P ads from Bybit."""
    url = "https://api2.bybit.com/fiat/otc/item/online"
    exchange = "Bybit"
    pay_filter = pay_filter or []

    try:
        all_ads = {"buy": [], "sell": []}

        for side_code, side_name in [("1", "buy"), ("0", "sell")]:
            payload = {
                "userId": "",
                "tokenId": ASSET,
                "currencyId": fiat,
                "payment": pay_filter if pay_filter else [],
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
            raw_items = (data.get("result") or {}).get("items") or []
            # Skip ads where merchant requires taker to have posted their own ad
            # (these show as "ineligible" for most users on Bybit)
            items = [
                i for i in raw_items
                if not (i.get("tradingPreferenceSet") or {}).get("hasUnPostAd")
            ]
            for item in items:
                price = _safe_float(item.get("price"))
                amount = _safe_float(item.get("lastQuantity") or item.get("quantity"))
                min_amount = _safe_float(item.get("minAmount"))
                max_amount = _safe_float(item.get("maxAmount"))
                merchant = item.get("nickName", "Unknown")

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
def fetch_okx(fiat="ETB", pay_filter=None):
    """Fetch P2P ads from OKX."""
    base_url = "https://www.okx.com/v3/c2c/tradingOrders/books"
    exchange = "OKX"
    pay_filter = pay_filter or []

    # OKX paymentMethod param: comma-separated or "all"
    pay_method_param = ",".join(
        OKX_PAY_METHODS.get(p, p) for p in pay_filter
    ) if pay_filter else "all"

    try:
        all_ads = {"buy": [], "sell": []}

        for side in ["buy", "sell"]:
            params = {
                "quoteCurrency": fiat.lower(),
                "baseCurrency": ASSET.lower(),
                "side": side,
                "paymentMethod": pay_method_param,
                "userType": "all",
                "showTrade": "false",
                "showFollow": "false",
                "showAlreadyTraded": "false",
                "isAbleFilter": "true",
                "receivingAds": "false",
            }

            get_headers = {
                "User-Agent": HEADERS["User-Agent"],
                "Accept": "application/json",
            }

            resp = requests.get(base_url, params=params, headers=get_headers, timeout=15)
            data = resp.json()

            ads_list = []
            items = data.get("data", {}).get(side, [])

            for item in items[:ADS_PER_PAGE]:
                price = _safe_float(item.get("price"))
                amount = _safe_float(item.get("availableAmount"))
                min_amount = _safe_float(item.get("quoteMinAmountPerOrder"))
                max_amount = _safe_float(item.get("quoteMaxAmountPerOrder"))
                merchant = item.get("nickName", "Unknown")

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
# Fetch all exchanges for a single pair
# ---------------------------------------------------------------------------
ALL_FETCHERS = [
    ("MEXC", fetch_mexc),
    ("Binance", fetch_binance),
    ("Bybit", fetch_bybit),
    ("OKX", fetch_okx),
]


def fetch_all(fiat="ETB", pay_filter=None):
    """Fetch P2P data from all exchanges for a given fiat. Returns list of result dicts."""
    pay_filter = pay_filter or []
    results = []
    for name, fetcher in ALL_FETCHERS:
        print(f"  Fetching {name} ({fiat})...")
        results.append(fetcher(fiat=fiat, pay_filter=pay_filter))
    return results


def fetch_all_pairs():
    """Fetch P2P data for all configured currency pairs. Returns dict keyed by fiat."""
    all_data = {}
    for pair in PAIRS:
        fiat = pair["fiat"]
        pay_filter = pair.get("pay_filter", [])
        print(f"[{fiat}] Fetching all exchanges...")
        all_data[fiat] = {
            "results": fetch_all(fiat=fiat, pay_filter=pay_filter),
            "last_refresh": _now(),
        }
    return all_data
