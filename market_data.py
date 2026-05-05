import yfinance as yf

STOCKS = ["AAPL","TSLA","NVDA","MSFT","AMZN","META"]

def market():
    try:
        data = yf.download(" ".join(STOCKS), period="1d", interval="1m", progress=False)

        out = {}

        for s in STOCKS:
            if s not in data:
                continue

            df = data[s].dropna()
            if len(df) < 10:
                continue

            price = float(df["Close"].iloc[-1])
            prev = float(df["Close"].iloc[-5])

            vol = 1.0
            if "Volume" in df:
                avg = df["Volume"].mean()
                vol = float(df["Volume"].iloc[-1]) / avg if avg else 1.0

            out[s] = {
                "price": price,
                "trend": "UP" if price > prev else "DOWN",
                "vol": float(vol)
            }

        return out

    except:
        return {}