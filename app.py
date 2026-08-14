import os
import re
import sqlite3
from datetime import datetime, timezone

import requests

from bs4 import BeautifulSoup

from flask import (
    Flask,
    jsonify,
    request,
    send_from_directory
)

from flask_cors import CORS


# ============================================================
# SMARTAGRI KOPARGAON
# FULL FLASK APPLICATION
#
# This single application serves:
#
# /
# /style.css
# /script.js
#
# AND:
#
# /api/market
# /api/market/history
# /api/status
# /health
# ============================================================


app = Flask(
    __name__,
    static_folder=".",
    static_url_path=""
)

CORS(app)


# ============================================================
# CONFIGURATION
# ============================================================

PORT = int(
    os.environ.get(
        "PORT",
        5000
    )
)


DATABASE = os.environ.get(
    "SMARTAGRI_DATABASE",
    "smartagri.db"
)


# ============================================================
# MARKET SOURCE
#
# MandiPulse pages are used as the external market source.
#
# The site states that its market data is compiled from
# Agmarknet / Government market data.
# ============================================================

BASE_URL = (
    "https://mandipulse.com/"
    "mandi/maharashtra-ahilyanagar-kopargaon-apmc"
)


CROP_URLS = {

    "onion":
        f"{BASE_URL}/onion",

    "wheat":
        f"{BASE_URL}/wheat"

}


HEADERS = {

    "User-Agent":
        (
            "Mozilla/5.0 "
            "(Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/151.0.0.0 "
            "Safari/537.36"
        ),

    "Accept":
        (
            "text/html,"
            "application/xhtml+xml,"
            "application/xml;q=0.9,"
            "*/*;q=0.8"
        ),

    "Accept-Language":
        "en-US,en;q=0.9"

}


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
        ]

    },

    "wheat": {

        "names": [
            "wheat",
            "Wheat",
            "WHEAT",
            "Gehun",
            "गेहूं",
            "गहू"
        ]

    }

}


# ============================================================
# DATABASE
# ============================================================

def get_db():

    connection = sqlite3.connect(
        DATABASE
    )

    connection.row_factory = (
        sqlite3.Row
    )

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
# DATABASE READ
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
# NUMBER PARSER
# ============================================================

def extract_number(text):

    if text is None:
        return None

    text = str(text)

    text = text.replace(
        ",",
        ""
    )

    match = re.search(
        r"₹?\s*(\d+(?:\.\d+)?)",
        text
    )

    if not match:

        return None

    value = float(
        match.group(1)
    )

    if value.is_integer():

        return int(value)

    return value


# ============================================================
# DATE NORMALIZATION
# ============================================================

def normalize_date(value):

    if not value:

        return datetime.now(
            timezone.utc
        ).strftime(
            "%Y-%m-%d"
        )

    text = str(value).strip()

    formats = [

        "%d/%m/%Y",
        "%d-%m-%Y",
        "%Y-%m-%d",
        "%d/%m/%y",
        "%d-%m-%y",
        "%Y/%m/%d",

        "%d %b %Y",
        "%d %B %Y"

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

            continue

    return datetime.now(
        timezone.utc
    ).strftime(
        "%Y-%m-%d"
    )


# ============================================================
# FETCH MARKET PAGE
# ============================================================

def fetch_market_page(crop):

    if crop not in CROP_URLS:

        raise ValueError(
            "Unsupported crop. "
            "Use onion or wheat."
        )

    url = CROP_URLS[crop]

    print(
        "=========================================="
    )

    print(
        "SMARTAGRI MARKET REQUEST"
    )

    print(
        f"Crop: {crop}"
    )

    print(
        f"Source: {url}"
    )

    print(
        "=========================================="
    )

    response = requests.get(
        url,
        headers=HEADERS,
        timeout=20
    )

    response.raise_for_status()

    return (
        response.text,
        url
    )


# ============================================================
# PARSE MARKET PAGE
# ============================================================

def parse_market_page(
    html,
    crop,
    source_url
):

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    text = soup.get_text(
        " ",
        strip=True
    )


    # --------------------------------------------------------
    # DATE
    # --------------------------------------------------------

    date_match = re.search(
        r"Updated on:\s*"
        r"([0-9]{1,2}\s+[A-Za-z]{3,9}\s+[0-9]{4})",
        text,
        re.IGNORECASE
    )

    if date_match:

        data_date = normalize_date(
            date_match.group(1)
        )

    else:

        data_date = (
            datetime.now(
                timezone.utc
            ).strftime(
                "%Y-%m-%d"
            )
        )


    # --------------------------------------------------------
    # MIN / MAX
    # --------------------------------------------------------

    min_price = None
    max_price = None

    range_match = re.search(
        r"Min:\s*₹?\s*([\d,]+)"
        r"\s*\|\s*Max:\s*₹?\s*([\d,]+)",
        text,
        re.IGNORECASE
    )

    if range_match:

        min_price = extract_number(
            range_match.group(1)
        )

        max_price = extract_number(
            range_match.group(2)
        )


    # --------------------------------------------------------
    # MODAL PRICE
    # --------------------------------------------------------

    modal_price = None

    modal_patterns = [

        r"Modal:\s*₹?\s*([\d,]+)",

        r"Modal Price:\s*₹?\s*([\d,]+)",

        r"Modal Price\s*₹?\s*([\d,]+)",

        r"modal_price\s*[:\-]\s*₹?\s*([\d,]+)"

    ]


    for pattern in modal_patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:

            modal_price = extract_number(
                match.group(1)
            )

            break


    # --------------------------------------------------------
    # FALLBACK PRICE EXTRACTION
    # --------------------------------------------------------
    #
    # If modal price is not explicitly labeled,
    # use a reasonable candidate from visible market text.
    #
    # We DO NOT invent a hardcoded price.
    # --------------------------------------------------------

    if modal_price is None:

        candidate_patterns = [

            r"₹\s*([\d,]+)",

            r"Rs\.?\s*([\d,]+)"

        ]

        candidates = []

        for pattern in candidate_patterns:

            for match in re.finditer(
                pattern,
                text,
                re.IGNORECASE
            ):

                value = extract_number(
                    match.group(1)
                )

                if value is not None:

                    candidates.append(
                        value
                    )


        if candidates:

            filtered = [

                value

                for value in candidates

                if 100 <= value <= 20000

            ]

            if filtered:

                modal_price = (
                    filtered[0]
                )


    if modal_price is None:

        raise RuntimeError(
            "Could not find a usable "
            "market price on the source page."
        )


    # --------------------------------------------------------
    # MARKET
    # --------------------------------------------------------

    market = (
        "Kopargaon APMC"
    )


    return {

        "crop":
            crop,

        "market":
            market,

        "price":
            modal_price,

        "min_price":
            min_price,

        "max_price":
            max_price,

        "modal_price":
            modal_price,

        "data_date":
            data_date,

        "source":
            "MandiPulse / Agmarknet",

        "source_url":
            source_url

    }


# ============================================================
# FETCH + PARSE
# ============================================================

def fetch_live_market_data(crop):

    html, source_url = (
        fetch_market_page(
            crop
        )
    )

    return parse_market_page(
        html,
        crop,
        source_url
    )


# ============================================================
# GET MARKET DATA
# ============================================================

def get_market_data(crop):

    crop = crop.lower().strip()

    if crop not in CROPS:

        return None, (
            "Unsupported crop. "
            "Use onion or wheat."
        )


    # --------------------------------------------------------
    # 1. LIVE SOURCE
    # --------------------------------------------------------

    try:

        live_data = (
            fetch_live_market_data(
                crop
            )
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

                "data_status":
                    "live",

                "message":
                    "Latest available market data fetched successfully."

            }, None


    except Exception as exc:

        print(
            "LIVE MARKET SOURCE ERROR:",
            repr(exc)
        )


    # --------------------------------------------------------
    # 2. HISTORICAL FALLBACK
    # --------------------------------------------------------

    latest = get_latest_price(
        crop
    )


    if latest:

        return {

            "crop":
                crop,

            "market":
                latest[
                    "market"
                ],

            "price":
                latest[
                    "price"
                ],

            "min_price":
                latest[
                    "min_price"
                ],

            "max_price":
                latest[
                    "max_price"
                ],

            "modal_price":
                latest[
                    "modal_price"
                ],

            "data_date":
                latest[
                    "data_date"
                ],

            "source":
                latest[
                    "source"
                ],

            "data_status":
                "historical_fallback",

            "message":
                (
                    "Live market source was unavailable. "
                    "Showing the latest successfully recorded "
                    "market price."
                )

        }, None


    # --------------------------------------------------------
    # 3. NO DATA
    # --------------------------------------------------------

    return None, (
        "No market data is currently available. "
        "The live market source could not be reached "
        "and there is no previously recorded price."
    )


# ============================================================
# TREND
# ============================================================

def calculate_trend(
    crop,
    current_price
):

    history = get_price_history(
        crop,
        10
    )


    if len(history) < 2:

        return {

            "trend":
                "Stable",

            "change":
                0,

            "change_percent":
                0

        }


    previous_price = float(
        history[1]["price"]
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
        current_price -
        previous_price
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


    if len(history) < 2:

        return {

            "forecast_price":
                round(
                    current_price
                ),

            "forecast_change_percent":
                0,

            "message":
                "Not enough historical data for a strong forecast."

        }


    prices = [

        float(row["price"])

        for row in history

        if row["price"] is not None

    ]


    if not prices:

        return {

            "forecast_price":
                round(
                    current_price
                ),

            "forecast_change_percent":
                0,

            "message":
                "Not enough historical data for a strong forecast."

        }


    average = (
        sum(prices) /
        len(prices)
    )


    previous = (

        prices[1]

        if len(prices) > 1

        else current_price

    )


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


    change_percent = (

        (
            forecast -
            current_price
        )
        /
        current_price

    ) * 100


    if change_percent > 3:

        message = (
            "Prices may increase based on "
            "recent recorded market movement."
        )

    elif change_percent < -3:

        message = (
            "Prices may weaken based on "
            "recent recorded market movement."
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
# DECISION ENGINE
# ============================================================

def calculate_decision(
    current_price,
    forecast_price,
    trend
):

    sell_now = (
        current_price
    )


    store_value = (
        forecast_price
    )


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
            "current recorded price. Storing "
            "may provide a better return if "
            "storage costs and crop quality "
            "are manageable."
        )


    elif (
        current_price >=
        forecast_price * 0.98
    ):

        action = "Sell Now"

        reason = (
            "The current market price is "
            "strong relative to the expected "
            "future price. Selling now may "
            "reduce price risk."
        )


    elif trend == "Increasing":

        action = "Store"

        reason = (
            "The recent recorded market trend "
            "is increasing. Holding the crop "
            "may provide an opportunity for "
            "a better price."
        )


    else:

        action = "Sell Now"

        reason = (
            "The expected price improvement "
            "is not large enough to clearly "
            "justify waiting."
        )


    return {

        "sell_now":
            round(
                sell_now
            ),

        "store":
            round(
                store_value
            ),

        "transport":
            round(
                transport_value
            ),

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
                    error or
                    "Market data unavailable"

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


        demand = (
            calculate_demand(
                trend_data["trend"]
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
                "Market service temporarily unavailable.",

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


    history = (
        get_price_history(
            crop,
            limit
        )
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

    onion = (
        get_latest_price(
            "onion"
        )
    )


    wheat = (
        get_latest_price(
            "wheat"
        )
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

        "source":
            "MandiPulse / Agmarknet",

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
#
# Flask now serves the frontend.
# ============================================================

@app.route(
    "/",
    methods=["GET"]
)
def home():

    return send_from_directory(
        ".",
        "index.html"
    )


@app.route(
    "/index.html",
    methods=["GET"]
)
def index_html():

    return send_from_directory(
        ".",
        "index.html"
    )


@app.route(
    "/style.css",
    methods=["GET"]
)
def style_css():

    return send_from_directory(
        ".",
        "style.css"
    )


@app.route(
    "/script.js",
    methods=["GET"]
)
def script_js():

    return send_from_directory(
        ".",
        "script.js"
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
        " Full-stack Flask application"
    )

    print(
        "=========================================="
    )

    print(
        f"Database: {DATABASE}"
    )

    print(
        "Frontend: /"
    )

    print(
        "Market API: /api/market?crop=onion"
    )

    print(
        "History API: /api/market/history?crop=onion"
    )

    print(
        "Health: /health"
    )

    print(
        "=========================================="
    )


    app.run(
        host="0.0.0.0",
        port=PORT,
        debug=False
    )
