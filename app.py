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
# SAFE INITIAL STATE (FIXED)
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
# TRADING LOOP (FIXED)
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
                pnl = 0

                if allowed:
                    if action == "BUY":
                        portfolio.buy(symbol, price, conf)
                    elif action == "SELL":
                        portfolio.sell(symbol, price)
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
                    "sharpe": {n: analytics.sharpe(n) for n, _ in agents}
                })

            cycle += 1

            # safe evolution
            agents = [(n, evolver.mutate(a)) for n, a in agents]

            latest_state = {
                "equity": round(portfolio.equity, 2),
                "cash": round(portfolio.cash, 2),
                "agent_scores": learn.agent_score,
                "active_agents": [a[0] for a in agents],
                "chop_zone": chop,
                "heartbeat": last_heartbeat["t"],
                "trades": trades[-20:]
            }

            time.sleep(1.5)

        except Exception as e:
            print("RECOVERED:", e)
            time.sleep(1)

# =========================
# WEBSOCKET
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

/* HEADER */
.header {
    padding:15px;
    text-align:center;
    font-size:20px;
    border-bottom:1px solid #1f2937;
    color:#00ffcc;
}

/* GRID */
.grid {
    display:grid;
    grid-template-columns: 1fr 1fr 1fr;
    gap:12px;
    padding:12px;
}

/* BOX STYLE */
.box {
    background:#0f172a;
    padding:12px;
    border-radius:10px;
    box-shadow:0 0 10px rgba(0,255,200,0.08);
}

/* BIG NUMBER */
.big {
    font-size:26px;
    font-weight:bold;
}

/* COLORS */
.green { color:#00ff88; }
.red { color:#ff4d4d; }
.yellow { color:#ffd700; }

/* SCROLL TAPE */
.tape {
    height:200px;
    overflow:auto;
    background:#0b1220;
    padding:10px;
    border-radius:10px;
}

/* TRADE ITEM */
.trade {
    border-bottom:1px solid #1f2937;
    padding:5px 0;
    font-size:12px;
}
</style>
</head>

<body>

<div class="header">
    🧠 PRO AI HEDGE FUND TERMINAL
</div>

<div class="grid">

    <!-- EQUITY -->
    <div class="box">
        <div class="big">EQUITY</div>
        <div id="equity">...</div>
    </div>

    <!-- CASH -->
    <div class="box">
        <div class="big">CASH</div>
        <div id="cash">...</div>
    </div>

    <!-- CHOP -->
    <div class="box">
        <div class="big">MARKET</div>
        <div id="chop">...</div>
    </div>

    <!-- AGENTS -->
    <div class="box">
        <div class="big">AGENTS</div>
        <pre id="agents"></pre>
    </div>

    <!-- SCORES -->
    <div class="box">
        <div class="big">SCORES</div>
        <pre id="scores"></pre>
    </div>

    <!-- LIVE PNL TAPE -->
    <div class="box" style="grid-column: span 3;">
        <div class="big">LIVE TRADE TAPE</div>
        <div class="tape" id="trades"></div>
    </div>

</div>

<script>

async function load(){
    const r = await fetch("/state");
    const d = await r.json();

    // EQUITY
    document.getElementById("equity").innerHTML =
        "<span class='green'>$" + (d.equity || 0).toFixed(2) + "</span>";

    // CASH
    document.getElementById("cash").innerText =
        "$" + (d.cash || 0).toFixed(2);

    // CHOP
    document.getElementById("chop").innerHTML =
        d.chop_zone ? "<span class='red'>CHOP MARKET</span>" : "<span class='green'>TRENDING</span>";

    // AGENTS
    document.getElementById("agents").innerText =
        JSON.stringify(d.active_agents || [], null, 2);

    // SCORES
    document.getElementById("scores").innerText =
        JSON.stringify(d.agent_scores || {}, null, 2);

    // TRADE TAPE
    let tape = "";
    (d.trades || []).slice(-20).reverse().forEach(t => {
        tape += `
        <div class="trade">
            ${t.symbol} | ${t.action} | ${t.price} | conf:${t.confidence}
        </div>`;
    });

    document.getElementById("trades").innerHTML = tape;
}

setInterval(load, 1000);
load();

</script>

</body>
</html>
"""