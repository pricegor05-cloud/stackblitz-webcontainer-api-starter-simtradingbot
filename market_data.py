import yfinance as yf
import time

STOCKS = [
    "AAPL","TSLA","NVDA","AMD","MSFT",
    "AMZN","META","GOOGL","NFLX","PLTR"
]

def market():
    try:
        data = yf.download(
            tickers=" ".join(STOCKS),
            period="1d",
            interval="1m",
            group_by="ticker",
            progress=False,
            threads=False,
            auto_adjust=True
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

                vol = 1.0
                vol_series = df["Volume"].dropna()

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

        # IMPORTANT FIX: avoid empty return bursts
        if len(out) == 0:
            return None

        return out

    except Exception as e:
        print("MARKET ERROR:", e)
        return None