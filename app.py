```python
from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS
import requests
import sqlite3
import os
import re
from datetime import datetime, timezone


# ============================================================
# SMARTAGRI KOPARGAON
# GOVERNMENT OGD / AGMARKNET MARKET DATA
# HISTORICAL DATABASE + TREND ANALYSIS
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
    },
    "wheat": {
        "commodity": "Wheat",
    },
}

# Government of India OGD / AGMARKNET resource
DATA_GOV_RESOURCE_ID = "9ef84268-d588-465a-a308-a864a43d0070"

DATA_GOV_API_URL = (
    f"https://api.data.gov.in/resource/{DATA_GOV_RESOURCE_ID}"
)

# API key MUST be stored as an environment variable.
#
# Windows local:
#   set DATA_GOV_API_KEY=YOUR_KEY
#
# Render:
#   Dashboard -> Environment -> Add Environment Variable
#   Name: DATA_GOV_API_KEY
#
DATA_GOV_API_KEY = os.environ.get("DATA_GOV_API_KEY", "").strip()

REQUEST_TIMEOUT = 30

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(BASE_DIR, "smartagri.db")


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
# GENERAL HELPERS
# ============================================================

def now_utc():
    return datetime.now(timezone.utc).isoformat()


def clean_text(value):
    if value is None:
        return ""

    return re.sub(r"\s+", " ", str(value)).strip()


def normalize_text(value):
    value = clean_text(value).lower()

    value = value.replace("apmc", "")
    value = value.replace("market", "")
    value = value.replace("-", " ")

    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def extract_number(value):
    if value is None:
        return None

    text = str(value)

    text = text.replace(",", "")
    text = text.replace("₹", "")
    text = text.replace("Rs.", "")
    text = text.replace("Rs", "")

    match = re.search(r"-?\d+(?:\.\d+)?", text)

    if not match:
        return None

    try:
        return float(match.group(0))
    except ValueError:
        return None


def crop_config(crop):
    crop = crop.strip().lower()

    return SUPPORTED_CROPS.get(crop)


def normalize_date(value):
    if not value:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")

    text = clean_text(value)

    formats = [
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%d/%m/%y",
        "%d-%m-%y",
        "%d %b %Y",
        "%d %B %Y",
        "%d-%b-%Y",
        "%d-%B-%Y",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(text, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass

    # Try extracting a YYYY-MM-DD date from a larger string.
    match = re.search(
        r"\b(20\d{2})[-/](\d{1,2})[-/](\d{1,2})\b",
        text
    )

    if match:
        try:
            return datetime(
                int(match.group(1)),
                int(match.group(2)),
                int(match.group(3))
            ).strftime("%Y-%m-%d")
        except ValueError:
            pass

    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def get_field(record, possible_names):
    """
    Return the first matching field from a data.gov.in record.
    Handles different capitalization/spelling.
    """

    if not isinstance(record, dict):
        return None

    normalized_record = {}

    for key, value in record.items():
        normalized_key = re.sub(
            r"[^a-z0-9]",
            "",
            str(key).lower()
        )

        normalized_record[normalized_key] = value

    for name in possible_names:
        normalized_name = re.sub(
            r"[^a-z0-9]",
            "",
            str(name).lower()
        )

        if normalized_name in normalized_record:
            return normalized_record[normalized_name]

    return None


# ============================================================
# GOVERNMENT DATA.GOV.IN API
# ============================================================

def fetch_government_market_data(crop):
    """
    Fetch current AGMARKNET mandi data from India's
    Government Open Data API.

    We filter by:
      State = Maharashtra
      District = Ahilyanagar
      Commodity = Onion/Wheat

    Then locally select Kopargaon APMC.
    """

    config = crop_config(crop)

    if not config:
        raise ValueError("Unsupported crop. Use onion or wheat.")

    if not DATA_GOV_API_KEY:
        raise RuntimeError(
            "DATA_GOV_API_KEY is not configured. "
            "Create a data.gov.in API key and add it as an "
            "environment variable."
        )

    commodity = config["commodity"]

    print()
    print("=" * 60)
    print("SMARTAGRI GOVERNMENT MARKET REQUEST")
    print("=" * 60)
    print("Crop:", crop)
    print("Commodity:", commodity)
    print("Market:", MARKET)
    print("District:", DISTRICT)
    print("State:", STATE)
    print("Source: Government of India OGD / AGMARKNET")
    print("Resource:", DATA_GOV_RESOURCE_ID)
    print("=" * 60)

    params = {
        "api-key": DATA_GOV_API_KEY,
        "format": "json",

        # Retrieve enough records so Kopargaon can be found.
        "limit": 1000,

        # Government dataset filters.
        "filters[state]": STATE,
        "filters[district]": DISTRICT,
        "filters[commodity]": commodity,
    }

    response = requests.get(
        DATA_GOV_API_URL,
        params=params,
        timeout=REQUEST_TIMEOUT,
    )

    response.raise_for_status()

    try:
        payload = response.json()
    except ValueError:
        raise RuntimeError(
            "Government API returned a non-JSON response."
        )

    if not isinstance(payload, dict):
        raise RuntimeError(
            "Government API returned an unexpected response."
        )

    records = payload.get("records", [])

    if not isinstance(records, list):
        records = []

    print("Government API records received:", len(records))

    if not records:
        raise RuntimeError(
            "Government API returned no records for "
            f"{commodity} in {DISTRICT}, {STATE}."
        )

    # --------------------------------------------------------
    # SELECT KOPARGAON
    # --------------------------------------------------------

    market_candidates = []

    wanted_market = normalize_text(MARKET)

    for record in records:

        record_market = get_field(
            record,
            [
                "market",
                "Market",
                "market_name",
                "Market Name",
            ]
        )

        if not record_market:
            continue

        normalized_market = normalize_text(record_market)

        # Strong match:
        # "Kopargaon APMC" -> "kopargaon"
        if "kopargaon" in normalized_market:
            market_candidates.append(record)

        elif wanted_market and wanted_market in normalized_market:
            market_candidates.append(record)

    if not market_candidates:
        # Provide useful debugging information.
        available_markets = []

        for record in records:
            record_market = get_field(
                record,
                [
                    "market",
                    "Market",
                    "market_name",
                    "Market Name",
                ]
            )

            if record_market:
                available_markets.append(
                    clean_text(record_market)
                )

        available_markets = list(
            dict.fromkeys(available_markets)
        )

        raise RuntimeError(
            "Kopargaon market was not found in the government "
            "API response. Available markets: "
            + ", ".join(available_markets[:20])
        )

    # --------------------------------------------------------
    # CHOOSE LATEST KOPARGAON RECORD
    # --------------------------------------------------------

    def record_date(record):
        value = get_field(
            record,
            [
                "arrival_date",
                "Arrival Date",
                "date",
                "Date",
            ]
        )

        return normalize_date(value)

    market_candidates.sort(
        key=record_date,
        reverse=True
    )

    selected = market_candidates[0]

    print("Selected government record:")
    print(selected)

    return selected


# ============================================================
# CONVERT GOVERNMENT RECORD TO SMARTAGRI RECORD
# ============================================================

def parse_government_record(raw_record, crop):
    config = crop_config(crop)

    if not config:
        raise ValueError("Unsupported crop.")

    commodity = config["commodity"]

    market_value = get_field(
        raw_record,
        [
            "market",
            "Market",
            "market_name",
            "Market Name",
        ]
    )

    district_value = get_field(
        raw_record,
        [
            "district",
            "District",
        ]
    )

    state_value = get_field(
        raw_record,
        [
            "state",
            "State",
        ]
    )

    variety = get_field(
        raw_record,
        [
            "variety",
            "Variety",
        ]
    )

    grade = get_field(
        raw_record,
        [
            "grade",
            "Grade",
        ]
    )

    arrival_date = get_field(
        raw_record,
        [
            "arrival_date",
            "Arrival Date",
            "date",
            "Date",
        ]
    )

    min_price = get_field(
        raw_record,
        [
            "min_price",
            "Min Price",
            "minimum_price",
            "Minimum Price",
        ]
    )

    max_price = get_field(
        raw_record,
        [
            "max_price",
            "Max Price",
            "maximum_price",
            "Maximum Price",
        ]
    )

    modal_price = get_field(
        raw_record,
        [
            "modal_price",
            "Modal Price",
            "modalprice",
        ]
    )

    # Some versions of the dataset use these variants.
    if modal_price is None:
        modal_price = get_field(
            raw_record,
            [
                "Modal_Price",
                "ModalPrice",
            ]
        )

    min_price = extract_number(min_price)
    max_price = extract_number(max_price)
    modal_price = extract_number(modal_price)

    if modal_price is None:
        raise RuntimeError(
            "Government API record does not contain a usable modal price."
        )

    if min_price is None:
        min_price = modal_price

    if max_price is None:
        max_price = modal_price

    if min_price > max_price:
        min_price, max_price = max_price, min_price

    actual_market = clean_text(
        market_value
    ) or MARKET

    actual_district = clean_text(
        district_value
    ) or DISTRICT

    actual_state = clean_text(
        state_value
    ) or STATE

    actual_variety = clean_text(
        variety
    )

    actual_grade = clean_text(
        grade
    )

    # Limit metadata length.
    if len(actual_grade) > 250:
        actual_grade = actual_grade[:250]

    if len(actual_variety) > 150:
        actual_variety = actual_variety[:150]

    return {
        "success": True,

        "crop": crop,
        "commodity": commodity,

        "market": actual_market,
        "district": actual_district,
        "state": actual_state,

        "variety": actual_variety,
        "grade": actual_grade,

        "arrival_date": normalize_date(arrival_date),

        "min_price": float(min_price),
        "max_price": float(max_price),
        "modal_price": float(modal_price),

        "unit": "Rs./Quintal",

        "source": (
            "Government of India OGD / AGMARKNET"
        ),

        "source_url": (
            "https://www.data.gov.in/"
        ),

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
# HISTORY
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
# TREND
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

        if change_percent >= 3:
            strength = "strong"
        else:
            strength = "moderate"

    elif change_percent < -0.5:
        direction = "falling"

        if change_percent <= -3:
            strength = "strong"
        else:
            strength = "moderate"

    else:
        direction = "stable"
        strength = "weak"

    return {
        "direction": direction,
        "strength": strength,
        "current_price": current_price,
        "previous_price": previous_price,
        "change_percent": (
            round(change_percent, 2)
            if change_percent is not None
            else None
        ),
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
# PRICE PREDICTION
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
                "At least 3 historical price records are "
                "recommended for a trend-based estimate."
            ),
            "unit": "Rs./Quintal",
        }

    recent = prices[-3:]

    first = recent[0]
    last = recent[-1]

    change = last - first

    average_change = change / 2

    estimated_price = last + average_change

    estimated_price = max(
        0,
        estimated_price
    )

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
        "estimated_price": round(
            estimated_price,
            2
        ),
        "confidence": confidence,
        "reason": (
            "Estimate based on the recent historical "
            "modal-price trend. This is an analytical "
            "estimate, not a guaranteed future price."
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
# COLLECT + STORE + ANALYZE
# ============================================================

def collect_market_data(crop):
    raw_record = fetch_government_market_data(
        crop
    )

    record = parse_government_record(
        raw_record,
        crop
    )

    stored, stored_record = store_record(
        record
    )

    history = get_history(
        crop
    )

    analysis = analyze_history(
        history
    )

    stored_record["stored"] = stored

    return {
        "success": True,
        "stored": stored,

        "record": stored_record,

        "analysis": analysis,

        "message": (
            "Government market data fetched, "
            "processed, stored, and analyzed successfully."
        ),
    }


# ============================================================
# API: HEALTH
# ============================================================

@app.route("/api/health")
def health():
    connection = get_db()

    total = connection.execute(
        """
        SELECT COUNT(*) AS count
        FROM market_history
        """
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

        "market_source": (
            "Government of India OGD / AGMARKNET"
        ),

        "government_api_configured": bool(
            DATA_GOV_API_KEY
        ),

        "government_resource_id": (
            DATA_GOV_RESOURCE_ID
        ),

        "fallback": False,

        "supported_crops": list(
            SUPPORTED_CROPS.keys()
        ),

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
    print("=" * 60)
    print("SMARTAGRI GOVERNMENT DATA COLLECTION")
    print("Selected crop:", crop)
    print("=" * 60)

    try:
        result = collect_market_data(
            crop
        )

        return jsonify(
            result
        )

    except requests.RequestException as error:
        print()
        print("SOURCE CONNECTION ERROR")
        print(error)

        return jsonify({
            "success": False,

            "fallback": False,

            "data_mode": (
                "government_ogd_agmarknet"
            ),

            "message": (
                "Unable to connect to the "
                "Government of India market-data API."
            ),

            "error": str(error),
        }), 502

    except Exception as error:
        print()
        print("COLLECTION ERROR")
        print(error)

        return jsonify({
            "success": False,

            "fallback": False,

            "data_mode": (
                "government_ogd_agmarknet"
            ),

            "message": (
                "Government market data could not "
                "be processed."
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
    print("=" * 60)
    print("SMARTAGRI MARKET ANALYSIS")
    print("Selected crop:", crop)
    print("=" * 60)

    try:
        result = collect_market_data(
            crop
        )

        history = get_history(
            crop
        )

        latest = (
            history[-1]
            if history
            else None
        )

        return jsonify({
            "success": True,

            "data_mode": (
                "government_ogd_agmarknet_plus_history"
            ),

            "fallback": False,

            "market": MARKET,

            "district": DISTRICT,

            "state": STATE,

            "history_count": len(history),

            "latest": latest,

            "analysis": result["analysis"],

            "message": (
                "Latest Government of India market "
                "data retrieved, stored, and analyzed "
                "against historical records."
            ),
        })

    except requests.RequestException as error:
        print()
        print("SOURCE CONNECTION ERROR")
        print(error)

        return jsonify({
            "success": False,

            "data_mode": (
                "government_ogd_agmarknet"
            ),

            "fallback": False,

            "market": MARKET,

            "district": DISTRICT,

            "state": STATE,

            "message": (
                "Government market data is currently "
                "unavailable."
            ),

            "error": str(error),
        }), 502

    except Exception as error:
        print()
        print("MARKET ANALYSIS ERROR")
        print(error)

        return jsonify({
            "success": False,

            "data_mode": (
                "government_ogd_agmarknet"
            ),

            "fallback": False,

            "market": MARKET,

            "district": DISTRICT,

            "state": STATE,

            "message": (
                "Government market data could not "
                "be processed."
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

    limit = max(
        1,
        min(limit, 5000)
    )

    records = get_history(
        crop,
        limit
    )

    analysis = analyze_history(
        records
    )

    commodity = SUPPORTED_CROPS[
        crop
    ]["commodity"]

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

        "message": (
            f"History cleared for {crop}."
        ),
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
    print("SMARTAGRI KOPARGAON")
    print("=" * 60)
    print(
        "GOVERNMENT OGD / AGMARKNET "
        "MARKET DATA + HISTORY + TREND ANALYSIS"
    )
    print("-" * 60)
    print("Onion")
    print("Wheat")
    print("-" * 60)
    print("Market:", MARKET)
    print("District:", DISTRICT)
    print("State:", STATE)
    print("-" * 60)
    print("Government API configured:",
          bool(DATA_GOV_API_KEY))
    print("Resource ID:", DATA_GOV_RESOURCE_ID)
    print("-" * 60)
    print("Database:", DATABASE_PATH)
    print("-" * 60)
    print("API:")
    print(
        "http://127.0.0.1:5000/api/health"
    )
    print(
        "http://127.0.0.1:5000/api/market?crop=onion"
    )
    print(
        "http://127.0.0.1:5000/api/market?crop=wheat"
    )
    print(
        "http://127.0.0.1:5000/api/history?crop=onion"
    )
    print(
        "http://127.0.0.1:5000/api/history?crop=wheat"
    )
    print(
        "http://127.0.0.1:5000/api/collect?crop=onion"
    )
    print(
        "http://127.0.0.1:5000/api/collect?crop=wheat"
    )
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
```
