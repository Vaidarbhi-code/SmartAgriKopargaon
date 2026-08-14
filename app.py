from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS
import requests
import sqlite3
import os
import re
import statistics
from datetime import datetime, timezone


# ============================================================
# SMARTAGRI KOPARGAON
# ============================================================
#
# GOVERNMENT API VERSION
#
# NO MANDIPULSE SCRAPING
# NO HARDCODED PRICES
# NO FALLBACK PRICES
#
# Data source:
# Government of India Open Government Data (OGD)
# AGMARKNET market-price dataset
#
# Features:
# - Live government market data
# - SQLite historical storage
# - One record per crop/market/day
# - Trend calculation
# - Moving averages
# - Simple short-term prediction
# - /api/market
# - /api/history
# - /api/collect
# - /api/health
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
# DATABASE
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

DATABASE_PATH = os.path.join(
    BASE_DIR,
    "smartagri.db"
)


def get_db_connection():
    connection = sqlite3.connect(
        DATABASE_PATH,
        timeout=30
    )

    connection.row_factory = sqlite3.Row

    return connection


def init_database():

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

    print("=" * 60)
    print("DATABASE READY")
    print("=" * 60)
    print("Database:", DATABASE_PATH)
    print("=" * 60)


init_database()


# ============================================================
# MARKET CONFIGURATION
# ============================================================

MARKET_NAME = "Kopargaon APMC"
DISTRICT = "Ahilyanagar"
STATE = "Maharashtra"

CROP_NAMES = {
    "onion": "Onion",
    "wheat": "Wheat"
}


# ============================================================
# GOVERNMENT OF INDIA OGD API
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

# IMPORTANT:
# Keep this below Gunicorn's normal timeout so the Flask
# worker never gets stuck waiting for the government API.

REQUEST_TIMEOUT = (
    5,
    8
)


# ============================================================
# HTTP HEADERS
# ============================================================

HEADERS = {
    "User-Agent": (
        "SmartAgriKopargaon/1.0 "
        "(Government OGD API Client)"
    ),
    "Accept": "application/json",
}


# ============================================================
# TEXT / NUMBER HELPERS
# ============================================================

def clean_text(value):

    if value is None:
        return ""

    return str(value).strip()


def extract_number(value):

    if value is None:
        return None

    text = str(value).strip()

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

        return float(
            match.group(0)
        )

    except ValueError:

        return None


# ============================================================
# NORMALIZE GOVERNMENT API FIELD NAMES
# ============================================================

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


def get_field(record, *possible_names):

    normalized = normalized_record(
        record
    )

    for name in possible_names:

        key = normalize_key(name)

        if key in normalized:

            return normalized[key]

    return None


# ============================================================
# DATE PARSING
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

    # Try extracting a date from longer text

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
# FIND BEST GOVERNMENT RECORD
# ============================================================

def find_matching_record(
    records,
    crop
):

    if not records:

        return None

    expected_commodity = (
        CROP_NAMES[crop]
    )

    candidates = []

    for record in records:

        commodity = clean_text(
            get_field(
                record,
                "commodity",
                "Commodity"
            )
        )

        market = clean_text(
            get_field(
                record,
                "market",
                "Market",
                "market_name"
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

        # ----------------------------------------------------
        # Commodity matching
        # ----------------------------------------------------

        commodity_match = (
            commodity.lower()
            == expected_commodity.lower()
        )

        if not commodity_match:

            commodity_match = (
                expected_commodity.lower()
                in commodity.lower()
                or
                commodity.lower()
                in expected_commodity.lower()
            )

        if not commodity_match:

            continue

        # ----------------------------------------------------
        # Market matching
        # ----------------------------------------------------

        market_match = (
            MARKET_NAME.lower()
            in market.lower()
            or
            market.lower()
            in MARKET_NAME.lower()
        )

        # ----------------------------------------------------
        # District matching
        # ----------------------------------------------------

        district_match = (
            DISTRICT.lower()
            in district.lower()
            or
            district.lower()
            in DISTRICT.lower()
        )

        # ----------------------------------------------------
        # State matching
        # ----------------------------------------------------

        state_match = (
            STATE.lower()
            in state.lower()
            or
            state.lower()
            in STATE.lower()
        )

        # Prefer exact market.
        # Still allow district/state matches because
        # government records can have slightly different
        # market naming.

        if market_match:

            score = 100

        elif district_match:

            score = 60

        else:

            score = 20

        if state_match:

            score += 20

        arrival_date = parse_date(
            get_field(
                record,
                "arrival_date",
                "arrivaldate",
                "date",
                "reported_date"
            )
        )

        if arrival_date:

            score += 10

        candidates.append(
            (
                score,
                arrival_date or "0000-00-00",
                record
            )
        )

    if not candidates:

        return None

    # Highest score, then newest date

    candidates.sort(
        key=lambda item: (
            item[0],
            item[1]
        ),
        reverse=True
    )

    return candidates[0][2]


# ============================================================
# FETCH GOVERNMENT MARKET DATA
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
    print("=" * 60)
    print("SMARTAGRI GOVERNMENT MARKET REQUEST")
    print("=" * 60)
    print("Crop:", crop)
    print("Commodity:", commodity)
    print("Market:", MARKET_NAME)
    print("District:", DISTRICT)
    print("State:", STATE)
    print("Resource:", DATA_GOV_RESOURCE_ID)
    print("=" * 60)

    # --------------------------------------------------------
    # Government API parameters
    # --------------------------------------------------------
    #
    # The filters are sent using the OGD API filter syntax.
    #
    # We request a small number of records because we only
    # need the latest relevant market record.
    # --------------------------------------------------------

    params = {

        "api-key":
            DATA_GOV_API_KEY,

        "format":
            "json",

        "limit":
            100,

        "offset":
            0,

        "filters[State]":
            STATE,

        "filters[District]":
            DISTRICT,

        "filters[Market]":
            MARKET_NAME,

        "filters[Commodity]":
            commodity
    }

    try:

        response = requests.get(
            DATA_GOV_API_URL,
            params=params,
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT
        )

        response.raise_for_status()

    except requests.Timeout as error:

        raise RuntimeError(
            "Government API timed out. "
            "The endpoint did not respond within "
            "the allowed time."
        ) from error

    except requests.RequestException as error:

        raise RuntimeError(
            "Government API request failed: "
            + str(error)
        ) from error

    # --------------------------------------------------------
    # Parse JSON
    # --------------------------------------------------------

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

    print(
        "Government records received:",
        len(records)
    )

    # --------------------------------------------------------
    # Find exact relevant record
    # --------------------------------------------------------

    selected = find_matching_record(
        records,
        crop
    )

    if selected is None:

        # If filters returned nothing, do one small
        # fallback API request using only commodity.
        #
        # This handles datasets where State/District/Market
        # field names differ slightly.

        fallback_params = {

            "api-key":
                DATA_GOV_API_KEY,

            "format":
                "json",

            "limit":
                100,

            "offset":
                0,

            "filters[Commodity]":
                commodity
        }

        try:

            fallback_response = requests.get(
                DATA_GOV_API_URL,
                params=fallback_params,
                headers=HEADERS,
                timeout=REQUEST_TIMEOUT
            )

            fallback_response.raise_for_status()

            fallback_payload = (
                fallback_response.json()
            )

            fallback_records = (
                fallback_payload.get(
                    "records",
                    []
                )
            )

            if isinstance(
                fallback_records,
                list
            ):

                selected = find_matching_record(
                    fallback_records,
                    crop
                )

        except requests.Timeout as error:

            raise RuntimeError(
                "Government API timed out while "
                "searching commodity data."
            ) from error

        except Exception:

            selected = None

    if selected is None:

        raise RuntimeError(
            "No matching government market record "
            "was found for "
            + commodity
            + " at "
            + MARKET_NAME
            + ", "
            + DISTRICT
            + ", "
            + STATE
            + "."
        )

    return selected


# ============================================================
# CONVERT GOVERNMENT RECORD TO SMARTAGRI RECORD
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
            "market_name"
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

        district = DISTRICT

    if not state:

        state = STATE

    if not arrival_date:

        raise RuntimeError(
            "Government API record did not contain "
            "a valid arrival date."
        )

    if min_price is None:

        raise RuntimeError(
            "Government API record did not contain "
            "a minimum price."
        )

    if max_price is None:

        raise RuntimeError(
            "Government API record did not contain "
            "a maximum price."
        )

    if modal_price is None:

        raise RuntimeError(
            "Government API record did not contain "
            "a modal price."
        )

    retrieved_at = (
        datetime.now(
            timezone.utc
        ).isoformat()
    )

    return {

        "crop":
            crop,

        "commodity":
            commodity,

        "market":
            market,

        "district":
            district,

        "state":
            state,

        "arrival_date":
            arrival_date,

        "variety":
            variety,

        "grade":
            grade,

        "min_price":
            float(min_price),

        "max_price":
            float(max_price),

        "modal_price":
            float(modal_price),

        "unit":
            "Rs./Quintal",

        "source":
            "Government of India OGD / AGMARKNET",

        "source_url":
            DATA_GOV_SOURCE_URL,

        "retrieved_at":
            retrieved_at
    }


# ============================================================
# STORE RECORD
# ============================================================

def store_record(record):

    connection = get_db_connection()

    cursor = connection.cursor()

    now = (
        datetime.now(
            timezone.utc
        ).isoformat()
    )

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
            created_at

        )

        VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?, ?, ?
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
                excluded.retrieved_at
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
            now
        )
    )

    connection.commit()

    stored_id = cursor.lastrowid

    connection.close()

    return stored_id


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
# TREND
# ============================================================

def calculate_trend(
    records
):

    if not records:

        return {

            "direction":
                "insufficient_data",

            "change_percent":
                None,

            "previous_price":
                None,

            "current_price":
                None,

            "strength":
                "insufficient_data"
        }

    prices = [

        float(
            record["modal_price"]
        )

        for record in records

        if record.get(
            "modal_price"
        ) is not None
    ]

    if not prices:

        return {

            "direction":
                "insufficient_data",

            "change_percent":
                None,

            "previous_price":
                None,

            "current_price":
                None,

            "strength":
                "insufficient_data"
        }

    current_price = prices[-1]

    if len(prices) < 2:

        return {

            "direction":
                "insufficient_data",

            "change_percent":
                None,

            "previous_price":
                None,

            "current_price":
                current_price,

            "strength":
                "insufficient_data"
        }

    previous_price = prices[-2]

    if previous_price == 0:

        change_percent = None

    else:

        change_percent = (
            (
                current_price
                - previous_price
            )
            / previous_price
        ) * 100

    if change_percent is None:

        direction = "unknown"
        strength = "unknown"

    elif change_percent > 1:

        direction = "rising"

        strength = (
            "strong"
            if change_percent >= 5
            else "moderate"
        )

    elif change_percent < -1:

        direction = "falling"

        strength = (
            "strong"
            if change_percent <= -5
            else "moderate"
        )

    else:

        direction = "stable"
        strength = "weak"

    return {

        "direction":
            direction,

        "change_percent":
            round(
                change_percent,
                2
            )
            if change_percent is not None
            else None,

        "previous_price":
            previous_price,

        "current_price":
            current_price,

        "strength":
            strength
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

    selected = prices[-window:]

    if not selected:

        return None

    return round(
        statistics.mean(selected),
        2
    )


# ============================================================
# ANALYSIS + PREDICTION
# ============================================================

def calculate_analysis(
    records
):

    prices = [

        float(
            record["modal_price"]
        )

        for record in records

        if record.get(
            "modal_price"
        ) is not None
    ]

    trend = calculate_trend(
        records
    )

    if not prices:

        return {

            "trend":
                trend,

            "moving_average_3":
                None,

            "moving_average_7":
                None,

            "moving_average_14":
                None,

            "lowest_price":
                None,

            "highest_price":
                None,

            "average_price":
                None,

            "prediction":
                {

                    "direction":
                        "insufficient_data",

                    "estimated_price":
                        None,

                    "confidence":
                        "low",

                    "reason":
                        "No historical prices available.",

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

        prediction_direction = (
            "insufficient_data"
        )

        estimated_price = None

        confidence = "low"

        reason = (
            "At least 3 daily historical "
            "records are recommended for "
            "a trend-based estimate."
        )

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
                        current - previous
                    )
                    / previous
                    * 100
                )

        if changes:

            average_change = (
                statistics.mean(
                    changes
                )
            )

        else:

            average_change = 0

        # Limit prediction movement
        capped_change = max(
            min(
                average_change,
                10
            ),
            -10
        )

        current_price = prices[-1]

        estimated_price = (
            current_price
            * (
                1
                + capped_change / 100
            )
        )

        estimated_price = round(
            estimated_price,
            2
        )

        if average_change > 1:

            prediction_direction = (
                "rising"
            )

        elif average_change < -1:

            prediction_direction = (
                "falling"
            )

        else:

            prediction_direction = (
                "stable"
            )

        if len(prices) >= 14:

            confidence = "high"

        elif len(prices) >= 7:

            confidence = "medium"

        else:

            confidence = "low"

        reason = (
            "Estimate based on recent "
            "historical modal-price movement."
        )

    return {

        "trend":
            trend,

        "moving_average_3":
            ma3,

        "moving_average_7":
            ma7,

        "moving_average_14":
            ma14,

        "lowest_price":
            min(prices),

        "highest_price":
            max(prices),

        "average_price":
            round(
                average_price,
                2
            ),

        "prediction":
            {

                "direction":
                    prediction_direction,

                "estimated_price":
                    estimated_price,

                "confidence":
                    confidence,

                "reason":
                    reason,

                "unit":
                    "Rs./Quintal"
            }
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
            DISTRICT,

        "state":
            STATE,

        "market_source":
            "Government of India OGD / AGMARKNET",

        "government_api_configured":
            bool(DATA_GOV_API_KEY),

        "government_resource_id":
            DATA_GOV_RESOURCE_ID,

        "fallback":
            False,

        "supported_crops":
            list(
                CROP_NAMES.keys()
            ),

        "total_history_records":
            total_records,

        "onion_records":
            onion_records,

        "wheat_records":
            wheat_records
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
                "Unsupported crop. "
                "Use onion or wheat."
        }), 400

    try:

        record, analysis = (
            collect_crop(crop)
        )

        return jsonify({

            "success":
                True,

            "stored":
                True,

            "message":
                "Government market data "
                "fetched and stored successfully.",

            "record":
                record,

            "analysis":
                analysis
        })

    except Exception as error:

        print(
            "COLLECTION ERROR:",
            error
        )

        return jsonify({

            "success":
                False,

            "stored":
                False,

            "message":
                "Government market data "
                "could not be collected.",

            "error":
                str(error)
        }), 502


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
                "Unsupported crop. "
                "Use onion or wheat."
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
            DISTRICT,

        "state":
            STATE,

        "count":
            len(records),

        "records":
            records,

        "analysis":
            analysis
    })


# ============================================================
# MARKET
# ============================================================
#
# /api/market:
#
# 1. Gets latest government data
# 2. Stores today's record
# 3. Reads historical records
# 4. Calculates trend
# 5. Calculates moving averages
# 6. Calculates prediction
#
# If government API temporarily fails:
# - existing history is returned
# - NO fake price is created
#
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
                "Unsupported crop. "
                "Use onion or wheat."
        }), 400

    try:

        record, analysis = (
            collect_crop(crop)
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

            "market":
                MARKET_NAME,

            "district":
                DISTRICT,

            "state":
                STATE,

            "source":
                "Government of India OGD / AGMARKNET",

            "latest":
                record,

            "analysis":
                analysis,

            "history_count":
                len(history),

            "message":
                "Live government market data "
                "retrieved, stored, and analyzed."
        })

    except Exception as error:

        print(
            "MARKET API ERROR:",
            error
        )

        # ----------------------------------------------------
        # Do not lose existing history if today's government
        # request fails.
        # ----------------------------------------------------

        history = get_history_records(
            crop,
            limit=365
        )

        if history:

            analysis = calculate_analysis(
                history
            )

            return jsonify({

                "success":
                    True,

                "data_mode":
                    "historical_only",

                "fallback":
                    False,

                "market":
                    MARKET_NAME,

                "district":
                    DISTRICT,

                "state":
                    STATE,

                "source":
                    "Government of India OGD / AGMARKNET",

                "latest":
                    history[-1],

                "analysis":
                    analysis,

                "history_count":
                    len(history),

                "message":
                    "Live government data is "
                    "temporarily unavailable. "
                    "Showing previously stored "
                    "government market data.",

                "live_error":
                    str(error)
            })

        return jsonify({

            "success":
                False,

            "data_mode":
                "unavailable",

            "fallback":
                False,

            "market":
                MARKET_NAME,

            "district":
                DISTRICT,

            "state":
                STATE,

            "message":
                "Government market data is "
                "currently unavailable and "
                "no historical records exist yet.",

            "error":
                str(error)
        }), 502


# ============================================================
# FRONTEND
# ============================================================

@app.route("/")
def home():

    return send_from_directory(
        BASE_DIR,
        "index.html"
    )


@app.route(
    "/<path:filename>"
)
def files(filename):

    return send_from_directory(
        BASE_DIR,
        filename
    )


# ============================================================
# START SERVER
# ============================================================

if __name__ == "__main__":

    print()
    print("=" * 60)
    print("SMARTAGRI KOPARGAON")
    print("=" * 60)
    print("GOVERNMENT API + HISTORICAL DATA MODE")
    print("-" * 60)
    print("Onion")
    print("Wheat")
    print("-" * 60)
    print("Market:", MARKET_NAME)
    print("District:", DISTRICT)
    print("State:", STATE)
    print("-" * 60)
    print("Government API configured:",
          bool(DATA_GOV_API_KEY))
    print("Resource:", DATA_GOV_RESOURCE_ID)
    print("-" * 60)
    print("Database:", DATABASE_PATH)
    print("=" * 60)

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
