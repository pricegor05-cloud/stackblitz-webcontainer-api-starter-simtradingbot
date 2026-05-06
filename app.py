from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import random
import time

app = FastAPI()

WATCHLIST = ["AAPL", "TSLA", "NVDA", "MSFT", "AMZN", "META", "AMD"]

# =========================
# 1. MOCK PRICE HISTORY ENGINE
# =========================
def get_price_history(symbol):
    return {
        "returns_5d": random.uniform(-0.05, 0.05),
        "returns_20d": random.uniform(-0.10, 0.10),
        "volatility": random.uniform(0.5, 3.0),
        "volume_trend": random.uniform(-1, 1)
    }

# =========================
# 2. TWITTER/X SENTIMENT (API READY STUB)
# =========================
def twitter_sentiment(symbol):
    # Replace later with X API (tweepy)
    return {
        "tweet_sentiment": random.uniform(-1, 1),
        "tweet_volume": random.uniform(0, 2),
        "viral_score": random.uniform(-1, 1)
    }

# =========================
# 3. FINBERT-STYLE NEWS NLP (SIMULATED STRUCTURE)
# =========================
def finbert_news_sentiment(symbol):
    # Replace later with transformers pipeline
    return {
        "news_sentiment": random.uniform(-1, 1),
        "news_confidence": random.uniform(0.5, 1.0)
    }

# =========================
# 4. FEATURE ENGINE (ML INPUT VECTOR)
# =========================
def build_features(symbol):
    price = get_price_history(symbol)
    twitter = twitter_sentiment(symbol)
    news = finbert_news_sentiment(symbol)

    return {
        **price,
        **twitter,
        **news
    }

# =========================
# 5. ML MODEL (SIMULATED WEIGHTED REGRESSION)
# =========================
def ml_model(features):
    score =
        (features["returns_5d"] * 120) +
        (features["returns_20d"] * 80) +
        (features["tweet_sentiment"] * 60) +
        (features["news_sentiment"] * 70) +
        (features["viral_score"] * 40) +
        (features["volume_trend"] * 30) -
        (features["volatility"] * 25)

    return max(-100, min(100, score))

# =========================
# 6. SIGNAL CLASSIFIER
# =========================
def signal(score):
    if score > 35:
        return "BUY (Bullish Bias)"
    elif score < -35:
        return "SELL (Bearish Bias)"
    else:
        return "WATCH (Neutral)"

# =========================
# 7. SCANNER ENGINE
# =========================
def scan():
    results = []

    for symbol in WATCHLIST:
        features = build_features(symbol)
        score = ml_model(features)

        results.append({
            "symbol": symbol,
            "score": round(score, 2),
            "signal": signal(score),
            "features": {
                "twitter": round(features["tweet_sentiment"], 2),
                "news": round(features["news_sentiment"], 2),
                "returns_5d": round(features["returns_5d"], 3)
            }
        })

    return sorted(results, key=lambda x: x["score"], reverse=True)

# =========================
# API ENDPOINT
# =========================
@app.get("/scan")
def scan_api():
    return {
        "timestamp": time.time(),
        "results": scan()
    }

# =========================
# UI DASHBOARD
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

<h2>AI SENTIMENT + ML STOCK BIAS ENGINE</h2>
<button onclick="load()">SCAN MARKET</button>

<table id="table"></table>

<script>
async function load(){
    const r = await fetch("/scan");
    const d = await r.json();

    let rows = "<tr><th>Symbol</th><th>Score</th><th>Signal</th><th>Twitter</th><th>News</th><th>5D Return</th></tr>";

    d.results.forEach(s=>{
        rows += `<tr>
            <td>${s.symbol}</td>
            <td>${s.score}</td>
            <td>${s.signal}</td>
            <td>${s.features.twitter}</td>
            <td>${s.features.news}</td>
            <td>${s.features.returns_5d}</td>
        </tr>`;
    });

    document.getElementById("table").innerHTML = rows;
}

load();
</script>

</body>
</html>
"""