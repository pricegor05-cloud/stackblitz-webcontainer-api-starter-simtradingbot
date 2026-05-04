import random
import time

# =========================
# 💰 PORTFOLIO ($5000)
# =========================
class Portfolio:
    def __init__(self, cash=5000):
        self.cash = cash
        self.positions = {}
        self.equity = cash

    def update(self, prices):
        total = self.cash
        for s, q in self.positions.items():
            total += q * prices[s]
        self.equity = total

    def buy(self, symbol, price):
        amount = self.equity * 0.1
        qty = amount / price
        self.cash -= amount
        self.positions[symbol] = self.positions.get(symbol, 0) + qty

    def sell(self, symbol, price):
        if symbol in self.positions:
            self.cash += self.positions[symbol] * price
            del self.positions[symbol]


# =========================
# 📊 MARKET
# =========================
STOCKS = ["AAPL", "TSLA", "NVDA", "AMD", "MSFT"]

def market():
    base = {"AAPL":180,"TSLA":200,"NVDA":450,"AMD":140,"MSFT":370}
    out = {}

    for s in STOCKS:
        out[s] = {
            "price": base[s] + random.uniform(-10,10),
            "vol": random.random(),
            "trend": random.choice(["UP","DOWN","SIDEWAYS"])
        }
    return out


# =========================
# 🤖 AI AGENTS
# =========================
class MomentumAI:
    def decide(self,d):
        return ("BUY",0.8) if d["trend"]=="UP" else ("HOLD",0.5)

class MeanReversionAI:
    def decide(self,d):
        return ("BUY",0.7) if d["vol"]>0.6 else ("SELL",0.6)

class BreakoutAI:
    def decide(self,d):
        return ("BUY",0.75) if d["vol"]>0.7 else ("HOLD",0.4)

class SentimentAI:
    def decide(self,d):
        return random.choice([("BUY",0.6),("SELL",0.6),("HOLD",0.5)])


# =========================
# 🧠 SELF-LEARNING CORE
# =========================
class LearningSystem:
    def __init__(self):
        self.agent_score = {
            "MomentumAI":1.0,
            "MeanReversionAI":1.0,
            "BreakoutAI":1.0,
            "SentimentAI":1.0
        }

    def weight(self, name):
        return self.agent_score[name]

    def update(self, agent_name, pnl):
        # reward good decisions
        if pnl > 0:
            self.agent_score[agent_name] *= 1.02
        else:
            self.agent_score[agent_name] *= 0.98

        # clamp stability
        self.agent_score[agent_name] = max(0.3, min(3.0, self.agent_score[agent_name]))


# =========================
# 🧠 META DECIDER (WEIGHTED)
# =========================
def decide(votes, weights):
    score = {"BUY":0,"SELL":0,"HOLD":0}

    for (action,conf),w in zip(votes, weights):
        score[action] += conf * w

    best = max(score, key=score.get)
    conf = score[best] / len(votes)

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
# 🚀 SELF-LEARNING FUND LOOP
# =========================
def run():
    portfolio = Portfolio(5000)
    learn = LearningSystem()
    risk = Risk()

    agents = [
        ("MomentumAI", MomentumAI()),
        ("MeanReversionAI", MeanReversionAI()),
        ("BreakoutAI", BreakoutAI()),
        ("SentimentAI", SentimentAI())
    ]

    while True:
        mkt = market()
        prices = {s:mkt[s]["price"] for s in mkt}
        portfolio.update(prices)

        print("\n💰 EQUITY:", round(portfolio.equity,2))
        print("📊 Agent Scores:", learn.agent_score)

        for symbol, data in mkt.items():

            votes = []
            weights = []

            for name, agent in agents:
                action, conf = agent.decide(data)
                votes.append((action, conf))
                weights.append(learn.weight(name))

            action, conf = decide(votes, weights)

            allowed = risk.approve(portfolio, action, conf)

            print(symbol, action, round(conf,2), "ALLOWED:", allowed)

            if allowed:

                entry = data["price"]

                if action == "BUY":
                    portfolio.buy(symbol, entry)
                    pnl = random.uniform(-2, 3)

                elif action == "SELL":
                    portfolio.sell(symbol, entry)
                    pnl = random.uniform(-3, 2)

                # 🧠 LEARNING STEP
                for name,_ in agents:
                    learn.update(name, pnl)

        time.sleep(2)


run()