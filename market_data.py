import yfinance as yf
import pandas as pd

STOCKS = ["AAPL", "TSLA", "NVDA", "AMD", "MSFT"]

def market():
    data = yf.download(
        tickers=" ".join(STOCKS),
        period="1d",
        interval="1m",
        group_by="ticker",
        progress=False
    )

    out = {}

    for s in STOCKS:
        try:
            df = data[s]

            price = df["Close"].iloc[-1]
            prev = df["Close"].iloc[-5]

            # simple derived signals
            trend = "UP" if price > prev else "DOWN"
            vol = float(df["Volume"].iloc[-1]) / df["Volume"].mean()

            out[s] = {
                "price": float(price),
                "trend": trend,
                "vol": float(vol)
            }

        except:
            continue

    return out