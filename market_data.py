import yfinance as yf

STOCKS = ["AAPL", "TSLA", "NVDA", "AMD", "MSFT","RBLX","AVGO","F","ZEC","META",
"SOFI"]

def market():
    try:
        data = yf.download(
            tickers=" ".join(STOCKS),
            period="1d",
            interval="1m",
            group_by="ticker",
            progress=False
        )
    except:
        return {}

    out = {}

    for s in STOCKS:
        try:
            df = data[s].dropna()

            if len(df) < 5:
                continue

            price = df["Close"].iloc[-1]
            prev = df["Close"].iloc[-5]

            trend = "UP" if price > prev else "DOWN"
            vol = float(df["Volume"].iloc[-1]) / max(1, df["Volume"].mean())

            out[s] = {
                "price": float(price),
                "trend": trend,
                "vol": float(vol)
            }

        except:
            continue

    return out