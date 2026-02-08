"""Quick test script for P2P fetchers."""
from fetchers import fetch_mexc, fetch_binance, fetch_bybit, fetch_okx

def test(name, func):
    print(f"=== {name} ===")
    r = func()
    if r['error']:
        print(f"  ERROR: {r['error']}")
    else:
        print(f"  Best Buy:  {r['best_buy_price']} ETB")
        print(f"  Best Sell: {r['best_sell_price']} ETB")
        print(f"  Avg Buy:   {r['avg_buy_price']} ETB")
        print(f"  Avg Sell:  {r['avg_sell_price']} ETB")
        print(f"  Ads:       {r['buy_count']} buy, {r['sell_count']} sell")
        if r['buy_ads']:
            ad = r['buy_ads'][0]
            print(f"  Top buy:   {ad['price']} by {ad['merchant']} via {ad['payment_methods']}")
        if r['sell_ads']:
            ad = r['sell_ads'][0]
            print(f"  Top sell:  {ad['price']} by {ad['merchant']} via {ad['payment_methods']}")
    print()

print("Testing all P2P fetchers for USDT/ETB...\n")
test("MEXC (Priority)", fetch_mexc)
test("Binance", fetch_binance)
test("Bybit", fetch_bybit)
test("OKX", fetch_okx)
