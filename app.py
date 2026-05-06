from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import time
import random

# =========================
# OPTIONAL: X API (SAFE FALLBACK)
# =========================
try:
    import tweepy
    X_AVAILABLE = True
except:
    X_AVAILABLE = False

app = FastAPI()

WATCHLIST = ["AAPL", "TSLA", "NVDA", "MSFT", "AMZN", "META", "AMD"]

# =========================
# X CLIENT (OPTIONAL)
# =========================
X_BEARER_TOKEN = None  # put your key here if using

if X_AVAILABLE and X_BEARER_TOKEN:
    x_client = tweepy.Client(bearer_token=X_BEARER_TOKEN, wait_on_rate_limit=True)
else:
    x_client = None

# =========================
# PRICE HISTORY ENGINE (SIM)
# =========================
def get_price_history(symbol):
    return {
        "returns_5d": random.uniform(-0.05, 0.05),
        "returns_20d": random.uniform(-0.10, 0.10),
        "volatility": random.uniform(0.5, 3.0),
        "volume_trend": random.uniform(-1, 1)
    }

# =========================
# TWITTER SENTIMENT (REAL IF AVAILABLE, ELSE SIM)
# =========================
def twitter_sentiment(symbol):

    if not x_client:
        return {
            "tweet_sentiment": random.uniform(-1, 1),
            "tweet_volume": random.randint(0, 20),
            "viral_score": random.uniform(0, 1)
        }

    try:
        query = f"{symbol} stock -is:retweet lang:en"

        tweets = x_client.search_recent_tweets(
            query=query,
            max_results=10,
            tweet_fields=["text"]
        )

        if not tweets.data:
            return {"tweet_sentiment": 0, "tweet_volume": 0, "viral_score": 0}

        bullish = ["buy", "bull", "moon", "long", "breakout", "up"]
        bearish = ["sell", "bear", "crash", "dump", "short", "down"]

        score = 0
        texts = [t.text.lower() for t in tweets.data]

        for t in texts:
            for w in bullish:
                if w in t:
                    score += 1
            for w in bearish:
                if w in t:
                    score -= 1

        volume = len(texts)

        return {
            "tweet_sentiment": max(-1, min(1, score / 10)),
            "tweet_volume": volume,
            "viral_score": min(1, volume / 10)
        }

    except:
        return {"tweet_sentiment": 0, "tweet_volume": 0, "viral_score": 0}

# =========================
# NEWS SENTIMENT (FINBERT PLACEHOLDER)
# =========================
def news_sentiment(symbol):
    return {
        "news_sentiment": random.uniform(-1, 1),
        "news_confidence": random.uniform(0.5, 1.0)
    }

# =========================
# FEATURE BUILDER
# =========================
def build_features(symbol):
    price = get_price_history(symbol)
    twitter = twitter_sentiment(symbol)
    news = news_sentiment(symbol)

    return {**price, **twitter, **news}

# =========================
# ML MODEL (FIXED + CLEAN)
# =========================
def ml_model(f):

    score = (
        (f["returns_5d"] * 120) +
        (f["returns_20d"] * 80) +
        (f["tweet_sentiment"] * 60) +
        (f["news_sentiment"] * 70) +
        (f["viral_score"] * 40) +
        (f["volume_trend"] * 30) -
        (f["volatility"] * 25)
    )

    return max(-100, min(100, score))

# =========================
# SIGNAL ENGINE
# =========================
def signal(score):
    if score > 35:
        return "BUY"
    elif score < -35:
        return "SELL"
    return "WATCH"

# =========================
# SCANNER
# =========================
def scan():
    results = []

    for s in WATCHLIST:
        f = build_features(s)
        score = ml_model(f)

        results.append({
            "symbol": s,
            "score": round(score, 2),
            "signal": signal(score),
            "tweet": round(f["tweet_sentiment"], 2),
            "news": round(f["news_sentiment"], 2),
            "volatility": round(f["volatility"], 2)
        })

    return sorted(results, key=lambda x: x["score"], reverse=True)

# =========================
# API
# =========================
@app.get("/scan")
def scan_api():
    return {
        "timestamp": time.time(),
        "results": scan()
    }

# =========================
# UI
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

<h2>AI STOCK SENTIMENT + ML BIAS ENGINE (CLEAN)</h2>
<button onclick="load()">SCAN</button>

<table id="t"></table>

<script>
async function load(){
    const r = await fetch("/scan");
    const d = await r.json();

    let h = "<tr><th>Stock</th><th>Score</th><th>Signal</th><th>Twitter</th><th>News</th><th>Vol</th></tr>";

    d.results.forEach(x=>{
        h += `<tr>
        <td>${x.symbol}</td>
        <td>${x.score}</td>
        <td>${x.signal}</td>
        <td>${x.tweet}</td>
        <td>${x.news}</td>
        <td>${x.volatility}</td>
        </tr>`;
    });

    document.getElementById("t").innerHTML = h;
}

load();
</script>

</body>
</html>
"""