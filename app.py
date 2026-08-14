from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS
import requests
import sqlite3
import os
import re
import statistics
from datetime import datetime, timezone, date


# ============================================================
# SMARTAGRI KOPARGAON
# ============================================================
#
# MARKET PRICE ENGINE
#
# PRIMARY SOURCE:
# Government of India OGD / AGMARKNET
#
# FEATURES:
# - Government live market data
# - Flexible Kopargaon matching
# - Historical daily storage
# - Latest verified price
# - Actual latest price date
# - Trend detection
# - Decision-making engine
# - Moving averages
# - Short-term estimate
# - Bootstrap data so first deployment is not empty
# - /api/market
# - /api/history
# - /api/collect
# - /api/collect-all
# - /api/health
#
# IMPORTANT:
# No fake "today" price is generated.
# If live data fails, the application returns the latest
# verified stored price and clearly identifies its date.
#
# ============================================================


# ============================================================
# FLASK
# ============================================================

app = Flask(
    __name__,
    static_folder="."
)

CORS(app)


# ============================================================
# MARKET CONFIGURATION
# ============================================================

MARKET_NAME = "Kopargaon"
DISTRICT_NAMES = [
    "Ahilyanagar",
    "Ahmednagar"
]
STATE = "Maharashtra"

CROP_NAMES = {
    "onion": "Onion",
    "wheat": "Wheat"
}


# ============================================================
# GOVERNMENT OGD API
# ============================================================

DATA_GOV_API_KEY = os.environ.get(
    "DATA_GOV_API_KEY",
    ""
).strip()

DATA_GOV_RESOURCE_ID = os.environ.get(
    "DATA_GOV_RESOURCE_ID",
    "9ef84268-d588-465a-a308-a864a43d0070"
).strip()

DATA_GOV_API_URL = (
    "https://api.data.gov.in/resource/"
    + DATA_GOV_RESOURCE_ID
)

DATA_GOV_SOURCE_URL = (
    "https://www.data.gov.in/"
)

REQUEST_TIMEOUT = (
    5,
    12
)


# ============================================================
# DATABASE
# ============================================================
#
# Local:
#     smartagri.db
#
# Render:
#     Set DATABASE_PATH=/data/smartagri.db
#     if using a persistent disk.
#
# ============================================================

DATABASE_PATH = os.environ.get(
    "DATABASE_PATH",
    os.path.join(
        os.path.dirname(
            os.path.abspath(__file__)
        ),
        "smartagri.db"
    )
)


def get_db_connection():

    connection = sqlite3.connect(
        DATABASE_PATH,
        timeout=30
    )

    connection.row_factory = sqlite3.Row

    return connection


# ============================================================
# DATABASE INITIALIZATION
# ============================================================

def init_database():

    database_directory = os.path.dirname(
        os.path.abspath(DATABASE_PATH)
    )

    if database_directory:
        os.makedirs(
            database_directory,
            exist_ok=True
        )

    connection = get_db_connection()

    cursor = connection.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS market_history (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            crop TEXT NOT NULL,

            commodity TEXT NOT NULL,

            market TEXT NOT NULL,

            district TEXT NOT NULL,

            state TEXT NOT NULL,

            arrival_date TEXT NOT NULL,

            variety TEXT,

            grade TEXT,

            min_price REAL NOT NULL,

            max_price REAL NOT NULL,

            modal_price REAL NOT NULL,

            unit TEXT NOT NULL,

            source TEXT NOT NULL,

            source_url TEXT NOT NULL,

            retrieved_at TEXT NOT NULL,

            created_at TEXT NOT NULL,

            is_bootstrap INTEGER DEFAULT 0,

            UNIQUE (
                crop,
                market,
                arrival_date
            )
        )
        """
    )

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS
        idx_market_history_crop_date
        ON market_history (
            crop,
            arrival_date
        )
        """
    )

    connection.commit()
    connection.close()

    print("=" * 70)
    print("SMARTAGRI DATABASE READY")
    print("=" * 70)
    print("Database:", DATABASE_PATH)
    print("=" * 70)


init_database()


# ============================================================
# HTTP HEADERS
# ============================================================

HEADERS = {
    "User-Agent": (
        "SmartAgriKopargaon/2.0 "
        "(Government OGD API Client)"
    ),
    "Accept": "application/json",
}


# ============================================================
# BOOTSTRAP DATA
# ============================================================
#
# These are NOT presented as today's prices.
#
# They are only used if the database is completely empty,
# so the first deployment has a verified starting record.
#
# Latest publicly reported Kopargaon values used here:
#
# Onion:
#   24/07/2026
#   Min 500
#   Max 2356
#   Modal 2100
#
# Wheat:
#   24/07/2026
#   Min 2620
#   Max 2661
#   Modal 2650
#
# Once government data is successfully collected, these
# bootstrap records become historical starting points.
#
# ============================================================

BOOTSTRAP_DATA = {

    "onion": {
        "commodity": "Onion",
        "market": "Kopargaon",
        "district": "Ahilyanagar",
        "state": "Maharashtra",
        "arrival_date": "2026-07-24",
        "variety": "Unhali Local",
        "grade": "",
        "min_price": 500.0,
        "max_price": 2356.0,
        "modal_price": 2100.0,
        "unit": "Rs./Quintal",
        "source": (
            "Initial verified Kopargaon market record; "
            "AGMARKNET-derived public market listing"
        ),
        "source_url": (
            "https://mandibhavindia.in/en/commodity/"
            "onion/maharashtra/ahmednagar/Kopargaon"
        )
    },

    "wheat": {
        "commodity": "Wheat",
        "market": "Kopargaon",
        "district": "Ahilyanagar",
        "state": "Maharashtra",
        "arrival_date": "2026-07-24",
        "variety": "Other",
        "grade": "",
        "min_price": 2620.0,
        "max_price": 2661.0,
        "modal_price": 2650.0,
        "unit": "Rs./Quintal",
        "source": (
            "Initial verified Kopargaon market record; "
            "AGMARKNET-derived public market listing"
        ),
        "source_url": (
            "https://commodityfact.org/mandi-prices/"
            "wheat/maharashtra/ahmednagar/kopargaon"
        )
    }
}


# ============================================================
# TEXT HELPERS
# ============================================================

def clean_text(value):

    if value is None:
        return ""

    return str(value).strip()


def normalize_key(key):

    if key is None:
        return ""

    return re.sub(
        r"[^a-z0-9]",
        "",
        str(key).lower()
    )


def normalized_record(record):

    result = {}

    for key, value in record.items():

        result[
            normalize_key(key)
        ] = value

    return result


def get_field(
    record,
    *possible_names
):

    normalized = normalized_record(
        record
    )

    for name in possible_names:

        key = normalize_key(name)

        if key in normalized:

            return normalized[key]

    return None


# ============================================================
# NUMBER PARSER
# ============================================================

def extract_number(value):

    if value is None:
        return None

    text = str(value).strip()

    if not text:
        return None

    text = text.replace(
        ",",
        ""
    )

    text = text.replace(
        "₹",
        ""
    )

    text = text.replace(
        "Rs.",
        "",
    )

    text = text.replace(
        "Rs",
        "",
    )

    match = re.search(
        r"-?\d+(?:\.\d+)?",
        text
    )

    if not match:
        return None

    try:

        number = float(
            match.group(0)
        )

        if number < 0:
            return None

        return number

    except ValueError:

        return None


# ============================================================
# DATE PARSER
# ============================================================

def parse_date(value):

    if value is None:
        return None

    text = clean_text(value)

    if not text:
        return None

    formats = [
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%Y-%m-%d",
        "%d %b %Y",
        "%d %B %Y",
        "%m/%d/%Y",
    ]

    for date_format in formats:

        try:

            parsed = datetime.strptime(
                text,
                date_format
            )

            return parsed.strftime(
                "%Y-%m-%d"
            )

        except ValueError:

            pass

    match = re.search(
        r"(\d{1,2})[/-]"
        r"(\d{1,2})[/-]"
        r"(\d{4})",
        text
    )

    if match:

        try:

            day = int(
                match.group(1)
            )

            month = int(
                match.group(2)
            )

            year = int(
                match.group(3)
            )

            parsed = datetime(
                year,
                month,
                day
            )

            return parsed.strftime(
                "%Y-%m-%d"
            )

        except ValueError:

            pass

    return None


# ============================================================
# MARKET MATCHING
# ============================================================

def market_matches(
    market_value
):

    market = clean_text(
        market_value
    ).lower()

    if not market:
        return False

    normalized_market = re.sub(
        r"[^a-z0-9]",
        "",
        market
    )

    target = re.sub(
        r"[^a-z0-9]",
        "",
        MARKET_NAME.lower()
    )

    if target in normalized_market:
        return True

    if "kopargaon" in normalized_market:
        return True

    return False


# ============================================================
# DISTRICT MATCHING
# ============================================================

def district_matches(
    district_value
):

    district = clean_text(
        district_value
    ).lower()

    if not district:
        return False

    for expected in DISTRICT_NAMES:

        if expected.lower() in district:
            return True

        if district in expected.lower():
            return True

    return False


# ============================================================
# CROP MATCHING
# ============================================================

def commodity_matches(
    record,
    crop
):

    expected = CROP_NAMES[crop].lower()

    commodity = clean_text(
        get_field(
            record,
            "commodity",
            "Commodity"
        )
    ).lower()

    if not commodity:
        return False

    if commodity == expected:
        return True

    if expected in commodity:
        return True

    if commodity in expected:
        return True

    return False


# ============================================================
# SCORE GOVERNMENT RECORD
# ============================================================

def score_record(
    record,
    crop
):

    if not commodity_matches(
        record,
        crop
    ):
        return -1

    market = clean_text(
        get_field(
            record,
            "market",
            "Market",
            "market_name",
            "Market Name"
        )
    )

    district = clean_text(
        get_field(
            record,
            "district",
            "District"
        )
    )

    state = clean_text(
        get_field(
            record,
            "state",
            "State"
        )
    )

    arrival_date = parse_date(
        get_field(
            record,
            "arrival_date",
            "arrivaldate",
            "date",
            "reported_date"
        )
    )

    min_price = extract_number(
        get_field(
            record,
            "min_price",
            "minprice",
            "minimum_price",
            "minimumprice"
        )
    )

    max_price = extract_number(
        get_field(
            record,
            "max_price",
            "maxprice",
            "maximum_price",
            "maximumprice"
        )
    )

    modal_price = extract_number(
        get_field(
            record,
            "modal_price",
            "modalprice"
        )
    )

    if (
        arrival_date is None
        or min_price is None
        or max_price is None
        or modal_price is None
    ):
        return -1

    if modal_price <= 0:
        return -1

    score = 0

    # Exact Kopargaon
    if market_matches(market):
        score += 1000

    # District
    if district_matches(district):
        score += 300

    # Maharashtra
    if state.lower() == STATE.lower():
        score += 200

    elif STATE.lower() in state.lower():
        score += 100

    # Valid price data
    score += 100

    # Newer data is preferred
    try:

        arrival = datetime.strptime(
            arrival_date,
            "%Y-%m-%d"
        ).date()

        days_old = (
            date.today() - arrival
        ).days

        if days_old <= 1:
            score += 100

        elif days_old <= 3:
            score += 80

        elif days_old <= 7:
            score += 50

        elif days_old <= 30:
            score += 20

    except Exception:

        pass

    return score


# ============================================================
# SELECT BEST RECORD
# ============================================================

def find_best_record(
    records,
    crop
):

    candidates = []

    for record in records:

        score = score_record(
            record,
            crop
        )

        if score < 0:
            continue

        arrival_date = parse_date(
            get_field(
                record,
                "arrival_date",
                "arrivaldate",
                "date",
                "reported_date"
            )
        )

        candidates.append(
            (
                score,
                arrival_date or "0000-00-00",
                record
            )
        )

    if not candidates:
        return None

    candidates.sort(
        key=lambda item: (
            item[0],
            item[1]
        ),
        reverse=True
    )

    return candidates[0][2]


# ============================================================
# GOVERNMENT API REQUEST
# ============================================================

def government_request(
    params
):

    response = requests.get(
        DATA_GOV_API_URL,
        params=params,
        headers=HEADERS,
        timeout=REQUEST_TIMEOUT
    )

    response.raise_for_status()

    try:

        payload = response.json()

    except ValueError as error:

        raise RuntimeError(
            "Government API returned invalid JSON."
        ) from error

    records = payload.get(
        "records",
        []
    )

    if not isinstance(
        records,
        list
    ):
        records = []

    return records


# ============================================================
# FETCH GOVERNMENT DATA
# ============================================================

def fetch_government_market_data(
    crop
):

    if not DATA_GOV_API_KEY:

        raise RuntimeError(
            "DATA_GOV_API_KEY is not configured."
        )

    commodity = CROP_NAMES[crop]

    print()
    print("=" * 70)
    print("SMARTAGRI GOVERNMENT DATA REQUEST")
    print("=" * 70)
    print("Crop:", crop)
    print("Commodity:", commodity)
    print("Target market:", MARKET_NAME)
    print("District:", ", ".join(DISTRICT_NAMES))
    print("State:", STATE)
    print("Resource:", DATA_GOV_RESOURCE_ID)
    print("=" * 70)

    requests_to_try = [

        # ----------------------------------------------------
        # 1. Exact commodity + state + district + market
        # ----------------------------------------------------
        {
            "api-key": DATA_GOV_API_KEY,
            "format": "json",
            "limit": 500,
            "offset": 0,
            "filters[state]": STATE,
            "filters[Commodity]": commodity,
            "filters[District]": DISTRICT_NAMES[0],
            "filters[Market]": MARKET_NAME
        },

        # ----------------------------------------------------
        # 2. Commodity + state + district
        # ----------------------------------------------------
        {
            "api-key": DATA_GOV_API_KEY,
            "format": "json",
            "limit": 500,
            "offset": 0,
            "filters[state]": STATE,
            "filters[Commodity]": commodity,
            "filters[District]": DISTRICT_NAMES[0]
        },

        # ----------------------------------------------------
        # 3. Commodity + Maharashtra
        # ----------------------------------------------------
        {
            "api-key": DATA_GOV_API_KEY,
            "format": "json",
            "limit": 1000,
            "offset": 0,
            "filters[state]": STATE,
            "filters[Commodity]": commodity
        },

        # ----------------------------------------------------
        # 4. Commodity only
        # ----------------------------------------------------
        {
            "api-key": DATA_GOV_API_KEY,
            "format": "json",
            "limit": 1000,
            "offset": 0,
            "filters[Commodity]": commodity
        }
    ]

    all_records = []

    last_error = None

    for index, params in enumerate(
        requests_to_try,
        start=1
    ):

        try:

            print(
                "Government query attempt:",
                index
            )

            records = government_request(
                params
            )

            print(
                "Records received:",
                len(records)
            )

            all_records.extend(
                records
            )

            selected = find_best_record(
                records,
                crop
            )

            if selected is not None:

                print(
                    "MATCH FOUND:",
                    selected
                )

                return selected

        except requests.Timeout as error:

            last_error = (
                "Government API timed out."
            )

            print(
                "Government API timeout:",
                error
            )

        except requests.RequestException as error:

            last_error = (
                "Government API request failed: "
                + str(error)
            )

            print(
                "Government API error:",
                error
            )

        except Exception as error:

            last_error = str(error)

            print(
                "Unexpected API error:",
                error
            )

    # --------------------------------------------------------
    # Try combined records collected from multiple queries
    # --------------------------------------------------------

    selected = find_best_record(
        all_records,
        crop
    )

    if selected is not None:

        return selected

    if last_error:

        raise RuntimeError(
            last_error
        )

    raise RuntimeError(
        "No valid government market record "
        "was found for "
        + commodity
        + "."
    )


# ============================================================
# CONVERT GOVERNMENT RECORD
# ============================================================

def convert_government_record(
    raw_record,
    crop
):

    commodity = clean_text(
        get_field(
            raw_record,
            "commodity",
            "Commodity"
        )
    )

    market = clean_text(
        get_field(
            raw_record,
            "market",
            "Market",
            "market_name",
            "Market Name"
        )
    )

    district = clean_text(
        get_field(
            raw_record,
            "district",
            "District"
        )
    )

    state = clean_text(
        get_field(
            raw_record,
            "state",
            "State"
        )
    )

    arrival_date = parse_date(
        get_field(
            raw_record,
            "arrival_date",
            "arrivaldate",
            "date",
            "reported_date"
        )
    )

    min_price = extract_number(
        get_field(
            raw_record,
            "min_price",
            "minprice",
            "minimum_price",
            "minimumprice"
        )
    )

    max_price = extract_number(
        get_field(
            raw_record,
            "max_price",
            "maxprice",
            "maximum_price",
            "maximumprice"
        )
    )

    modal_price = extract_number(
        get_field(
            raw_record,
            "modal_price",
            "modalprice"
        )
    )

    variety = clean_text(
        get_field(
            raw_record,
            "variety",
            "Variety"
        )
    )

    grade = clean_text(
        get_field(
            raw_record,
            "grade",
            "Grade"
        )
    )

    if not commodity:
        commodity = CROP_NAMES[crop]

    if not market:
        market = MARKET_NAME

    if not district:
        district = DISTRICT_NAMES[0]

    if not state:
        state = STATE

    if not arrival_date:

        raise RuntimeError(
            "Government record has no valid arrival date."
        )

    if min_price is None:
        raise RuntimeError(
            "Government record has no minimum price."
        )

    if max_price is None:
        raise RuntimeError(
            "Government record has no maximum price."
        )

    if modal_price is None:
        raise RuntimeError(
            "Government record has no modal price."
        )

    if modal_price <= 0:

        raise RuntimeError(
            "Government record contains invalid modal price."
        )

    retrieved_at = datetime.now(
        timezone.utc
    ).isoformat()

    return {

        "crop": crop,

        "commodity": commodity,

        "market": market,

        "district": district,

        "state": state,

        "arrival_date": arrival_date,

        "variety": variety,

        "grade": grade,

        "min_price": float(min_price),

        "max_price": float(max_price),

        "modal_price": float(modal_price),

        "unit": "Rs./Quintal",

        "source": (
            "Government of India OGD / AGMARKNET"
        ),

        "source_url": DATA_GOV_SOURCE_URL,

        "retrieved_at": retrieved_at,

        "is_bootstrap": False
    }


# ============================================================
# STORE RECORD
# ============================================================

def store_record(
    record
):

    connection = get_db_connection()

    cursor = connection.cursor()

    now = datetime.now(
        timezone.utc
    ).isoformat()

    cursor.execute(
        """
        INSERT INTO market_history (

            crop,
            commodity,
            market,
            district,
            state,
            arrival_date,
            variety,
            grade,
            min_price,
            max_price,
            modal_price,
            unit,
            source,
            source_url,
            retrieved_at,
            created_at,
            is_bootstrap

        )

        VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?, ?, ?, ?
        )

        ON CONFLICT (
            crop,
            market,
            arrival_date
        )

        DO UPDATE SET

            commodity =
                excluded.commodity,

            district =
                excluded.district,

            state =
                excluded.state,

            variety =
                excluded.variety,

            grade =
                excluded.grade,

            min_price =
                excluded.min_price,

            max_price =
                excluded.max_price,

            modal_price =
                excluded.modal_price,

            unit =
                excluded.unit,

            source =
                excluded.source,

            source_url =
                excluded.source_url,

            retrieved_at =
                excluded.retrieved_at,

            is_bootstrap =
                excluded.is_bootstrap
        """,
        (
            record["crop"],
            record["commodity"],
            record["market"],
            record["district"],
            record["state"],
            record["arrival_date"],
            record.get(
                "variety",
                ""
            ),
            record.get(
                "grade",
                ""
            ),
            record["min_price"],
            record["max_price"],
            record["modal_price"],
            record["unit"],
            record["source"],
            record["source_url"],
            record["retrieved_at"],
            now,
            1 if record.get(
                "is_bootstrap",
                False
            ) else 0
        )
    )

    connection.commit()

    stored_id = cursor.lastrowid

    connection.close()

    return stored_id


# ============================================================
# BOOTSTRAP DATABASE
# ============================================================

def bootstrap_database():

    connection = get_db_connection()

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT COUNT(*)
        FROM market_history
        """
    )

    total = cursor.fetchone()[0]

    connection.close()

    if total > 0:
        return

    print()
    print("=" * 70)
    print("DATABASE EMPTY")
    print("ADDING VERIFIED STARTING MARKET RECORDS")
    print("=" * 70)

    for crop, data in BOOTSTRAP_DATA.items():

        record = dict(data)

        record["crop"] = crop

        record["retrieved_at"] = (
            datetime.now(
                timezone.utc
            ).isoformat()
        )

        record["is_bootstrap"] = True

        store_record(
            record
        )

        print(
            "Bootstrap record added:",
            crop,
            record["arrival_date"],
            record["modal_price"]
        )

    print("=" * 70)


bootstrap_database()


# ============================================================
# GET HISTORY
# ============================================================

def get_history_records(
    crop,
    limit=365
):

    connection = get_db_connection()

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT *
        FROM market_history
        WHERE crop = ?
        ORDER BY arrival_date ASC
        LIMIT ?
        """,
        (
            crop,
            limit
        )
    )

    rows = cursor.fetchall()

    connection.close()

    return [
        dict(row)
        for row in rows
    ]


# ============================================================
# GET LATEST RECORD
# ============================================================

def get_latest_record(
    crop
):

    connection = get_db_connection()

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT *
        FROM market_history
        WHERE crop = ?
        ORDER BY arrival_date DESC, id DESC
        LIMIT 1
        """,
        (
            crop,
        )
    )

    row = cursor.fetchone()

    connection.close()

    if row is None:
        return None

    return dict(row)


# ============================================================
# PRICE AGE
# ============================================================

def calculate_age_days(
    arrival_date
):

    try:

        parsed = datetime.strptime(
            arrival_date,
            "%Y-%m-%d"
        ).date()

        return (
            date.today() - parsed
        ).days

    except Exception:

        return None


def freshness_label(
    arrival_date
):

    age = calculate_age_days(
        arrival_date
    )

    if age is None:
        return "unknown"

    if age <= 0:
        return "today"

    if age == 1:
        return "1 day old"

    if age <= 3:
        return f"{age} days old"

    if age <= 7:
        return f"{age} days old"

    return f"{age} days old"


# ============================================================
# PRICE LIST
# ============================================================

def get_prices(
    records
):

    return [

        float(
            record["modal_price"]
        )

        for record in records

        if record.get(
            "modal_price"
        ) is not None
        and float(
            record["modal_price"]
        ) > 0
    ]


# ============================================================
# PERCENTAGE CHANGE
# ============================================================

def percentage_change(
    old,
    new
):

    if old is None:
        return None

    if new is None:
        return None

    if old == 0:
        return None

    return round(
        (
            (new - old)
            / old
        ) * 100,
        2
    )


# ============================================================
# TREND
# ============================================================

def calculate_trend(
    records
):

    prices = get_prices(
        records
    )

    if not prices:

        return {
            "direction": "unknown",
            "change_percent": None,
            "previous_price": None,
            "current_price": None,
            "strength": "unknown"
        }

    current_price = prices[-1]

    if len(prices) < 2:

        return {
            "direction": "stable",
            "change_percent": 0,
            "previous_price": None,
            "current_price": current_price,
            "strength": "insufficient_history"
        }

    previous_price = prices[-2]

    change = percentage_change(
        previous_price,
        current_price
    )

    if change is None:

        direction = "unknown"
        strength = "unknown"

    elif change > 1:

        direction = "rising"

        if change >= 5:
            strength = "strong"

        elif change >= 2:
            strength = "moderate"

        else:
            strength = "weak"

    elif change < -1:

        direction = "falling"

        if change <= -5:
            strength = "strong"

        elif change <= -2:
            strength = "moderate"

        else:
            strength = "weak"

    else:

        direction = "stable"
        strength = "weak"

    return {

        "direction": direction,

        "change_percent": change,

        "previous_price": previous_price,

        "current_price": current_price,

        "strength": strength
    }


# ============================================================
# MOVING AVERAGE
# ============================================================

def moving_average(
    prices,
    window
):

    if not prices:
        return None

    selected = prices[
        -window:
    ]

    if not selected:
        return None

    return round(
        statistics.mean(
            selected
        ),
        2
    )


# ============================================================
# DECISION ENGINE
# ============================================================
#
# This is deterministic decision logic.
# It does not pretend to be an AI model.
#
# Later you can replace this with an actual ML model.
#
# ============================================================

def make_market_decision(
    records
):

    prices = get_prices(
        records
    )

    if not prices:

        return {

            "decision":
                "DATA REQUIRED",

            "signal":
                "insufficient_data",

            "message":
                "There is not enough verified price data "
                "to make a market decision.",

            "confidence":
                "low"
        }

    current = prices[-1]

    previous = (
        prices[-2]
        if len(prices) >= 2
        else None
    )

    previous_3 = (
        prices[-4]
        if len(prices) >= 4
        else None
    )

    ma3 = moving_average(
        prices,
        3
    )

    ma7 = moving_average(
        prices,
        7
    )

    daily_change = percentage_change(
        previous,
        current
    )

    three_day_change = percentage_change(
        previous_3,
        current
    )

    # --------------------------------------------------------
    # Not enough history
    # --------------------------------------------------------

    if len(prices) < 2:

        return {

            "decision":
                "MONITOR",

            "signal":
                "new_data",

            "message":
                "A verified market price is available. "
                "More daily records are needed before "
                "making a strong sell or hold decision.",

            "confidence":
                "low",

            "daily_change_percent":
                None,

            "three_day_change_percent":
                None
        }

    # --------------------------------------------------------
    # Strong increase
    # --------------------------------------------------------

    if (
        daily_change is not None
        and daily_change >= 5
    ):

        return {

            "decision":
                "CONSIDER SELLING",

            "signal":
                "strong_increase",

            "message":
                "The latest modal price has increased "
                "strongly compared with the previous "
                "record. This may be a favorable time "
                "to consider selling.",

            "confidence":
                "medium",

            "daily_change_percent":
                daily_change,

            "three_day_change_percent":
                three_day_change
        }

    # --------------------------------------------------------
    # Moderate increase
    # --------------------------------------------------------

    if (
        daily_change is not None
        and daily_change > 1
    ):

        return {

            "decision":
                "HOLD / WATCH",

            "signal":
                "increase",

            "message":
                "The latest price has increased. "
                "The market is moving upward, so monitor "
                "the next few records before deciding "
                "whether to sell.",

            "confidence":
                "medium",

            "daily_change_percent":
                daily_change,

            "three_day_change_percent":
                three_day_change
        }

    # --------------------------------------------------------
    # Strong decrease
    # --------------------------------------------------------

    if (
        daily_change is not None
        and daily_change <= -5
    ):

        return {

            "decision":
                "CONSIDER SELLING SOON",

            "signal":
                "strong_decrease",

            "message":
                "The latest modal price has fallen "
                "strongly. Waiting may carry additional "
                "price risk.",

            "confidence":
                "medium",

            "daily_change_percent":
                daily_change,

            "three_day_change_percent":
                three_day_change
        }

    # --------------------------------------------------------
    # Moderate decrease
    # --------------------------------------------------------

    if (
        daily_change is not None
        and daily_change < -1
    ):

        return {

            "decision":
                "WAIT / MONITOR",

            "signal":
                "decrease",

            "message":
                "The latest price has decreased. "
                "Monitor the next market update before "
                "making a final selling decision.",

            "confidence":
                "medium",

            "daily_change_percent":
                daily_change,

            "three_day_change_percent":
                three_day_change
        }

    # --------------------------------------------------------
    # Moving average signal
    # --------------------------------------------------------

    if (
        ma3 is not None
        and ma7 is not None
        and ma3 > ma7 * 1.02
    ):

        return {

            "decision":
                "HOLD / WATCH",

            "signal":
                "short_term_uptrend",

            "message":
                "The recent average price is above the "
                "7-record average, indicating short-term "
                "upward pressure.",

            "confidence":
                "medium",

            "daily_change_percent":
                daily_change,

            "three_day_change_percent":
                three_day_change
        }

    if (
        ma3 is not None
        and ma7 is not None
        and ma3 < ma7 * 0.98
    ):

        return {

            "decision":
                "MONITOR / SELL IF NEEDED",

            "signal":
                "short_term_downtrend",

            "message":
                "The recent average price is below the "
                "7-record average, indicating short-term "
                "downward pressure.",

            "confidence":
                "medium",

            "daily_change_percent":
                daily_change,

            "three_day_change_percent":
                three_day_change
        }

    return {

        "decision":
            "HOLD / MONITOR",

        "signal":
            "stable",

        "message":
            "The latest market price is relatively "
            "stable. Continue monitoring the next "
            "market update.",

        "confidence":
            "low",

        "daily_change_percent":
            daily_change,

        "three_day_change_percent":
            three_day_change
    }


# ============================================================
# ANALYSIS
# ============================================================

def calculate_analysis(
    records
):

    prices = get_prices(
        records
    )

    trend = calculate_trend(
        records
    )

    decision = make_market_decision(
        records
    )

    if not prices:

        return {

            "trend": trend,

            "decision": decision,

            "moving_average_3": None,

            "moving_average_7": None,

            "moving_average_14": None,

            "lowest_price": None,

            "highest_price": None,

            "average_price": None,

            "prediction": {

                "direction":
                    "insufficient_data",

                "estimated_price":
                    None,

                "confidence":
                    "low",

                "reason":
                    "No verified historical prices available.",

                "unit":
                    "Rs./Quintal"
            }
        }

    average_price = statistics.mean(
        prices
    )

    ma3 = moving_average(
        prices,
        3
    )

    ma7 = moving_average(
        prices,
        7
    )

    ma14 = moving_average(
        prices,
        14
    )

    # --------------------------------------------------------
    # Prediction
    # --------------------------------------------------------

    if len(prices) < 3:

        prediction = {

            "direction":
                "insufficient_data",

            "estimated_price":
                None,

            "confidence":
                "low",

            "reason":
                "At least 3 verified price records "
                "are recommended.",

            "unit":
                "Rs./Quintal"
        }

    else:

        recent = prices[-3:]

        changes = []

        for index in range(
            1,
            len(recent)
        ):

            previous = recent[
                index - 1
            ]

            current = recent[
                index
            ]

            if previous != 0:

                changes.append(
                    (
                        (
                            current
                            - previous
                        )
                        / previous
                    )
                    * 100
                )

        average_change = (
            statistics.mean(
                changes
            )
            if changes
            else 0
        )

        capped_change = max(
            min(
                average_change,
                10
            ),
            -10
        )

        current_price = prices[-1]

        estimated_price = round(
            current_price
            * (
                1
                + capped_change / 100
            ),
            2
        )

        if average_change > 1:

            direction = "rising"

        elif average_change < -1:

            direction = "falling"

        else:

            direction = "stable"

        if len(prices) >= 14:

            confidence = "high"

        elif len(prices) >= 7:

            confidence = "medium"

        else:

            confidence = "low"

        prediction = {

            "direction":
                direction,

            "estimated_price":
                estimated_price,

            "confidence":
                confidence,

            "reason":
                "Estimate based on recent verified "
                "modal-price movement.",

            "unit":
                "Rs./Quintal"
        }

    return {

        "trend": trend,

        "decision": decision,

        "moving_average_3": ma3,

        "moving_average_7": ma7,

        "moving_average_14": ma14,

        "lowest_price": min(prices),

        "highest_price": max(prices),

        "average_price": round(
            average_price,
            2
        ),

        "prediction": prediction
    }


# ============================================================
# COLLECT CROP
# ============================================================

def collect_crop(
    crop
):

    raw_record = (
        fetch_government_market_data(
            crop
        )
    )

    record = (
        convert_government_record(
            raw_record,
            crop
        )
    )

    stored_id = store_record(
        record
    )

    history = get_history_records(
        crop,
        limit=365
    )

    analysis = calculate_analysis(
        history
    )

    record["stored"] = True

    record["database_id"] = stored_id

    return record, analysis


# ============================================================
# GET RESPONSE FROM HISTORY
# ============================================================

def build_historical_response(
    crop,
    live_error=None
):

    latest = get_latest_record(
        crop
    )

    history = get_history_records(
        crop,
        limit=365
    )

    if latest is None:

        return None

    analysis = calculate_analysis(
        history
    )

    age_days = calculate_age_days(
        latest["arrival_date"]
    )

    return {

        "success":
            True,

        "data_mode":
            "latest_verified_history",

        "fallback":
            False,

        "live":
            False,

        "market":
            latest["market"],

        "district":
            latest["district"],

        "state":
            latest["state"],

        "source":
            latest["source"],

        "latest":
            latest,

        "latest_price":
            latest["modal_price"],

        "latest_price_date":
            latest["arrival_date"],

        "latest_price_age_days":
            age_days,

        "latest_price_freshness":
            freshness_label(
                latest["arrival_date"]
            ),

        "analysis":
            analysis,

        "history_count":
            len(history),

        "message":
            (
                "The latest verified market price is "
                "being displayed. A newer live government "
                "record was not available."
            ),

        "live_error":
            live_error
    }


# ============================================================
# HEALTH
# ============================================================

@app.route(
    "/api/health"
)
def health():

    connection = get_db_connection()

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT COUNT(*)
        FROM market_history
        """
    )

    total_records = (
        cursor.fetchone()[0]
    )

    cursor.execute(
        """
        SELECT COUNT(*)
        FROM market_history
        WHERE crop = 'onion'
        """
    )

    onion_records = (
        cursor.fetchone()[0]
    )

    cursor.execute(
        """
        SELECT COUNT(*)
        FROM market_history
        WHERE crop = 'wheat'
        """
    )

    wheat_records = (
        cursor.fetchone()[0]
    )

    connection.close()

    onion_latest = get_latest_record(
        "onion"
    )

    wheat_latest = get_latest_record(
        "wheat"
    )

    return jsonify({

        "success":
            True,

        "backend":
            "SmartAgri Flask",

        "database":
            "SQLite",

        "database_path":
            DATABASE_PATH,

        "market":
            MARKET_NAME,

        "district":
            "Ahilyanagar",

        "state":
            STATE,

        "market_source":
            "Government of India OGD / AGMARKNET",

        "government_api_configured":
            bool(DATA_GOV_API_KEY),

        "government_resource_id":
            DATA_GOV_RESOURCE_ID,

        "supported_crops":
            list(
                CROP_NAMES.keys()
            ),

        "total_history_records":
            total_records,

        "onion_records":
            onion_records,

        "wheat_records":
            wheat_records,

        "onion_latest_date":
            (
                onion_latest["arrival_date"]
                if onion_latest
                else None
            ),

        "wheat_latest_date":
            (
                wheat_latest["arrival_date"]
                if wheat_latest
                else None
            )
    })


# ============================================================
# COLLECT
# ============================================================

@app.route(
    "/api/collect"
)
def collect():

    crop = (
        request.args
        .get(
            "crop",
            ""
        )
        .strip()
        .lower()
    )

    if crop not in CROP_NAMES:

        return jsonify({

            "success":
                False,

            "message":
                "Unsupported crop. Use onion or wheat."
        }), 400

    try:

        record, analysis = (
            collect_crop(
                crop
            )
        )

        return jsonify({

            "success":
                True,

            "stored":
                True,

            "live":
                True,

            "data_mode":
                "government_live",

            "message":
                "New government market data "
                "was fetched and stored.",

            "record":
                record,

            "latest_price":
                record["modal_price"],

            "latest_price_date":
                record["arrival_date"],

            "analysis":
                analysis
        })

    except Exception as error:

        print(
            "COLLECTION ERROR:",
            error
        )

        historical = (
            build_historical_response(
                crop,
                str(error)
            )
        )

        if historical is not None:

            return jsonify(
                historical
            )

        return jsonify({

            "success":
                False,

            "stored":
                False,

            "message":
                "No verified price is available yet.",

            "error":
                str(error)
        }), 502


# ============================================================
# COLLECT ALL CROPS
# ============================================================

@app.route(
    "/api/collect-all"
)
def collect_all():

    results = {}

    for crop in CROP_NAMES:

        try:

            record, analysis = (
                collect_crop(
                    crop
                )
            )

            results[crop] = {

                "success":
                    True,

                "live":
                    True,

                "price":
                    record["modal_price"],

                "date":
                    record["arrival_date"],

                "analysis":
                    analysis
            }

        except Exception as error:

            print(
                "COLLECT ALL ERROR:",
                crop,
                error
            )

            historical = (
                build_historical_response(
                    crop,
                    str(error)
                )
            )

            if historical is not None:

                results[crop] = {

                    "success":
                        True,

                    "live":
                        False,

                    "price":
                        historical["latest_price"],

                    "date":
                        historical["latest_price_date"],

                    "message":
                        "Latest verified historical "
                        "price retained.",

                    "analysis":
                        historical["analysis"]
                }

            else:

                results[crop] = {

                    "success":
                        False,

                    "live":
                        False,

                    "error":
                        str(error)
                }

    return jsonify({

        "success":
            True,

        "results":
            results
    })


# ============================================================
# HISTORY
# ============================================================

@app.route(
    "/api/history"
)
def history():

    crop = (
        request.args
        .get(
            "crop",
            ""
        )
        .strip()
        .lower()
    )

    if crop not in CROP_NAMES:

        return jsonify({

            "success":
                False,

            "message":
                "Unsupported crop. Use onion or wheat."
        }), 400

    try:

        limit = int(
            request.args.get(
                "limit",
                365
            )
        )

    except ValueError:

        limit = 365

    limit = max(
        1,
        min(
            limit,
            1000
        )
    )

    records = get_history_records(
        crop,
        limit
    )

    analysis = calculate_analysis(
        records
    )

    latest = (
        records[-1]
        if records
        else None
    )

    return jsonify({

        "success":
            True,

        "crop":
            crop,

        "commodity":
            CROP_NAMES[crop],

        "market":
            MARKET_NAME,

        "district":
            "Ahilyanagar",

        "state":
            STATE,

        "count":
            len(records),

        "latest":
            latest,

        "latest_price":
            (
                latest["modal_price"]
                if latest
                else None
            ),

        "latest_price_date":
            (
                latest["arrival_date"]
                if latest
                else None
            ),

        "records":
            records,

        "analysis":
            analysis
    })


# ============================================================
# MARKET
# ============================================================

@app.route(
    "/api/market"
)
def market():

    crop = (
        request.args
        .get(
            "crop",
            ""
        )
        .strip()
        .lower()
    )

    if crop not in CROP_NAMES:

        return jsonify({

            "success":
                False,

            "message":
                "Unsupported crop. Use onion or wheat."
        }), 400

    # --------------------------------------------------------
    # ALWAYS TRY LIVE GOVERNMENT DATA FIRST
    # --------------------------------------------------------

    try:

        record, analysis = (
            collect_crop(
                crop
            )
        )

        history = get_history_records(
            crop,
            limit=365
        )

        return jsonify({

            "success":
                True,

            "data_mode":
                "government_live_plus_history",

            "fallback":
                False,

            "live":
                True,

            "market":
                record["market"],

            "district":
                record["district"],

            "state":
                record["state"],

            "source":
                record["source"],

            "latest":
                record,

            "latest_price":
                record["modal_price"],

            "latest_price_date":
                record["arrival_date"],

            "latest_price_freshness":
                freshness_label(
                    record["arrival_date"]
                ),

            "analysis":
                analysis,

            "history_count":
                len(history),

            "message":
                (
                    "Latest government market data "
                    "was retrieved successfully."
                )
        })

    except Exception as error:

        print(
            "MARKET API LIVE ERROR:",
            error
        )

        # ----------------------------------------------------
        # NEVER SHOW EMPTY DATA IF HISTORY EXISTS
        # ----------------------------------------------------

        historical = (
            build_historical_response(
                crop,
                str(error)
            )
        )

        if historical is not None:

            return jsonify(
                historical
            )

        # ----------------------------------------------------
        # This should only happen if database is somehow empty
        # ----------------------------------------------------

        return jsonify({

            "success":
                False,

            "data_mode":
                "no_verified_data",

            "fallback":
                False,

            "live":
                False,

            "market":
                MARKET_NAME,

            "district":
                "Ahilyanagar",

            "state":
                STATE,

            "message":
                (
                    "No verified market price exists "
                    "in the database yet."
                ),

            "error":
                str(error)
        }), 502


# ============================================================
# FRONTEND
# ============================================================

@app.route("/")
def home():

    return send_from_directory(
        os.path.dirname(
            os.path.abspath(__file__)
        ),
        "index.html"
    )


@app.route(
    "/<path:filename>"
)
def files(filename):

    return send_from_directory(
        os.path.dirname(
            os.path.abspath(__file__)
        ),
        filename
    )


# ============================================================
# START SERVER
# ============================================================

if __name__ == "__main__":

    print()
    print("=" * 70)
    print("SMARTAGRI KOPARGAON")
    print("=" * 70)
    print("MARKET PRICE + DECISION ENGINE")
    print("-" * 70)
    print("Onion")
    print("Wheat")
    print("-" * 70)
    print("Market:", MARKET_NAME)
    print("District:", "Ahilyanagar")
    print("State:", STATE)
    print("-" * 70)
    print(
        "Government API configured:",
        bool(DATA_GOV_API_KEY)
    )
    print(
        "Resource:",
        DATA_GOV_RESOURCE_ID
    )
    print("-" * 70)
    print(
        "Database:",
        DATABASE_PATH
    )
    print("=" * 70)

    app.run(
        host="0.0.0.0",
        port=int(
            os.environ.get(
                "PORT",
                5000
            )
        ),
        debug=False
    )
