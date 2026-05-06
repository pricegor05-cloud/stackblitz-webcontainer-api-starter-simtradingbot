import time
import random

class ExecutionEngine:
    def __init__(self):
        self.orders = []

    def apply_slippage(self, price, side):
        slip = random.uniform(0.0005, 0.002)

        return price * (1 + slip) if side == "BUY" else price * (1 - slip)

    def execute(self, symbol, side, price, qty):
        exec_price = self.apply_slippage(price, side)

        time.sleep(0.05)  # latency simulation

        order = {
            "symbol": symbol,
            "side": side,
            "price": round(exec_price, 4),
            "qty": qty,
            "status": "FILLED",
            "timestamp": time.time()
        }

        self.orders.append(order)
        return order