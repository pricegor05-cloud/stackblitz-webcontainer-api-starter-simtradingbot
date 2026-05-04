from fastapi import FastAPI
from fastapi.responses import HTMLResponse, FileResponse
import threading
import time
import os

from engine import (
    Portfolio,
    MomentumAI,
    MeanReversionAI,
    BreakoutAI,
    SentimentAI,
    LearningSystem,
    Risk,
    decide
)

from market_data import market

app = FastAPI()

portfolio = Portfolio(5000)
learn = LearningSystem()
risk = Risk()

agents = [
    ("MomentumAI", MomentumAI()),
    ("MeanReversionAI", MeanReversionAI()),
    ("BreakoutAI", BreakoutAI()),
    ("SentimentAI", SentimentAI())
]

latest_state = {}

# =========================
# 🚀 TRADING LOOP
# =========================
def trading_loop():
    global latest_state

    while True:
        mkt = market()
        prices = {s: mkt[s]["price"] for s in mkt}

        portfolio.update(prices)

        trades = []

        for symbol, data in mkt.items():

            votes = []
            weights = []

            for name, agent in agents:
                action, conf = agent.decide(data)
                votes.append((action, conf))
                weights.append(learn.weight(name))

            action, conf = decide(votes, weights)
            allowed = risk.approve(portfolio, action, conf)

            pnl = 0

            if allowed:
                price = data["price"]

                if action == "BUY":
                    portfolio.buy(symbol, price)
                    pnl = 1
                elif action == "SELL":
                    portfolio.sell(symbol, price)
                    pnl = 1

                for name, _ in agents:
                    learn.update(name, pnl)

            trades.append({
                "symbol": symbol,
                "action": action,
                "confidence": round(conf, 2),
                "allowed": allowed,
                "price": data["price"]
            })

        latest_state = {
            "equity": round(portfolio.equity, 2),
            "cash": round(portfolio.cash, 2),
            "positions": portfolio.positions,
            "agent_scores": learn.agent_score,
            "trades": trades
        }

        time.sleep(30)

threading.Thread(target=trading_loop, daemon=True).start()


# =========================
# 🌐 ROUTES
# =========================
@app.get("/")
def home():
    return {"status": "AI Hedge Fund Running"}


@app.get("/state")
def state():
    return latest_state


# =========================
# 📊 INLINE DASHBOARD
# =========================
@app.get("/dashboard", response_class=HTMLResponse)
def dashboard():
    return """
    <html>
    <head>
        <title>AI Hedge Fund</title>
        <meta http-equiv="refresh" content="5">
        <style>
            body { background:#0f0f0f; color:white; font-family:Arial; }
            .box { background:#1e1e1e; padding:20px; margin:10px; border-radius:10px; }
        </style>
    </head>
    <body>
        <h1>🏦 AI Hedge Fund Simulator</h1>

        <div class="box">
            <h2>Live API</h2>
            <a href="/state" style="color:cyan">View Live Data</a>
        </div>

        <div class="box">
            <p>Auto updates every 30s</p>
        </div>
    </body>
    </html>
    """


# =========================
# 🟢 EXTERNAL FRONTEND LOADER (NEW FIX)
# =========================
@app.get("/ui")
def ui():
    file_path = "frontend.html"

    if os.path.exists(file_path):
        return FileResponse(file_path)

    return {"error": "frontend.html not found"}