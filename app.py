from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import sqlite3
import re
import os
from datetime import datetime, timezone

# ============================================================
# SMARTAGRI KOPARGAON
# LIVE MARKET + HISTORICAL DATABASE + TREND ANALYSIS
# ============================================================

app = Flask(__name__, static_folder=".")
CORS(app)

# ============================================================
# CONFIGURATION
# ============================================================

MARKET = "Kopargaon APMC"
DISTRICT = "Ahilyanagar"
STATE = "Maharashtra"

SUPPORTED_CROPS = {
    "onion": {
        "commodity": "Onion",
        "url": "https://mandipulse.com/mandi/maharashtra-ahilyanagar-kopargaon-apmc/onion",
    },
    "wheat": {
        "commodity": "Wheat",
        "url": "https://mandipulse.com/mandi/maharashtra-ahilyanagar-kopargaon-apmc/wheat",
    },
}

# Render has a writable temporary filesystem.
# For persistent production history, use a persistent disk/database later.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(BASE_DIR, "smartagri.db")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/151.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;"
        "q=0.9,image/avif,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://mandipulse.com/",
    "Connection": "keep-alive",
}

REQUEST_TIMEOUT = 30


# ============================================================
# DATABASE
# ============================================================

def get_db():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_database():
    connection = get_db()

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS market_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            crop TEXT NOT NULL,
            commodity TEXT NOT NULL,

            market TEXT NOT NULL,
            district TEXT NOT NULL,
            state TEXT NOT NULL,

            variety TEXT,
            grade TEXT,

            arrival_date TEXT,

            min_price REAL NOT NULL,
            max_price REAL NOT NULL,
            modal_price REAL NOT NULL,

            unit TEXT NOT NULL,

            source TEXT,
            source_url TEXT,

            retrieved_at TEXT NOT NULL,
            created_at TEXT NOT NULL,

            UNIQUE(crop, arrival_date, modal_price)
        )
        """
    )

    connection.commit()
    connection.close()

    print()
    print("=" * 60)
    print("DATABASE READY")
    print("=" * 60)
    print("Database:", DATABASE_PATH)
    print("=" * 60)
    print()


# ============================================================
# HELPERS
# ============================================================

def now_utc():
    return datetime.now(timezone.utc).isoformat()


def clean_text(value):
    if value is None:
        return ""

    return re.sub(r"\s+", " ", str(value)).strip()


def extract_number(text):
    if not text:
        return None

    text = str(text).replace(",", "").replace("₹", "")

    match = re.search(r"(\d+(?:\.\d+)?)", text)

    if not match:
        return None

    value = float(match.group(1))

    if value.is_integer():
        return int(value)

    return value


def crop_config(crop):
    crop = crop.strip().lower()

    if crop not in SUPPORTED_CROPS:
        return None

    return SUPPORTED_CROPS[crop]


# ============================================================
# FETCH MARKET PAGE
# ============================================================

def fetch_market_page(crop):
    config = crop_config(crop)

    if not config:
        raise ValueError("Unsupported crop. Use onion or wheat.")

    url = config["url"]

    print()
    print("=" * 50)
    print("SMARTAGRI MARKET REQUEST")
    print("Crop:", crop)
    print("Source:", url)
    print("=" * 50)

    response = requests.get(
        url,
        headers=HEADERS,
        timeout=REQUEST_TIMEOUT,
        allow_redirects=True,
    )

    response.raise_for_status()

    return response.text, url


# ============================================================
# PARSE MARKET PAGE
# ============================================================

def parse_market_page(html, crop, source_url):
    config = crop_config(crop)

    if not config:
        raise ValueError("Unsupported crop.")

    commodity = config["commodity"]

    soup = BeautifulSoup(html, "html.parser")

    # Get visible text.
    text = soup.get_text(" ", strip=True)
    text = clean_text(text)

    if not text:
        raise RuntimeError("External market page returned no readable data.")

    # --------------------------------------------------------
    # DATE
    # --------------------------------------------------------

    arrival_date = None

    date_patterns = [
        r"Updated on:\s*([0-9]{1,2}\s+[A-Za-z]{3,9}\s+[0-9]{4})",
        r"Updated:\s*([0-9]{1,2}\s+[A-Za-z]{3,9}\s+[0-9]{4})",
        r"([0-9]{1,2}\s+[A-Za-z]{3,9}\s+[0-9]{4})",
    ]

    for pattern in date_patterns:
        match = re.search(pattern, text, re.IGNORECASE)

        if match:
            raw_date = clean_text(match.group(1))

            for fmt in (
                "%d %b %Y",
                "%d %B %Y",
                "%d %b %Y",
            ):
                try:
                    arrival_date = datetime.strptime(
                        raw_date,
                        fmt
                    ).strftime("%Y-%m-%d")
                    break
                except ValueError:
                    pass

            if arrival_date:
                break

    # If page does not expose a readable date, use retrieval date.
    if not arrival_date:
        arrival_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # --------------------------------------------------------
    # MINIMUM / MAXIMUM PRICE
    # --------------------------------------------------------

    min_price = None
    max_price = None

    range_patterns = [
        r"Min:\s*₹?\s*([\d,]+(?:\.\d+)?)\s*\|\s*Max:\s*₹?\s*([\d,]+(?:\.\d+)?)",
        r"Min:\s*₹?\s*([\d,]+(?:\.\d+)?).*?Max:\s*₹?\s*([\d,]+(?:\.\d+)?)",
        r"Minimum:\s*₹?\s*([\d,]+(?:\.\d+)?).*?Maximum:\s*₹?\s*([\d,]+(?:\.\d+)?)",
    ]

    for pattern in range_patterns:
        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:
            min_price = extract_number(match.group(1))
            max_price = extract_number(match.group(2))
            break

    # --------------------------------------------------------
    # MODAL PRICE
    # --------------------------------------------------------

    modal_price = None

    modal_patterns = [
        rf"{commodity}\s+Price\s+Today.*?₹\s*([\d,]+(?:\.\d+)?)\s*/\s*Quintal",
        rf"₹\s*([\d,]+(?:\.\d+)?)\s*/\s*Quintal",
        rf"₹\s*([\d,]+(?:\.\d+)?)\s*per\s*Quintal",
    ]

    for pattern in modal_patterns:
        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:
            modal_price = extract_number(match.group(1))
            break

    # --------------------------------------------------------
    # SECONDARY PRICE EXTRACTION
    # --------------------------------------------------------

    if modal_price is None:
        prices = []

        for match in re.finditer(
            r"₹?\s*([\d,]+(?:\.\d+)?)",
            text
        ):
            value = extract_number(match.group(1))

            if value is not None and 100 <= value <= 100000:
                prices.append(value)

        if prices:
            # Prefer a value near the commodity/price text.
            modal_price = prices[0]

    # --------------------------------------------------------
    # VARIETY
    # --------------------------------------------------------

    variety = ""

    variety_match = re.search(
        r"Variety:\s*([^|]+?)(?:\s+Grade:|\s+Min:|\s+Max:|$)",
        text,
        re.IGNORECASE
    )

    if variety_match:
        variety = clean_text(variety_match.group(1))

    # --------------------------------------------------------
    # GRADE
    # --------------------------------------------------------

    grade = ""

    grade_match = re.search(
        r"Grade:\s*([^|]+?)(?:\s+Min:|\s+Max:|\s+Modal:|$)",
        text,
        re.IGNORECASE
    )

    if grade_match:
        grade = clean_text(grade_match.group(1))

    # --------------------------------------------------------
    # FALLBACK METADATA EXTRACTION
    # --------------------------------------------------------

    if not variety:
        variety_match = re.search(
            r"([A-Za-z]+)\s+variety",
            text,
            re.IGNORECASE
        )

        if variety_match:
            variety = clean_text(variety_match.group(1))

    # Avoid storing huge page descriptions as grade.
    if len(grade) > 250:
        grade = grade[:250]

    # --------------------------------------------------------
    # VALIDATION
    # --------------------------------------------------------

    if modal_price is None:
        raise RuntimeError(
            "Could not find the modal/latest price on the external market page."
        )

    if min_price is None:
        min_price = modal_price

    if max_price is None:
        max_price = modal_price

    if min_price > max_price:
        min_price, max_price = max_price, min_price

    # --------------------------------------------------------
    # RESULT
    # --------------------------------------------------------

    return {
        "success": True,
        "crop": crop,
        "commodity": commodity,
        "market": MARKET,
        "district": DISTRICT,
        "state": STATE,
        "variety": variety,
        "grade": grade,
        "arrival_date": arrival_date,
        "min_price": float(min_price),
        "max_price": float(max_price),
        "modal_price": float(modal_price),
        "unit": "Rs./Quintal",
        "source": "MandiPulse / Agmarknet Government Market Data",
        "source_url": source_url,
        "retrieved_at": now_utc(),
    }


# ============================================================
# STORE RECORD
# ============================================================

def store_record(record):
    connection = get_db()

    try:
        cursor = connection.execute(
            """
            INSERT OR IGNORE INTO market_history (
                crop,
                commodity,
                market,
                district,
                state,
                variety,
                grade,
                arrival_date,
                min_price,
                max_price,
                modal_price,
                unit,
                source,
                source_url,
                retrieved_at,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record["crop"],
                record["commodity"],
                record["market"],
                record["district"],
                record["state"],
                record.get("variety", ""),
                record.get("grade", ""),
                record.get("arrival_date"),
                record["min_price"],
                record["max_price"],
                record["modal_price"],
                record["unit"],
                record.get("source", ""),
                record.get("source_url", ""),
                record["retrieved_at"],
                now_utc(),
            )
        )

        connection.commit()

        stored = cursor.rowcount > 0

        # If today's exact record already exists, retrieve it.
        if not stored:
            existing = connection.execute(
                """
                SELECT *
                FROM market_history
                WHERE crop = ?
                  AND arrival_date = ?
                  AND modal_price = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (
                    record["crop"],
                    record["arrival_date"],
                    record["modal_price"],
                )
            ).fetchone()

            if existing:
                record = dict(existing)

        return stored, record

    finally:
        connection.close()


# ============================================================
# GET HISTORY
# ============================================================

def get_history(crop, limit=365):
    connection = get_db()

    rows = connection.execute(
        """
        SELECT *
        FROM market_history
        WHERE crop = ?
        ORDER BY arrival_date ASC, id ASC
        LIMIT ?
        """,
        (crop, limit)
    ).fetchall()

    connection.close()

    return [dict(row) for row in rows]


# ============================================================
# TREND CALCULATION
# ============================================================

def calculate_trend(records):
    prices = [
        float(record["modal_price"])
        for record in records
        if record.get("modal_price") is not None
    ]

    if not prices:
        return {
            "direction": "insufficient_data",
            "strength": "insufficient_data",
            "current_price": None,
            "previous_price": None,
            "change_percent": None,
        }

    current_price = prices[-1]

    if len(prices) < 2:
        return {
            "direction": "insufficient_data",
            "strength": "insufficient_data",
            "current_price": current_price,
            "previous_price": None,
            "change_percent": None,
        }

    previous_price = prices[-2]

    if previous_price == 0:
        change_percent = None
    else:
        change_percent = (
            (current_price - previous_price)
            / previous_price
        ) * 100

    if change_percent is None:
        direction = "insufficient_data"
        strength = "insufficient_data"

    elif change_percent > 0.5:
        direction = "rising"
        strength = "strong" if change_percent >= 3 else "moderate"

    elif change_percent < -0.5:
        direction = "falling"
        strength = "strong" if change_percent <= -3 else "moderate"

    else:
        direction = "stable"
        strength = "weak"

    return {
        "direction": direction,
        "strength": strength,
        "current_price": current_price,
        "previous_price": previous_price,
        "change_percent": round(change_percent, 2)
        if change_percent is not None
        else None,
    }


# ============================================================
# MOVING AVERAGE
# ============================================================

def moving_average(prices, window):
    if not prices:
        return None

    selected = prices[-window:]

    if not selected:
        return None

    return round(
        sum(selected) / len(selected),
        2
    )


# ============================================================
# SIMPLE PRICE PREDICTION
# ============================================================

def calculate_prediction(records):
    prices = [
        float(record["modal_price"])
        for record in records
        if record.get("modal_price") is not None
    ]

    if len(prices) < 3:
        return {
            "direction": "insufficient_data",
            "estimated_price": None,
            "confidence": "low",
            "reason": (
                "At least 3 historical price records are recommended "
                "for a trend-based estimate."
            ),
            "unit": "Rs./Quintal",
        }

    recent = prices[-3:]

    first = recent[0]
    last = recent[-1]

    change = last - first

    average_change = change / 2

    estimated_price = last + average_change

    # Prevent an unrealistic negative prediction.
    estimated_price = max(0, estimated_price)

    percent_change = (
        (change / first) * 100
        if first != 0
        else 0
    )

    if percent_change > 2:
        direction = "rising"

    elif percent_change < -2:
        direction = "falling"

    else:
        direction = "stable"

    if len(prices) >= 7:
        confidence = "medium"
    else:
        confidence = "low"

    return {
        "direction": direction,
        "estimated_price": round(estimated_price, 2),
        "confidence": confidence,
        "reason": (
            "Estimate based on the recent historical modal-price trend. "
            "This is an analytical estimate, not a guaranteed future price."
        ),
        "unit": "Rs./Quintal",
    }


# ============================================================
# FULL ANALYSIS
# ============================================================

def analyze_history(records):
    prices = [
        float(record["modal_price"])
        for record in records
        if record.get("modal_price") is not None
    ]

    if not prices:
        return {
            "average_price": None,
            "highest_price": None,
            "lowest_price": None,
            "moving_average_3": None,
            "moving_average_7": None,
            "moving_average_14": None,
            "trend": calculate_trend(records),
            "prediction": calculate_prediction(records),
        }

    return {
        "average_price": round(
            sum(prices) / len(prices),
            2
        ),

        "highest_price": max(prices),

        "lowest_price": min(prices),

        "moving_average_3": moving_average(
            prices,
            3
        ),

        "moving_average_7": moving_average(
            prices,
            7
        ),

        "moving_average_14": moving_average(
            prices,
            14
        ),

        "trend": calculate_trend(records),

        "prediction": calculate_prediction(records),
    }


# ============================================================
# FETCH + STORE + ANALYZE
# ============================================================

def collect_market_data(crop):
    html, source_url = fetch_market_page(crop)

    record = parse_market_page(
        html,
        crop,
        source_url
    )

    stored, stored_record = store_record(record)

    history = get_history(crop)

    analysis = analyze_history(history)

    stored_record["stored"] = stored

    return {
        "success": True,
        "stored": stored,
        "record": stored_record,
        "analysis": analysis,
        "message": (
            "Market data fetched, processed, stored, "
            "and analyzed successfully."
        ),
    }


# ============================================================
# API: HEALTH
# ============================================================

@app.route("/api/health")
def health():
    connection = get_db()

    total = connection.execute(
        "SELECT COUNT(*) AS count FROM market_history"
    ).fetchone()["count"]

    onion = connection.execute(
        """
        SELECT COUNT(*) AS count
        FROM market_history
        WHERE crop = 'onion'
        """
    ).fetchone()["count"]

    wheat = connection.execute(
        """
        SELECT COUNT(*) AS count
        FROM market_history
        WHERE crop = 'wheat'
        """
    ).fetchone()["count"]

    connection.close()

    return jsonify({
        "success": True,
        "backend": "SmartAgri Flask",
        "database": "SQLite",
        "database_path": DATABASE_PATH,
        "market": MARKET,
        "district": DISTRICT,
        "state": STATE,
        "market_source": "MandiPulse / Agmarknet",
        "fallback": False,
        "supported_crops": list(SUPPORTED_CROPS.keys()),
        "total_history_records": total,
        "onion_records": onion,
        "wheat_records": wheat,
    })


# ============================================================
# API: COLLECT
# ============================================================

@app.route("/api/collect")
def collect():
    crop = request.args.get(
        "crop",
        ""
    ).strip().lower()

    if crop not in SUPPORTED_CROPS:
        return jsonify({
            "success": False,
            "message": (
                "Unsupported crop. Use onion or wheat."
            ),
        }), 400

    print()
    print("=" * 50)
    print("🌾 SMARTAGRI DATA COLLECTION")
    print("Selected crop:", crop)
    print("=" * 50)

    try:
        result = collect_market_data(crop)

        return jsonify(result)

    except requests.RequestException as error:
        print()
        print("❌ SOURCE CONNECTION ERROR")
        print(error)

        return jsonify({
            "success": False,
            "fallback": False,
            "data_mode": "external_live_plus_history",
            "message": (
                "Unable to connect to the external market "
                "data source."
            ),
            "error": str(error),
        }), 502

    except Exception as error:
        print()
        print("❌ COLLECTION ERROR")
        print(error)

        return jsonify({
            "success": False,
            "fallback": False,
            "data_mode": "external_live_plus_history",
            "message": (
                "The external market source did not return "
                "a usable price record."
            ),
            "error": str(error),
        }), 502


# ============================================================
# API: MARKET
# ============================================================

@app.route("/api/market")
def market():
    crop = request.args.get(
        "crop",
        ""
    ).strip().lower()

    if crop not in SUPPORTED_CROPS:
        return jsonify({
            "success": False,
            "message": (
                "Unsupported crop. Use onion or wheat."
            ),
        }), 400

    print()
    print("=" * 50)
    print("🌾 SMARTAGRI MARKET ANALYSIS")
    print("Selected crop:", crop)
    print("=" * 50)

    try:
        result = collect_market_data(crop)

        history = get_history(crop)

        latest = history[-1] if history else None

        return jsonify({
            "success": True,
            "data_mode": "external_live_plus_history",
            "fallback": False,

            "market": MARKET,
            "district": DISTRICT,
            "state": STATE,

            "history_count": len(history),

            "latest": latest,

            "analysis": result["analysis"],

            "message": (
                "Latest market data retrieved, stored, "
                "and analyzed against historical records."
            ),
        })

    except requests.RequestException as error:
        print()
        print("❌ SOURCE CONNECTION ERROR")
        print(error)

        return jsonify({
            "success": False,
            "data_mode": "external_live_plus_history",
            "fallback": False,
            "market": MARKET,
            "district": DISTRICT,
            "state": STATE,
            "message": (
                "Live external market data is currently "
                "unavailable. No fallback price is being shown."
            ),
            "error": str(error),
        }), 502

    except Exception as error:
        print()
        print("❌ MARKET ANALYSIS ERROR")
        print(error)

        return jsonify({
            "success": False,
            "data_mode": "external_live_plus_history",
            "fallback": False,
            "market": MARKET,
            "district": DISTRICT,
            "state": STATE,
            "message": (
                "Market data could not be processed."
            ),
            "error": str(error),
        }), 502


# ============================================================
# API: HISTORY
# ============================================================

@app.route("/api/history")
def history():
    crop = request.args.get(
        "crop",
        ""
    ).strip().lower()

    if crop not in SUPPORTED_CROPS:
        return jsonify({
            "success": False,
            "message": (
                "Unsupported crop. Use onion or wheat."
            ),
        }), 400

    try:
        limit = int(
            request.args.get(
                "limit",
                "365"
            )
        )

    except ValueError:
        limit = 365

    limit = max(1, min(limit, 5000))

    records = get_history(
        crop,
        limit
    )

    analysis = analyze_history(records)

    commodity = SUPPORTED_CROPS[crop]["commodity"]

    return jsonify({
        "success": True,

        "crop": crop,
        "commodity": commodity,

        "market": MARKET,
        "district": DISTRICT,
        "state": STATE,

        "count": len(records),

        "records": records,

        "analysis": analysis,
    })


# ============================================================
# API: CLEAR HISTORY
# ============================================================

@app.route("/api/clear-history")
def clear_history():
    crop = request.args.get(
        "crop",
        ""
    ).strip().lower()

    if crop not in SUPPORTED_CROPS:
        return jsonify({
            "success": False,
            "message": (
                "Unsupported crop. Use onion or wheat."
            ),
        }), 400

    connection = get_db()

    connection.execute(
        """
        DELETE FROM market_history
        WHERE crop = ?
        """,
        (crop,)
    )

    connection.commit()
    connection.close()

    return jsonify({
        "success": True,
        "message": f"History cleared for {crop}.",
    })


# ============================================================
# SERVE FRONTEND
# ============================================================

@app.route("/")
def home():
    return send_from_directory(
        BASE_DIR,
        "index.html"
    )


@app.route("/<path:filename>")
def files(filename):
    return send_from_directory(
        BASE_DIR,
        filename
    )


# ============================================================
# STARTUP
# ============================================================

init_database()


if __name__ == "__main__":

    print()
    print("=" * 60)
    print("🌾 SMARTAGRI KOPARGAON")
    print("=" * 60)
    print("LIVE MARKET + HISTORICAL DATA + TREND ANALYSIS")
    print("-" * 60)
    print("🧅 Onion")
    print("🌾 Wheat")
    print("-" * 60)
    print("Market:", MARKET)
    print("District:", DISTRICT)
    print("State:", STATE)
    print("-" * 60)
    print("Database:", DATABASE_PATH)
    print("-" * 60)
    print("API:")
    print("http://127.0.0.1:5000/api/health")
    print("http://127.0.0.1:5000/api/market?crop=onion")
    print("http://127.0.0.1:5000/api/market?crop=wheat")
    print("http://127.0.0.1:5000/api/history?crop=onion")
    print("http://127.0.0.1:5000/api/history?crop=wheat")
    print("http://127.0.0.1:5000/api/collect?crop=onion")
    print("http://127.0.0.1:5000/api/collect?crop=wheat")
    print("=" * 60)
    print()

    port = int(
        os.environ.get(
            "PORT",
            "5000"
        )
    )

    app.run(
        host="0.0.0.0",
        port=port,
        debug=True
    )
