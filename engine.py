import random

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

        self.positions[symbol] = {"qty": qty, "entry": price}

    def sell(self, symbol, price):
        if symbol in self.positions:
            pos = self.positions[symbol]
            self.cash += pos["qty"] * price
            del self.positions[symbol]


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
        return random.choice([("BUY",0.6),("SELL",0.6),("HOLD",0.5)])


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
        self.agent_score[name] = self.agent_score.get(name, 1.0)
        self.agent_score[name] *= (1.02 if pnl > 0 else 0.98)
        self.agent_score[name] = max(0.3, min(3.0, self.agent_score[name]))


def decide(votes, weights):
    score = {"BUY":0,"SELL":0,"HOLD":0}

    for (a,c),w in zip(votes, weights):
        score[a] += c*w

    best = max(score, key=score.get)
    total = sum(score.values()) + 1e-9

    return best, score[best]/total


class Risk:
    def approve(self, portfolio, action, conf):
        return portfolio.equity > 4000 and conf > 0.55 and action != "HOLD"


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


class EvolutionEngine:
    def __init__(self, learn):
        self.learn = learn

    def mutate(self, agent):
        class M:
            def decide(self, d):
                try:
                    a,c = agent.decide(d)
                except:
                    return "HOLD",0.5

                if random.random()<0.05:
                    return "BUY",0.9
                if random.random()<0.05:
                    return "SELL",0.9
                return a,c
        return M()


class HeadTrader:
    def approve_trade(self, s,a,c,d,p,chop=False):
        if chop or c < 0.6:
            return False
        if a=="BUY" and d.get("trend")=="DOWN":
            return False
        return True


def detect_chop(mkt):
    vols=[mkt[s]["vol"] for s in mkt if "vol" in mkt[s]]
    if not vols:
        return False
    avg=sum(vols)/len(vols)
    up=sum(1 for s in mkt if mkt[s]["trend"]=="UP")
    down=sum(1 for s in mkt if mkt[s]["trend"]=="DOWN")
    return avg<0.95 and abs(up-down)<len(mkt)*0.25