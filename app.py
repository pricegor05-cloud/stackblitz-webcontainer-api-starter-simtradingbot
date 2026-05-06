from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import threading, time, random

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
evolver = EvolutionEngine(learn)

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
# CORE V MAX SYSTEM
# =========================
class CoreVMax:
    def __init__(self):
        self.risk_mode = "NORMAL"
        self.last_trade_score = 0

    def score_trade(self, action, conf, data, portfolio):
        volatility = data.get("volatility", 1)
        spread = data.get("spread", 0.01)

        equity_factor = portfolio.equity / 5000
        risk_penalty = 1 if equity_factor > 0.95 else 0.7

        score = (conf * 100) * risk_penalty - (volatility * 10) - (spread * 50)
        self.last_trade_score = score

        return max(0, min(100, score))

    def update_risk_mode(self, portfolio):
        dd = (5000 - portfolio.equity) / 5000

        if dd > 0.08:
            self.risk_mode = "KILL"
        elif dd > 0.04:
            self.risk_mode = "CAUTION"
        else:
            self.risk_mode = "NORMAL"

    def position_size(self, conf, equity):
        base_risk = 0.02
        multiplier = 0.5 if self.risk_mode == "CAUTION" else 1
        return equity * base_risk * conf * multiplier

    def allow_trade(self):
        return self.risk_mode != "KILL"

core = CoreVMax()

# =========================
# STATE
# =========================
trade_history = []
equity_curve = []

daily_trade_count = 0
last_trade_time = {}
day_start_equity = 5000

MAX_TRADES_PER_DAY = 20
TRADE_COOLDOWN_SEC = 8

last_heartbeat = {"t": time.time()}
latest_state = {}

# =========================
# RESET DAY
# =========================
def reset_day():
    global daily_trade_count, trade_history, last_trade_time, day_start_equity

    if hasattr(portfolio, "positions"):
        for symbol, pos in list(portfolio.positions.items()):
            try:
                price = pos.get("price", None)
                if price:
                    portfolio.sell(symbol, price)
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
# TRADING LOOP (CORE V MAX)
# =========================
def trading_loop():
    global daily_trade_count, latest_state

    while True:
        try:
            last_heartbeat["t"] = time.time()

            mkt = market()
            if not mkt:
                time.sleep(1)
                continue

            portfolio.update({s: mkt[s]["price"] for s in mkt})

            # CORE V MAX RISK UPDATE
            core.update_risk_mode(portfolio)

            if core.risk_mode == "KILL":
                time.sleep(2)
                continue

            for symbol, data in mkt.items():

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

                score = core.score_trade(action, conf, data, portfolio)

                allowed = (
                    risk.approve(portfolio, action, conf)
                    and core.allow_trade()
                    and score > 55
                )

                price = data["price"]

                # SLIPPAGE MODEL
                slippage = price * random.uniform(0.0002, 0.0008)

                if allowed and action == "BUY":

                    size = core.position_size(conf, portfolio.equity)

                    exec_engine.execute("BUY", symbol, price + slippage, conf)
                    portfolio.buy(symbol, price, size)

                    trade_history.append({
                        "symbol": symbol,
                        "entry": price,
                        "exit": None,
                        "pnl": 0
                    })

                    daily_trade_count += 1
                    last_trade_time[symbol] = time.time()

                elif allowed and action == "SELL":

                    exec_engine.execute("SELL", symbol, price - slippage, conf)
                    portfolio.sell(symbol, price)

                    for t in reversed(trade_history):
                        if t["symbol"] == symbol and t["exit"] is None:
                            t["exit"] = price
                            t["pnl"] = round(price - t["entry"], 4)
                            break

                    daily_trade_count += 1
                    last_trade_time[symbol] = time.time()

            closed = [t for t in trade_history if t["exit"] is not None]
            wins = [t for t in closed if t["pnl"] > 0]
            win_rate = round((len(wins) / len(closed)) * 100, 2) if closed else 0

            equity_curve.append(round(portfolio.equity, 2))
            if len(equity_curve) > 200:
                equity_curve.pop(0)

            latest_state = {
                "equity": round(portfolio.equity, 2),
                "cash": round(portfolio.cash, 2),
                "daily_trades": daily_trade_count,
                "max_trades": MAX_TRADES_PER_DAY,
                "win_rate": win_rate,
                "risk_mode": core.risk_mode,
                "last_trade_score": round(core.last_trade_score, 2),
                "equity_curve": equity_curve,
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
<head>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

<style>
body { background:#05070a; color:#00ffcc; font-family:monospace; }
.green { color:#00ff88; }
.red { color:#ff4d4d; }
</style>
</head>

<body>

<h2>CORE V MAX PROP FIRM TERMINAL</h2>
<button onclick="fetch('/reset_day')">RESET DAY</button>

<div id="stats"></div>
<canvas id="chart"></canvas>
<table id="trades"></table>

<script>
let chart;

async function load(){
    const r = await fetch("/state");
    const d = await r.json();

    document.getElementById("stats").innerHTML =
    `Equity: $${d.equity} | Trades: ${d.daily_trades}/${d.max_trades} | WinRate: ${d.win_rate}% | Risk: ${d.risk_mode} | Score: ${d.last_trade_score}`;

    const ctx = document.getElementById('chart').getContext('2d');

    if(!chart){
        chart = new Chart(ctx,{
            type:'line',
            data:{labels:d.equity_curve.map((_,i)=>i),datasets:[{data:d.equity_curve}]}
        });
    } else {
        chart.data.labels = d.equity_curve.map((_,i)=>i);
        chart.data.datasets[0].data = d.equity_curve;
        chart.update();
    }
}

setInterval(load,1000);
load();
</script>

</body>
</html>
"""