from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import random
import time

app = FastAPI()

# =========================
# MOCK MARKET DATA ENGINE
# (replace later with yfinance / real API)
# =========================
WATCHLIST = ["AAPL", "TSLA", "NVDA", "MSFT", "AMZN", "META", "AMD", "GOOGL"]

def get_market_data(symbol):
    # fake but structured realism
    return {
        "symbol": symbol,
        "price": round(random.uniform(50, 500), 2),
        "volatility": random.uniform(0.5, 3.0),
        "momentum": random.uniform(-2, 2),
        "volume_spike": random.uniform(0, 2),
        "news_sentiment": random.uniform(-1, 1),
        "social_hype": random.uniform(-1, 1)
    }

# =========================
# AI SCORING ENGINE
# =========================
def ai_score(data):
    score =
        (data["momentum"] * 25) +
        (data["news_sentiment"] * 20) +
        (data["social_hype"] * 15) +
        (data["volume_spike"] * 10) -
        (data["volatility"] * 8)

    return max(-100, min(100, score))

def classify(score):
    if score > 35:
        return "BUY"
    elif score < -35:
        return "SELL"
    else:
        return "WATCH"

# =========================
# SCAN ENGINE
# =========================
def scan_market():
    results = []

    for symbol in WATCHLIST:
        data = get_market_data(symbol)
        score = ai_score(data)
        signal = classify(score)

        results.append({
            "symbol": symbol,
            "score": round(score, 2),
            "signal": signal,
            "price": data["price"],
            "momentum": round(data["momentum"], 2),
            "sentiment": round(data["news_sentiment"], 2),
            "hype": round(data["social_hype"], 2)
        })

    # rank strongest first
    results.sort(key=lambda x: x["score"], reverse=True)
    return results

# =========================
# API ENDPOINT
# =========================
@app.get("/scan")
def scan():
    return {
        "timestamp": time.time(),
        "top_picks": scan_market()
    }

# =========================
# SIMPLE UI
# =========================
@app.get("/", response_class=HTMLResponse)
def ui():
    return """
<html>
<head>
<style>
body { background:#0b0f14; color:#00ffcc; font-family:monospace; }
table { width:100%; border-collapse:collapse; }
td, th { padding:8px; border-bottom:1px solid #222; }
.buy { color:#00ff88; }
.sell { color:#ff4d4d; }
.watch { color:#ffd966; }
</style>
</head>

<body>
<h2>AI NEXT DAY STOCK BIAS ENGINE</h2>
<button onclick="load()">SCAN</button>

<table id="table"></table>

<script>
async function load(){
    const r = await fetch("/scan");
    const d = await r.json();

    let rows = "<tr><th>Symbol</th><th>Score</th><th>Signal</th><th>Price</th><th>Momentum</th><th>Sentiment</th></tr>";

    d.top_picks.forEach(s=>{
        rows += `<tr>
            <td>${s.symbol}</td>
            <td>${s.score}</td>
            <td class="${s.signal.toLowerCase()}">${s.signal}</td>
            <td>${s.price}</td>
            <td>${s.momentum}</td>
            <td>${s.sentiment}</td>
        </tr>`;
    });

    document.getElementById("table").innerHTML = rows;
}

load();
</script>

</body>
</html>
"""