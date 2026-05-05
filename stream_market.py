import random
import time
import threading

STOCKS = ["AAPL","TSLA","NVDA","AMD","MSFT","AMZN","META","GOOGL","NFLX","PLTR"]

base_prices = {
    s: random.uniform(100, 500) for s in STOCKS
}

live_market = {}

def generate_tick():
    global base_prices, live_market

    for s in STOCKS:
        drift = random.uniform(-0.3, 0.3)
        base_prices[s] += drift

        price = max(1, base_prices[s])

        momentum = random.uniform(-1, 1)

        live_market[s] = {
            "price": round(price, 2),
            "trend": "UP" if momentum > 0 else "DOWN",
            "vol": random.uniform(0.5, 1.5),
            "momentum": momentum
        }

def stream_loop():
    while True:
        generate_tick()
        time.sleep(1)   # 🔥 real-time tick speed

def market():
    return live_market

# start streaming immediately
threading.Thread(target=stream_loop, daemon=True).start()