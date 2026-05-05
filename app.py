from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
import threading, time, random, asyncio

from engine import *
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

tracker = PerformanceTracker()
memory = TradeMemory()
compound = CompoundEngine(portfolio)

agents = [
    ("MomentumAI", MomentumAI()),
    ("MeanReversionAI", MeanReversionAI()),
    ("BreakoutAI", BreakoutAI()),
    ("SentimentAI", SentimentAI())
]

latest_state = {}
cycle = 0
clients = []
last_heartbeat = {"t": time.time()}

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
# TRADING LOOP (LEVEL 3 CORE)
# =========================
def trading_loop():
    global agents, latest_state, cycle

    while True:
        try:
            last_heartbeat["t"] = time.time()

            mkt = market()
            if not mkt:
                time.sleep(2)
                continue

            portfolio.update({s: mkt[s]["price"] for s in mkt})

            trades = []
            chop = detect_chop(mkt)

            for symbol, data in mkt.items():

                votes, weights = [], []

                for name, agent in agents:

                    action, conf = agent.decide(data)

                    conf = memory.adjust(name, conf)

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

                    tracker.update_trade(name, pnl)
                    memory.record(name, conf, pnl)

                    # 🔥 SHARPE BOOST
                    learn.agent_score[name] *= (1 + tracker.sharpe(name) * 0.01)

                trades.append({
                    "symbol": symbol,
                    "action": action,
                    "confidence": round(conf, 2),
                    "allowed": allowed,
                    "price": round(price, 2),
                    "chop": chop
                })

            cycle += 1
            if cycle % 5 == 0:
                agents = evolve_agents()

            compound.run()

            latest_state = {
                "equity": round(portfolio.equity, 2),
                "cash": round(portfolio.cash, 2),
                "agent_scores": learn.agent_score,
                "active_agents": [a[0] for a in agents],
                "chop_zone": chop,
                "heartbeat": last_heartbeat["t"],
                "trades": trades[-20:]
            }

            # websocket push
            asyncio.run(broadcast(latest_state))

            time.sleep(5)

        except Exception as e:
            print("RECOVERED:", e)
            time.sleep(2)

# =========================
# WEBSOCKET
# =========================
@app.websocket("/ws")
async def ws(websocket: WebSocket):
    await websocket.accept()
    clients.append(websocket)

    try:
        while True:
            await websocket.send_json(latest_state)
            await asyncio.sleep(1)
    except:
        clients.remove(websocket)

async def broadcast(data):
    dead = []
    for c in clients:
        try:
            await c.send_json(data)
        except:
            dead.append(c)

    for d in dead:
        clients.remove(d)

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
    return open("frontend.html").read()