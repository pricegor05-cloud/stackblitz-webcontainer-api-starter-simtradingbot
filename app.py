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
# WATCHDOG (ANTI FREEZE)
# =========================
def watchdog():
    global agents, latest_state

    while True:
        time.sleep(10)

        if time.time() - last_heartbeat["t"] > 25:
            print("⚠️ SYSTEM RESET (WATCHDOG TRIGGERED)")
            agents = reset_agents()
            last_heartbeat["t"] = time.time()

# =========================
# CHOP DETECTOR
# =========================
def detect_chop(mkt):
    vols = [mkt[s]["vol"] for s in mkt if "vol" in mkt[s]]
    if not vols:
        return False

    avg_vol = sum(vols) / len(vols)
    up = sum(1 for s in mkt if mkt[s]["trend"] == "UP")
    down = sum(1 for s in mkt if mkt[s]["trend"] == "DOWN")

    return avg_vol < 0.9 and abs(up - down) < len(mkt) * 0.2

# =========================
# EVOLUTION
# =========================
def evolve_agents():
    global agents

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
            new_name = f"{name}_v2_{random.randint(100,999)}"
            new_agents.append((new_name, mutated))
            updated_scores[new_name] = score * random.uniform(0.95, 1.05)

    learn.agent_score.update(updated_scores)
    return new_agents

# =========================
# TRADING LOOP (FIXED + ALWAYS ACTIVE)
# =========================
def trading_loop():
    global agents, latest_state, cycle

    while True:
        try:
            last_heartbeat["t"] = time.time()

            mkt = market()

            if not mkt or len(mkt) == 0:
                time.sleep(2)
                continue

            prices = {s: mkt[s]["price"] for s in mkt}
            portfolio.update(prices)

            trades = []
            chop = detect_chop(mkt)

            # 🔥 FORCE ACTIVITY (PREVENT EQUITY FREEZE)
            if len(mkt) > 0:
                sym = random.choice(list(mkt.keys()))
                if random.random() < 0.12:
                    portfolio.buy(sym, mkt[sym]["price"], 0.55)

            for symbol, data in mkt.items():

                votes, weights = [], []

                for name, agent in agents:
                    try:
                        action, conf = agent.decide(data)

                        # FIX 3 — sanitize agents
                        if action not in ["BUY", "SELL", "HOLD"]:
                            action, conf = "HOLD", 0.5

                        conf = max(0.3, min(conf, 0.95))

                    except:
                        action, conf = "HOLD", 0.5

                    votes.append((action, conf))
                    weights.append(learn.weight(name))

                action, conf = decide(votes, weights)

                allowed = risk.approve(portfolio, action, conf)

                if allowed:
                    allowed = head_trader.approve_trade(
                        symbol,
                        action,
                        conf,
                        data,
                        portfolio,
                        chop
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

            latest_state = {
                "equity": round(portfolio.equity, 2),
                "cash": round(portfolio.cash, 2),
                "agent_scores": learn.agent_score,
                "active_agents": [a[0] for a in agents],
                "chop_zone": chop,
                "heartbeat": last_heartbeat["t"],
                "trades": trades[-20:]
            }

            time.sleep(5)

        except Exception as e:
            print("🔥 LOOP RECOVERED:", e)
            time.sleep(2)

# =========================
# START SYSTEM THREADS (FIX 4)
# =========================
threading.Thread(target=trading_loop, daemon=True).start()
threading.Thread(target=watchdog, daemon=True).start()

# =========================
# API
# =========================
@app.get("/state")
def state():
    return latest_state

@app.get("/ui", response_class=HTMLResponse)
def ui():
    return open("frontend.html").read()