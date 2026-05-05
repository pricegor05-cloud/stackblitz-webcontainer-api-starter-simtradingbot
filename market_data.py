import yfinance as yf
import pandas as pd

STOCKS = ["AAPL", "TSLA", "NVDA", "AMD", "MSFT"]

# =========================
# 🧠 MARKET ENGINE (UPGRADED)
# =========================
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

                if len(df) < 10:
                    continue

                close = df["Close"].dropna()
                vol_data = df["Volume"].dropna()

                if len(close) < 10:
                    continue

                price = float(close.iloc[-1])
                prev = float(close.iloc[-5])

                # =========================
                # 📊 VOLUME STRENGTH (FIXED)
                # =========================
                vol = 1.0
                if len(vol_data) > 5:
                    avg_vol = vol_data.mean()
                    if avg_vol > 0:
                        vol = float(vol_data.iloc[-1]) / float(avg_vol)

                # =========================
                # ⚡ VOLATILITY FILTER
                # =========================
                returns = close.pct_change().dropna()
                volatility = float(returns.std()) if len(returns) > 2 else 0.0

                # =========================
                # 🧠 FINAL SIGNAL BUILD
                # =========================
                out[s] = {
                    "price": price,
                    "trend": "UP" if price > prev else "DOWN",
                    "vol": float(vol),
                    "volatility": float(volatility)
                }

            except Exception:
                continue

        return out

    except Exception as e:
        print("MARKET ERROR:", e)
        return {}