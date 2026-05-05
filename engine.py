import random

# =========================
# 💰 PORTFOLIO
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
        risk_budget = self.equity * 0.05
        size = risk_budget * max(0.2, min(confidence, 1.0))

        if self.cash < size or price <= 0:
            return

        qty = size / price
        self.cash -= size

        self.positions[symbol] = {
            "qty": qty,
            "entry": price
        }

    def sell(self, symbol, price):
        if symbol in self.positions:
            pos = self.positions[symbol]
            self.cash += pos["qty"] * price
            del self.positions[symbol]


# =========================
# 🤖 AI AGENTS
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
        return random.choice([
            ("BUY", 0.6),
            ("SELL", 0.6),
            ("HOLD", 0.5)
        ])


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
        if name not in self.agent_score:
            self.agent_score[name] = 1.0

        if pnl > 0:
            self.agent_score[name] *= 1.02
        else:
            self.agent_score[name] *= 0.98

        self.agent_score[name] = max(0.3, min(3.0, self.agent_score[name]))


# =========================
# 🧠 META DECIDER
# =========================
def decide(votes, weights):
    score = {"BUY": 0, "SELL": 0, "HOLD": 0}

    for (action, conf), w in zip(votes, weights):
        score[action] += conf * w

    best = max(score, key=score.get)
    total = sum(score.values()) + 1e-9
    conf = score[best] / total

    return best, conf


# =========================
# ⚖️ RISK ENGINE
# =========================
class Risk:
    def approve(self, portfolio, action, conf):
        if portfolio.equity < 4000:
            return False
        if conf < 0.55:
            return False
        if action == "HOLD":
            return False
        return True


# =========================
# 🛑 TRADE MANAGER
# =========================
class TradeManager:
    def __init__(self):
        self.stop_loss = 0.03
        self.take_profit = 0.06

    def check_exit(self, portfolio, symbol, price, trend_signal=0):
        if symbol not in portfolio.positions:
            return False

        pos = portfolio.positions[symbol]
        entry = pos["entry"]

        change = (price - entry) / entry

        if trend_signal == -1 and change > 0.02:
            return True
        if change <= -self.stop_loss:
            return True
        if change >= self.take_profit:
            return True

        return False


# =========================
# 🧠 EVOLUTION ENGINE
# =========================
class EvolutionEngine:
    def __init__(self, learning):
        self.learning = learning

    def mutate(self, agent):
        class Mutated:
            def decide(self, d):
                try:
                    a, c = agent.decide(d)
                except:
                    return "HOLD", 0.5

                if random.random() < 0.08:
                    return ("BUY", 0.9)
                if random.random() < 0.08:
                    return ("SELL", 0.9)
                return a, c

        return Mutated()


# =========================
# 🧠 HEAD TRADER (FIXED)
# =========================
class HeadTrader:
    def __init__(self):
        self.cooldown = {}

    def approve_trade(self, symbol, action, conf, data, portfolio, chop=False):

        trend = data.get("trend", "FLAT")
        vol = data.get("vol", 1)

        if chop:
            return False

        if conf < 0.60:
            return False

        if action == "BUY" and trend == "DOWN" and vol > 1.1:
            return False

        if action == "SELL" and trend == "UP" and vol > 1.1:
            return False

        return True


# =========================
# 🧠 CHOP ZONE DETECTOR (FIXED)
# =========================
def detect_chop(mkt):
    vols = [mkt[s]["vol"] for s in mkt if "vol" in mkt[s]]

    if not vols:
        return False

    avg_vol = sum(vols) / len(vols)

    ups = sum(1 for s in mkt if mkt[s]["trend"] == "UP")
    downs = sum(1 for s in mkt if mkt[s]["trend"] == "DOWN")

    imbalance = abs(ups - downs)

    if avg_vol < 0.95 and imbalance < len(mkt) * 0.25:
        return True

    return False