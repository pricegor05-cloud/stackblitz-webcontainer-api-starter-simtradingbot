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
# CORE SYSTEM (UNCHANGED)
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

analytics = Analytics()

agents = [
    ("MomentumAI", MomentumAI()),
    ("MeanReversionAI", MeanReversionAI()),
    ("BreakoutAI", BreakoutAI()),
    ("SentimentAI", SentimentAI())
]

# =========================
# NEW ENGINE LAYER
# =========================
exec_engine = ExecutionEngine()
risk_engine = RiskEngine(max_daily_loss=150)
heatmap = HeatMap()

# SAFE fallback (prevents crashes)
if not hasattr(exec_engine, "orders"):
    exec_engine.orders = []

# =========================
# TRADE MEMORY
# =========================
trade_history = []

cycle = 0
clients = []
last_heartbeat = {"t": time.time()}

# =========================
# SAFE INITIAL STATE
# =========================
latest_state = {
    "equity": 5000,
    "cash": 5000,
    "agent_scores": {},
    "active_agents": [],
    "chop_zone": False,
    "heartbeat": time.time(),
    "trades": [],
    "trade_history": [],
    "wins": 0,
    "losses": 0,
    "risk_score": 0,
    "executions": [],
    "heatmap": {}
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
# CLOSE TRADE MATCHING
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
    global agents, latest_state, cycle

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
                # EXECUTION + TRADE LOGIC
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

            agents = [(n, evolver.mutate(a)) for n, a in agents]

            # =========================
            # SAFE STATE UPDATE
            # =========================
            wins = sum(1 for t in trade_history if t.get("pnl", 0) > 0)
            losses = sum(1 for t in trade_history if t.get("pnl", 0) < 0)

            latest_state = {
                "equity": round(portfolio.equity, 2),
                "cash": round(portfolio.cash, 2),
                "agent_scores": learn.agent_score,
                "active_agents": [a[0] for a in agents],
                "chop_zone": chop,
                "heartbeat": last_heartbeat["t"],
                "trades": trades[-20:],

                "trade_history": trade_history[-100:],

                # UI SUPPORT
                "wins": wins,
                "losses": losses,
                "risk_score": heatmap.total_risk() if hasattr(heatmap, "total_risk") else 0,
                "executions": exec_engine.orders[-20:],
                "heatmap": heatmap.snapshot() if hasattr(heatmap, "snapshot") else {}
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
# STATE API
# =========================
@app.get("/state")
def state():
    return latest_state

# =========================
# UI
# =========================
@app.get("/ui", response_class=HTMLResponse)
def ui():
    return """
<!DOCTYPE html>
<html>
<head>
<title>AI TRADING TERMINAL</title>
<style>
body { margin:0; background:#05070a; color:#00ffcc; font-family:monospace; }
.header { padding:12px; text-align:center; }
.grid { display:grid; grid-template-columns:1fr 1fr 1fr; gap:12px; padding:12px; }
.box { background:#0f172a; padding:12px; border-radius:10px; }
.big { font-size:20px; }
.green { color:#00ff88; }
.red { color:#ff4d4d; }
.tape { height:200px; overflow:auto; background:#0b1220; padding:10px; }
</style>
</head>

<body>

<div class="header">🧠 AI TRADING TERMINAL</div>

<div class="grid">

<div class="box"><div class="big">EQUITY</div><div id="eq"></div></div>
<div class="box"><div class="big">CASH</div><div id="cash"></div></div>
<div class="box"><div class="big">WIN/LOSS</div><div id="wl"></div></div>

<div class="box"><div class="big">AGENTS</div><pre id="agents"></pre></div>
<div class="box"><div class="big">RISK</div><div id="risk"></div></div>

<div class="box" style="grid-column: span 3;">
<div class="big">TRADES</div>
<div class="tape" id="trades"></div>
</div>

</div>

<script>

async function load(){
    const r = await fetch("/state");
    const d = await r.json();

    document.getElementById("eq").innerHTML =
        "<span class='green'>$"+d.equity+"</span>";

    document.getElementById("cash").innerText = "$"+d.cash;

    document.getElementById("wl").innerText =
        d.wins+"W / "+d.losses+"L";

    document.getElementById("risk").innerText = d.risk_score;

    document.getElementById("agents").innerText =
        JSON.stringify(d.agent_scores, null, 2);

    let t="";
    (d.trade_history||[]).slice(-20).forEach(x=>{
        t += x.symbol+" "+x.side+" pnl:"+x.pnl+"\n";
    });

    document.getElementById("trades").innerText = t;
}

setInterval(load,1000);
load();

</script>

</body>
</html>
"""