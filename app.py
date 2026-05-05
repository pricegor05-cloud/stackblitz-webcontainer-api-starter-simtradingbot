from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import threading, time, random

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

agents = [
    ("MomentumAI", MomentumAI()),
    ("MeanReversionAI", MeanReversionAI()),
    ("BreakoutAI", BreakoutAI()),
    ("SentimentAI", SentimentAI())
]

latest_state = {}
cycle = 0
last_heartbeat = {"t": time.time()}

# =========================
# 🧠 STEP 1 — AGENT HEARTBEAT TRACKING
# =========================
agent_heartbeat = {}

def reset_agents():
    return [
        ("MomentumAI", MomentumAI()),
        ("MeanReversionAI", MeanReversionAI()),
        ("BreakoutAI", BreakoutAI()),
        ("SentimentAI", SentimentAI())
    ]

# =========================
# 🛟 STEP 2 — WATCHDOG (AUTO RECOVERY)
# =========================
def watchdog():
    global agents
    while True:
        time.sleep(10)

        if time.time() - last_heartbeat["t"] > 20:
            print("⚠️ WATCHDOG RESET TRIGGERED")

            agents = reset_agents()
            last_heartbeat["t"] = time.time()

            agent_heartbeat.clear()

# =========================
# 🚨 STEP 3 — SAFE MARKET HANDLING
# =========================
def safe_market():
    try:
        mkt = market()
        if not mkt or len(mkt) == 0:
            latest_state["error"] = "market_empty"
            return None
        return mkt
    except Exception as e:
        latest_state["error"] = str(e)
        return None

# =========================
# 🧠 STEP 4 — TRADING LOOP (HARDENED)
# =========================
def trading_loop():
    global agents, latest_state, cycle

    while True:
        try:
            last_heartbeat["t"] = time.time()

            mkt = safe_market()
            if not mkt:
                time.sleep(2)
                continue

            prices = {s: mkt[s]["price"] for s in mkt}
            portfolio.update(prices)

            trades = []
            chop = detect_chop(mkt)

            for s, d in mkt.items():

                votes, weights = [], []

                for n, a in agents:
                    try:
                        act, conf = a.decide(d)
                    except:
                        act, conf = "HOLD", 0.5

                    votes.append((act, conf))
                    weights.append(learn.weight(n))

                    # 🟢 STEP 1 — update agent heartbeat
                    agent_heartbeat[n] = time.time()

                action, conf = decide(votes, weights)

                allowed = risk.approve(portfolio, action, conf)

                if allowed:
                    allowed = head_trader.approve_trade(s, action, conf, d, portfolio, chop)

                if chop:
                    allowed = False

                price = d["price"]
                pnl = 0

                if allowed:
                    if action == "BUY":
                        portfolio.buy(s, price, conf)
                    elif action == "SELL":
                        portfolio.sell(s, price)

                if trade_manager.check_exit(portfolio, s, price):
                    portfolio.sell(s, price)
                    pnl = 1

                for n, _ in agents:
                    learn.update(n, pnl)

                trades.append({
                    "symbol": s,
                    "action": action,
                    "confidence": round(conf, 2),
                    "allowed": allowed,
                    "price": round(price, 2),
                    "chop": chop
                })

            cycle += 1
            if cycle % 5 == 0:
                agents = evolve_agents()

            # =========================
            # 🟢 STEP 5 — ACTIVE AGENTS FILTER
            # =========================
            active_agents = [
                name for name, t in agent_heartbeat.items()
                if time.time() - t < 30
            ]

            latest_state = {
                "equity": round(portfolio.equity, 2),
                "cash": round(portfolio.cash, 2),
                "agent_scores": learn.agent_score,
                "active_agents": active_agents,
                "chop_zone": chop,
                "heartbeat": last_heartbeat["t"],
                "trades": trades[-20:]
            }

            time.sleep(5)

        except Exception as e:
            print("🔥 LOOP RECOVERED:", e)
            latest_state["error"] = str(e)
            time.sleep(2)

# =========================
# START SYSTEM THREADS
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