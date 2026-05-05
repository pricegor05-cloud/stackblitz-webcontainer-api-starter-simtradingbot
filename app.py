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
        <title>Institutional AI Trading Terminal</title>
        <meta http-equiv="refresh" content="2">

        <style>
            body {
                margin: 0;
                background: #0b0f14;
                color: #d1d5db;
                font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
            }

            .topbar {
                background: #111827;
                padding: 12px 20px;
                font-size: 14px;
                border-bottom: 1px solid #1f2937;
            }

            .grid {
                display: grid;
                grid-template-columns: 1fr 1fr 1fr;
                gap: 12px;
                padding: 12px;
            }

            .panel {
                background: #111827;
                border: 1px solid #1f2937;
                border-radius: 8px;
                padding: 12px;
                height: 280px;
                overflow: auto;
            }

            .title {
                font-size: 12px;
                color: #9ca3af;
                margin-bottom: 8px;
            }

            .value {
                font-size: 18px;
                color: #22c55e;
            }

            .red { color: #ef4444; }
            .yellow { color: #facc15; }
            .cyan { color: #22d3ee; }

            table {
                width: 100%;
                font-size: 12px;
            }

            td {
                padding: 4px 0;
                border-bottom: 1px solid #1f2937;
            }

            .footer {
                padding: 10px 20px;
                font-size: 11px;
                color: #6b7280;
                border-top: 1px solid #1f2937;
            }
        </style>
    </head>

    <body>

        <div class="topbar">
            🏦 AI HEDGE FUND TERMINAL | LIVE SIMULATION | REFRESH 2s
        </div>

        <div class="grid">

            <div class="panel">
                <div class="title">PORTFOLIO EQUITY</div>
                <div class="value">$""" + str(latest_state.get("equity", 0)) + """</div>

                <div class="title" style="margin-top:10px;">CASH</div>
                <div class="value cyan">$""" + str(latest_state.get("cash", 0)) + """</div>
            </div>

            <div class="panel">
                <div class="title">ACTIVE AGENTS</div>
                <table>
                """ + "".join([
                    f"<tr><td>{k}</td><td class='yellow'>{v:.2f}</td></tr>"
                    for k, v in (latest_state.get("agent_scores") or {}).items()
                ]) + """
                </table>
            </div>

            <div class="panel">
                <div class="title">ACTIVE STRATEGIES</div>
                """ + "<br>".join(latest_state.get("active_agents", [])) + """
            </div>

        </div>

        <div class="grid">

            <div class="panel" style="grid-column: span 3;">
                <div class="title">TRADE EXECUTION FEED</div>
                <table>
                """ + "".join([
                    f"<tr>"
                    f"<td>{t['symbol']}</td>"
                    f"<td>{t['action']}</td>"
                    f"<td class='cyan'>{t['confidence']}</td>"
                    f"<td>{t['price']:.2f}</td>"
                    f"</tr>"
                    for t in (latest_state.get("trades") or [])[-15:]
                ]) + """
                </table>
            </div>

        </div>

        <div class="footer">
            AI Hedge Fund Simulation Engine | Institutional Terminal UI | Paper Trading Mode
        </div>

    </body>
    </html>
    """


@app.get("/ui", response_class=HTMLResponse)
def ui():
    return """
    <html>
    <head>
        <title>AI Trading Terminal v2</title>

        <style>
            body {
                background: #0b0f14;
                color: #d1d5db;
                font-family: monospace;
                margin: 0;
            }

            .top {
                padding: 10px;
                background: #111827;
                border-bottom: 1px solid #1f2937;
            }

            .grid {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 10px;
                padding: 10px;
            }

            .box {
                background: #111827;
                padding: 10px;
                border-radius: 6px;
                border: 1px solid #1f2937;
            }

            .cyan { color: #22d3ee; }
        </style>
    </head>

    <body>
        <div class="top">🏦 LIVE AI HEDGE FUND TERMINAL</div>

        <div class="grid">
            <div class="box">
                <div>Equity</div>
                <h2 id="equity">...</h2>

                <div>Cash</div>
                <h3 id="cash">...</h3>
            </div>

            <div class="box">
                <div>Agents</div>
                <pre id="agents"></pre>
            </div>
        </div>

        <div class="box" style="margin:10px;">
            <div>Trades</div>
            <pre id="trades"></pre>
        </div>

        <script>
            async function load() {
                const res = await fetch("/state");
                const data = await res.json();

                document.getElementById("equity").innerText = data.equity;
                document.getElementById("cash").innerText = data.cash;

                document.getElementById("agents").innerText =
                    JSON.stringify(data.agent_scores, null, 2);

                document.getElementById("trades").innerText =
                    JSON.stringify(data.trades.slice(-10), null, 2);
            }

            setInterval(load, 1500);
            load();
        </script>

    </body>
    </html>
    """