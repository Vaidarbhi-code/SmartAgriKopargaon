import csv
import io
import os
from datetime import datetime, timedelta, timezone

import certifi
from flask import (
    Flask,
    jsonify,
    request,
    send_file,
    send_from_directory,
)
from flask_cors import CORS
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import PyMongoError
from pymongo.server_api import ServerApi

from scraper import scrape_crop


# ============================================================
# SMARTAGRI KOPARGAON
# NaPanta + MongoDB Atlas + Forecast API
# ============================================================

app = Flask(
    __name__,
    static_folder="."
)

CORS(app)


# ============================================================
# CONFIGURATION
# ============================================================

PORT = int(
    os.environ.get("PORT", "5000")
)

MONGODB_URI = os.environ.get(
    "MONGODB_URI",
    ""
).strip()

MONGODB_DB_NAME = os.environ.get(
    "MONGODB_DB_NAME",
    "SmartAgriKopargaon"
).strip()

MONGODB_COLLECTION = os.environ.get(
    "MONGODB_COLLECTION",
    "market_prices"
).strip()

SCRAPE_INTERVAL_HOURS = float(
    os.environ.get(
        "SCRAPE_INTERVAL_HOURS",
        "6"
    )
)


# ============================================================
# SUPPORTED CROPS
# ============================================================

SUPPORTED_CROPS = {
    "onion",
    "wheat",
}


# ============================================================
# MONGODB GLOBALS
# ============================================================

mongo_client = None
mongo_db = None
market_collection = None


# ============================================================
# MONGODB CONNECTION
# ============================================================

def connect_mongodb():
    """
    Connect to MongoDB Atlas.

    TLS/SSL is explicitly configured using certifi.
    """

    global mongo_client
    global mongo_db
    global market_collection

    if not MONGODB_URI:
        print("=" * 70)
        print("MongoDB connection FAILED")
        print("MONGODB_URI environment variable is missing.")
        print("=" * 70)

        return False

    try:
        print("=" * 70)
        print("Connecting to MongoDB Atlas...")
        print("=" * 70)

        mongo_client = MongoClient(
            MONGODB_URI,

            # TLS
            tls=True,
            tlsCAFile=certifi.where(),

            # MongoDB stable API
            server_api=ServerApi(
                "1",
                strict=True,
                deprecation_errors=True
            ),

            # Connection timeouts
            serverSelectionTimeoutMS=20000,
            connectTimeoutMS=20000,
            socketTimeoutMS=20000,

            # Atlas recommended settings
            retryWrites=True,
        )

        # Force an actual connection test.
        mongo_client.admin.command("ping")

        mongo_db = mongo_client[
            MONGODB_DB_NAME
        ]

        market_collection = mongo_db[
            MONGODB_COLLECTION
        ]

        create_indexes()

        print("=" * 70)
        print("MongoDB connection SUCCESSFUL")
        print(
            f"Database: {MONGODB_DB_NAME}"
        )
        print(
            f"Collection: {MONGODB_COLLECTION}"
        )
        print("=" * 70)

        return True

    except Exception as exc:

        print("=" * 70)
        print("MongoDB connection FAILED")
        print(repr(exc))
        print("=" * 70)

        mongo_client = None
        mongo_db = None
        market_collection = None

        return False


# ============================================================
# INDEXES
# ============================================================

def create_indexes():

    if market_collection is None:
        return

    try:

        existing_indexes = (
            market_collection.index_information()
        )

        create_index_if_missing(
            existing_indexes,
            [
                ("crop", ASCENDING),
                ("market", ASCENDING),
                ("data_date", DESCENDING),
            ],
            "market_price_lookup"
        )

        create_index_if_missing(
            existing_indexes,
            [
                ("crop", ASCENDING),
                ("data_date", DESCENDING),
            ],
            "crop_date_lookup"
        )

        create_index_if_missing(
            existing_indexes,
            [
                ("crop", ASCENDING),
                ("market", ASCENDING),
                ("data_date", ASCENDING),
                ("variety", ASCENDING),
                ("source_name", ASCENDING),
            ],
            "unique_daily_market_record",
            unique=True
        )

    except Exception as exc:

        print(
            "MongoDB index setup warning:",
            repr(exc)
        )


def create_index_if_missing(
    existing_indexes,
    keys,
    name,
    unique=False
):

    wanted = tuple(keys)

    for existing_name, info in (
        existing_indexes.items()
    ):

        existing_key = tuple(
            info.get("key", [])
        )

        if existing_key == wanted:

            print(
                "MongoDB index already exists:",
                existing_name
            )

            return

    try:

        market_collection.create_index(
            keys,
            name=name,
            unique=unique
        )

        print(
            "MongoDB index created:",
            name
        )

    except Exception as exc:

        print(
            f"Could not create index {name}:",
            repr(exc)
        )


# ============================================================
# CONNECT AT STARTUP
# ============================================================

connect_mongodb()


# ============================================================
# DATABASE READY
# ============================================================

def mongodb_ready():

    return (
        market_collection is not None
    )


# ============================================================
# SERIALIZE MONGODB DOCUMENT
# ============================================================

def serialize_document(document):

    if not document:
        return None

    result = dict(document)

    result.pop(
        "_id",
        None
    )

    for key in [
        "scraped_at",
        "created_at",
        "updated_at",
    ]:

        value = result.get(key)

        if isinstance(
            value,
            datetime
        ):

            if value.tzinfo is None:

                value = value.replace(
                    tzinfo=timezone.utc
                )

            result[key] = (
                value.astimezone(
                    timezone.utc
                ).isoformat()
            )

    return result


# ============================================================
# SAVE RECORDS
# ============================================================

def save_records(records):

    if not mongodb_ready():

        raise RuntimeError(
            "MongoDB is not connected."
        )

    inserted = 0
    updated = 0
    skipped = 0

    for record in records:

        crop = str(
            record.get(
                "crop",
                ""
            )
        ).lower().strip()

        if crop not in SUPPORTED_CROPS:

            skipped += 1
            continue

        data_date = str(
            record.get(
                "data_date",
                ""
            )
        ).strip()

        if not data_date:

            skipped += 1
            continue

        market = str(
            record.get(
                "market",
                "Kopargaon"
            )
        ).strip()

        if not market:
            market = "Kopargaon"

        variety = str(
            record.get(
                "variety",
                ""
            )
        ).strip()

        source_name = str(
            record.get(
                "source_name",
                record.get(
                    "source",
                    "NaPanta"
                )
            )
        ).strip()

        if not source_name:
            source_name = "NaPanta"

        now = datetime.now(
            timezone.utc
        )

        document = dict(record)

        document["crop"] = crop
        document["market"] = market
        document["data_date"] = data_date
        document["variety"] = variety
        document["source_name"] = source_name
        document["updated_at"] = now
        document["scraped_at"] = now

        filter_query = {
            "crop": crop,
            "market": market,
            "data_date": data_date,
            "variety": variety,
            "source_name": source_name,
        }

        try:

            result = (
                market_collection
                .update_one(
                    filter_query,
                    {
                        "$set": document,
                        "$setOnInsert": {
                            "created_at": now
                        },
                    },
                    upsert=True
                )
            )

            if result.upserted_id is not None:

                inserted += 1

            elif result.modified_count > 0:

                updated += 1

        except PyMongoError as exc:

            print(
                "MongoDB save error:",
                repr(exc)
            )

            skipped += 1

    return {
        "inserted": inserted,
        "updated": updated,
        "skipped": skipped,
        "total_processed": len(records),
    }


# ============================================================
# LATEST RECORD
# ============================================================

def get_latest_record(crop):

    if not mongodb_ready():
        return None

    document = (
        market_collection
        .find_one(
            {
                "crop": crop
            },
            sort=[
                (
                    "data_date",
                    DESCENDING
                ),
                (
                    "updated_at",
                    DESCENDING
                ),
            ]
        )
    )

    return serialize_document(
        document
    )


# ============================================================
# HISTORY
# ============================================================

def get_history(
    crop,
    limit=30
):

    if not mongodb_ready():
        return []

    cursor = (
        market_collection
        .find(
            {
                "crop": crop
            },
            {
                "_id": 0
            }
        )
        .sort(
            [
                (
                    "data_date",
                    DESCENDING
                ),
                (
                    "updated_at",
                    DESCENDING
                ),
            ]
        )
        .limit(limit)
    )

    return [
        serialize_document(
            document
        )
        for document in cursor
    ]


# ============================================================
# LAST SCRAPED
# ============================================================

def get_last_scraped(crop):

    if not mongodb_ready():
        return None

    document = (
        market_collection
        .find_one(
            {
                "crop": crop
            },
            sort=[
                (
                    "updated_at",
                    DESCENDING
                )
            ]
        )
    )

    if not document:
        return None

    return document.get(
        "updated_at"
    )


# ============================================================
# SCRAPER REFRESH
# ============================================================

def refresh_crop(crop):

    print(
        f"Refreshing {crop} from NaPanta..."
    )

    records = scrape_crop(
        crop
    )

    if not records:

        raise RuntimeError(
            f"No records returned for {crop}."
        )

    database_result = save_records(
        records
    )

    latest = get_latest_record(
        crop
    )

    return {
        "crop": crop,
        "scraped_records": len(records),
        "database": database_result,
        "latest": latest,
    }


# ============================================================
# SHOULD REFRESH
# ============================================================

def should_refresh(crop):

    last_scraped = get_last_scraped(
        crop
    )

    if last_scraped is None:
        return True

    if last_scraped.tzinfo is None:

        last_scraped = (
            last_scraped.replace(
                tzinfo=timezone.utc
            )
        )

    age = (
        datetime.now(timezone.utc)
        - last_scraped
    )

    return (
        age >= timedelta(
            hours=SCRAPE_INTERVAL_HOURS
        )
    )


# ============================================================
# ENSURE DATA
# ============================================================

def ensure_crop_data(crop):

    latest = get_latest_record(
        crop
    )

    # --------------------------------------------------------
    # Use MongoDB if recent enough.
    # --------------------------------------------------------

    if (
        latest is not None
        and not should_refresh(crop)
    ):

        return (
            latest,
            "database"
        )

    # --------------------------------------------------------
    # Try live refresh.
    # --------------------------------------------------------

    try:

        result = refresh_crop(
            crop
        )

        if result.get("latest"):

            return (
                result["latest"],
                "scraped"
            )

    except Exception as exc:

        print(
            f"NaPanta refresh failed "
            f"for {crop}:",
            repr(exc)
        )

        # Historical MongoDB fallback.
        if latest:

            return (
                latest,
                "historical_fallback"
            )

        raise

    if latest:

        return (
            latest,
            "historical_fallback"
        )

    raise RuntimeError(
        f"No market data available "
        f"for {crop}."
    )


# ============================================================
# PRICE
# ============================================================

def get_record_price(record):

    if not record:
        return None

    value = record.get(
        "modal_price"
    )

    if value is None:

        value = record.get(
            "price"
        )

    if value is None:
        return None

    try:

        return float(value)

    except (
        TypeError,
        ValueError
    ):

        return None


# ============================================================
# TREND
# ============================================================

def calculate_trend(
    crop,
    current_price
):

    history = get_history(
        crop,
        10
    )

    prices = []

    for row in history:

        price = get_record_price(
            row
        )

        if price is not None:

            prices.append(price)

    if len(prices) < 2:

        return {
            "trend": "Stable",
            "change": 0,
            "change_percent": 0,
        }

    previous_price = prices[1]

    if previous_price <= 0:

        return {
            "trend": "Stable",
            "change": 0,
            "change_percent": 0,
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
        ),
    }


# ============================================================
# FORECAST
# ============================================================

def calculate_forecast(
    crop,
    current_price
):

    history = get_history(
        crop,
        30
    )

    prices = []

    for row in history:

        price = get_record_price(
            row
        )

        if price is not None:

            prices.append(price)

    if len(prices) < 2:

        forecast = current_price

    else:

        recent_prices = prices[:7]

        average = (
            sum(recent_prices)
            / len(recent_prices)
        )

        previous = prices[1]

        movement = (
            current_price
            - previous
        )

        forecast = (
            average
            + movement * 0.5
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

    if change_percent > 3:

        message = (
            "Prices may increase based "
            "on recent daily market movement."
        )

    elif change_percent < -3:

        message = (
            "Prices may weaken based "
            "on recent daily market movement."
        )

    else:

        message = (
            "Prices are expected to remain "
            "relatively stable."
        )

    return {
        "forecast_price": forecast,
        "forecast_change_percent": round(
            change_percent,
            2
        ),
        "message": message,
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
# DECISION
# ============================================================

def calculate_decision(
    current_price,
    forecast_price,
    trend
):

    transport_cost = (
        current_price * 0.05
    )

    transport_value = (
        current_price
        - transport_cost
    )

    if (
        forecast_price
        > current_price * 1.08
    ):

        action = "Store"

        reason = (
            "The expected future price is "
            "significantly higher than the "
            "current market price."
        )

    elif (
        current_price
        >= forecast_price * 0.98
    ):

        action = "Sell Now"

        reason = (
            "The current market price is "
            "strong relative to the expected "
            "future price."
        )

    elif trend == "Increasing":

        action = "Store"

        reason = (
            "The recent daily market trend "
            "is increasing, so holding may "
            "provide an opportunity."
        )

    else:

        action = "Sell Now"

        reason = (
            "The expected improvement is "
            "not large enough to clearly "
            "justify waiting."
        )

    return {
        "sell_now": round(
            current_price
        ),
        "store": round(
            forecast_price
        ),
        "transport": round(
            transport_value
        ),
        "best_action": action,
        "reason": reason,
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

    if crop not in SUPPORTED_CROPS:

        return jsonify({
            "success": False,
            "error": (
                "Supported crops: "
                "onion, wheat"
            ),
        }), 400

    if not mongodb_ready():

        return jsonify({
            "success": False,
            "error": (
                "MongoDB is not connected. "
                "Check MONGODB_URI in Render."
            ),
        }), 503

    try:

        market_data, status = (
            ensure_crop_data(
                crop
            )
        )

        current_price = (
            get_record_price(
                market_data
            )
        )

        if current_price is None:

            raise RuntimeError(
                "Market record does not contain "
                "a valid modal price."
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
            trend_data["trend"]
        )

        if status == "scraped":

            message = (
                "Latest available market data "
                "was scraped from NaPanta and "
                "saved to MongoDB."
            )

        elif status == "historical_fallback":

            message = (
                "Live NaPanta scraping was "
                "temporarily unavailable. "
                "Showing the latest market "
                "record stored in MongoDB."
            )

        else:

            message = (
                "Showing the latest available "
                "market record stored in MongoDB."
            )

        return jsonify({

            "success": True,

            "crop": crop,

            "market": market_data.get(
                "market",
                "Kopargaon"
            ),

            "district": market_data.get(
                "district",
                "Ahilyanagar"
            ),

            "state": market_data.get(
                "state",
                "Maharashtra"
            ),

            "commodity": market_data.get(
                "commodity",
                crop.title()
            ),

            "variety": market_data.get(
                "variety",
                ""
            ),

            "current_price": round(
                current_price
            ),

            "price": round(
                current_price
            ),

            "min_price": market_data.get(
                "min_price"
            ),

            "max_price": market_data.get(
                "max_price"
            ),

            "modal_price": market_data.get(
                "modal_price"
            ),

            "latest_date": market_data.get(
                "data_date"
            ),

            "data_date": market_data.get(
                "data_date"
            ),

            "source": market_data.get(
                "source_name",
                "NaPanta"
            ),

            "source_name": market_data.get(
                "source_name",
                "NaPanta"
            ),

            "source_url": market_data.get(
                "source_url",
                ""
            ),

            "data_status": status,

            "message": message,

            "trend": trend_data[
                "trend"
            ],

            "price_change": trend_data[
                "change"
            ],

            "change_percent": trend_data[
                "change_percent"
            ],

            "demand": demand,

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
                ],
        })

    except Exception as exc:

        print(
            "MARKET API ERROR:",
            repr(exc)
        )

        return jsonify({
            "success": False,
            "error": (
                "Unable to obtain market data."
            ),
            "details": str(exc),
        }), 503


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
                "30"
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

    if crop not in SUPPORTED_CROPS:

        return jsonify({
            "success": False,
            "error": "Unsupported crop",
        }), 400

    if not mongodb_ready():

        return jsonify({
            "success": False,
            "error": (
                "MongoDB is not connected."
            ),
        }), 503

    history = get_history(
        crop,
        limit
    )

    return jsonify({

        "success": True,

        "crop": crop,

        "count": len(
            history
        ),

        "history": history,

    })


# ============================================================
# MANUAL REFRESH
# ============================================================

@app.route(
    "/api/market/refresh",
    methods=["POST"]
)
def market_refresh():

    crop = request.args.get(
        "crop"
    )

    if not crop:

        body = (
            request.get_json(
                silent=True
            )
            or {}
        )

        crop = body.get(
            "crop"
        )

    if crop:

        crop = str(
            crop
        ).lower().strip()

        if crop not in SUPPORTED_CROPS:

            return jsonify({
                "success": False,
                "error": "Unsupported crop",
            }), 400

        crops = [crop]

    else:

        crops = [
            "onion",
            "wheat",
        ]

    if not mongodb_ready():

        return jsonify({
            "success": False,
            "error": (
                "MongoDB is not connected."
            ),
        }), 503

    results = {}

    for selected_crop in crops:

        try:

            results[
                selected_crop
            ] = refresh_crop(
                selected_crop
            )

        except Exception as exc:

            print(
                f"Refresh error for "
                f"{selected_crop}:",
                repr(exc)
            )

            results[
                selected_crop
            ] = {
                "success": False,
                "error": str(exc),
            }

    return jsonify({
        "success": True,
        "results": results,
    })


# ============================================================
# CSV EXPORT
# ============================================================

CSV_FIELDS = [
    "crop",
    "market",
    "district",
    "state",
    "commodity",
    "variety",
    "grade",
    "min_price",
    "max_price",
    "modal_price",
    "price",
    "data_date",
    "source",
    "source_name",
    "source_url",
    "scraped_at",
]


@app.route(
    "/api/market/export-csv",
    methods=["GET"]
)
def export_csv():

    crop = request.args.get(
        "crop"
    )

    if crop:

        crop = crop.lower().strip()

        if crop not in SUPPORTED_CROPS:

            return jsonify({
                "success": False,
                "error": "Unsupported crop",
            }), 400

    if not mongodb_ready():

        return jsonify({
            "success": False,
            "error": (
                "MongoDB is not connected."
            ),
        }), 503

    query = {}

    if crop:
        query["crop"] = crop

    cursor = (
        market_collection
        .find(
            query,
            {
                "_id": 0
            }
        )
        .sort(
            [
                (
                    "crop",
                    ASCENDING
                ),
                (
                    "data_date",
                    DESCENDING
                ),
            ]
        )
    )

    output = io.StringIO(
        newline=""
    )

    writer = csv.DictWriter(
        output,
        fieldnames=CSV_FIELDS,
        extrasaction="ignore"
    )

    writer.writeheader()

    for document in cursor:

        row = serialize_document(
            document
        )

        writer.writerow(
            {
                field: row.get(
                    field,
                    ""
                )
                for field in CSV_FIELDS
            }
        )

    output.seek(0)

    if crop:

        filename = (
            f"smartagri_market_{crop}.csv"
        )

    else:

        filename = (
            "smartagri_market.csv"
        )

    return send_file(
        io.BytesIO(
            output.getvalue().encode(
                "utf-8"
            )
        ),
        mimetype="text/csv",
        as_attachment=True,
        download_name=filename,
    )


# ============================================================
# CSV IMPORT
# ============================================================

@app.route(
    "/api/market/import-csv",
    methods=["POST"]
)
def import_csv():

    if not mongodb_ready():

        return jsonify({
            "success": False,
            "error": (
                "MongoDB is not connected."
            ),
        }), 503

    if "file" not in request.files:

        return jsonify({
            "success": False,
            "error": (
                "Attach a CSV file using "
                "the form field 'file'."
            ),
        }), 400

    uploaded_file = (
        request.files["file"]
    )

    if not uploaded_file.filename:

        return jsonify({
            "success": False,
            "error": "No file selected.",
        }), 400

    try:

        text = (
            uploaded_file
            .read()
            .decode("utf-8-sig")
        )

        reader = csv.DictReader(
            io.StringIO(text)
        )

        records = []

        for row in reader:

            crop = (
                row.get(
                    "crop",
                    ""
                )
                .strip()
                .lower()
            )

            if crop not in SUPPORTED_CROPS:
                continue

            data_date = (
                row.get(
                    "data_date",
                    ""
                )
                .strip()
            )

            if not data_date:
                continue

            market = (
                row.get(
                    "market",
                    "Kopargaon"
                )
                .strip()
            )

            if not market:
                market = "Kopargaon"

            def parse_float(value):

                if value in (
                    None,
                    ""
                ):

                    return None

                try:

                    return float(
                        str(value)
                        .replace(",", "")
                        .replace("₹", "")
                        .replace("Rs.", "")
                        .replace("Rs", "")
                        .strip()
                    )

                except (
                    ValueError,
                    TypeError
                ):

                    return None

            modal_value = (
                row.get(
                    "modal_price"
                )
                or row.get(
                    "price"
                )
            )

            modal_price = parse_float(
                modal_value
            )

            if modal_price is None:
                continue

            records.append({

                "crop": crop,

                "market": market,

                "district": (
                    row.get(
                        "district",
                        "Ahilyanagar"
                    )
                    .strip()
                ),

                "state": (
                    row.get(
                        "state",
                        "Maharashtra"
                    )
                    .strip()
                ),

                "commodity": (
                    row.get(
                        "commodity",
                        crop.title()
                    )
                    .strip()
                ),

                "variety": (
                    row.get(
                        "variety",
                        ""
                    )
                    .strip()
                ),

                "grade": (
                    row.get(
                        "grade",
                        ""
                    )
                    .strip()
                ),

                "min_price": parse_float(
                    row.get(
                        "min_price"
                    )
                ),

                "max_price": parse_float(
                    row.get(
                        "max_price"
                    )
                ),

                "modal_price": modal_price,

                "price": modal_price,

                "data_date": data_date,

                "source": (
                    row.get(
                        "source",
                        "CSV import"
                    )
                    .strip()
                ),

                "source_name": (
                    row.get(
                        "source_name",
                        "CSV import"
                    )
                    .strip()
                ),

                "source_url": (
                    row.get(
                        "source_url",
                        ""
                    )
                    .strip()
                ),

                "scraped_at":
                    datetime.now(
                        timezone.utc
                    ),
            })

        if not records:

            return jsonify({
                "success": False,
                "error": (
                    "No valid market records "
                    "were found in the CSV."
                ),
            }), 400

        result = save_records(
            records
        )

        return jsonify({

            "success": True,

            "message": (
                "CSV records imported "
                "into MongoDB."
            ),

            "records": result,

        })

    except Exception as exc:

        print(
            "CSV import error:",
            repr(exc)
        )

        return jsonify({
            "success": False,
            "error": str(exc),
        }), 400


# ============================================================
# DATABASE STATS
# ============================================================

@app.route(
    "/api/market/stats",
    methods=["GET"]
)
def market_stats():

    if not mongodb_ready():

        return jsonify({
            "success": False,
            "error": (
                "MongoDB is not connected."
            ),
        }), 503

    stats = {}

    for crop in [
        "onion",
        "wheat",
    ]:

        count = (
            market_collection
            .count_documents(
                {
                    "crop": crop
                }
            )
        )

        latest = get_latest_record(
            crop
        )

        stats[crop] = {
            "records": count,
            "latest": latest,
        }

    return jsonify({

        "success": True,

        "database":
            MONGODB_DB_NAME,

        "collection":
            MONGODB_COLLECTION,

        "stats":
            stats,

    })


# ============================================================
# STATUS
# ============================================================

@app.route(
    "/api/status",
    methods=["GET"]
)
def status():

    latest = {
        "onion": get_latest_record(
            "onion"
        ),
        "wheat": get_latest_record(
            "wheat"
        ),
    }

    return jsonify({

        "success": True,

        "service":
            "SmartAgri Kopargaon",

        "status":
            "online",

        "database":
            (
                "MongoDB"
                if mongodb_ready()
                else
                "MongoDB not connected"
            ),

        "mongodb_connected":
            mongodb_ready(),

        "database_name":
            MONGODB_DB_NAME,

        "collection":
            MONGODB_COLLECTION,

        "scraper":
            "NaPanta Daily",

        "latest":
            latest,

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
            "SmartAgri Kopargaon",

        "mongodb_connected":
            mongodb_ready(),

    })


# ============================================================
# FRONTEND
# ============================================================

@app.route("/")
def home():

    index_path = os.path.join(
        app.root_path,
        "index.html"
    )

    if os.path.exists(index_path):

        return send_from_directory(
            app.root_path,
            "index.html"
        )

    return jsonify({

        "name":
            "SmartAgri Kopargaon",

        "status":
            "running",

        "database":
            (
                "MongoDB"
                if mongodb_ready()
                else
                "MongoDB not connected"
            ),

        "endpoints": [

            "/api/market?crop=onion",

            "/api/market?crop=wheat",

            "/api/market/history?crop=onion",

            "/api/market/history?crop=wheat",

            "/api/market/refresh?crop=onion",

            "/api/market/refresh?crop=wheat",

            "/api/market/export-csv",

            "/api/market/export-csv?crop=onion",

            "/api/market/export-csv?crop=wheat",

            "/api/market/import-csv",

            "/api/market/stats",

            "/api/status",

            "/health",

        ],

    })


# ============================================================
# FRONTEND STATIC FILES
# ============================================================

@app.route(
    "/<path:filename>"
)
def static_files(filename):

    safe_files = {
        "index.html",
        "style.css",
        "script.js",
    }

    if filename in safe_files:

        return send_from_directory(
            app.root_path,
            filename
        )

    return jsonify({
        "error": "Not Found"
    }), 404


# ============================================================
# START SERVER
# ============================================================

if __name__ == "__main__":

    print("=" * 70)
    print("SmartAgri Kopargaon")
    print("NaPanta + MongoDB Atlas + Forecast")
    print("=" * 70)

    print(
        f"MongoDB connected: "
        f"{mongodb_ready()}"
    )

    print(
        f"Database: "
        f"{MONGODB_DB_NAME}"
    )

    print(
        f"Collection: "
        f"{MONGODB_COLLECTION}"
    )

    print(
        f"Scrape interval: "
        f"{SCRAPE_INTERVAL_HOURS} hours"
    )

    print("=" * 70)

    app.run(
        host="0.0.0.0",
        port=PORT,
        debug=False
    )
