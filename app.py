import os
import sqlite3
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
from flask import Flask, jsonify, request
from flask_cors import CORS


# ============================================================
# SMARTAGRI KOPARGAON
# MARKET INTELLIGENCE BACKEND
# ============================================================

app = Flask(__name__)
CORS(app)


# ============================================================
# CONFIGURATION
# ============================================================

PORT = int(os.environ.get("PORT", 5000))

DATABASE = os.environ.get(
    "SMARTAGRI_DATABASE",
    "smartagri.db"
)

INDIA_TZ = ZoneInfo("Asia/Kolkata")


# ============================================================
# DATA.GOV.IN CONFIGURATION
# ============================================================

DATA_GOV_API_KEY = os.environ.get(
    "DATA_GOV_API_KEY",
    ""
)

DATA_GOV_RESOURCE_ID = os.environ.get(
    "DATA_GOV_RESOURCE_ID",
    "9ef84268-d588-465a-a308-a864a43d0070"
)

DATA_GOV_URL = (
    "https://api.data.gov.in/resource/"
    + DATA_GOV_RESOURCE_ID
)


# ============================================================
# CROP CONFIGURATION
# ============================================================

CROPS = {
    "onion": {
        "names": [
            "onion",
            "Onion",
            "ONION",
            "Kanda",
            "Kandaa",
            "कांदा",
            "कांदा "
        ],
        "baseline": 2200
    },

    "wheat": {
        "names": [
            "wheat",
            "Wheat",
            "WHEAT",
            "Gehun",
            "गेहूं",
            "गहू"
        ],
        "baseline": 2600
    }
}


# ============================================================
# BASELINE PRICES
# ============================================================
#
# These are ONLY used if the application has never recorded
# a price for the crop and all live sources fail.
#
# They are NOT labelled as live market prices.
# ============================================================

BASELINE_PRICES = {
    "onion": 2200,
    "wheat": 2600
}


# ============================================================
# TIME HELPERS
# ============================================================

def now_india():
    return datetime.now(INDIA_TZ)


def today_india():
    return now_india().strftime("%Y-%m-%d")


def current_timestamp():
    return now_india().isoformat()


# ============================================================
# DATABASE
# ============================================================

def get_db():
    connection = sqlite3.connect(
        DATABASE,
        timeout=30
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

    now = current_timestamp()

    # --------------------------------------------------------
    # Prevent duplicate records for the same crop/date/source.
    # --------------------------------------------------------

    existing = cursor.execute(
        """
        SELECT id
        FROM market_prices
        WHERE crop = ?
        AND data_date = ?
        AND source = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (
            crop,
            data_date,
            source
        )
    ).fetchone()

    if existing:

        cursor.execute(
            """
            UPDATE market_prices

            SET
                market = ?,
                price = ?,
                min_price = ?,
                max_price = ?,
                modal_price = ?,
                fetched_at = ?

            WHERE id = ?
            """,
            (
                market,
                price,
                min_price,
                max_price,
                modal_price,
                now,
                existing["id"]
            )
        )

    else:

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
# LATEST PRICE
# ============================================================

def get_latest_price(crop):

    connection = get_db()

    cursor = connection.cursor()

    row = cursor.execute(
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

    cursor = connection.cursor()

    rows = cursor.execute(
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

    history = get_price_history(
        crop,
        10
    )

    if len(history) < 2:
        return None

    latest_date = history[0]["data_date"]

    for row in history[1:]:

        if row["data_date"] != latest_date:

            return row

    return None


# ============================================================
# PRICE PARSER
# ============================================================

def parse_price(value):

    if value is None:
        return None

    try:

        text = str(value).strip()

        text = (
            text
            .replace(",", "")
            .replace("₹", "")
            .replace("Rs.", "")
            .replace("Rs", "")
            .strip()
        )

        number = float(text)

        if number <= 0:
            return None

        return number

    except Exception:

        return None


# ============================================================
# DATE PARSER
# ============================================================

def normalize_date(value):

    if not value:

        return today_india()

    text = str(value).strip()

    formats = [
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%Y-%m-%d",
        "%d/%m/%y",
        "%d-%m-%y",
        "%Y/%m/%d",
        "%d.%m.%Y"
    ]

    for fmt in formats:

        try:

            parsed = datetime.strptime(
                text,
                fmt
            )

            return parsed.strftime(
                "%Y-%m-%d"
            )

        except ValueError:

            pass

    return today_india()


# ============================================================
# CROP MATCHING
# ============================================================

def crop_matches(
    record_crop,
    requested_crop
):

    if not record_crop:
        return False

    record_text = str(
        record_crop
    ).strip().lower()

    requested_crop = (
        requested_crop
        .strip()
        .lower()
    )

    if requested_crop not in CROPS:
        return False

    names = CROPS[
        requested_crop
    ]["names"]

    for name in names:

        name_text = str(
            name
        ).strip().lower()

        if record_text == name_text:
            return True

    return requested_crop in record_text


# ============================================================
# FIELD HELPER
# ============================================================

def first_value(
    record,
    keys
):

    for key in keys:

        value = record.get(key)

        if value is not None:
            return value

    return None


# ============================================================
# GOVERNMENT RECORD PARSER
# ============================================================

def parse_government_record(
    record,
    crop
):

    modal_price = parse_price(
        first_value(
            record,
            [
                "modal_price",
                "Modal_Price",
                "modal",
                "Modal Price",
                "modal price",
                "price_per_quintal",
                "Price",
                "price"
            ]
        )
    )

    min_price = parse_price(
        first_value(
            record,
            [
                "min_price",
                "Min_Price",
                "minimum_price",
                "Minimum_Price",
                "min"
            ]
        )
    )

    max_price = parse_price(
        first_value(
            record,
            [
                "max_price",
                "Max_Price",
                "maximum_price",
                "Maximum_Price",
                "max"
            ]
        )
    )

    if modal_price is None:
        return None

    data_date = normalize_date(
        first_value(
            record,
            [
                "arrival_date",
                "Arrival_Date",
                "date",
                "Date",
                "price_date",
                "Price_Date",
                "reported_date"
            ]
        )
    )

    market = first_value(
        record,
        [
            "market",
            "Market",
            "market_name",
            "Market_Name",
            "mandi"
        ]
    )

    if not market:
        market = "Kopargaon"

    return {

        "crop": crop,

        "market": str(market),

        "price": modal_price,

        "min_price": min_price,

        "max_price": max_price,

        "modal_price": modal_price,

        "data_date": data_date,

        "source": "data.gov.in / Agmarknet"

    }


# ============================================================
# DATA.GOV.IN
# ============================================================

def fetch_from_data_gov(crop):

    if not DATA_GOV_API_KEY:

        return None, (
            "Government API key is not configured."
        )

    params = {

        "api-key": DATA_GOV_API_KEY,

        "format": "json",

        "limit": 5000
    }

    response = requests.get(
        DATA_GOV_URL,
        params=params,
        timeout=20
    )

    response.raise_for_status()

    payload = response.json()

    records = payload.get(
        "records",
        []
    )

    if not records:

        return None, (
            "Government API returned no records."
        )

    # --------------------------------------------------------
    # Exact crop + Kopargaon search
    # --------------------------------------------------------

    matches = []

    for record in records:

        commodity = first_value(
            record,
            [
                "commodity",
                "Commodity",
                "crop",
                "Crop",
                "commodity_name",
                "Commodity_Name"
            ]
        )

        if not crop_matches(
            commodity,
            crop
        ):
            continue

        record_text = (
            str(record)
            .lower()
        )

        if "kopargaon" in record_text:

            parsed = parse_government_record(
                record,
                crop
            )

            if parsed:
                matches.append(parsed)

    # --------------------------------------------------------
    # Pick newest Kopargaon record
    # --------------------------------------------------------

    if matches:

        matches.sort(
            key=lambda item:
                item["data_date"],
            reverse=True
        )

        return matches[0], None

    return None, (
        f"No Kopargaon record was found "
        f"in the government dataset for "
        f"{crop}."
    )


# ============================================================
# SECONDARY SOURCE
# ============================================================
#
# This intentionally remains disabled until a verified API
# endpoint is configured.
#
# Do NOT invent live prices.
# ============================================================

def fetch_secondary_source(crop):

    secondary_url = os.environ.get(
        "SECONDARY_MARKET_API_URL",
        ""
    ).strip()

    if not secondary_url:
        return None

    try:

        response = requests.get(
            secondary_url,
            params={
                "crop": crop,
                "market": "Kopargaon"
            },
            timeout=15
        )

        response.raise_for_status()

        payload = response.json()

        # Expected format:
        #
        # {
        #   "price": 2300,
        #   "market": "Kopargaon",
        #   "data_date": "2026-08-14"
        # }

        price = parse_price(
            payload.get("price")
        )

        if price is None:
            return None

        return {

            "crop": crop,

            "market": payload.get(
                "market",
                "Kopargaon"
            ),

            "price": price,

            "min_price": parse_price(
                payload.get(
                    "min_price"
                )
            ),

            "max_price": parse_price(
                payload.get(
                    "max_price"
                )
            ),

            "modal_price": parse_price(
                payload.get(
                    "modal_price"
                )
            ) or price,

            "data_date": normalize_date(
                payload.get(
                    "data_date"
                )
            ),

            "source": payload.get(
                "source",
                "Secondary market source"
            )

        }

    except Exception as exc:

        print(
            "SECONDARY SOURCE ERROR:",
            repr(exc)
        )

        return None


# ============================================================
# MARKET DATA
# ============================================================

def get_market_data(crop):

    crop = crop.lower().strip()

    if crop not in CROPS:

        return None, "Unsupported crop."


    # ========================================================
    # 1. LIVE GOVERNMENT DATA
    # ========================================================

    try:

        live_data, live_error = (
            fetch_from_data_gov(crop)
        )

        if live_data:

            save_market_price(

                crop=crop,

                market=live_data[
                    "market"
                ],

                price=live_data[
                    "price"
                ],

                source=live_data[
                    "source"
                ],

                data_date=live_data[
                    "data_date"
                ],

                min_price=live_data.get(
                    "min_price"
                ),

                max_price=live_data.get(
                    "max_price"
                ),

                modal_price=live_data.get(
                    "modal_price"
                )
            )

            return {

                **live_data,

                "data_status": "live",

                "message": (
                    "Latest available market "
                    "price fetched successfully."
                )

            }, None

        print(
            "GOVERNMENT SOURCE:",
            live_error
        )

    except Exception as exc:

        print(
            "GOVERNMENT API ERROR:",
            repr(exc)
        )


    # ========================================================
    # 2. SECONDARY SOURCE
    # ========================================================

    try:

        secondary_data = (
            fetch_secondary_source(
                crop
            )
        )

        if secondary_data:

            save_market_price(

                crop=crop,

                market=secondary_data[
                    "market"
                ],

                price=secondary_data[
                    "price"
                ],

                source=secondary_data[
                    "source"
                ],

                data_date=secondary_data[
                    "data_date"
                ],

                min_price=secondary_data.get(
                    "min_price"
                ),

                max_price=secondary_data.get(
                    "max_price"
                ),

                modal_price=secondary_data.get(
                    "modal_price"
                )
            )

            return {

                **secondary_data,

                "data_status": "live",

                "message": (
                    "Latest available market "
                    "price fetched successfully."
                )

            }, None

    except Exception as exc:

        print(
            "SECONDARY API ERROR:",
            repr(exc)
        )


    # ========================================================
    # 3. DATABASE
    # ========================================================

    latest = get_latest_price(
        crop
    )

    if latest:

        return {

            "crop": crop,

            "market": latest[
                "market"
            ],

            "price": latest[
                "price"
            ],

            "min_price": latest[
                "min_price"
            ],

            "max_price": latest[
                "max_price"
            ],

            "modal_price": latest[
                "modal_price"
            ],

            "data_date": latest[
                "data_date"
            ],

            "source": latest[
                "source"
            ],

            "data_status":
                "recorded",

            "message": (
                "Showing the latest recorded "
                "market price."
            )

        }, None


    # ========================================================
    # 4. INITIAL BASELINE
    # ========================================================

    baseline_price = BASELINE_PRICES[
        crop
    ]

    date = today_india()

    save_market_price(

        crop=crop,

        market="Kopargaon",

        price=baseline_price,

        source="SmartAgri baseline",

        data_date=date,

        modal_price=baseline_price
    )

    return {

        "crop": crop,

        "market": "Kopargaon",

        "price": baseline_price,

        "min_price": None,

        "max_price": None,

        "modal_price": baseline_price,

        "data_date": date,

        "source": "SmartAgri baseline",

        "data_status": "baseline",

        "message": (
            "Initial reference price recorded. "
            "It will be replaced when a newer "
            "market price becomes available."
        )

    }, None


# ============================================================
# TREND ANALYSIS
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

    try:

        previous_price = float(
            previous["price"]
        )

    except Exception:

        return {

            "trend": "Stable",

            "change": 0,

            "change_percent": 0

        }

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

        "trend": trend,

        "change": round(
            change,
            2
        ),

        "change_percent": round(
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

    prices = []

    for row in history:

        try:

            value = float(
                row["price"]
            )

            if value > 0:
                prices.append(value)

        except Exception:
            pass

    if len(prices) < 2:

        forecast = current_price

    else:

        average = (
            sum(prices)
            / len(prices)
        )

        previous = prices[1]

        movement = (
            current_price
            - previous
        )

        forecast = (
            average
            + movement * 0.50
        )

    # --------------------------------------------------------
    # Keep forecast within a reasonable range.
    # --------------------------------------------------------

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

    if current_price <= 0:

        change_percent = 0

    else:

        change_percent = (
            (
                forecast
                - current_price
            )
            / current_price
        ) * 100

    change_percent = round(
        change_percent,
        2
    )

    if change_percent > 3:

        message = (
            "Prices may increase based "
            "on recent recorded movement."
        )

    elif change_percent < -3:

        message = (
            "Prices may weaken based "
            "on recent recorded movement."
        )

    else:

        message = (
            "Prices are expected to remain "
            "relatively stable."
        )

    return {

        "forecast_price": forecast,

        "forecast_change_percent":
            change_percent,

        "message": message

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

    sell_value = current_price

    store_value = forecast_price

    # Estimated transport deduction.
    transport_cost = (
        current_price
        * 0.05
    )

    transport_value = (
        current_price
        - transport_cost
    )

    # --------------------------------------------------------
    # Strong expected increase
    # --------------------------------------------------------

    if forecast_price > (
        current_price * 1.08
    ):

        action = "Store"

        reason = (
            "The forecast price is significantly "
            "higher than the current recorded price. "
            "Storing may provide a better return if "
            "storage cost, crop quality and market "
            "risk are manageable."
        )

    # --------------------------------------------------------
    # Current price is already strong
    # --------------------------------------------------------

    elif current_price >= (
        forecast_price * 0.98
    ):

        action = "Sell Now"

        reason = (
            "The current recorded price is strong "
            "relative to the expected future price. "
            "Selling now may reduce price risk."
        )

    # --------------------------------------------------------
    # Increasing trend
    # --------------------------------------------------------

    elif trend == "Increasing":

        action = "Store"

        reason = (
            "Recent recorded prices are increasing. "
            "Holding the crop may provide an opportunity "
            "for a better price, subject to storage costs "
            "and market risk."
        )

    # --------------------------------------------------------
    # Default
    # --------------------------------------------------------

    else:

        action = "Sell Now"

        reason = (
            "The expected price improvement is not "
            "large enough to clearly justify waiting."
        )

    return {

        "sell_now": round(
            sell_value
        ),

        "store": round(
            store_value
        ),

        "transport": round(
            transport_value
        ),

        "best_action": action,

        "reason": reason

    }


# ============================================================
# BUILD COMPLETE MARKET RESPONSE
# ============================================================

def build_market_response(
    crop,
    market_data
):

    current_price = float(
        market_data["price"]
    )

    trend_data = calculate_trend(
        crop,
        current_price
    )

    forecast_data = calculate_forecast(
        crop,
        current_price
    )

    demand = calculate_demand(
        trend_data["trend"]
    )

    decision = calculate_decision(

        current_price,

        forecast_data[
            "forecast_price"
        ],

        trend_data[
            "trend"
        ]
    )

    return {

        "success": True,

        "crop": crop,

        "market": market_data[
            "market"
        ],

        "current_price": round(
            current_price
        ),

        "price": round(
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
            trend_data[
                "trend"
            ],

        "price_change":
            trend_data[
                "change"
            ],

        "change_percent":
            trend_data[
                "change_percent"
            ],

        "demand":
            demand,

        "forecast_price":
            forecast_data[
                "forecast_price"
            ],

        "forecast_change_percent":
            forecast_data[
                "forecast_change_percent"
            ],

        "forecast_message":
            forecast_data[
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

    }


# ============================================================
# MARKET API
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

            "success": False,

            "error": (
                "Supported crops: "
                "onion, wheat"
            )

        }), 400

    try:

        market_data, error = (
            get_market_data(crop)
        )

        if market_data:

            return jsonify(
                build_market_response(
                    crop,
                    market_data
                )
            )

        return jsonify({

            "success": True,

            "crop": crop,

            "market": "Kopargaon",

            "current_price":
                BASELINE_PRICES[crop],

            "price":
                BASELINE_PRICES[crop],

            "latest_date":
                today_india(),

            "data_date":
                today_india(),

            "source":
                "SmartAgri baseline",

            "data_status":
                "baseline",

            "message":
                "Showing the latest available reference price.",

            "trend": "Stable",

            "price_change": 0,

            "change_percent": 0,

            "demand": "Stable",

            "forecast_price":
                BASELINE_PRICES[crop],

            "forecast_change_percent": 0,

            "forecast_message":
                "Prices are currently estimated to remain stable.",

            "sell_now":
                BASELINE_PRICES[crop],

            "store":
                BASELINE_PRICES[crop],

            "transport":
                round(
                    BASELINE_PRICES[crop]
                    * 0.95
                ),

            "best_action":
                "Sell Now",

            "recommendation":
                "Sell Now",

            "recommendation_reason":
                "The system does not yet have enough historical market observations to justify waiting.",

            "fallback_reason":
                error

        })

    except Exception as exc:

        print(
            "MARKET API ERROR:",
            repr(exc)
        )

        # ----------------------------------------------------
        # Last-resort database fallback
        # ----------------------------------------------------

        try:

            latest = get_latest_price(
                crop
            )

            if latest:

                response = build_market_response(

                    crop,

                    {

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
                            "recorded",

                        "message":
                            "Showing the latest recorded market price."

                    }

                )

                return jsonify(
                    response
                )

        except Exception as fallback_error:

            print(
                "DATABASE FALLBACK ERROR:",
                repr(fallback_error)
            )

        # ----------------------------------------------------
        # Absolute fallback
        # ----------------------------------------------------

        baseline = BASELINE_PRICES[
            crop
        ]

        return jsonify({

            "success": True,

            "crop": crop,

            "market": "Kopargaon",

            "current_price":
                baseline,

            "price":
                baseline,

            "latest_date":
                today_india(),

            "data_date":
                today_india(),

            "source":
                "SmartAgri baseline",

            "data_status":
                "baseline",

            "message":
                "Showing the latest available reference price.",

            "trend":
                "Stable",

            "price_change":
                0,

            "change_percent":
                0,

            "demand":
                "Stable",

            "forecast_price":
                baseline,

            "forecast_change_percent":
                0,

            "forecast_message":
                "Prices are currently estimated to remain stable.",

            "sell_now":
                baseline,

            "store":
                baseline,

            "transport":
                round(
                    baseline * 0.95
                ),

            "best_action":
                "Sell Now",

            "recommendation":
                "Sell Now",

            "recommendation_reason":
                "The system is using its latest available reference price while the market source is unavailable."

        })


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

            "success": False,

            "error":
                "Supported crops: onion, wheat"

        }), 400

    history = get_price_history(
        crop,
        limit
    )

    return jsonify({

        "success": True,

        "crop": crop,

        "count": len(history),

        "history": history

    })


# ============================================================
# STATUS API
# ============================================================

@app.route(
    "/api/status",
    methods=["GET"]
)
def status():

    onion = get_latest_price(
        "onion"
    )

    wheat = get_latest_price(
        "wheat"
    )

    return jsonify({

        "success": True,

        "service":
            "SmartAgri Kopargaon",

        "status":
            "online",

        "timezone":
            "Asia/Kolkata",

        "today":
            today_india(),

        "database":
            DATABASE,

        "government_api_configured":
            bool(
                DATA_GOV_API_KEY
            ),

        "latest": {

            "onion": onion,

            "wheat": wheat

        }

    })


# ============================================================
# HEALTH CHECK
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
            "SmartAgri Kopargaon",

        "date":
            today_india()

    })


# ============================================================
# HOME
# ============================================================

@app.route(
    "/",
    methods=["GET"]
)
def home():

    return jsonify({

        "name":
            "SmartAgri Kopargaon",

        "status":
            "running",

        "message":
            "SmartAgri market intelligence backend is running.",

        "endpoints": [

            "/api/market?crop=onion",

            "/api/market?crop=wheat",

            "/api/market/history?crop=onion",

            "/api/market/history?crop=wheat",

            "/api/status",

            "/health"

        ]

    })


# ============================================================
# STARTUP
# ============================================================

initialize_database()


if __name__ == "__main__":

    print(
        "=========================================="
    )

    print(
        " SmartAgri Kopargaon Backend"
    )

    print(
        "=========================================="
    )

    print(
        f"Database: {DATABASE}"
    )

    print(
        "Timezone: Asia/Kolkata"
    )

    print(
        "Market API:"
    )

    print(
        "  /api/market?crop=onion"
    )

    print(
        "  /api/market?crop=wheat"
    )

    print(
        "History API:"
    )

    print(
        "  /api/market/history?crop=onion"
    )

    print(
        "  /api/market/history?crop=wheat"
    )

    print(
        "Government API configured:",
        bool(DATA_GOV_API_KEY)
    )

    print(
        "=========================================="
    )

    app.run(
        host="0.0.0.0",
        port=PORT,
        debug=False
    )
