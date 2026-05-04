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
        for s, q in self.positions.items():
            if s in prices:
                total += q * prices[s]
        self.equity = total

    def buy(self, symbol, price):
        if self.cash <= 0:
            return
        amount = self.equity * 0.1
        qty = amount / price
        self.cash -= amount
        self.positions[symbol] = self.positions.get(symbol, 0) + qty

    def sell(self, symbol, price):
        if symbol in self.positions:
            self.cash += self.positions[symbol] * price
            del self.positions[symbol]


# =========================
# 🤖 AI AGENTS
# =========================
class MomentumAI:
    def decide(self, d):
        return ("BUY", 0.8) if d["trend"] == "UP" else ("HOLD", 0.5)

class MeanReversionAI:
    def decide(self, d):
        return ("BUY", 0.7) if d["vol"] > 0.6 else ("SELL", 0.6)

class BreakoutAI:
    def decide(self, d):
        return ("BUY", 0.75) if d["vol"] > 0.7 else ("HOLD", 0.4)

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
        return self.agent_score[name]

    def update(self, agent_name, pnl):
        if pnl > 0:
            self.agent_score[agent_name] *= 1.02
        else:
            self.agent_score[agent_name] *= 0.98

        self.agent_score[agent_name] = max(0.3, min(3.0, self.agent_score[agent_name]))


# =========================
# 🧠 META DECIDER
# =========================
def decide(votes, weights):
    score = {"BUY": 0, "SELL": 0, "HOLD": 0}

    for (action, conf), w in zip(votes, weights):
        score[action] += conf * w

    best = max(score, key=score.get)
    total = sum(score.values())
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