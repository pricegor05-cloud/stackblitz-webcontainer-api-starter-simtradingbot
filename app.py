from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import threading, time

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
# STATE
# =========================
trade_history = []
daily_trade_count = 0
last_trade_time = {}
day_start_equity = 5000

MAX_TRADES_PER_DAY = 20
TRADE_COOLDOWN_SEC = 8

cycle = 0
last_heartbeat = {"t": time.time()}

latest_state = {
    "equity": 5000,
    "cash": 5000,
    "daily_trades": 0,
    "max_trades": MAX_TRADES_PER_DAY,
    "trades": [],
    "trade_history": []
}

# =========================
# RESET DAY (FLAT MODE FIX)
# =========================
def reset_day():
    global daily_trade_count, trade_history, last_trade_time, day_start_equity

    # 🔥 CLOSE ALL POSITIONS
    if hasattr(portfolio, "positions"):
        for symbol, pos in list(portfolio.positions.items()):
            try:
                price = pos.get("price", None)
                if price:
                    portfolio.sell(symbol, price)

                    for t in reversed(trade_history):
                        if t["symbol"] == symbol and t["exit"] is None:
                            t["exit"] = price
                            t["pnl"] = round(price - t["entry"], 4)
                            break
            except:
                pass

    daily_trade_count = 0
    trade_history = []
    last_trade_time = {}
    day_start_equity = portfolio.equity

# =========================
# WATCHDOG
# =========================
def watchdog():
    global agents
    while True:
        time.sleep(10)
        if time.time() - last_heartbeat["t"] > 25:
            agents = [
                ("MomentumAI", MomentumAI()),
                ("MeanReversionAI", MeanReversionAI()),
                ("BreakoutAI", BreakoutAI()),
                ("SentimentAI", SentimentAI())
            ]
            last_heartbeat["t"] = time.time()

# =========================
# TRADING LOOP
# =========================
def trading_loop():
    global cycle, daily_trade_count, latest_state

    while True:
        try:
            last_heartbeat["t"] = time.time()

            mkt = market()
            if not mkt:
                time.sleep(1)
                continue

            portfolio.update({s: mkt[s]["price"] for s in mkt})

            # 🔥 HARD FLAT PROTECTION (fix ghost equity movement)
            if daily_trade_count == 0 and hasattr(portfolio, "positions"):
                for symbol, pos in list(portfolio.positions.items()):
                    try:
                        price = mkt.get(symbol, {}).get("price", None)
                        if price:
                            portfolio.sell(symbol, price)

                            for t in reversed(trade_history):
                                if t["symbol"] == symbol and t["exit"] is None:
                                    t["exit"] = price
                                    t["pnl"] = round(price - t["entry"], 4)
                                    break
                    except:
                        pass

            trades = []

            for symbol, data in mkt.items():

                # ⏱ cooldown
                if symbol in last_trade_time:
                    if time.time() - last_trade_time[symbol] < TRADE_COOLDOWN_SEC:
                        continue

                if daily_trade_count >= MAX_TRADES_PER_DAY:
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

                price = data["price"]

                # BUY
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

                # SELL
                elif allowed and action == "SELL":
                    exec_engine.execute("SELL", symbol, price, conf)
                    portfolio.sell(symbol, price)

                    for t in reversed(trade_history):
                        if t["symbol"] == symbol and t["exit"] is None:
                            t["exit"] = price
                            t["pnl"] = round(price - t["entry"], 4)
                            break

                    daily_trade_count += 1
                    last_trade_time[symbol] = time.time()

                trades.append({
                    "symbol": symbol,
                    "action": action,
                    "price": round(price, 2),
                    "allowed": allowed
                })

            cycle += 1

            latest_state = {
                "equity": round(portfolio.equity, 2),
                "cash": round(portfolio.cash, 2),
                "daily_trades": daily_trade_count,
                "max_trades": MAX_TRADES_PER_DAY,
                "trades": trades[-20:],
                "trade_history": trade_history[-50:]
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
    return {"status": "reset complete"}

# =========================
# UI
# =========================
@app.get("/ui", response_class=HTMLResponse)
def ui():
    return """
<html>
<body style="background:#05070a;color:#00ffcc;font-family:monospace">

<h2>PROP FIRM TERMINAL</h2>

<button onclick="fetch('/reset_day')">RESET DAY</button>

<div id="data"></div>

<script>
async function load(){
    const r = await fetch("/state");
    const d = await r.json();

    document.getElementById("data").innerHTML =
    `
    Equity: ${d.equity}<br>
    Cash: ${d.cash}<br>
    Trades: ${d.daily_trades}/${d.max_trades}<br>
    <pre>${JSON.stringify(d.trade_history, null, 2)}</pre>
    `;
}
setInterval(load, 1000);
load();
</script>

</body>
</html>
"""