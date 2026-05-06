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
# DAY TRADING ENGINE
# =========================
trade_counter = 0
TRADE_TARGET = 30

daily_stats = {
    "trades": 0,
    "start_equity": 5000,
    "profit": 0
}

MAX_TRADES = 40
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
# TRADING LOOP (FIXED + DAY TRADER MODE)
# =========================
def trading_loop():
    global agents, latest_state, cycle, trade_counter

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

            # reset daily session
            if cycle % 200 == 0:
                daily_stats["trades"] = 0
                daily_stats["start_equity"] = portfolio.equity
                trade_counter = 0

            daily_stats["profit"] = portfolio.equity - daily_stats["start_equity"]

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

                # DAY TRADING LIMITS
                if (
                    daily_stats["trades"] >= MAX_TRADES or
                    daily_stats["profit"] >= DAILY_TARGET or
                    daily_stats["profit"] <= DAILY_STOP
                ):
                    allowed = False

                if chop:
                    allowed = False

                price = data["price"]
                pnl = 0

                if allowed:
                    if action == "BUY":
                        portfolio.buy(symbol, price, conf)
                        daily_stats["trades"] += 1
                        trade_counter += 1

                    elif action == "SELL":
                        portfolio.sell(symbol, price)
                        daily_stats["trades"] += 1
                        trade_counter += 1

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

            agents = [(n, evolver.mutate(a)) for n, a in agents]

            latest_state = {
                "equity": round(portfolio.equity, 2),
                "cash": round(portfolio.cash, 2),
                "agent_scores": learn.agent_score,
                "active_agents": [a[0] for a in agents],
                "chop_zone": chop,
                "heartbeat": last_heartbeat["t"],
                "trades": trades[-20:],
                "daily_trades": daily_stats["trades"],
                "daily_profit": round(daily_stats["profit"], 2),
                "trade_counter": trade_counter
            }

            time.sleep(1.2)

        except Exception as e:
            print("RECOVERED:", e)
            time.sleep(1)


# =========================
# START SYSTEM THREADS
# =========================
threading.Thread(target=trading_loop, daemon=True).start()
threading.Thread(target=watchdog, daemon=True).start()


# =========================
# ROUTES (FIXED CLEAN)
# =========================
@app.get("/state")
def state():
    return latest_state


@app.get("/ui", response_class=HTMLResponse)
def ui():
    return open("frontend.html").read()