import yfinance as yf
import pandas as pd

STOCKS = [
    "AAPL", "TSLA", "NVDA", "AMD", "MSFT",
    "META", "AMZN", "GOOGL", "NFLX",
    "SPY", "QQQ", "IWM","RBLX","AVGO"
]

# =========================
# 🧠 SCORING ENGINE
# =========================
def score_stock(price, prev, vol, volatility):
    trend_score = 1 if price > prev else -1

    # normalize volume impact
    vol_score = min(vol, 3.0)  # cap extreme spikes

    # volatility sweet spot (not too low, not crazy high)
    vol_adjust = 1.0
    if 0.01 < volatility < 0.05:
        vol_adjust = 1.3
    elif volatility >= 0.08:
        vol_adjust = 0.7

    score = (trend_score * 1.5) + (vol_score * 0.7) * vol_adjust

    return score


# =========================
# 🚀 SCANNER V3
# =========================
def market(top_n=8):
    try:
        data = yf.download(
            tickers=" ".join(STOCKS),
            period="1d",
            interval="1m",
            group_by="ticker",
            progress=False,
            threads=False
        )

        scored = []

        for s in STOCKS:
            try:
                if s not in data:
                    continue

                df = data[s]

                if df is None or df.empty:
                    continue

                if len(df) < 20:
                    continue

                close = df["Close"].dropna()
                volume = df["Volume"].dropna()

                if len(close) < 10:
                    continue

                price = float(close.iloc[-1])
                prev = float(close.iloc[-5])

                # volume strength
                vol = 1.0
                if len(volume) > 5 and volume.mean() > 0:
                    vol = float(volume.iloc[-1]) / float(volume.mean())

                # volatility
                returns = close.pct_change().dropna()
                volatility = float(returns.std()) if len(returns) > 2 else 0.0

                score = score_stock(price, prev, vol, volatility)

                scored.append((s, score, {
                    "price": price,
                    "trend": "UP" if price > prev else "DOWN",
                    "vol": float(vol),
                    "volatility": float(volatility),
                    "score": float(score)
                }))

            except Exception:
                continue

        # =========================
        # 🎯 SELECT TOP STOCKS
        # =========================
        scored.sort(key=lambda x: x[1], reverse=True)
        top = scored[:top_n]

        out = {}
        for s, _, data in top:
            out[s] = data

        return out

    except Exception as e:
        print("SCANNER ERROR:", e)
        return {}