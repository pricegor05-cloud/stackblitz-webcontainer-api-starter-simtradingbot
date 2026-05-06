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
# RESET DAY (FLAT MODE)
# =========================
def reset_day():
    global daily_trade_count, trade_history, last_trade_time, day_start_equity

    # CLOSE ALL POSITIONS
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
    global daily_trade_count, latest_state

    while True:
        try:
            last_heartbeat["t"] = time.time()

            mkt = market()
            if not mkt:
                time.sleep(1)
                continue

            portfolio.update({s: mkt[s]["price"] for s in mkt})

            # 🔥 HARD FLAT FIX
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
                allowed = risk.approve(portfolio, action, conf)

                price = data["price"]

                if allowed and action == "BUY":
                    exec_engine.execute("BUY", symbol, price, conf)
                    portfolio.buy(symbol, price, conf)

                    trade_history.append({
                        "symbol": symbol,
                        "entry": price,
                        "exit": None,
                        "pnl": 0
                    })

                    daily_trade_count += 1
                    last_trade_time[symbol] = time.time()

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

            # 📊 WIN RATE
            closed = [t for t in trade_history if t["exit"] is not None]
            wins = [t for t in closed if t["pnl"] > 0]
            win_rate = round((len(wins) / len(closed)) * 100, 2) if closed else 0

            # 📈 EQUITY CURVE
            equity_curve.append(round(portfolio.equity, 2))
            if len(equity_curve) > 200:
                equity_curve.pop(0)

            latest_state = {
                "equity": round(portfolio.equity, 2),
                "cash": round(portfolio.cash, 2),
                "daily_trades": daily_trade_count,
                "max_trades": MAX_TRADES_PER_DAY,
                "win_rate": win_rate,
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
# UI (FULL TERMINAL)
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
table { width:100%; }
td { padding:4px; border-bottom:1px solid #222; }
</style>
</head>

<body>

<h2>PROP FIRM TERMINAL</h2>
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
    `Equity: $${d.equity} | Cash: $${d.cash} | Trades: ${d.daily_trades}/${d.max_trades} | WinRate: ${d.win_rate}%`;

    const ctx = document.getElementById('chart').getContext('2d');

    if(!chart){
        chart = new Chart(ctx,{
            type:'line',
            data:{
                labels:d.equity_curve.map((_,i)=>i),
                datasets:[{data:d.equity_curve}]
            }
        });
    } else {
        chart.data.labels = d.equity_curve.map((_,i)=>i);
        chart.data.datasets[0].data = d.equity_curve;
        chart.update();
    }

    let rows = "<tr><td>Symbol</td><td>Entry</td><td>Exit</td><td>PnL</td></tr>";

    d.trade_history.forEach(t=>{
        let c = t.pnl > 0 ? "green" : "red";
        rows += `<tr>
            <td>${t.symbol}</td>
            <td>${t.entry}</td>
            <td>${t.exit ?? "-"}</td>
            <td class="${c}">${t.pnl}</td>
        </tr>`;
    });

    document.getElementById("trades").innerHTML = rows;
}

setInterval(load,1000);
load();
</script>

</body>
</html>
"""