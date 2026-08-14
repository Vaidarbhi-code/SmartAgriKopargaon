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
# GOVERNMENT OGD / AGMARKNET VERSION
#
# Source:
# Government of India Open Government Data
# AGMARKNET market-price dataset
#
# NO MANDIPULSE
# NO HARDCODED PRICES
# NO FAKE PRICES
#
# The backend:
#
# 1. Requests government market data
# 2. Searches commodity records
# 3. Matches Kopargaon using flexible names
# 4. Stores successful government records
# 5. Maintains SQLite history
# 6. Calculates trend
# 7. Calculates moving averages
# 8. Calculates a simple short-term estimate
#
# Supported:
#   onion
#   wheat
#
# API:
#   /api/health
#   /api/market?crop=onion
#   /api/market?crop=wheat
#   /api/collect?crop=onion
#   /api/history?crop=onion
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

    print("=" * 70)
    print("SMARTAGRI DATABASE READY")
    print("=" * 70)
    print("Database:", DATABASE_PATH)
    print("=" * 70)


init_database()


# ============================================================
# MARKET CONFIGURATION
# ============================================================

MARKET_NAME = "Kopargaon"

DISTRICT = "Ahilyanagar"

STATE = "Maharashtra"


# ------------------------------------------------------------
# Important:
#
# Government data may use different names for the same place.
#
# Examples that may occur:
#
# Kopargaon
# Kopargaon APMC
# Kopargaon (APMC)
# Kopargaon Market
# Kopargaon(Mandi)
#
# Therefore we DO NOT require an exact string match.
# ------------------------------------------------------------

MARKET_ALIASES = [
    "kopargaon",
    "kopargaon apmc",
    "kopargaon market",
    "kopargaon mandi",
    "kopargaon(mandi)",
    "kopargaon(apmc)"
]


DISTRICT_ALIASES = [
    "ahilyanagar",
    "ahmednagar",
    "ahmadnagar",
    "nagar"
]


STATE_ALIASES = [
    "maharashtra"
]


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


# ============================================================
# REQUEST CONFIGURATION
# ============================================================

REQUEST_TIMEOUT = (
    8,
    15
)


HEADERS = {

    "User-Agent":
        "SmartAgriKopargaon/2.0 "
        "(Government OGD API Client)",

    "Accept":
        "application/json"

}


# ============================================================
# TEXT HELPERS
# ============================================================

def clean_text(value):

    if value is None:
        return ""

    return str(value).strip()


def normalize_text(value):

    text = clean_text(value).lower()

    text = re.sub(
        r"[^a-z0-9]+",
        " ",
        text
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    ).strip()

    return text


# ============================================================
# NUMBER HELPERS
# ============================================================

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
        ""
    )

    text = text.replace(
        "Rs",
        ""
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
# NORMALIZE API KEYS
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


def get_field(
    record,
    *possible_names
):

    normalized = normalized_record(
        record
    )

    for name in possible_names:

        key = normalize_key(
            name
        )

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

        "%m/%d/%Y"

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


    # Try extracting a date from text.

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
# LOCATION MATCHING
# ============================================================

def contains_alias(
    value,
    aliases
):

    normalized = normalize_text(
        value
    )

    if not normalized:
        return False

    for alias in aliases:

        alias_normalized = normalize_text(
            alias
        )

        if (
            alias_normalized
            in normalized
        ):

            return True

    return False


def market_match_score(
    market
):

    normalized_market = normalize_text(
        market
    )

    if not normalized_market:

        return 0


    # Strongest possible match.

    if normalized_market == "kopargaon":

        return 100


    if normalized_market == "kopargaon apmc":

        return 100


    if (
        "kopargaon"
        in normalized_market
    ):

        return 95


    return 0


def district_match_score(
    district
):

    normalized_district = normalize_text(
        district
    )

    if not normalized_district:

        return 0


    if (
        normalized_district
        == "ahilyanagar"
    ):

        return 40


    if (
        normalized_district
        == "ahmednagar"
    ):

        return 40


    if (
        normalized_district
        == "ahmadnagar"
    ):

        return 40


    if (
        "ahilyanagar"
        in normalized_district
    ):

        return 40


    if (
        "ahmednagar"
        in normalized_district
    ):

        return 40


    if (
        "ahmadnagar"
        in normalized_district
    ):

        return 40


    return 0


def state_match_score(
    state
):

    normalized_state = normalize_text(
        state
    )

    if (
        normalized_state
        == "maharashtra"
    ):

        return 20


    if (
        "maharashtra"
        in normalized_state
    ):

        return 20


    return 0


# ============================================================
# FIND BEST RECORD
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
                "Commodity",
                "commodity_name",
                "commodityname"
            )
        )


        market = clean_text(
            get_field(
                record,
                "market",
                "Market",
                "market_name",
                "marketname"
            )
        )


        district = clean_text(
            get_field(
                record,
                "district",
                "District",
                "district_name",
                "districtname"
            )
        )


        state = clean_text(
            get_field(
                record,
                "state",
                "State",
                "state_name",
                "statename"
            )
        )


        # ----------------------------------------------------
        # Commodity
        # ----------------------------------------------------

        commodity_normalized = normalize_text(
            commodity
        )

        expected_normalized = normalize_text(
            expected_commodity
        )


        commodity_match = (

            commodity_normalized
            == expected_normalized

        )


        if not commodity_match:

            commodity_match = (

                expected_normalized
                in commodity_normalized

                or

                commodity_normalized
                in expected_normalized

            )


        if not commodity_match:

            continue


        # ----------------------------------------------------
        # Location scores
        # ----------------------------------------------------

        market_score = (
            market_match_score(
                market
            )
        )


        district_score = (
            district_match_score(
                district
            )
        )


        state_score = (
            state_match_score(
                state
            )
        )


        # ----------------------------------------------------
        # We ONLY accept Kopargaon records.
        #
        # This prevents accidentally showing a price from
        # another Maharashtra market.
        # ----------------------------------------------------

        if market_score <= 0:

            continue


        # ----------------------------------------------------
        # Date
        # ----------------------------------------------------

        arrival_date = parse_date(
            get_field(
                record,
                "arrival_date",
                "arrivaldate",
                "date",
                "reported_date",
                "reportdate"
            )
        )


        if arrival_date:

            date_score = 10

        else:

            date_score = 0


        # ----------------------------------------------------
        # Price availability
        # ----------------------------------------------------

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


        # We need at least a usable price.

        if (
            min_price is None
            and
            max_price is None
            and
            modal_price is None
        ):

            continue


        total_score = (
            market_score
            +
            district_score
            +
            state_score
            +
            date_score
        )


        candidates.append(
            (
                total_score,
                arrival_date or "0000-00-00",
                record
            )
        )


    if not candidates:

        return None


    # Highest location score.
    # If equal, newest date wins.

    candidates.sort(
        key=lambda item: (
            item[0],
            item[1]
        ),
        reverse=True
    )


    selected = candidates[0][2]


    print()
    print(
        "MATCHED GOVERNMENT RECORD"
    )
    print(
        "Commodity:",
        get_field(
            selected,
            "commodity",
            "Commodity"
        )
    )
    print(
        "Market:",
        get_field(
            selected,
            "market",
            "Market",
            "market_name"
        )
    )
    print(
        "District:",
        get_field(
            selected,
            "district",
            "District"
        )
    )
    print(
        "State:",
        get_field(
            selected,
            "state",
            "State"
        )
    )
    print(
        "Date:",
        get_field(
            selected,
            "arrival_date",
            "arrivaldate",
            "date"
        )
    )
    print(
        "Modal:",
        get_field(
            selected,
            "modal_price",
            "modalprice"
        )
    )
    print()


    return selected


# ============================================================
# GOVERNMENT API REQUEST
# ============================================================

def government_request(
    params
):

    try:

        response = requests.get(

            DATA_GOV_API_URL,

            params=params,

            headers=HEADERS,

            timeout=REQUEST_TIMEOUT

        )

        print(
            "Government API URL:",
            response.url
        )

        print(
            "Government API status:",
            response.status_code
        )


        response.raise_for_status()


    except requests.Timeout as error:

        raise RuntimeError(
            "Government OGD API timed out."
        ) from error


    except requests.RequestException as error:

        raise RuntimeError(
            "Government OGD API request failed: "
            + str(error)
        ) from error


    try:

        payload = response.json()

    except ValueError as error:

        raise RuntimeError(
            "Government OGD API returned invalid JSON."
        ) from error


    if not isinstance(
        payload,
        dict
    ):

        raise RuntimeError(
            "Government OGD API returned an unexpected response."
        )


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


    return records


# ============================================================
# FETCH GOVERNMENT DATA
# ============================================================

def fetch_government_market_data(
    crop
):

    if not DATA_GOV_API_KEY:

        raise RuntimeError(
            "DATA_GOV_API_KEY is not configured on Render."
        )


    commodity = CROP_NAMES[crop]


    print()
    print("=" * 70)
    print("SMARTAGRI GOVERNMENT MARKET REQUEST")
    print("=" * 70)
    print("Crop:", crop)
    print("Commodity:", commodity)
    print("Target market:", MARKET_NAME)
    print("Target district:", DISTRICT)
    print("Target state:", STATE)
    print("Resource:", DATA_GOV_RESOURCE_ID)
    print("=" * 70)


    # ========================================================
    # REQUEST 1
    #
    # Search only commodity.
    #
    # We intentionally do NOT filter Market here because
    # the government dataset may use a different market
    # spelling/name.
    # ========================================================

    params = {

        "api-key":
            DATA_GOV_API_KEY,

        "format":
            "json",

        "limit":
            1000,

        "offset":
            0,

        "filters[Commodity]":
            commodity

    }


    records = government_request(
        params
    )


    selected = find_matching_record(
        records,
        crop
    )


    if selected is not None:

        return selected


    # ========================================================
    # REQUEST 2
    #
    # Try state filter.
    # ========================================================

    state_params = {

        "api-key":
            DATA_GOV_API_KEY,

        "format":
            "json",

        "limit":
            1000,

        "offset":
            0,

        "filters[State]":
            STATE,

        "filters[Commodity]":
            commodity

    }


    state_records = government_request(
        state_params
    )


    selected = find_matching_record(
        state_records,
        crop
    )


    if selected is not None:

        return selected


    # ========================================================
    # REQUEST 3
    #
    # Try district filter using the current official name.
    # ========================================================

    district_params = {

        "api-key":
            DATA_GOV_API_KEY,

        "format":
            "json",

        "limit":
            1000,

        "offset":
            0,

        "filters[District]":
            DISTRICT,

        "filters[Commodity]":
            commodity

    }


    district_records = government_request(
        district_params
    )


    selected = find_matching_record(
        district_records,
        crop
    )


    if selected is not None:

        return selected


    # ========================================================
    # REQUEST 4
    #
    # Old district name.
    # ========================================================

    old_district_params = {

        "api-key":
            DATA_GOV_API_KEY,

        "format":
            "json",

        "limit":
            1000,

        "offset":
            0,

        "filters[District]":
            "Ahmednagar",

        "filters[Commodity]":
            commodity

    }


    old_district_records = government_request(
        old_district_params
    )


    selected = find_matching_record(
        old_district_records,
        crop
    )


    if selected is not None:

        return selected


    # ========================================================
    # Nothing found.
    # ========================================================

    raise RuntimeError(
        "No Kopargaon government market record "
        "was found for "
        + commodity
        + ". "
        "The OGD API responded, but the returned records "
        "did not contain a Kopargaon market entry with "
        "usable price data."
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
            "Commodity",
            "commodity_name",
            "commodityname"
        )
    )


    market = clean_text(
        get_field(
            raw_record,
            "market",
            "Market",
            "market_name",
            "marketname"
        )
    )


    district = clean_text(
        get_field(
            raw_record,
            "district",
            "District",
            "district_name",
            "districtname"
        )
    )


    state = clean_text(
        get_field(
            raw_record,
            "state",
            "State",
            "state_name",
            "statename"
        )
    )


    arrival_date = parse_date(
        get_field(
            raw_record,
            "arrival_date",
            "arrivaldate",
            "date",
            "reported_date",
            "reportdate"
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
            "Government record does not contain a valid date."
        )


    # --------------------------------------------------------
    # If one price field is missing, derive it only from
    # other REAL government price fields.
    #
    # No external/fake value is introduced.
    # --------------------------------------------------------

    if modal_price is None:

        if (
            min_price is not None
            and
            max_price is not None
        ):

            modal_price = (
                min_price
                +
                max_price
            ) / 2


    if min_price is None:

        if modal_price is not None:

            min_price = modal_price


    if max_price is None:

        if modal_price is not None:

            max_price = modal_price


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
# HISTORY
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
                -
                previous_price
            )
            /
            previous_price

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
# ANALYSIS
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


    # ========================================================
    # SHORT-TERM ESTIMATE
    # ========================================================

    if len(prices) < 3:

        prediction_direction = (
            "insufficient_data"
        )

        estimated_price = None

        confidence = "low"

        reason = (
            "At least 3 historical "
            "government price records "
            "are recommended."
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
                        current
                        -
                        previous
                    )
                    /
                    previous
                    *
                    100

                )


        if changes:

            average_change = statistics.mean(
                changes
            )

        else:

            average_change = 0


        # Keep the estimate conservative.

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
            *
            (
                1
                +
                capped_change / 100
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
            "government historical "
            "modal-price movement."
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
            bool(
                DATA_GOV_API_KEY
            ),

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
# COLLECT ENDPOINT
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
# HISTORY ENDPOINT
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
# MARKET ENDPOINT
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
                record["market"],

            "district":
                record["district"],

            "state":
                record["state"],

            "source":
                "Government of India OGD / AGMARKNET",

            "latest":
                record,

            "analysis":
                analysis,

            "history_count":
                len(history),

            "message":
                "Government market data "
                "retrieved, stored and analyzed."

        })


    except Exception as error:

        print(
            "MARKET API ERROR:",
            error
        )


        # ====================================================
        # If live government request fails, use previously
        # stored GOVERNMENT data.
        #
        # Still no fake price.
        # ====================================================

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
                    history[-1]["market"],

                "district":
                    history[-1]["district"],

                "state":
                    history[-1]["state"],

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
                "no historical government "
                "records have been stored yet.",

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
    print("=" * 70)
    print("SMARTAGRI KOPARGAON")
    print("=" * 70)
    print("GOVERNMENT OGD / AGMARKNET")
    print("-" * 70)
    print("Onion")
    print("Wheat")
    print("-" * 70)
    print("Market:", MARKET_NAME)
    print("District:", DISTRICT)
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
