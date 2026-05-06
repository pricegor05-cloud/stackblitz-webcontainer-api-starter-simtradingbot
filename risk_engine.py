class RiskEngine:
    def __init__(self, max_daily_loss=100):
        self.start_equity = None
        self.max_daily_loss = max_daily_loss

    def reset_day(self, equity):
        self.start_equity = equity

    def allow_trade(self, equity):
        if self.start_equity is None:
            self.start_equity = equity

        return (self.start_equity - equity) < self.max_daily_loss