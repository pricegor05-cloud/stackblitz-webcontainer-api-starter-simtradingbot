import random

# =========================
# 💰 PORTFOLIO (REAL EXECUTION)
# =========================
class Portfolio:
    def __init__(self, cash=5000):
        self.cash = cash
        self.positions = {}  # symbol -> {qty, entry}
        self.equity = cash

    def update(self, prices):
        total = self.cash

        for s, pos in self.positions.items():
            if s in prices:
                total += pos["qty"] * prices[s]

        self.equity = total

    # 🟢 POSITION SIZING BUY
    def buy(self, symbol, price, confidence=0.5):
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

    # 🔴 EXIT POSITION
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
# 🧠 TREND REVERSAL DETECTOR
# =========================
def detect_reversal(data):
    if data["vol"] > 1.2:
        return -1

    if data["trend"] == "DOWN":
        return -1

    if data["trend"] == "UP" and data["vol"] < 0.8:
        return 1

    return 0


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

        # 🔴 early exit on reversal
        if trend_signal == -1 and change > 0.02:
            return True

        # 🔴 stop loss
        if change <= -self.stop_loss:
            return True

        # 🟢 take profit
        if change >= self.take_profit:
            return True

        return False


# =========================
# 🧬 STRATEGY EVOLUTION ENGINE
# =========================
class EvolutionEngine:
    def __init__(self, learning_system):
        self.learn = learning_system

    def evolve(self, agents):
        new_agents = []

        for name, agent in agents:
            score = self.learn.agent_score[name]

            # 🟢 keep strong
            if score > 1.2:
                new_agents.append((name, agent))

            # 🔴 remove weak
            elif score < 0.8:
                continue

            # 🧬 mutate medium
            else:
                mutated = self.mutate(agent)
                new_name = name + "_v2"
                new_agents.append((new_name, mutated))

                self.learn.agent_score[new_name] = score * random.uniform(0.9, 1.1)

        return new_agents

    def mutate(self, agent):
        class MutatedAgent:
            def decide(self, d):
                action, conf = agent.decide(d)

                if random.random() < 0.08:
                    return ("BUY", 0.9)
                if random.random() < 0.08:
                    return ("SELL", 0.9)

                return action, conf

        return MutatedAgent()