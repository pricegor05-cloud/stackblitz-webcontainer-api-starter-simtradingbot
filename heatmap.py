class HeatMap:
    def __init__(self):
        self.exposure = {}

    def update(self, symbol, value):
        self.exposure[symbol] = value

    def total_risk(self):
        return sum(abs(v) for v in self.exposure.values())

    def snapshot(self):
        return dict(self.exposure)