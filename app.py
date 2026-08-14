import os
import sqlite3
from datetime import datetime, timezone

import requests
from flask import Flask, jsonify, request, render_template
from flask_cors import CORS


# ============================================================
# SMARTAGRI KOPARGAON
# REAL MARKET DATA BACKEND
# ============================================================

app = Flask(
    __name__,
    template_folder=".",
    static_folder=".",
    static_url_path=""
)

CORS(app)


# ============================================================
# CONFIGURATION
# ============================================================

PORT = int(os.environ.get("PORT", 5000))

DATABASE = os.environ.get(
    "SMARTAGRI_DATABASE",
    "smartagri.db"
)


# ============================================================
# AGMARKNET CONFIGURATION
# ============================================================

AGMARKNET_BASE_URL = (
    "https://api.agmarknet.gov.in/v1"
)

AGMARKNET_HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Origin": "https://agmarknet.gov.in",
    "Referer": "https://agmarknet.gov.in/",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/151.0.0.0 Safari/537.36"
    )
}


# ============================================================
# LOCATION
# ============================================================

TARGET_STATE = "Maharashtra"
TARGET_DISTRICT = "Ahilyanagar"
TARGET_MARKET = "Kopargaon"


# ============================================================
# CROP CONFIGURATION
# ============================================================

CROPS = {

    "onion": {
        "names": [
            "onion",
            "kanda",
            "कांदा"
        ]
    },

    "wheat": {
        "names": [
            "wheat",
            "गेहूं",
            "गहू"
        ]
    }

}


# ============================================================
# EMERGENCY FALLBACK
# ============================================================
#
# IMPORTANT:
#
# These are NOT claimed to be live prices.
#
# They are used only if:
#
# 1. Agmarknet cannot be reached
# 2. No database record exists
#
# Once real data is saved, SQLite becomes the fallback.
# ============================================================

FALLBACK_PRICES = {

    "onion": 1950,

    "wheat": 2599

}


# ============================================================
# DATABASE
# ============================================================

def get_db():

    connection = sqlite3.connect(
        DATABASE
    )

    connection.row_factory = sqlite3.Row

    return connection


def initialize_database():

    connection = get_db()

    cursor = connection.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS market_prices (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            crop TEXT NOT NULL,

            market TEXT NOT NULL,

            price REAL NOT NULL,

            min_price REAL,

            max_price REAL,

            modal_price REAL,

            source TEXT NOT NULL,

            data_date TEXT NOT NULL,

            fetched_at TEXT NOT NULL,

            created_at TEXT NOT NULL

        )
        """
    )

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS
        idx_market_crop_date

        ON market_prices(
            crop,
            data_date
        )
        """
    )

    connection.commit()

    connection.close()


# ============================================================
# SAVE PRICE
# ============================================================

def save_market_price(
    crop,
    market,
    price,
    source,
    data_date,
    min_price=None,
    max_price=None,
    modal_price=None
):

    connection = get_db()

    cursor = connection.cursor()

    now = datetime.now(
        timezone.utc
    ).isoformat()

    cursor.execute(
        """
        INSERT INTO market_prices
        (
            crop,
            market,
            price,
            min_price,
            max_price,
            modal_price,
            source,
            data_date,
            fetched_at,
            created_at
        )

        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            crop,
            market,
            price,
            min_price,
            max_price,
            modal_price,
            source,
            data_date,
            now,
            now
        )
    )

    connection.commit()

    connection.close()


# ============================================================
# LATEST DATABASE RECORD
# ============================================================

def get_latest_price(crop):

    connection = get_db()

    row = connection.execute(
        """
        SELECT *

        FROM market_prices

        WHERE crop = ?

        ORDER BY
            data_date DESC,
            id DESC

        LIMIT 1
        """,
        (crop,)
    ).fetchone()

    connection.close()

    if row is None:

        return None

    return dict(row)


# ============================================================
# HISTORY
# ============================================================

def get_price_history(
    crop,
    limit=30
):

    connection = get_db()

    rows = connection.execute(
        """
        SELECT *

        FROM market_prices

        WHERE crop = ?

        ORDER BY
            data_date DESC,
            id DESC

        LIMIT ?
        """,
        (
            crop,
            limit
        )
    ).fetchall()

    connection.close()

    return [
        dict(row)
        for row in rows
    ]


# ============================================================
# PREVIOUS DIFFERENT-DAY PRICE
# ============================================================

def get_previous_price(crop):

    connection = get_db()

    rows = connection.execute(
        """
        SELECT *

        FROM market_prices

        WHERE crop = ?

        GROUP BY data_date

        ORDER BY
            data_date DESC

        LIMIT 2
        """,
        (crop,)
    ).fetchall()

    connection.close()

    if len(rows) < 2:

        return None

    return dict(rows[1])


# ============================================================
# NUMBER PARSER
# ============================================================

def parse_price(value):

    if value is None:

        return None

    try:

        text = str(value)

        text = (
            text
            .replace(",", "")
            .replace("₹", "")
            .replace("Rs.", "")
            .replace("Rs", "")
            .strip()
        )

        return float(text)

    except Exception:

        return None


# ============================================================
# DATE PARSER
# ============================================================

def normalize_date(value):

    if not value:

        return datetime.now(
            timezone.utc
        ).strftime("%Y-%m-%d")

    value = str(value).strip()

    formats = [

        "%d/%m/%Y",

        "%d-%m-%Y",

        "%Y-%m-%d",

        "%d/%m/%y",

        "%d-%m-%y",

        "%Y/%m/%d"

    ]

    for fmt in formats:

        try:

            parsed = datetime.strptime(
                value,
                fmt
            )

            return parsed.strftime(
                "%Y-%m-%d"
            )

        except ValueError:

            pass

    return datetime.now(
        timezone.utc
    ).strftime("%Y-%m-%d")


# ============================================================
# TEXT MATCHING
# ============================================================

def text_matches(
    value,
    search
):

    if value is None:

        return False

    return (
        str(search).strip().lower()
        in
        str(value).strip().lower()
    )


# ============================================================
# AGMARKNET REQUEST
# ============================================================

def agmarknet_get(
    endpoint,
    params=None
):

    url = (
        AGMARKNET_BASE_URL
        + endpoint
    )

    response = requests.get(
        url,
        params=params,
        headers=AGMARKNET_HEADERS,
        timeout=20
    )

    response.raise_for_status()

    return response.json()


# ============================================================
# GET AGMARKNET FILTERS
# ============================================================

def get_agmarknet_filters():

    return agmarknet_get(
        "/daily-price-arrival/filters"
    )


# ============================================================
# FIND COMMODITY
# ============================================================

def find_commodity_id(
    crop,
    filters
):

    crop_names = [
        name.lower()
        for name
        in CROPS[crop]["names"]
    ]

    possible_lists = [

        filters.get("data", {}).get(
            "commodity_data",
            []
        ),

        filters.get(
            "commodity_data",
            []
        ),

        filters.get("data", {}).get(
            "commodities",
            []
        )

    ]

    for records in possible_lists:

        if not isinstance(
            records,
            list
        ):

            continue

        for record in records:

            if not isinstance(
                record,
                dict
            ):

                continue

            name = (
                record.get("commodity_name")
                or record.get("commodity")
                or record.get("name")
                or ""
            )

            lowered = str(
                name
            ).lower()

            for crop_name in crop_names:

                if (
                    crop_name in lowered
                ):

                    return (
                        record.get("commodity_id")
                        or record.get("id")
                    )

    return None


# ============================================================
# FIND LOCATION IDS
# ============================================================

def find_location_ids():

    payload = agmarknet_get(
        "/location/state",
        {
            "page": 1
        }
    )

    states = (
        payload.get("states", [])
        or
        payload.get("data", [])
        or
        payload.get("data", {}).get(
            "states",
            []
        )
    )

    state_id = None
    district_id = None

    for state in states:

        state_name = (
            state.get("state_name")
            or state.get("name")
            or ""
        )

        if not text_matches(
            state_name,
            TARGET_STATE
        ):

            continue

        state_id = (
            state.get("state_id")
            or state.get("id")
        )

        districts = (
            state.get("districts", [])
        )

        for district in districts:

            district_name = (
                district.get(
                    "district_name"
                )
                or district.get("name")
                or ""
            )

            if text_matches(
                district_name,
                TARGET_DISTRICT
            ):

                district_id = (
                    district.get(
                        "district_id"
                    )
                    or district.get("id")
                )

                break

        break

    return (
        state_id,
        district_id
    )


# ============================================================
# FIND KOPARGAON MARKET
# ============================================================

def find_market_id(
    commodity_id,
    state_id,
    district_id
):

    payload = agmarknet_post_markets(
        commodity_id,
        state_id,
        district_id
    )

    records = (
        payload.get("markets", [])
        or payload.get("data", [])
        or payload.get("data", {}).get(
            "markets",
            []
        )
    )

    for record in records:

        name = (
            record.get("market_name")
            or record.get("market")
            or record.get("name")
            or ""
        )

        if text_matches(
            name,
            TARGET_MARKET
        ):

            return (
                record.get("market_id")
                or record.get("id")
            )

    return None


# ============================================================
# MARKET LIST REQUEST
# ============================================================

def agmarknet_post_markets(
    commodity_id,
    state_id,
    district_id
):

    url = (
        AGMARKNET_BASE_URL
        + "/markets"
    )

    payload = {

        "commodity_id": commodity_id,

        "state_id": state_id,

        "district_id": district_id

    }

    response = requests.post(
        url,
        json=payload,
        headers={
            **AGMARKNET_HEADERS,
            "Content-Type": "application/json"
        },
        timeout=20
    )

    response.raise_for_status()

    return response.json()


# ============================================================
# MARKET DAILY REPORT
# ============================================================

def fetch_agmarknet_market_price(
    crop
):

    filters = get_agmarknet_filters()

    commodity_id = find_commodity_id(
        crop,
        filters
    )

    if commodity_id is None:

        raise RuntimeError(
            f"Could not find Agmarknet commodity ID for {crop}"
        )

    state_id, district_id = (
        find_location_ids()
    )

    if state_id is None:

        raise RuntimeError(
            "Could not find Maharashtra state ID"
        )

    market_id = find_market_id(
        commodity_id,
        state_id,
        district_id
    )

    if market_id is None:

        raise RuntimeError(
            "Could not find Kopargaon market ID"
        )

    today = datetime.now(
        timezone.utc
    ).strftime("%Y-%m-%d")

    endpoint = (
        "/prices-and-arrivals/"
        "market-report/daily"
    )

    url = (
        AGMARKNET_BASE_URL
        + endpoint
    )

    payload = {

        "date": today,

        "market_ids": [
            market_id
        ],

        "state_ids": [
            state_id
        ]

    }

    response = requests.post(
        url,
        json=payload,
        headers={
            **AGMARKNET_HEADERS,
            "Content-Type":
                "application/json"
        },
        timeout=25
    )

    response.raise_for_status()

    data = response.json()

    return extract_market_record(
        data,
        crop
    )


# ============================================================
# EXTRACT PRICE RECORD
# ============================================================

def extract_market_record(
    payload,
    crop
):

    records = []

    if isinstance(
        payload,
        list
    ):

        records = payload

    elif isinstance(
        payload,
        dict
    ):

        possible_keys = [

            "data",

            "records",

            "results",

            "market_data",

            "price_data"

        ]

        for key in possible_keys:

            value = payload.get(
                key
            )

            if isinstance(
                value,
                list
            ):

                records.extend(
                    value
                )

            elif isinstance(
                value,
                dict
            ):

                records.append(
                    value
                )

    for record in records:

        if not isinstance(
            record,
            dict
        ):

            continue

        record_text = str(
            record
        ).lower()

        if (
            "kopargaon"
            not in record_text
        ):

            continue

        commodity = (
            record.get("commodity")
            or record.get(
                "commodity_name"
            )
            or ""
        )

        if not text_matches(
            commodity,
            crop
        ):

            continue

        modal = parse_price(
            record.get(
                "modal_price"
            )
            or record.get(
                "Modal_Price"
            )
            or record.get(
                "modal"
            )
            or record.get(
                "today_modal"
            )
            or record.get(
                "price"
            )
        )

        if modal is None:

            continue

        minimum = parse_price(
            record.get(
                "min_price"
            )
            or record.get(
                "Min_Price"
            )
            or record.get(
                "minimum_price"
            )
        )

        maximum = parse_price(
            record.get(
                "max_price"
            )
            or record.get(
                "Max_Price"
            )
            or record.get(
                "maximum_price"
            )
        )

        date = normalize_date(
            record.get(
                "arrival_date"
            )
            or record.get(
                "date"
            )
            or record.get(
                "price_date"
            )
            or record.get(
                "report_date"
            )
        )

        market = (
            record.get("market")
            or record.get(
                "market_name"
            )
            or TARGET_MARKET
        )

        return {

            "crop": crop,

            "market": str(
                market
            ),

            "price": modal,

            "min_price": minimum,

            "max_price": maximum,

            "modal_price": modal,

            "data_date": date,

            "source":
                "Agmarknet 2.0"

        }

    return None


# ============================================================
# REAL DATA ENGINE
# ============================================================

def get_market_data(
    crop
):

    # --------------------------------------------------------
    # 1. REAL AGMARKNET DATA
    # --------------------------------------------------------

    try:

        live = (
            fetch_agmarknet_market_price(
                crop
            )
        )

        if live:

            save_market_price(
                crop=crop,
                market=live["market"],
                price=live["price"],
                source=live["source"],
                data_date=live["data_date"],
                min_price=live.get(
                    "min_price"
                ),
                max_price=live.get(
                    "max_price"
                ),
                modal_price=live.get(
                    "modal_price"
                )
            )

            return {
                **live,
                "data_status":
                    "live",
                "message":
                    "Latest Kopargaon mandi price fetched from Agmarknet."
            }

    except Exception as exc:

        print(
            "AGMARKNET ERROR:",
            repr(exc)
        )


    # --------------------------------------------------------
    # 2. DATABASE
    # --------------------------------------------------------

    latest = get_latest_price(
        crop
    )

    if latest:

        return {

            "crop": crop,

            "market":
                latest["market"],

            "price":
                latest["price"],

            "min_price":
                latest["min_price"],

            "max_price":
                latest["max_price"],

            "modal_price":
                latest["modal_price"],

            "data_date":
                latest["data_date"],

            "source":
                latest["source"],

            "data_status":
                "historical_fallback",

            "message":
                "Latest recorded market price is being displayed."

        }


    # --------------------------------------------------------
    # 3. EMERGENCY BASELINE
    # --------------------------------------------------------

    price = FALLBACK_PRICES[
        crop
    ]

    today = datetime.now(
        timezone.utc
    ).strftime("%Y-%m-%d")

    save_market_price(
        crop=crop,
        market=TARGET_MARKET,
        price=price,
        source="SmartAgri emergency baseline",
        data_date=today,
        modal_price=price
    )

    return {

        "crop": crop,

        "market":
            TARGET_MARKET,

        "price":
            price,

        "min_price":
            None,

        "max_price":
            None,

        "modal_price":
            price,

        "data_date":
            today,

        "source":
            "SmartAgri emergency baseline",

        "data_status":
            "baseline",

        "message":
            "Emergency baseline used because no market record is available."

    }


# ============================================================
# TREND
# ============================================================

def calculate_trend(
    crop,
    current_price
):

    previous = get_previous_price(
        crop
    )

    if not previous:

        return {
            "trend": "Stable",
            "change": 0,
            "change_percent": 0
        }

    previous_price = float(
        previous["price"]
    )

    if previous_price <= 0:

        return {
            "trend": "Stable",
            "change": 0,
            "change_percent": 0
        }

    change = (
        current_price
        - previous_price
    )

    change_percent = (
        change
        / previous_price
    ) * 100

    if change_percent > 2:

        trend = "Increasing"

    elif change_percent < -2:

        trend = "Decreasing"

    else:

        trend = "Stable"

    return {

        "trend":
            trend,

        "change":
            round(
                change,
                2
            ),

        "change_percent":
            round(
                change_percent,
                2
            )

    }


# ============================================================
# FORECAST
# ============================================================

def calculate_forecast(
    crop,
    current_price
):

    history = get_price_history(
        crop,
        7
    )

    prices = [

        float(row["price"])

        for row in history

        if row.get("price")
        is not None

    ]

    if len(prices) < 2:

        forecast = current_price

    else:

        average = (
            sum(prices)
            / len(prices)
        )

        recent_change = (
            current_price
            - prices[1]
        )

        forecast = (
            average
            + (
                recent_change
                * 0.5
            )
        )

    minimum = (
        current_price
        * 0.75
    )

    maximum = (
        current_price
        * 1.35
    )

    forecast = max(
        minimum,
        min(
            forecast,
            maximum
        )
    )

    forecast = round(
        forecast
    )

    change_percent = (

        (
            forecast
            - current_price
        )
        / current_price

    ) * 100

    if change_percent > 3:

        message = (
            "Prices may increase based on recent market movement."
        )

    elif change_percent < -3:

        message = (
            "Prices may weaken based on recent market movement."
        )

    else:

        message = (
            "Prices are expected to remain relatively stable."
        )

    return {

        "forecast_price":
            forecast,

        "forecast_change_percent":
            round(
                change_percent,
                2
            ),

        "message":
            message

    }


# ============================================================
# DEMAND
# ============================================================

def calculate_demand(
    trend
):

    if trend == "Increasing":

        return "High"

    if trend == "Decreasing":

        return "Moderate"

    return "Stable"


# ============================================================
# SMART DECISION
# ============================================================

def calculate_decision(
    current_price,
    forecast_price,
    trend
):

    sell_now = current_price

    store = forecast_price

    transport = (
        current_price
        * 0.95
    )

    if (
        forecast_price
        > current_price
        * 1.08
    ):

        action = "Store"

        reason = (
            "The expected future price is significantly "
            "higher than the current market price. "
            "Storing may provide a better return if "
            "storage costs and crop quality are manageable."
        )

    elif (
        current_price
        >= forecast_price
        * 0.98
    ):

        action = "Sell Now"

        reason = (
            "The current market price is strong relative "
            "to the expected future price. Selling now "
            "may reduce price risk."
        )

    elif trend == "Increasing":

        action = "Store"

        reason = (
            "The recent market trend is increasing. "
            "Holding the crop may provide an opportunity "
            "for a better price."
        )

    else:

        action = "Sell Now"

        reason = (
            "The expected price improvement is not large "
            "enough to clearly justify waiting."
        )

    return {

        "sell_now":
            round(sell_now),

        "store":
            round(store),

        "transport":
            round(transport),

        "best_action":
            action,

        "reason":
            reason

    }


# ============================================================
# MAIN MARKET API
# ============================================================

@app.route(
    "/api/market",
    methods=["GET"]
)
def market_api():

    crop = request.args.get(
        "crop",
        "onion"
    ).lower().strip()

    if crop not in CROPS:

        return jsonify({

            "success":
                False,

            "error":
                "Supported crops: onion, wheat"

        }), 400

    try:

        market_data = (
            get_market_data(
                crop
            )
        )

        current_price = float(
            market_data["price"]
        )

        trend = calculate_trend(
            crop,
            current_price
        )

        forecast = calculate_forecast(
            crop,
            current_price
        )

        demand = calculate_demand(
            trend["trend"]
        )

        decision = calculate_decision(

            current_price,

            forecast[
                "forecast_price"
            ],

            trend[
                "trend"
            ]

        )

        return jsonify({

            "success":
                True,

            "crop":
                crop,

            "market":
                market_data[
                    "market"
                ],

            "current_price":
                round(
                    current_price
                ),

            "price":
                round(
                    current_price
                ),

            "min_price":
                market_data.get(
                    "min_price"
                ),

            "max_price":
                market_data.get(
                    "max_price"
                ),

            "modal_price":
                market_data.get(
                    "modal_price"
                ),

            "latest_date":
                market_data[
                    "data_date"
                ],

            "data_date":
                market_data[
                    "data_date"
                ],

            "source":
                market_data[
                    "source"
                ],

            "data_status":
                market_data[
                    "data_status"
                ],

            "message":
                market_data[
                    "message"
                ],

            "trend":
                trend[
                    "trend"
                ],

            "price_change":
                trend[
                    "change"
                ],

            "change_percent":
                trend[
                    "change_percent"
                ],

            "demand":
                demand,

            "forecast_price":
                forecast[
                    "forecast_price"
                ],

            "forecast_change_percent":
                forecast[
                    "forecast_change_percent"
                ],

            "forecast_message":
                forecast[
                    "message"
                ],

            "sell_now":
                decision[
                    "sell_now"
                ],

            "store":
                decision[
                    "store"
                ],

            "transport":
                decision[
                    "transport"
                ],

            "best_action":
                decision[
                    "best_action"
                ],

            "recommendation":
                decision[
                    "best_action"
                ],

            "recommendation_reason":
                decision[
                    "reason"
                ]

        })

    except Exception as exc:

        print(
            "MARKET API ERROR:",
            repr(exc)
        )

        return jsonify({

            "success":
                False,

            "error":
                "Market analysis failed.",

            "details":
                str(exc)

        }), 200


# ============================================================
# HISTORY API
# ============================================================

@app.route(
    "/api/market/history",
    methods=["GET"]
)
def market_history():

    crop = request.args.get(
        "crop",
        "onion"
    ).lower().strip()

    try:

        limit = int(
            request.args.get(
                "limit",
                30
            )
        )

    except ValueError:

        limit = 30

    limit = max(
        1,
        min(
            limit,
            365
        )
    )

    if crop not in CROPS:

        return jsonify({

            "success":
                False,

            "error":
                "Unsupported crop"

        }), 400

    history = get_price_history(
        crop,
        limit
    )

    return jsonify({

        "success":
            True,

        "crop":
            crop,

        "count":
            len(history),

        "history":
            history

    })


# ============================================================
# STATUS
# ============================================================

@app.route(
    "/api/status",
    methods=["GET"]
)
def status():

    return jsonify({

        "success":
            True,

        "service":
            "SmartAgri Kopargaon",

        "status":
            "online",

        "database":
            DATABASE,

        "agmarknet":
            "enabled",

        "latest": {

            "onion":
                get_latest_price(
                    "onion"
                ),

            "wheat":
                get_latest_price(
                    "wheat"
                )

        }

    })


# ============================================================
# HEALTH
# ============================================================

@app.route(
    "/health",
    methods=["GET"]
)
def health():

    return jsonify({

        "status":
            "healthy",

        "service":
            "SmartAgri Kopargaon"

    })


# ============================================================
# FRONTEND
# ============================================================

@app.route(
    "/",
    methods=["GET"]
)
def frontend():

    return render_template(
        "index.html"
    )


# ============================================================
# STARTUP
# ============================================================

initialize_database()


if __name__ == "__main__":

    print(
        "=========================================="
    )

    print(
        " SmartAgri Kopargaon"
    )

    print(
        " Real Market Intelligence Backend"
    )

    print(
        "=========================================="
    )

    print(
        f"Database: {DATABASE}"
    )

    print(
        "Agmarknet: enabled"
    )

    print(
        "Market: Kopargaon"
    )

    print(
        "=========================================="
    )

    app.run(
        host="0.0.0.0",
        port=PORT,
        debug=False
    )
