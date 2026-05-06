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

# =========================
# 🔥 ENGINE LAYER
# =========================
exec_engine = ExecutionEngine()
risk_engine = RiskEngine(max_daily_loss=150)
heatmap = HeatMap()

# =========================
# ANALYTICS
# =========================
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
# TRADE CLOSE MATCH
# =========================
def close_trade(symbol, price):
    for t in reversed(trade_history):
        if t["symbol"] == symbol and t["exit"] is None:
            t["exit"] = price
            t["pnl"] = round(price - t["entry"], 4)
            return

# =========================
# TRADING LOOP
# =========================
def trading_loop():
    global agents, latest_state, cycle, heatmap

    while True:
        try:
            last_heartbeat["t"] = time.time()

            mkt = market()
            if not mkt:
                time.sleep(1)
                continue

            prices = {s: mkt[s]["price"] for s in mkt}
            portfolio.update(prices)

            # =========================
            # 🔴 STEP 6 — KILL SWITCH
            # =========================
            if not risk_engine.allow_trade(portfolio.equity):
                for s in list(portfolio.positions.keys()):
                    if s in prices:
                        portfolio.sell(s, prices[s])
                continue

            trades = []
            chop = detect_chop(mkt)

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
                qty = max(1, int(conf * 10))

                # =========================
                # 🔵 STEP 5 — EXECUTION ENGINE
                # =========================
                if allowed and action == "BUY":
                    order = exec_engine.execute(symbol, "BUY", price, qty)

                    portfolio.buy(symbol, order["price"], conf)
                    heatmap.update(symbol, qty)

                    trade_history.append({
                        "symbol": symbol,
                        "side": "BUY",
                        "entry": order["price"],
                        "exit": None,
                        "pnl": 0,
                        "confidence": conf,
                        "time": time.time()
                    })

                elif allowed and action == "SELL":
                    order = exec_engine.execute(symbol, "SELL", price, qty)

                    portfolio.sell(symbol, order["price"])
                    heatmap.update(symbol, -qty)

                    close_trade(symbol, order["price"])

                pnl = conf

                for name, _ in agents:
                    learn.update(name, pnl)
                    analytics.update(name, pnl)

                trades.append({
                    "symbol": symbol,
                    "action": action,
                    "confidence": round(conf, 2),
                    "allowed": allowed,
                    "price": round(price, 2)
                })

            cycle += 1

            # =========================
            # 🔁 STEP 7 — DAILY RESET
            # =========================
            if cycle % 200 == 0:
                risk_engine.reset_day(portfolio.equity)
                heatmap = HeatMap()

            agents = [(n, evolver.mutate(a)) for n, a in agents]

            # =========================
            # 🟢 STEP 8 — STATE UPDATE
            # =========================
            latest_state = {
                "equity": round(portfolio.equity, 2),
                "cash": round(portfolio.cash, 2),
                "agent_scores": learn.agent_score,
                "active_agents": [a[0] for a in agents],
                "chop_zone": chop,
                "heartbeat": last_heartbeat["t"],
                "trades": trades[-20:],
                "trade_history": trade_history[-100:],

                # NEW DATA
                "heatmap": heatmap.snapshot(),
                "risk_score": heatmap.total_risk(),
                "executions": exec_engine.orders[-20:]
            }

            time.sleep(1.2)

        except Exception as e:
            print("RECOVERED:", e)
            time.sleep(1)

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
    return """
<!DOCTYPE html>
<html>
<head>
<title>PRO AI TRADING TERMINAL</title>

<style>
body {
    margin:0;
    background:#05070a;
    color:#00ffcc;
    font-family: monospace;
}
.header { padding:15px; text-align:center; }
.grid { display:grid; grid-template-columns: 1fr 1fr 1fr; gap:12px; padding:12px; }
.box { background:#0f172a; padding:12px; border-radius:10px; }
.big { font-size:24px; font-weight:bold; }
.green { color:#00ff88; }
.red { color:#ff4d4d; }
.tape { height:200px; overflow:auto; background:#0b1220; padding:10px; border-radius:10px; }
.trade { border-bottom:1px solid #1f2937; padding:5px; font-size:12px; }
</style>
</head>

<body>

<div class="header">🧠 PRO AI TRADING TERMINAL</div>

<div class="grid">

<div class="box">
<div class="big">EQUITY</div>
<div id="equity"></div>
</div>

<div class="box">
<div class="big">CASH</div>
<div id="cash"></div>
</div>

<div class="box">
<div class="big">CHOP</div>
<div id="chop"></div>
</div>

<div class="box">
<div class="big">AGENTS</div>
<pre id="agents"></pre>
</div>

<div class="box">
<div class="big">SCORES</div>
<pre id="scores"></pre>
</div>

<div class="box" style="grid-column: span 3;">
<div class="big">TRADE HISTORY (REAL PNL)</div>
<div class="tape" id="history"></div>
</div>

</div>

<script>

async function load(){
    const r = await fetch("/state");
    const d = await r.json();

    document.getElementById("equity").innerHTML =
        "<span class='green'>$" + d.equity + "</span>";

    document.getElementById("cash").innerText = "$" + d.cash;

    document.getElementById("chop").innerText = d.chop_zone;

    document.getElementById("agents").innerText =
        JSON.stringify(d.active_agents, null, 2);

    document.getElementById("scores").innerText =
        JSON.stringify(d.agent_scores, null, 2);

    let h = "";
    (d.trade_history || []).slice(-20).reverse().forEach(t => {
        h += `<div class="trade">
            ${t.symbol} | ${t.side} | entry:${t.entry} | exit:${t.exit} | pnl:${t.pnl}
        </div>`;
    });

    document.getElementById("history").innerHTML = h;
}

setInterval(load, 1000);
load();

</script>

</body>
</html>
"""