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
                price = prices[s]
                total += pos["qty"] * price

        self.equity = total

    # =========================
    # 🟢 POSITION SIZING BUY
    # =========================
    def buy(self, symbol, price, confidence=0.5):
        risk_budget = self.equity * 0.05  # 5% max risk per trade
        size = risk_budget * max(0.2, min(confidence, 1.0))

        if self.cash < size:
            return

        qty = size / price
        self.cash -= size

        self.positions[symbol] = {
            "qty": qty,
            "entry": price
        }

    # =========================
    # 🔴 EXIT POSITION
    # =========================
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
# 🧠 META DECIDER (FIXED)
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
# 🛑 TRADE MANAGER (STOP LOSS / TAKE PROFIT)
# =========================
class TradeManager:
    def __init__(self):
        self.stop_loss = 0.03
        self.take_profit = 0.06

    def check_exit(self, portfolio, symbol, price):
        if symbol not in portfolio.positions:
            return False

        pos = portfolio.positions[symbol]
        entry = pos["entry"]

        change = (price - entry) / entry

        if change <= -self.stop_loss:
            return True

        if change >= self.take_profit:
            return True

        return False

        # =========================
# 🧬 STRATEGY EVOLUTION ENGINE (STEP 1)
# =========================
class EvolutionEngine:
    def __init__(self, learning_system):
        self.learn = learning_system

    def evolve(self, agents):
        new_agents = []

        for name, agent in agents:
            score = self.learn.agent_score[name]

            # 🟢 strong strategies survive
            if score > 1.2:
                new_agents.append((name, agent))

            # 🔴 weak strategies removed
            elif score < 0.8:
                continue

            # 🧬 medium strategies mutate
            else:
                mutated = self.mutate(agent)
                new_name = name + "_v2"
                new_agents.append((new_name, mutated))

                # inherit score with noise
                self.learn.agent_score[new_name] = score * random.uniform(0.9, 1.1)

        return new_agents

    # =========================
    # 🧪 MUTATION LOGIC
    # =========================
    def mutate(self, agent):
        class MutatedAgent:
            def decide(self, d):
                base_action, base_conf = agent.decide(d)

                # small random exploration (real trading concept)
                if random.random() < 0.08:
                    return ("BUY", 0.9)
                if random.random() < 0.08:
                    return ("SELL", 0.9)

                return base_action, base_conf

        return MutatedAgent()