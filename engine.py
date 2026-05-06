from collections import defaultdict, deque
import math
import random
import time

# =========================
# 📊 DAY TRADING ENGINE (FIXED)
# =========================
class DayTradingEngine:
    def __init__(self):
        self.trade_log = []
        self.agent_stats = defaultdict(lambda: {
            "wins": 0,
            "losses": 0,
            "pnl": 0.0
        })
        self.daily_pnl = 0.0
        self.max_daily_loss = -200
        self.max_daily_profit = 300

    def log_trade(self, agent, symbol, action, entry, exit_price):
        if exit_price is None:
            return

        pnl = (exit_price - entry) if action == "BUY" else (entry - exit_price)

        self.trade_log.append({
            "agent": agent,
            "symbol": symbol,
            "pnl": pnl,
            "time": time.time()
        })

        self.daily_pnl += pnl

        stats = self.agent_stats[agent]
        stats["pnl"] += pnl

        if pnl > 0:
            stats["wins"] += 1
        else:
            stats["losses"] += 1

    def win_rate(self, agent):
        s = self.agent_stats[agent]
        total = s["wins"] + s["losses"]
        return s["wins"] / total if total > 0 else 0.5

    def allow_trading(self):
        return self.daily_pnl >= self.max_daily_loss

    def reset_day(self):
        self.trade_log.clear()
        self.daily_pnl = 0.0
        self.agent_stats.clear()


# =========================
# 💰 PORTFOLIO (FIXED EQUITY LOGIC)
# =========================
class Portfolio:
    def __init__(self, cash=5000):
        self.cash = cash
        self.positions = {}
        self.equity = cash

    def update(self, prices):
        total = self.cash

        for s, pos in self.positions.items():
            if s in prices:
                total += pos["qty"] * prices[s]

        self.equity = total

    def buy(self, symbol, price, confidence=0.5):
        if price <= 0:
            return

        risk_budget = self.equity * 0.05
        size = risk_budget * max(0.2, min(confidence, 1.0))

        if self.cash < size:
            return

        qty = size / price
        self.cash -= size

        self.positions[symbol] = {
            "qty": qty,
            "entry": price
        }

    def sell(self, symbol, price):
        if symbol not in self.positions:
            return

        pos = self.positions[symbol]
        self.cash += pos["qty"] * price
        del self.positions[symbol]


# =========================
# 🤖 AGENTS
# =========================
class MomentumAI:
    def decide(self, d):
        return ("BUY", 0.8) if d.get("trend") == "UP" else ("HOLD", 0.5)

class MeanReversionAI:
    def decide(self, d):
        return ("BUY", 0.7) if d.get("vol", 0) > 0.6 else ("SELL", 0.6)

class BreakoutAI:
    def decide(self, d):
        return ("BUY", 0.75) if d.get("vol", 0) > 0.7 else ("HOLD", 0.4)

class SentimentAI:
    def decide(self, d):
        return random.choice([("BUY", 0.6), ("SELL", 0.6), ("HOLD", 0.5)])


# =========================
# 🧠 LEARNING SYSTEM
# =========================
class LearningSystem:
    def __init__(self):
        self.agent_score = {
            "MomentumAI": 1.0,
            "MeanReversionAI": 1.0,
            "BreakoutAI": 1.0,
            "SentimentAI": 1.0
        }

    def weight(self, name):
        return self.agent_score.get(name, 1.0)

    def update(self, name, pnl):
        score = self.agent_score.get(name, 1.0)
        score *= (1.02 if pnl > 0 else 0.98)
        self.agent_score[name] = max(0.3, min(3.0, score))


# =========================
# 📊 ANALYTICS
# =========================
class Analytics:
    def __init__(self):
        self.pnl_history = defaultdict(list)

    def update(self, agent, pnl):
        self.pnl_history[agent].append(pnl)

    def sharpe(self, agent):
        data = self.pnl_history[agent]
        if len(data) < 2:
            return 0.0

        avg = sum(data) / len(data)
        var = sum((x - avg) ** 2 for x in data) / len(data)

        return avg / math.sqrt(var) if var != 0 else 0


# =========================
# 🧠 DECISION ENGINE
# =========================
def decide(votes, weights):
    score = {"BUY": 0, "SELL": 0, "HOLD": 0}

    for (a, c), w in zip(votes, weights):
        score[a] += c * w

    best = max(score, key=score.get)
    total = sum(score.values()) + 1e-9

    return best, score[best] / total


# =========================
# ⚠️ RISK
# =========================
class Risk:
    def approve(self, portfolio, action, conf):
        return portfolio.equity > 4000 and conf > 0.55 and action != "HOLD"


# =========================
# 📉 TRADE MANAGER
# =========================
class TradeManager:
    def __init__(self):
        self.stop_loss = 0.03
        self.take_profit = 0.06

    def check_exit(self, portfolio, symbol, price):
        if symbol not in portfolio.positions:
            return False

        pos = portfolio.positions[symbol]
        change = (price - pos["entry"]) / pos["entry"]

        return change <= -self.stop_loss or change >= self.take_profit


# =========================
# 🧬 EVOLUTION ENGINE
# =========================
class EvolutionEngine:
    def __init__(self, learn):
        self.learn = learn

    def mutate(self, agent):
        class Wrapped:
            def decide(self, d):
                try:
                    a, c = agent.decide(d)
                except:
                    return "HOLD", 0.5

                if random.random() < 0.03:
                    return random.choice(["BUY", "SELL"]), 0.9

                return a, c

        return Wrapped()


# =========================
# 🧠 HEAD TRADER
# =========================
class HeadTrader:
    def approve_trade(self, s, a, c, d, portfolio, chop=False):
        if chop or c < 0.6:
            return False
        if a == "BUY" and d.get("trend") == "DOWN":
            return False
        return True


# =========================
# 📊 CHOP DETECTION
# =========================
def detect_chop(mkt):
    vols = [mkt[s]["vol"] for s in mkt if "vol" in mkt[s]]
    if not vols:
        return False

    avg = sum(vols) / len(vols)
    up = sum(1 for s in mkt if mkt[s]["trend"] == "UP")
    down = sum(1 for s in mkt if mkt[s]["trend"] == "DOWN")

    return avg < 0.95 and abs(up - down) < len(mkt) * 0.25


# =========================
# 📊 PERFORMANCE TRACKER
# =========================
class PerformanceTracker:
    def __init__(self):
        self.pnl = defaultdict(float)
        self.trades = defaultdict(int)
        self.history = defaultdict(lambda: deque(maxlen=100))

    def update_trade(self, agent, profit):
        self.pnl[agent] += profit
        self.trades[agent] += 1
        self.history[agent].append(profit)

    def sharpe(self, agent):
        h = list(self.history[agent])
        if len(h) < 2:
            return 0.0

        avg = sum(h) / len(h)
        std = (sum((x - avg) ** 2 for x in h) / len(h)) ** 0.5

        return avg / std if std != 0 else 0


# =========================
# 🧠 TRADE MEMORY
# =========================
class TradeMemory:
    def __init__(self):
        self.memory = defaultdict(lambda: deque(maxlen=50))

    def record(self, agent, conf, result):
        self.memory[agent].append((conf, result))

    def adjust(self, agent, conf):
        m = self.memory[agent]
        if not m:
            return conf

        success = sum(1 for c, r in m if r > 0) / len(m)
        return conf * (0.5 + success)


# =========================
# 💰 COMPOUND ENGINE
# =========================
class CompoundEngine:
    def __init__(self, portfolio):
        self.portfolio = portfolio

    def run(self):
        if self.portfolio.cash <= 0:
            return

        growth = (self.portfolio.equity - self.portfolio.cash) / max(self.portfolio.cash, 1)

        if growth > 0.02:
            self.portfolio.cash += self.portfolio.equity * 0.01