from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
import threading, time, asyncio

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
# 🔒 SINGLE SOURCE OF TRUTH (LEDGER)
# =========================
trade_ledger = []
positions = {}   # symbol -> open trade

# =========================
# DAY TRADING CONTROLS
# =========================
MAX_TRADES_PER_DAY = 30
daily_trades = 0
daily_start_equity = 5000

cycle = 0
clients = []
last_heartbeat = {"t": time.time()}

# =========================
# STABLE STATE (NEVER CHANGES SHAPE)
# =========================
latest_state = {
    "equity": 5000,
    "cash": 5000,
    "daily_pnl": 0,
    "daily_trades": 0,
    "win_rate": 0,
    "agent_scores": {},
    "active_agents": [],
    "chop_zone": False,
    "heartbeat": time.time(),
    "trades": [],
    "ledger": []
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
# CLOSE TRADE (REAL PNL ENGINE)
# =========================
def close_trade(symbol, price):
    global trade_ledger

    for t in reversed(trade_ledger):
        if t["symbol"] == symbol and t["exit"] is None:
            t["exit"] = price
            t["pnl"] = round(price - t["entry"], 4)
            positions.pop(symbol, None)
            return t

    return None

# =========================
# TRADING LOOP (CORE ENGINE)
# =========================
def trading_loop():
    global agents, cycle, daily_trades, latest_state

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
            # DAILY RESET
            # =========================
            if cycle % 200 == 0:
                daily_trades = 0
                daily_start_equity = portfolio.equity
                positions.clear()

            daily_pnl = portfolio.equity - daily_start_equity

            # =========================
            # FLATTEN RULE (NO OVERNIGHT)
            # =========================
            if daily_trades >= MAX_TRADES_PER_DAY:
                for s in list(positions.keys()):
                    portfolio.sell(s, mkt[s]["price"])
                    close_trade(s, mkt[s]["price"])
                time.sleep(1)
                continue

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

                # =========================
                # BUY LOGIC
                # =========================
                if allowed and action == "BUY" and symbol not in positions:
                    portfolio.buy(symbol, price, conf)

                    positions[symbol] = {
                        "entry": price,
                        "time": time.time()
                    }

                    trade_ledger.append({
                        "symbol": symbol,
                        "entry": price,
                        "exit": None,
                        "pnl": 0,
                        "side": "BUY"
                    })

                    daily_trades += 1

                # =========================
                # SELL LOGIC
                # =========================
                elif allowed and action == "SELL" and symbol in positions:
                    portfolio.sell(symbol, price)
                    close_trade(symbol, price)
                    daily_trades += 1

                pnl_signal = conf

                for name, _ in agents:
                    learn.update(name, pnl_signal)
                    analytics.update(name, pnl_signal)

                trades.append({
                    "symbol": symbol,
                    "action": action,
                    "confidence": round(conf, 2),
                    "price": round(price, 2)
                })

            cycle += 1
            agents = [(n, evolver.mutate(a)) for n, a in agents]

            # =========================
            # WIN RATE
            # =========================
            wins = sum(1 for t in trade_ledger if t["pnl"] > 0)
            losses = sum(1 for t in trade_ledger if t["pnl"] < 0)
            total = wins + losses
            win_rate = (wins / total * 100) if total > 0 else 0

            # =========================
            # STATE (LOCKED SHAPE)
            # =========================
            latest_state = {
                "equity": round(portfolio.equity, 2),
                "cash": round(portfolio.cash, 2),
                "daily_pnl": round(daily_pnl, 2),
                "daily_trades": daily_trades,
                "win_rate": round(win_rate, 2),
                "agent_scores": learn.agent_score,
                "active_agents": [a[0] for a in agents],
                "chop_zone": chop,
                "heartbeat": last_heartbeat["t"],
                "trades": trades[-20:],
                "ledger": trade_ledger[-100:]
            }

            time.sleep(1.2)

        except Exception as e:
            print("RECOVERED:", e)
            time.sleep(1)

# =========================
# START SYSTEM
# =========================
threading.Thread(target=trading_loop, daemon=True).start()

# =========================
# ROUTES
# =========================
@app.get("/state")
def state():
    return latest_state

@app.get("/ui", response_class=HTMLResponse)
def ui():
    return """
    <html>
    <body style="background:#05070a;color:#00ffcc;font-family:monospace">
        <h2>LOCKED PROP FIRM CORE</h2>

        <div id="data"></div>

        <script>
        async function load(){
            const r = await fetch("/state");
            const d = await r.json();

            document.getElementById("data").innerHTML =
            `
            Equity: ${d.equity}<br>
            Cash: ${d.cash}<br>
            Daily PnL: ${d.daily_pnl}<br>
            Trades: ${d.daily_trades}<br>
            Win Rate: ${d.win_rate}%<br>
            `;
        }
        setInterval(load, 1000);
        load();
        </script>
    </body>
    </html>
    """