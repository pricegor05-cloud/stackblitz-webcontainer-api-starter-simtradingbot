import yfinance as yf
import time
import random

STOCKS = [
    "AAPL","TSLA","NVDA","AMD","MSFT",
    "AMZN","META","GOOGL","NFLX","PLTR"
]

# =========================
# 🧠 CACHE (LAST GOOD DATA)
# =========================
cache = {}

# =========================
# 🔵 SYNTHETIC FALLBACK ENGINE
# =========================
def synthetic_market():
    out = {}

    for s in STOCKS:
        last = cache.get(s, {"price": 100})

        drift = random.uniform(-0.3, 0.3)
        price = max(1, last["price"] * (1 + drift / 100))

        trend = "UP" if drift > 0 else "DOWN"
        vol = random.uniform(0.5, 1.5)

        out[s] = {
            "price": price,
            "trend": trend,
            "vol": vol,
            "momentum": drift / 100
        }

    return out


# =========================
# 🟢 LIVE MARKET (PRIMARY)
# =========================
def live_market():
    try:
        data = yf.download(
            tickers=" ".join(STOCKS),
            period="1d",
            interval="1m",
            group_by="ticker",
            progress=False,
            threads=False
        )

        if data is None or len(data) == 0:
            return None

        out = {}

        for s in STOCKS:
            try:
                if s not in data:
                    continue

                df = data[s].dropna()
                if df.empty or len(df) < 10:
                    continue

                price = float(df["Close"].iloc[-1])
                prev = float(df["Close"].iloc[-5])

                vol_series = df["Volume"].dropna()
                vol = 1.0

                if len(vol_series) > 5:
                    avg_vol = vol_series.mean()
                    vol = float(vol_series.iloc[-1]) / avg_vol if avg_vol != 0 else 1.0

                momentum = (price - prev) / prev

                out[s] = {
                    "price": price,
                    "trend": "UP" if momentum > 0 else "DOWN",
                    "vol": float(vol),
                    "momentum": float(momentum)
                }

            except:
                continue

        return out if len(out) > 0 else None

    except Exception:
        return None


# =========================
# 🧠 LEVEL 2 MARKET ENGINE
# =========================
def market():
    global cache

    data = live_market()

    # 🟢 CASE 1: LIVE WORKING
    if data:
        cache = data
        return data

    # 🟡 CASE 2: USE CACHE
    if cache:
        print("🟡 MARKET FALLBACK: using cached data")
        return cache

    # 🔵 CASE 3: SYNTHETIC MODE
    print("🔵 MARKET SYNTHETIC MODE ACTIVE")
    return synthetic_market()