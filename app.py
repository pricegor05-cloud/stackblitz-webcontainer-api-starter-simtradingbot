from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import threading
import time
import random
from engine import HeadTrader

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
# CORE SYSTEM
# =========================
portfolio = Portfolio(5000)
learn = LearningSystem()
risk = Risk()
trade_manager = TradeManager()
evolver = EvolutionEngine(learn)
head_trader = HeadTrader()

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
# EVOLUTION (SAFE VERSION)
# =========================
def evolve_agents():
    global agents

    new_agents = []
    updated_scores = learn.agent_score.copy()

    for name, agent in agents:
        score = learn.agent_score.get(name, 1.0)

        # keep strong
        if score > 1.2:
            new_agents.append((name, agent))

        # remove weak
        elif score < 0.8:
            continue

        # mutate medium
        else:
            mutated = evolver.mutate(agent)
            new_name = name + "_v2_" + str(random.randint(100, 999))
            new_agents.append((new_name, mutated))
            updated_scores[new_name] = score * random.uniform(0.95, 1.05)

    # prevent explosion
    new_agents = sorted(
        new_agents,
        key=lambda x: learn.agent_score.get(x[0], 1.0),
        reverse=True
    )[:MAX_AGENTS]

    # CLEAN SCORE MAP (IMPORTANT FIX)
    clean = {}
    for name, _ in new_agents:
        clean[name] = updated_scores.get(name, 1.0)

    learn.agent_score = clean

    return new_agents


# =========================
# TRADING LOOP
# =========================
def trading_loop():
    global latest_state, agents, cycle

    while True:
        mkt = market()
        if not mkt:
            time.sleep(2)
            continue

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
            # 🟡 RISK ENGINE FIRST
            allowed = risk.approve(portfolio, action, conf)
            # 🧠 HEAD TRADER FINAL AUTHORITY (STEP 3)
            if allowed:
                allowed = head_trader.approve_trade(
                    symbol,
                    action,
                    conf,
                    data,
                    portfolio
    )

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
                "price": round(price, 2)
            })

        cycle += 1
        if cycle % 5 == 0:
            agents = evolve_agents()

        latest_state = {
            "equity": round(portfolio.equity, 2),
            "cash": round(portfolio.cash, 2),
            "positions": portfolio.positions,
            "agent_scores": learn.agent_score,
            "active_agents": [a[0] for a in agents],
            "trades": trades[-20:]
        }

        time.sleep(5)


threading.Thread(target=trading_loop, daemon=True).start()


# =========================
# ROUTES
# =========================
@app.get("/")
def home():
    return {"status": "running"}


@app.get("/state")
def state():
    return latest_state


# =========================
# FIXED UI (NO STRING BUGS)
# =========================
@app.get("/ui", response_class=HTMLResponse)
def ui():
    return """
    <html>
    <head>
        <title>AI Trading Terminal</title>
        <style>
            body { background:#0b0f14; color:white; font-family:monospace; }
            .box { background:#111827; margin:10px; padding:10px; border-radius:8px; }
        </style>
    </head>

    <body>
        <h2>LIVE AI TRADING TERMINAL</h2>

        <div class="box">
            <h3>Equity: <span id="eq">...</span></h3>
            <h3>Cash: <span id="cash">...</span></h3>
        </div>

        <div class="box">
            <h3>Agents</h3>
            <pre id="agents"></pre>
        </div>

        <div class="box">
            <h3>Trades</h3>
            <pre id="trades"></pre>
        </div>

        <script>
            async function load(){
                const r = await fetch("/state");
                const d = await r.json();

                document.getElementById("eq").innerText = d.equity;
                document.getElementById("cash").innerText = d.cash;

                document.getElementById("agents").innerText =
                    JSON.stringify(d.agent_scores || {}, null, 2);

                document.getElementById("trades").innerText =
                    JSON.stringify(d.trades || [], null, 2);
            }

            setInterval(load, 1500);
            load();
        </script>
    </body>
    </html>
    """