from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
import threading, time, asyncio

from execution_engine import ExecutionEngine
from risk_engine import RiskEngine
from heatmap import HeatMap

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

exec_engine = ExecutionEngine()
risk_engine = RiskEngine(max_daily_loss=150)
heatmap = HeatMap()

analytics = Analytics()

agents = [
    ("MomentumAI", MomentumAI()),
    ("MeanReversionAI", MeanReversionAI()),
    ("BreakoutAI", BreakoutAI()),
    ("SentimentAI", SentimentAI())
]

# =========================
# TRADE MEMORY
# =========================
trade_history = []

latest_state = {
    "equity": 5000,
    "cash": 5000,
    "agent_scores": {},
    "active_agents": [],
    "chop_zone": False,
    "heartbeat": time.time(),
    "trades": [],
    "trade_history": []
}

cycle = 0
clients = []
last_heartbeat = {"t": time.time()}

# =========================
# 🔒 PROP FIRM CONTROLS (NEW)
# =========================
MAX_TRADES_PER_DAY = 20
TRADE_COOLDOWN_SEC = 8

daily_trade_count = 0
last_trade_time = {}   # symbol -> timestamp

day_start_equity = 5000


# =========================
# RESET DAY FUNCTION
# =========================
def reset_day():
    global daily_trade_count, trade_history, day_start_equity, last_trade_time

    daily_trade_count = 0
    trade_history = []
    last_trade_time = {}
    day_start_equity = portfolio.equity


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
# CLOSE TRADE
# =========================
def close_trade(symbol, price):
    for t in reversed(trade_history):
        if t["symbol"] == symbol and t["exit"] is None:
            t["exit"] = price
            t["pnl"] = round(price - t["entry"], 4)
            return


# =========================
# TRADING LOOP (PROP FIRM MODE)
# =========================
def trading_loop():
    global agents, latest_state, cycle, daily_trade_count

    while True:
        try:
            last_heartbeat["t"] = time.time()

            mkt = market()
            if not mkt:
                time.sleep(1)
                continue

            portfolio.update({s: mkt[s]["price"] for s in mkt})

            trades = []
            chop = detect_chop(mkt)

            # =========================
            # DAY RESET CHECK
            # =========================
            if portfolio.equity - day_start_equity > 2000 or daily_trade_count >= MAX_TRADES_PER_DAY:
                reset_day()

            for symbol, data in mkt.items():

                # =========================
                # COOLDOWN CHECK
                # =========================
                if symbol in last_trade_time:
                    if time.time() - last_trade_time[symbol] < TRADE_COOLDOWN_SEC:
                        continue

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
                # PROP FIRM LIMITS
                # =========================
                if daily_trade_count >= MAX_TRADES_PER_DAY:
                    allowed = False

                price = data["price"]

                # =========================
                # EXECUTION
                # =========================
                if allowed and action == "BUY":
                    exec_engine.execute("BUY", symbol, price, conf)
                    portfolio.buy(symbol, price, conf)

                    trade_history.append({
                        "symbol": symbol,
                        "side": "BUY",
                        "entry": price,
                        "exit": None,
                        "pnl": 0,
                        "time": time.time()
                    })

                    daily_trade_count += 1
                    last_trade_time[symbol] = time.time()

                elif allowed and action == "SELL":
                    exec_engine.execute("SELL", symbol, price, conf)
                    portfolio.sell(symbol, price)
                    close_trade(symbol, price)

                    daily_trade_count += 1
                    last_trade_time[symbol] = time.time()

                for name, _ in agents:
                    learn.update(name, conf)
                    analytics.update(name, conf)

                trades.append({
                    "symbol": symbol,
                    "action": action,
                    "price": round(price, 2),
                    "allowed": allowed
                })

            cycle += 1

            agents = [(n, evolver.mutate(a)) for n, a in agents]

            latest_state = {
                "equity": round(portfolio.equity, 2),
                "cash": round(portfolio.cash, 2),
                "active_agents": [a[0] for a in agents],
                "trades": trades[-20:],
                "trade_history": trade_history[-100:],
                "daily_trades": daily_trade_count,
                "max_trades": MAX_TRADES_PER_DAY
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


@app.get("/reset_day")
def reset_day_route():
    reset_day()
    return {"status": "day reset complete"}


@app.get("/ui", response_class=HTMLResponse)
def ui():
    return """
<html>
<head>
<style>
body { background:#05070a; color:#00ffcc; font-family:monospace; }
button {
    background:#00ffcc;
    border:none;
    padding:10px;
    margin:10px;
    cursor:pointer;
}
</style>
</head>

<body>

<h2>PROP FIRM TERMINAL</h2>

<button onclick="fetch('/reset_day')">
RESET DAY
</button>

<div id="data"></div>

<script>

async function load(){
    const r = await fetch("/state");
    const d = await r.json();

    document.getElementById("data").innerHTML =
    `
    <p>Equity: ${d.equity}</p>
    <p>Cash: ${d.cash}</p>
    <p>Trades Today: ${d.daily_trades}/${d.max_trades}</p>
    <pre>${JSON.stringify(d.trade_history, null, 2)}</pre>
    `;
}

setInterval(load, 1000);
load();

</script>

</body>
</html>
"""