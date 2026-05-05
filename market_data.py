import yfinance as yf
import pandas as pd

STOCKS = ["AAPL", "TSLA", "NVDA", "AMD", "MSFT"]

def market():
    try:
        data = yf.download(
            tickers=" ".join(STOCKS),
            period="1d",
            interval="1m",
            group_by="ticker",
            progress=False,
            threads=False
        )

        out = {}

        for s in STOCKS:
            try:
                if s not in data:
                    continue

                df = data[s]

                if df is None or df.empty:
                    continue

                if len(df["Close"]) < 5:
                    continue

                price = float(df["Close"].iloc[-1])
                prev = float(df["Close"].iloc[-5])

                vol_series = df["Volume"].dropna()

                vol = 1.0
                if len(vol_series) > 0 and vol_series.mean() != 0:
                    vol = float(vol_series.iloc[-1]) / float(vol_series.mean())

                out[s] = {
                    "price": price,
                    "trend": "UP" if price > prev else "DOWN",
                    "vol": float(vol)
                }

            except Exception:
                continue

        return out

    except Exception as e:
        print("MARKET ERROR:", e)
        return {}