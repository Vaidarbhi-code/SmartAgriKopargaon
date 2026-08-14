import os
import sqlite3
from datetime import datetime, timezone

import requests
from flask import Flask, jsonify, request, render_template
from flask_cors import CORS


# ============================================================
# SMARTAGRI KOPARGAON
# COMPLETE FLASK BACKEND
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
            "कांदा"
        ],
        "default_price": 2200
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
        "default_price": 2600
    }
}


# ============================================================
# FALLBACK BASELINE
# ============================================================

FALLBACK_PRICES = {
    "onion": 2200,
    "wheat": 2600
}


# ============================================================
# DATABASE
# ============================================================

def get_db():
    connection = sqlite3.connect(DATABASE)
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

        ON market_prices(crop, data_date)
        """
    )

    connection.commit()
    connection.close()


# ============================================================
# DATABASE SAVE
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
        ORDER BY data_date DESC, id DESC
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

def get_price_history(crop, limit=30):

    connection = get_db()
    cursor = connection.cursor()

    rows = cursor.execute(
        """
        SELECT *
        FROM market_prices
        WHERE crop = ?
        ORDER BY data_date DESC, id DESC
        LIMIT ?
        """,
        (crop, limit)
    ).fetchall()

    connection.close()

    return [dict(row) for row in rows]


# ============================================================
# PREVIOUS PRICE
# ============================================================

def get_previous_price(crop):

    history = get_price_history(
        crop,
        10
    )

    if len(history) < 2:
        return None

    return history[1]


# ============================================================
# PRICE PARSER
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
            continue

    return datetime.now(
        timezone.utc
    ).strftime("%Y-%m-%d")


# ============================================================
# CROP MATCHING
# ============================================================

def crop_matches(
    record_crop,
    requested_crop
):

    if not record_crop:
        return False

    record_crop = str(
        record_crop
    ).strip().lower()

    requested_crop = (
        requested_crop
        .strip()
        .lower()
    )

    if requested_crop not in CROPS:
        return False

    for name in CROPS[
        requested_crop
    ]["names"]:

        if record_crop == str(
            name
        ).strip().lower():

            return True

    return requested_crop in record_crop


# ============================================================
# GOVERNMENT RECORD PARSER
# ============================================================

def parse_government_record(
    record,
    crop
):

    modal_price = parse_price(
        record.get("modal_price")
        or record.get("Modal_Price")
        or record.get("modal")
        or record.get("Modal Price")
    )

    min_price = parse_price(
        record.get("min_price")
        or record.get("Min_Price")
        or record.get("minimum_price")
    )

    max_price = parse_price(
        record.get("max_price")
        or record.get("Max_Price")
        or record.get("maximum_price")
    )

    if modal_price is None:

        modal_price = parse_price(
            record.get(
                "price_per_quintal"
            )
            or record.get("Price")
            or record.get("price")
        )

    if modal_price is None:
        return None

    data_date = normalize_date(
        record.get("arrival_date")
        or record.get("Arrival_Date")
        or record.get("date")
        or record.get("Date")
        or record.get("price_date")
    )

    market = (
        record.get("market")
        or record.get("Market")
        or record.get("market_name")
        or "Kopargaon"
    )

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
            "Government API key is not configured"
        )

    params = {

        "api-key":
            DATA_GOV_API_KEY,

        "format":
            "json",

        "limit":
            1000

    }

    response = requests.get(
        DATA_GOV_URL,
        params=params,
        timeout=15
    )

    response.raise_for_status()

    payload = response.json()

    records = payload.get(
        "records",
        []
    )

    if not records:

        return None, (
            "No records returned by government API"
        )

    # --------------------------------------------------------
    # Search Kopargaon + crop
    # --------------------------------------------------------

    for record in records:

        crop_value = (
            record.get("commodity")
            or record.get("Commodity")
            or record.get("crop")
            or record.get("Crop")
            or record.get("commodity_name")
            or ""
        )

        if not crop_matches(
            crop_value,
            crop
        ):
            continue

        record_text = (
            str(record)
            .lower()
        )

        if "kopargaon" not in record_text:
            continue

        parsed = parse_government_record(
            record,
            crop
        )

        if parsed:
            return parsed, None

    return None, (
        f"No Kopargaon record found for {crop}"
    )


# ============================================================
# SECONDARY SOURCE
# ============================================================

def fetch_secondary_source(crop):

    # Reserved for a verified secondary
    # market source later.

    return None


# ============================================================
# MARKET DATA
# ============================================================

def get_market_data(crop):

    crop = (
        crop
        .lower()
        .strip()
    )

    if crop not in CROPS:

        return None, (
            "Unsupported crop"
        )

    # --------------------------------------------------------
    # 1. GOVERNMENT LIVE DATA
    # --------------------------------------------------------

    try:

        live_data, error = (
            fetch_from_data_gov(
                crop
            )
        )

        if live_data:

            save_market_price(

                crop,

                live_data["market"],

                live_data["price"],

                live_data["source"],

                live_data["data_date"],

                live_data.get(
                    "min_price"
                ),

                live_data.get(
                    "max_price"
                ),

                live_data.get(
                    "modal_price"
                )
            )

            return {

                **live_data,

                "data_status":
                    "live",

                "message":
                    "Latest market price fetched successfully."

            }, None

    except Exception as exc:

        print(
            "Government API error:",
            repr(exc)
        )

    # --------------------------------------------------------
    # 2. SECONDARY SOURCE
    # --------------------------------------------------------

    try:

        secondary_data = (
            fetch_secondary_source(
                crop
            )
        )

        if secondary_data:

            save_market_price(

                crop,

                secondary_data["market"],

                secondary_data["price"],

                secondary_data["source"],

                secondary_data["data_date"],

                secondary_data.get(
                    "min_price"
                ),

                secondary_data.get(
                    "max_price"
                ),

                secondary_data.get(
                    "modal_price"
                )
            )

            return {

                **secondary_data,

                "data_status":
                    "live",

                "message":
                    "Latest market price fetched successfully."

            }, None

    except Exception as exc:

        print(
            "Secondary API error:",
            repr(exc)
        )

    # --------------------------------------------------------
    # 3. DATABASE FALLBACK
    # --------------------------------------------------------

    latest = get_latest_price(
        crop
    )

    if latest:

        return {

            "crop":
                crop,

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
                "Showing the latest recorded market price."

        }, None

    # --------------------------------------------------------
    # 4. BASELINE
    # --------------------------------------------------------

    baseline_price = (
        FALLBACK_PRICES[crop]
    )

    today = datetime.now(
        timezone.utc
    ).strftime("%Y-%m-%d")

    save_market_price(

        crop,

        "Kopargaon",

        baseline_price,

        "SmartAgri baseline",

        today,

        None,

        None,

        baseline_price
    )

    return {

        "crop":
            crop,

        "market":
            "Kopargaon",

        "price":
            baseline_price,

        "min_price":
            None,

        "max_price":
            None,

        "modal_price":
            baseline_price,

        "data_date":
            today,

        "source":
            "SmartAgri baseline",

        "data_status":
            "baseline",

        "message":
            "Latest available SmartAgri market baseline."

    }, None


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

            "trend":
                "Stable",

            "change":
                0,

            "change_percent":
                0

        }

    previous_price = float(
        previous["price"]
    )

    if previous_price <= 0:

        return {

            "trend":
                "Stable",

            "change":
                0,

            "change_percent":
                0

        }

    change = (
        current_price
        - previous_price
    )

    change_percent = (
        change /
        previous_price
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
        if row["price"] is not None
    ]

    if len(prices) < 2:

        forecast = current_price

    else:

        average = (
            sum(prices) /
            len(prices)
        )

        previous = prices[1]

        movement = (
            current_price -
            previous
        )

        forecast = (
            average +
            movement * 0.5
        )

    minimum = (
        current_price * 0.75
    )

    maximum = (
        current_price * 1.35
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

    forecast_change = (
        (
            forecast -
            current_price
        )
        /
        current_price
    ) * 100

    if forecast_change > 3:

        message = (
            "Prices may increase based "
            "on recent market movement."
        )

    elif forecast_change < -3:

        message = (
            "Prices may weaken based "
            "on recent market movement."
        )

    else:

        message = (
            "Prices are expected to remain "
            "relatively stable."
        )

    return {

        "forecast_price":
            forecast,

        "forecast_change_percent":
            round(
                forecast_change,
                2
            ),

        "message":
            message

    }


# ============================================================
# DEMAND
# ============================================================

def calculate_demand(trend):

    if trend == "Increasing":
        return "High"

    if trend == "Decreasing":
        return "Moderate"

    return "Stable"


# ============================================================
# DECISION ENGINE
# ============================================================

def calculate_decision(
    current_price,
    forecast_price,
    trend
):

    sell_value = current_price

    store_value = forecast_price

    transport_value = (
        current_price * 0.95
    )

    if (
        forecast_price >
        current_price * 1.08
    ):

        action = "Store"

        reason = (
            "The expected future price is "
            "significantly higher than the "
            "current price. Storing may provide "
            "a better return if storage costs "
            "and crop quality are manageable."
        )

    elif (
        current_price >=
        forecast_price * 0.98
    ):

        action = "Sell Now"

        reason = (
            "The current market price is strong "
            "relative to the expected future price. "
            "Selling now may reduce price risk."
        )

    elif trend == "Increasing":

        action = "Store"

        reason = (
            "The recent market trend is increasing. "
            "Holding the crop may provide an "
            "opportunity for a better price."
        )

    else:

        action = "Sell Now"

        reason = (
            "The expected price improvement is "
            "not large enough to clearly justify "
            "waiting."
        )

    return {

        "sell_now":
            round(sell_value),

        "store":
            round(store_value),

        "transport":
            round(transport_value),

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

        market_data, error = (
            get_market_data(
                crop
            )
        )

        if not market_data:

            return jsonify({

                "success":
                    False,

                "error":
                    error

            }), 200

        current_price = float(
            market_data["price"]
        )

        trend_data = (
            calculate_trend(
                crop,
                current_price
            )
        )

        forecast_data = (
            calculate_forecast(
                crop,
                current_price
            )
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

        return jsonify({

            "success":
                True,

            "crop":
                crop,

            "market":
                market_data["market"],

            "current_price":
                round(current_price),

            "price":
                round(current_price),

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
                market_data["data_date"],

            "data_date":
                market_data["data_date"],

            "source":
                market_data["source"],

            "data_status":
                market_data["data_status"],

            "message":
                market_data["message"],

            "trend":
                trend_data["trend"],

            "price_change":
                trend_data["change"],

            "change_percent":
                trend_data["change_percent"],

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
                decision["sell_now"],

            "store":
                decision["store"],

            "transport":
                decision["transport"],

            "best_action":
                decision["best_action"],

            "recommendation":
                decision["best_action"],

            "recommendation_reason":
                decision["reason"]

        })

    except Exception as exc:

        print(
            "MARKET API ERROR:",
            repr(exc)
        )

        latest = get_latest_price(
            crop
        )

        if latest:

            current_price = float(
                latest["price"]
            )

            trend_data = (
                calculate_trend(
                    crop,
                    current_price
                )
            )

            forecast_data = (
                calculate_forecast(
                    crop,
                    current_price
                )
            )

            decision = (
                calculate_decision(

                    current_price,

                    forecast_data[
                        "forecast_price"
                    ],

                    trend_data[
                        "trend"
                    ]
                )
            )

            return jsonify({

                "success":
                    True,

                "crop":
                    crop,

                "market":
                    latest["market"],

                "current_price":
                    round(current_price),

                "price":
                    round(current_price),

                "min_price":
                    latest["min_price"],

                "max_price":
                    latest["max_price"],

                "modal_price":
                    latest["modal_price"],

                "latest_date":
                    latest["data_date"],

                "data_date":
                    latest["data_date"],

                "source":
                    latest["source"],

                "data_status":
                    "historical_fallback",

                "message":
                    "Showing the latest recorded market price.",

                "trend":
                    trend_data["trend"],

                "price_change":
                    trend_data["change"],

                "change_percent":
                    trend_data[
                        "change_percent"
                    ],

                "demand":
                    calculate_demand(
                        trend_data["trend"]
                    ),

                "forecast_price":
                    forecast_data[
                        "forecast_price"
                    ],

                "forecast_change_percent":
                    forecast_data[
                        "forecast_change_percent"
                    ],

                "forecast_message":
                    forecast_data["message"],

                "sell_now":
                    decision["sell_now"],

                "store":
                    decision["store"],

                "transport":
                    decision["transport"],

                "best_action":
                    decision["best_action"],

                "recommendation":
                    decision["best_action"],

                "recommendation_reason":
                    decision["reason"]

            })

        return jsonify({

            "success":
                False,

            "error":
                "Market service temporarily unavailable"

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

    onion = get_latest_price(
        "onion"
    )

    wheat = get_latest_price(
        "wheat"
    )

    return jsonify({

        "success":
            True,

        "service":
            "SmartAgri Kopargaon",

        "status":
            "online",

        "database":
            DATABASE,

        "government_api_configured":
            bool(
                DATA_GOV_API_KEY
            ),

        "latest":
            {

                "onion":
                    onion,

                "wheat":
                    wheat

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
def home():

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
        "=========================================="
    )

    print(
        f"Database: {DATABASE}"
    )

    print(
        f"Government API configured: "
        f"{bool(DATA_GOV_API_KEY)}"
    )

    app.run(
        host="0.0.0.0",
        port=PORT,
        debug=False
    )
