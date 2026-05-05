from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
import threading, time, asyncio

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

cycle = 0
clients = []
last_heartbeat = {"t": time.time()}

# =========================
# SAFE STATE (NO CRASH DEFAULT)
# =========================
latest_state = {
    "equity": 5000,
    "cash": 5000,
    "agent_scores": {},
    "active_agents": [],
    "chop_zone": False,
    "heartbeat": time.time(),
    "trades": []
}

# =========================
# RESET AGENTS
# =========================
def reset_agents():
    return [
        ("MomentumAI", MomentumAI()),
        ("MeanReversionAI", MeanReversionAI()),
        ("BreakoutAI", BreakoutAI()),
        ("SentimentAI", SentimentAI())
    ]

# =========================
# WATCHDOG (SELF HEAL)
# =========================
def watchdog():
    global agents, latest_state

    while True:
        time.sleep(10)

        if time.time() - last_heartbeat["t"] > 25:
            print("⚠️ WATCHDOG RESET")
            agents = reset_agents()
            last_heartbeat["t"] = time.time()

            # prevent UI freeze
            latest_state["active_agents"] = [a[0] for a in agents]

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
# TRADING LOOP (STABLE VERSION)
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

            portfolio.update({s: mkt[s]["price"] for s in mkt})

            trades = []

            # ALWAYS DEFINE CHOP SAFELY
            chop = detect_chop(mkt) if mkt else False

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

                    pnl = conf

                # UPDATE LEARNING SAFELY
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

            # SAFE EVOLUTION (NO BREAKING AGENTS)
            try:
                agents = [(n, evolver.mutate(a)) for n, a in agents]
            except:
                agents = reset_agents()

            # =========================
            # ALWAYS VALID STATE (FIX)
            # =========================
            latest_state = {
                "equity": round(portfolio.equity, 2),
                "cash": round(portfolio.cash, 2),
                "agent_scores": learn.agent_score,
                "active_agents": [a[0] for a in agents],
                "chop_zone": chop,
                "heartbeat": last_heartbeat["t"],
                "trades": trades[-20:] if trades else []
            }

            time.sleep(1.5)

        except Exception as e:
            print("RECOVERED LOOP:", e)
            time.sleep(1)

# =========================
# WEBSOCKET STREAM
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

# =========================
# START SYSTEM
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