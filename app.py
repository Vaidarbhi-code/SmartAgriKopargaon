import os
import csv
import io
from datetime import datetime, timezone

import requests
from flask import Flask, jsonify, request, Response
from flask_cors import CORS
from pymongo import MongoClient, DESCENDING
from pymongo.errors import PyMongoError


# ============================================================
# SMARTAGRI KOPARGAON
# MONGODB + CSV MARKET INTELLIGENCE BACKEND
# ============================================================

app = Flask(__name__)
CORS(app)


# ============================================================
# CONFIGURATION
# ============================================================

PORT = int(os.environ.get("PORT", 5000))

MONGODB_URI = os.environ.get("MONGODB_URI", "")
MONGODB_DATABASE = os.environ.get(
    "MONGODB_DATABASE",
    "SmartAgriKopargaon"
)

# Government data.gov.in API key
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
# MONGODB
# ============================================================

mongo_client = None
mongo_db = None
market_collection = None


def initialize_mongodb():

    global mongo_client
    global mongo_db
    global market_collection

    if not MONGODB_URI:
        print("WARNING: MONGODB_URI is not configured.")
        return False

    try:

        mongo_client = MongoClient(
            MONGODB_URI,
            serverSelectionTimeoutMS=10000
        )

        # Force connection test.
        mongo_client.admin.command("ping")

        mongo_db = mongo_client[MONGODB_DATABASE]

        market_collection = mongo_db["market_prices"]

        # Useful indexes for historical queries.
        market_collection.create_index(
            [
                ("crop", 1),
                ("data_date", -1)
            ]
        )

        market_collection.create_index(
            [
                ("crop", 1),
                ("market", 1),
                ("data_date", -1)
            ]
        )

        print(
            "MongoDB connected successfully."
        )

        print(
            f"MongoDB database: {MONGODB_DATABASE}"
        )

        return True

    except Exception as exc:

        print(
            "MongoDB connection failed:",
            repr(exc)
        )

        mongo_client = None
        mongo_db = None
        market_collection = None

        return False


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
# BASELINE FALLBACK
# ============================================================

FALLBACK_PRICES = {

    "onion": 2200,

    "wheat": 2600
}


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

    record_crop = (
        str(record_crop)
        .strip()
        .lower()
    )

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

        if record_crop == (
            str(name)
            .strip()
            .lower()
        ):

            return True

    return requested_crop in record_crop


# ============================================================
# SAVE MARKET DATA TO MONGODB
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

    if market_collection is None:

        return False

    try:

        now = datetime.now(
            timezone.utc
        )

        document = {

            "crop": crop,

            "market": market,

            "price": float(price),

            "min_price": (
                float(min_price)
                if min_price is not None
                else None
            ),

            "max_price": (
                float(max_price)
                if max_price is not None
                else None
            ),

            "modal_price": (
                float(modal_price)
                if modal_price is not None
                else None
            ),

            "source": source,

            "data_date": data_date,

            "fetched_at": now,

            "created_at": now

        }

        # Do not repeatedly create identical records
        # for the same crop/market/date/price/source.
        existing = market_collection.find_one({

            "crop": crop,

            "market": market,

            "data_date": data_date,

            "price": float(price),

            "source": source

        })

        if existing:

            return True

        market_collection.insert_one(
            document
        )

        return True

    except PyMongoError as exc:

        print(
            "MongoDB save error:",
            repr(exc)
        )

        return False


# ============================================================
# GET LATEST MARKET DATA
# ============================================================

def get_latest_price(crop):

    if market_collection is None:
        return None

    try:

        document = market_collection.find_one(
            {
                "crop": crop
            },
            sort=[
                ("data_date", DESCENDING),
                ("created_at", DESCENDING)
            ]
        )

        if document is None:
            return None

        document.pop(
            "_id",
            None
        )

        return document

    except PyMongoError as exc:

        print(
            "MongoDB latest-data error:",
            repr(exc)
        )

        return None


# ============================================================
# GET HISTORICAL DATA
# ============================================================

def get_price_history(
    crop,
    limit=30
):

    if market_collection is None:
        return []

    try:

        cursor = (
            market_collection
            .find(
                {
                    "crop": crop
                }
            )
            .sort(
                [
                    ("data_date", DESCENDING),
                    ("created_at", DESCENDING)
                ]
            )
            .limit(limit)
        )

        history = []

        for document in cursor:

            document.pop(
                "_id",
                None
            )

            # Convert MongoDB datetime values
            # into JSON-friendly strings.
            for key in [
                "fetched_at",
                "created_at"
            ]:

                if isinstance(
                    document.get(key),
                    datetime
                ):

                    document[key] = (
                        document[key]
                        .isoformat()
                    )

            history.append(
                document
            )

        return history

    except PyMongoError as exc:

        print(
            "MongoDB history error:",
            repr(exc)
        )

        return []


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

            or record.get(
                "Price"
            )

            or record.get(
                "price"
            )
        )

    if modal_price is None:
        return None

    data_date = normalize_date(

        record.get(
            "arrival_date"
        )

        or record.get(
            "Arrival_Date"
        )

        or record.get(
            "date"
        )

        or record.get(
            "Date"
        )

        or record.get(
            "price_date"
        )
    )

    market = (

        record.get(
            "market"
        )

        or record.get(
            "Market"
        )

        or record.get(
            "market_name"
        )

        or "Kopargaon"
    )

    return {

        "crop": crop,

        "market": str(
            market
        ),

        "price": modal_price,

        "min_price": min_price,

        "max_price": max_price,

        "modal_price": modal_price,

        "data_date": data_date,

        "source":
            "data.gov.in / Agmarknet"

    }


# ============================================================
# DATA.GOV.IN FETCH
# ============================================================

def fetch_from_data_gov(crop):

    if not DATA_GOV_API_KEY:

        return None, (
            "DATA_GOV_API_KEY is not configured"
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
            "No records returned by government API"
        )

    # --------------------------------------------------------
    # Find exact Kopargaon + crop records.
    # --------------------------------------------------------

    matches = []

    for record in records:

        crop_value = (

            record.get(
                "commodity"
            )

            or record.get(
                "Commodity"
            )

            or record.get(
                "crop"
            )

            or record.get(
                "Crop"
            )

            or record.get(
                "commodity_name"
            )

            or ""
        )

        if not crop_matches(
            crop_value,
            crop
        ):

            continue

        market_value = (

            record.get(
                "market"
            )

            or record.get(
                "Market"
            )

            or record.get(
                "market_name"
            )

            or ""
        )

        district_value = (

            record.get(
                "district"
            )

            or record.get(
                "District"
            )

            or ""
        )

        combined = (

            f"{market_value} "
            f"{district_value}"
        ).lower()

        if "kopargaon" in combined:

            parsed = parse_government_record(
                record,
                crop
            )

            if parsed:

                matches.append(
                    parsed
                )

    if matches:

        # Prefer the newest date.
        matches.sort(
            key=lambda item:
                item["data_date"],
            reverse=True
        )

        return matches[0], None

    return None, (
        f"No Kopargaon record found for {crop}"
    )


# ============================================================
# SECONDARY SOURCE
# ============================================================

def fetch_secondary_source(crop):

    # Reserved for another verified market source.
    #
    # We deliberately do not invent a market source.
    #
    # This function can later be connected to another
    # verified API.

    return None


# ============================================================
# MARKET DATA PIPELINE
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
    # 1. Government API
    # --------------------------------------------------------

    try:

        live_data, error = (
            fetch_from_data_gov(
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
                    "Latest market price fetched successfully."

            }, None

    except Exception as exc:

        print(
            "Government API error:",
            repr(exc)
        )

    # --------------------------------------------------------
    # 2. Secondary API
    # --------------------------------------------------------

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

                "data_status":
                    "live",

                "message":
                    "Latest market price fetched successfully."

            }, None

    except Exception as exc:

        print(
            "Secondary source error:",
            repr(exc)
        )

    # --------------------------------------------------------
    # 3. MongoDB historical fallback
    # --------------------------------------------------------

    latest = get_latest_price(
        crop
    )

    if latest:

        return {

            "crop":
                crop,

            "market":
                latest.get(
                    "market",
                    "Kopargaon"
                ),

            "price":
                latest.get(
                    "price"
                ),

            "min_price":
                latest.get(
                    "min_price"
                ),

            "max_price":
                latest.get(
                    "max_price"
                ),

            "modal_price":
                latest.get(
                    "modal_price"
                ),

            "data_date":
                latest.get(
                    "data_date"
                ),

            "source":
                latest.get(
                    "source"
                ),

            "data_status":
                "historical_fallback",

            "message":
                "Live market service was temporarily unavailable. Showing the latest recorded market price."

        }, None

    # --------------------------------------------------------
    # 4. Initial baseline
    # --------------------------------------------------------

    baseline_price = FALLBACK_PRICES[
        crop
    ]

    today = datetime.now(
        timezone.utc
    ).strftime(
        "%Y-%m-%d"
    )

    save_market_price(

        crop=crop,

        market="Kopargaon",

        price=baseline_price,

        source="SmartAgri baseline",

        data_date=today,

        modal_price=baseline_price
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

    if len(history) < 2:

        forecast = current_price

    else:

        prices = [

            float(
                row["price"]
            )

            for row in history

            if row.get(
                "price"
            ) is not None

        ]

        if not prices:

            forecast = current_price

        else:

            average = (
                sum(prices)
                / len(prices)
            )

            previous = (

                prices[1]

                if len(prices) > 1

                else current_price

            )

            movement = (
                current_price
                - previous
            )

            forecast = (
                average
                + (
                    movement
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

    if forecast > (
        current_price
        * 1.03
    ):

        message = (
            "Prices may increase based on recent market movement."
        )

    elif forecast < (
        current_price
        * 0.97
    ):

        message = (
            "Prices may weaken based on recent market movement."
        )

    else:

        message = (
            "Prices are expected to remain relatively stable."
        )

    forecast_change = (

        (
            forecast
            - current_price
        )
        / current_price
    ) * 100

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

    transport_cost = (
        current_price
        * 0.05
    )

    transport_value = (
        current_price
        - transport_cost
    )

    if forecast_price > (
        current_price
        * 1.08
    ):

        action = "Store"

        reason = (
            "The expected future price is significantly higher than today's recorded price. Storing may provide a better return if storage costs and crop quality are manageable."
        )

    elif current_price >= (
        forecast_price
        * 0.98
    ):

        action = "Sell Now"

        reason = (
            "The current market price is strong relative to the expected future price. Selling now may reduce price risk."
        )

    elif trend == "Increasing":

        action = "Store"

        reason = (
            "The recent market trend is increasing. Holding the crop may provide an opportunity for a better price."
        )

    else:

        action = "Sell Now"

        reason = (
            "The expected price improvement is not large enough to clearly justify waiting."
        )

    return {

        "sell_now":
            round(
                sell_value
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
# CSV IMPORT
# ============================================================

def import_csv_data(
    csv_content
):

    if market_collection is None:

        return {

            "success":
                False,

            "error":
                "MongoDB is not connected."

        }

    reader = csv.DictReader(
        io.StringIO(
            csv_content
        )
    )

    imported = 0
    skipped = 0

    for row in reader:

        crop_value = (

            row.get("crop")
            or row.get("Crop")
            or row.get("commodity")
            or row.get("Commodity")
            or ""
        ).strip().lower()

        if crop_value not in CROPS:

            skipped += 1
            continue

        market = (

            row.get("market")
            or row.get("Market")
            or "Kopargaon"
        ).strip()

        price = parse_price(

            row.get("price")
            or row.get("Price")
            or row.get("modal_price")
            or row.get("Modal_Price")
        )

        if price is None:

            skipped += 1
            continue

        min_price = parse_price(
            row.get("min_price")
            or row.get("Min_Price")
        )

        max_price = parse_price(
            row.get("max_price")
            or row.get("Max_Price")
        )

        modal_price = parse_price(
            row.get("modal_price")
            or row.get("Modal_Price")
        )

        data_date = normalize_date(

            row.get("data_date")
            or row.get("date")
            or row.get("Date")
        )

        source = (

            row.get("source")
            or "CSV import"
        )

        saved = save_market_price(

            crop=crop_value,

            market=market,

            price=price,

            source=source,

            data_date=data_date,

            min_price=min_price,

            max_price=max_price,

            modal_price=modal_price
        )

        if saved:

            imported += 1

        else:

            skipped += 1

    return {

        "success":
            True,

        "imported":
            imported,

        "skipped":
            skipped

    }


# ============================================================
# CSV IMPORT API
# ============================================================

@app.route(
    "/api/market/import-csv",
    methods=["POST"]
)
def market_import_csv():

    if "file" not in request.files:

        return jsonify({

            "success":
                False,

            "error":
                "Please upload a CSV file using the 'file' field."

        }), 400

    uploaded_file = request.files[
        "file"
    ]

    try:

        content = (
            uploaded_file
            .read()
            .decode("utf-8-sig")
        )

        result = import_csv_data(
            content
        )

        return jsonify(
            result
        )

    except Exception as exc:

        return jsonify({

            "success":
                False,

            "error":
                str(exc)

        }), 500


# ============================================================
# CSV EXPORT API
# ============================================================

@app.route(
    "/api/market/export-csv",
    methods=["GET"]
)
def market_export_csv():

    crop = request.args.get(
        "crop"
    )

    if crop:

        crop = (
            crop
            .lower()
            .strip()
        )

        if crop not in CROPS:

            return jsonify({

                "success":
                    False,

                "error":
                    "Unsupported crop."

            }), 400

        history = get_price_history(
            crop,
            3650
        )

    else:

        history = []

        for crop_name in CROPS:

            history.extend(
                get_price_history(
                    crop_name,
                    3650
                )
            )

    output = io.StringIO()

    fieldnames = [

        "crop",

        "market",

        "price",

        "min_price",

        "max_price",

        "modal_price",

        "source",

        "data_date",

        "fetched_at",

        "created_at"

    ]

    writer = csv.DictWriter(

        output,

        fieldnames=fieldnames
    )

    writer.writeheader()

    for row in history:

        writer.writerow({

            field:
                row.get(
                    field,
                    ""
                )

            for field in fieldnames

        })

    response = Response(

        output.getvalue(),

        mimetype="text/csv"

    )

    response.headers[
        "Content-Disposition"
    ] = (
        "attachment; "
        "filename=smartagri_market_history.csv"
    )

    return response


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
                    or
                    "Unable to obtain market data"

            })

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

        return jsonify({

            "success":
                True,

            "crop":
                crop,

            "market":
                market_data.get(
                    "market",
                    "Kopargaon"
                ),

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

        # Try MongoDB one more time.
        latest = get_latest_price(
            crop
        )

        if latest:

            current_price = float(
                latest["price"]
            )

            trend_data = calculate_trend(

                crop,

                current_price
            )

            forecast_data = calculate_forecast(

                crop,

                current_price
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
                    latest.get(
                        "market",
                        "Kopargaon"
                    ),

                "current_price":
                    round(
                        current_price
                    ),

                "price":
                    round(
                        current_price
                    ),

                "min_price":
                    latest.get(
                        "min_price"
                    ),

                "max_price":
                    latest.get(
                        "max_price"
                    ),

                "modal_price":
                    latest.get(
                        "modal_price"
                    ),

                "latest_date":
                    latest[
                        "data_date"
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
                    "Showing the latest recorded market price because the live market service is temporarily unavailable.",

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
                    calculate_demand(
                        trend_data[
                            "trend"
                        ]
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

        return jsonify({

            "success":
                False,

            "error":
                "Market service temporarily unavailable",

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
            3650
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
# DATABASE STATUS
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

    mongodb_connected = (
        market_collection is not None
    )

    return jsonify({

        "success":
            True,

        "service":
            "SmartAgri Kopargaon",

        "status":
            "online",

        "database":
            MONGODB_DATABASE,

        "mongodb_connected":
            mongodb_connected,

        "government_api_configured":
            bool(
                DATA_GOV_API_KEY
            ),

        "latest": {

            "onion":
                onion,

            "wheat":
                wheat

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

    mongodb_status = (
        market_collection is not None
    )

    return jsonify({

        "status":
            "healthy",

        "service":
            "SmartAgri Kopargaon",

        "mongodb":
            (
                "connected"
                if mongodb_status
                else "not_connected"
            )

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

        "database":
            (
                "MongoDB"
                if market_collection is not None
                else "MongoDB not connected"
            ),

        "endpoints": [

            "/api/market?crop=onion",

            "/api/market?crop=wheat",

            "/api/market/history?crop=onion",

            "/api/market/history?crop=wheat",

            "/api/market/import-csv",

            "/api/market/export-csv",

            "/api/status",

            "/health"

        ]

    })


# ============================================================
# STARTUP
# ============================================================

initialize_mongodb()


if __name__ == "__main__":

    print(
        "=========================================="
    )

    print(
        " SmartAgri Kopargaon Backend"
    )

    print(
        " MongoDB + CSV"
    )

    print(
        "=========================================="
    )

    print(
        f"MongoDB database: "
        f"{MONGODB_DATABASE}"
    )

    print(
        f"MongoDB connected: "
        f"{market_collection is not None}"
    )

    print(
        f"Government API configured: "
        f"{bool(DATA_GOV_API_KEY)}"
    )

    print(
        "Market API: /api/market?crop=onion"
    )

    print(
        "History API: /api/market/history?crop=onion"
    )

    print(
        "CSV import: /api/market/import-csv"
    )

    print(
        "CSV export: /api/market/export-csv"
    )

    print(
        "=========================================="
    )

    app.run(

        host="0.0.0.0",

        port=PORT,

        debug=False

    )
