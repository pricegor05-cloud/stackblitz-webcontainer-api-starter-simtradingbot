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

    analytics = Analytics()

    while True:
        try:
            last_heartbeat["t"] = time.time()

            mkt = market()

            prices = {s: mkt[s]["price"] for s in mkt}
            portfolio.update(prices)

            trades = []
            chop = detect_chop(mkt)

            # 🔥 FORCE ACTIVE STATE (NO IDLE LOOP)
            if len(mkt) == 0:
                continue

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

                price = data["price"]
                pnl = 0

                if allowed:
                    if action == "BUY":
                        portfolio.buy(symbol, price, conf)
                    elif action == "SELL":
                        portfolio.sell(symbol, price)

                    pnl = conf  # 💰 proxy pnl signal

                # 🧠 UPDATE AI MEMORY (IMPORTANT FIX)
                for name, _ in agents:
                    learn.update(name, pnl)
                    analytics.update(name, pnl)

                trades.append({
                    "symbol": symbol,
                    "action": action,
                    "confidence": round(conf, 2),
                    "allowed": allowed,
                    "price": round(price, 2),
                    "sharpe": {n: analytics.sharpe(n) for n, _ in agents}
                })

            cycle += 1

            # 🧬 ALWAYS EVOLVE (NOT STOPPED EVERY 5 TICKS ONLY)
            agents = evolve_agents()

            latest_state = {
                "equity": round(portfolio.equity, 2),
                "cash": round(portfolio.cash, 2),
                "agent_scores": learn.agent_score,
                "active_agents": [a[0] for a in agents],
                "chop_zone": chop,
                "heartbeat": last_heartbeat["t"],
                "trades": trades[-20:]
            }

            time.sleep(1.5)  # 🔥 FASTER STREAM = LIVE FEEL

        except Exception as e:
            print("RECOVERED:", e)
            time.sleep(1)

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