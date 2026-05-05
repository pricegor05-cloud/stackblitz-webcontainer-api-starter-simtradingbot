from fastapi import FastAPI
from fastapi.responses import HTMLResponse, FileResponse
import threading
import time
import os
import random

from engine import (
    Portfolio,
    MomentumAI,
    MeanReversionAI,
    BreakoutAI,
    SentimentAI,
    LearningSystem,
    Risk,
    TradeManager,
    EvolutionEngine,
    decide
)

from market_data import market

app = FastAPI()

# =========================
# 🏦 CORE SYSTEM
# =========================
portfolio = Portfolio(5000)
learn = LearningSystem()
risk = Risk()
trade_manager = TradeManager()

evolver = EvolutionEngine(learn)

agents = [
    ("MomentumAI", MomentumAI()),
    ("MeanReversionAI", MeanReversionAI()),
    ("BreakoutAI", BreakoutAI()),
    ("SentimentAI", SentimentAI())
]

latest_state = {}

cycle = 0
MAX_AGENTS = 10


# =========================
# 🧬 EVOLUTION ENGINE (STEP 3 FIXED)
# =========================
def evolve_agents():
    global agents, learn, evolver

    new_agents = []
    updated_scores = learn.agent_score.copy()

    for name, agent in agents:
        score = learn.agent_score.get(name, 1.0)

        if score > 1.2:
            new_agents.append((name, agent))

        elif score < 0.8:
            continue

        else:
            mutated = evolver.mutate(agent)
            new_name = name + "_v2"
            new_agents.append((new_name, mutated))
            updated_scores[new_name] = score * random.uniform(0.9, 1.1)

    new_agents = sorted(
        new_agents,
        key=lambda x: learn.agent_score.get(x[0], 1.0),
        reverse=True
    )[:MAX_AGENTS]

    clean_scores = {}
    for name, _ in new_agents:
        clean_scores[name] = updated_scores.get(name, 1.0)

    learn.agent_score = clean_scores

    return new_agents


# =========================
# 🚀 TRADING LOOP
# =========================
def trading_loop():
    global latest_state, agents, cycle

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

            price = data["price"]
            pnl = 0

            if allowed:
                if action == "BUY":
                    portfolio.buy(symbol, price, conf)
                elif action == "SELL":
                    portfolio.sell(symbol, price)

            if trade_manager.check_exit(portfolio, symbol, price):
                portfolio.sell(symbol, price)
                pnl = 1

            for name, _ in agents:
                learn.update(name, pnl)

            trades.append({
                "symbol": symbol,
                "action": action,
                "confidence": round(conf, 2),
                "allowed": allowed,
                "price": price
            })

        # 🧬 EVOLVE EVERY 5 CYCLES
        cycle += 1
        if cycle % 5 == 0:
            agents = evolve_agents()

        latest_state = {
            "equity": round(portfolio.equity, 2),
            "cash": round(portfolio.cash, 2),
            "positions": portfolio.positions,
            "agent_scores": learn.agent_score,
            "active_agents": [a[0] for a in agents],
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
            <a href="/state" style="color:cyan">View Live Data</a>
        </div>
    </body>
    </html>
    """


@app.get("/ui")
def ui():
    file_path = "frontend.html"
    if os.path.exists(file_path):
        return FileResponse(file_path)
    return {"error": "frontend.html not found"}