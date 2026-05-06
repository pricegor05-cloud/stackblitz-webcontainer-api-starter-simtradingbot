from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import time
import random

app = FastAPI()

# =========================
# CONFIG
# =========================
WATCHLIST = ["AAPL", "TSLA", "NVDA", "MSFT", "AMZN", "META", "AMD"]

# =========================
# SAFE RANDOM MARKET ENGINE (NO DEPENDENCIES)
# =========================
def get_market_data(symbol):
    return {
        "symbol": symbol,
        "price": round(random.uniform(50, 500), 2),
        "returns_5d": random.uniform(-0.05, 0.05),
        "returns_20d": random.uniform(-0.10, 0.10),
        "volatility": random.uniform(0.5, 3.0),
        "volume_trend": random.uniform(-1, 1)
    }

# =========================
# SAFE SOCIAL SENTIMENT (NO API REQUIRED)
# =========================
def social_sentiment(symbol):
    return {
        "tweet_sentiment": random.uniform(-1, 1),
        "tweet_volume": random.randint(0, 20),
        "viral_score": random.uniform(0, 1)
    }

# =========================
# SAFE NEWS SENTIMENT (SIMULATED NLP LAYER)
# =========================
def news_sentiment(symbol):
    return {
        "news_sentiment": random.uniform(-1, 1)
    }

# =========================
# FEATURE BUILDER (ROBUST)
# =========================
def build_features(symbol):
    m = get_market_data(symbol)
    s = social_sentiment(symbol)
    n = news_sentiment(symbol)

    return {
        **m,
        **s,
        **n
    }

# =========================
# SAFE ML MODEL (NO SYNTAX RISK)
# =========================
def ml_model(f):
    score = (
        (f["returns_5d"] * 120) +
        (f["returns_20d"] * 80) +
        (f["tweet_sentiment"] * 50) +
        (f["news_sentiment"] * 60) +
        (f["viral_score"] * 30) +
        (f["volume_trend"] * 25) -
        (f["volatility"] * 20)
    )

    if score > 100:
        score = 100
    if score < -100:
        score = -100

    return score

# =========================
# SIGNAL ENGINE
# =========================
def signal(score):
    if score > 30:
        return "BUY"
    elif score < -30:
        return "SELL"
    return "WATCH"

# =========================
# SCAN ENGINE
# =========================
def scan_market():
    results = []

    for symbol in WATCHLIST:
        f = build_features(symbol)
        score = ml_model(f)

        results.append({
            "symbol": symbol,
            "score": round(score, 2),
            "signal": signal(score),
            "price": f["price"],
            "tweet": round(f["tweet_sentiment"], 2),
            "news": round(f["news_sentiment"], 2),
            "volatility": round(f["volatility"], 2)
        })

    results.sort(key=lambda x: x["score"], reverse=True)
    return results

# =========================
# API ENDPOINT
# =========================
@app.get("/scan")
def scan():
    return {
        "timestamp": time.time(),
        "results": scan_market()
    }

# =========================
# UI (SAFE + SIMPLE)
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

<h2>ZERO ERROR AI STOCK BIAS ENGINE</h2>
<button onclick="load()">SCAN</button>

<table id="table"></table>

<script>
async function load(){
    const r = await fetch("/scan");
    const d = await r.json();

    let html = "<tr><th>Stock</th><th>Score</th><th>Signal</th><th>Price</th><th>Tweet</th><th>News</th></tr>";

    d.results.forEach(x=>{
        html += `<tr>
            <td>${x.symbol}</td>
            <td>${x.score}</td>
            <td>${x.signal}</td>
            <td>${x.price}</td>
            <td>${x.tweet}</td>
            <td>${x.news}</td>
        </tr>`;
    });

    document.getElementById("table").innerHTML = html;
}

load();
</script>

</body>
</html>
"""
@app.get("/ui", response_class=HTMLResponse)
def ui_alias():
    return ui()