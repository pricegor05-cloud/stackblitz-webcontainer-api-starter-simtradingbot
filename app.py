from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
import threading, time, random, asyncio

from engine import *
from stream_market import market

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

tracker = PerformanceTracker()
memory = TradeMemory()
compound = CompoundEngine(portfolio)

agents = [
    ("MomentumAI", MomentumAI()),
    ("MeanReversionAI", MeanReversionAI()),
    ("BreakoutAI", BreakoutAI()),
    ("SentimentAI", SentimentAI())
]

latest_state = {
    "equity": 5000,
    "cash": 5000,
    "agent_scores": {},
    "active_agents": [],
    "chop_zone": False,
    "heartbeat": time.time(),
    "trades": []
}

cycle = 0
clients = []
last_heartbeat = {"t": time.time()}

# =========================
# 📊 DAY TRADING CONTROLS (NEW)
# =========================
daily_stats = {
    "trades": 0,
    "start_equity": 5000,
    "profit": 0
}

MAX_TRADES = 10
DAILY_TARGET = 100
DAILY_STOP = -50


# =========================
# RESET
# =========================
def reset_agents():
    return [
        ("MomentumAI", MomentumAI()),
        ("MeanReversionAI", MeanReversionAI()),
        ("BreakoutAI", BreakoutAI()),
        ("SentimentAI", SentimentAI())
    ]


# =========================
# WATCHDOG
# =========================
def watchdog():
    global agents
    while True:
        time.sleep(10)
        if time.time() - last_heartbeat["t"] > 25:
            agents = reset_agents()
            last_heartbeat["t"] = time.time()


# =========================
# CHOP DETECTOR
# =========================
def detect_chop(mkt):
    vols = [mkt[s]["vol"] for s in mkt if "vol" in mkt[s]]
    if not vols:
        return False

    avg = sum(vols) / len(vols)
    up = sum(1 for s in mkt if mkt[s]["trend"] == "UP")
    down = sum(1 for s in mkt if mkt[s]["trend"] == "DOWN")

    return avg < 0.9 and abs(up - down) < len(mkt) * 0.2


# =========================
# TRADING LOOP (DAY TRADER ENGINE)
# =========================
def trading_loop():
    global agents, latest_state, cycle

    analytics = Analytics()

    while True:
        try:
            last_heartbeat["t"] = time.time()

            mkt = market()
            if not mkt:
                time.sleep(1)
                continue

            prices = {s: mkt[s]["price"] for s in mkt}
            portfolio.update(prices)

            trades = []
            chop = detect_chop(mkt)

            # =========================
            # DAILY RESET (SIMULATED DAY)
            # =========================
            if cycle % 200 == 0:
                daily_stats["trades"] = 0
                daily_stats["start_equity"] = portfolio.equity

            daily_stats["profit"] = portfolio.equity - daily_stats["start_equity"]

            # =========================
            # STOCK LOOP
            # =========================
            for symbol, data in mkt.items():

                votes, weights = [], []

                for name, agent in agents:
                    try:
                        action, conf = agent.decide(data)
                    except:
                        action, conf = "HOLD", 0.5

                    votes.append((action, conf))
                    weights.append(learn.weight(name))

                action, conf = decide(votes, weights)

                allowed = risk.approve(portfolio, action, conf)

                if allowed:
                    allowed = head_trader.approve_trade(
                        symbol, action, conf, data, portfolio, chop
                    )

                if chop:
                    allowed = False

                # =========================
                # 🛑 DAY TRADING LIMITS (NEW)
                # =========================
                if (
                    daily_stats["trades"] >= MAX_TRADES or
                    daily_stats["profit"] >= DAILY_TARGET or
                    daily_stats["profit"] <= DAILY_STOP
                ):
                    allowed = False

                price = data["price"]
                pnl = 0

                if allowed:
                    if action == "BUY":
                        portfolio.buy(symbol, price, conf)
                        daily_stats["trades"] += 1

                    elif action == "SELL":
                        portfolio.sell(symbol, price)
                        daily_stats["trades"] += 1

                    pnl = conf

                for name, _ in agents:
                    learn.update(name, pnl)
                    analytics.update(name, pnl)

                trades.append({
                    "symbol": symbol,
                    "action": action,
                    "confidence": round(conf, 2),
                    "allowed": allowed,
                    "price": round(price, 2),
                    "daily_trades": daily_stats["trades"],
                    "daily_profit": round(daily_stats["profit"], 2)
                })

            cycle += 1

            agents = [(name, evolver.mutate(agent)) for name, agent in agents]

            latest_state = {
                "equity": round(portfolio.equity, 2),
                "cash": round(portfolio.cash, 2),
                "agent_scores": learn.agent_score,
                "active_agents": [a[0] for a in agents],
                "chop_zone": chop,
                "heartbeat": last_heartbeat["t"],
                "trades": trades[-20:],

                # =========================
                # LIVE DAY TRADING STATS
                # =========================
                "daily_trades": daily_stats["trades"],
                "daily_profit": round(daily_stats["profit"], 2),
                "daily_target": DAILY_TARGET
            }

            time.sleep(1.2)

        except Exception as e:
            print("RECOVERED:", e)
            time.sleep(1)


# =========================
# START THREADS
# =========================
threading.Thread(target=trading_loop, daemon=True).start()
threading.Thread(target=watchdog, daemon=True).start()


# =========================
# ROUTES
# =========================
@app.get("/state")
def state():
    return latest_state


@app.get("/ui", response_class=HTMLResponse)
def ui():
    return """
    <html>
    <head>
        <title>AI Day Trading Terminal</title>
        <style>
            body { background:#0b0f14; color:white; font-family:monospace; }
            .box { background:#111827; margin:10px; padding:10px; border-radius:8px; }
        </style>
    </head>

    <body>
        <h2>LIVE DAY TRADING AI</h2>

        <div class="box">
            <h3>Equity: <span id="eq">...</span></h3>
            <h3>Cash: <span id="cash">...</span></h3>
            <h3>Daily Profit: <span id="profit">...</span></h3>
            <h3>Trades Today: <span id="trades">...</span></h3>
        </div>

        <div class="box">
            <h3>Agents</h3>
            <pre id="agents"></pre>
        </div>

        <div class="box">
            <h3>Live Trades</h3>
            <pre id="log"></pre>
        </div>

        <script>
            async function load(){
                const r = await fetch("/state");
                const d = await r.json();

                document.getElementById("eq").innerText = d.equity;
                document.getElementById("cash").innerText = d.cash;

                document.getElementById("profit").innerText = d.daily_profit;
                document.getElementById("trades").innerText = d.daily_trades;

                document.getElementById("agents").innerText =
                    JSON.stringify(d.agent_scores, null, 2);

                document.getElementById("log").innerText =
                    JSON.stringify(d.trades || [], null, 2);
            }

            setInterval(load, 1000);
            load();
        </script>
    </body>
    </html>
    """