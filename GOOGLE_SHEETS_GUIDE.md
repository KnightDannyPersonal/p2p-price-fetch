# Google Sheets Integration

Fetch live P2P prices directly into Google Sheets cells using the `/api/price/simple` endpoint.

## Formula

```
=IMPORTDATA("https://p2p-price-fetch.onrender.com/api/price/simple?fiat=FIAT&exchange=EXCHANGE&field=FIELD")
```

## Parameters

| Parameter  | Required | Values                              | Default   |
|------------|----------|-------------------------------------|-----------|
| `fiat`     | No       | `ETB`, `USD`, `EUR`                 | `ETB`     |
| `exchange` | No       | `MEXC`, `Binance`, `Bybit`, `OKX`   | First available |
| `field`    | No       | `best_buy`, `best_sell`, `avg_buy`, `avg_sell` | `best_sell` |

## Examples

**Best sell price on Binance for USDT/ETB:**
```
=IMPORTDATA("https://p2p-price-fetch.onrender.com/api/price/simple?fiat=ETB&exchange=Binance&field=best_sell")
```

**Best buy price on MEXC for USDT/USD:**
```
=IMPORTDATA("https://p2p-price-fetch.onrender.com/api/price/simple?fiat=USD&exchange=MEXC&field=best_buy")
```

**Average sell price on OKX for USDT/EUR:**
```
=IMPORTDATA("https://p2p-price-fetch.onrender.com/api/price/simple?fiat=EUR&exchange=OKX&field=avg_sell")
```

**Best sell from any exchange (returns first available):**
```
=IMPORTDATA("https://p2p-price-fetch.onrender.com/api/price/simple?fiat=ETB&field=best_sell")
```

## Notes

- The endpoint returns a single plain-text number (e.g. `191.02`), which Google Sheets reads as a numeric value.
- Returns `N/A` if no data is available for the given combination.
- Data is refreshed every 30 seconds on the server. Google Sheets refreshes `IMPORTDATA` roughly every hour, or when you reopen the sheet.
- USD and EUR pairs are filtered to Dukascopy and Payoneer payment methods only.
