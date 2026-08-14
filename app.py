import csv
import io
import os
from datetime import datetime, timedelta, timezone

from flask import (
    Flask,
    jsonify,
    request,
    send_file,
    send_from_directory,
)
from flask_cors import CORS
from pymongo import MongoClient, ASCENDING, DESCENDING

from scraper import scrape_crop


# ============================================================
# SMARTAGRI KOPARGAON
# AGMARKNET CEDA + MONGODB BACKEND
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
    os.environ.get(
        "PORT",
        5000
    )
)

MONGODB_URI = os.environ.get(
    "MONGODB_URI",
    ""
)

MONGODB_DB_NAME = os.environ.get(
    "MONGODB_DB_NAME",
    "SmartAgriKopargaon"
)

MONGODB_COLLECTION = os.environ.get(
    "MONGODB_COLLECTION",
    "market_prices"
)

SCRAPE_INTERVAL_HOURS = float(
    os.environ.get(
        "SCRAPE_INTERVAL_HOURS",
        "6"
    )
)


# ============================================================
# AGMARKNET
# ============================================================

AGMARKNET_API_URL = (
    "https://agmarknet.ceda.ashoka.edu.in/api/prices"
)


# ============================================================
# MONGODB
# ============================================================

mongo_client = None
mongo_db = None
market_collection = None


def connect_mongodb():

    global mongo_client
    global mongo_db
    global market_collection

    if not MONGODB_URI:

        print(
            "WARNING: MONGODB_URI is not configured."
        )

        return False

    try:

        mongo_client = MongoClient(
            MONGODB_URI,
            serverSelectionTimeoutMS=10000
        )

        mongo_client.admin.command(
            "ping"
        )

        mongo_db = mongo_client[
            MONGODB_DB_NAME
        ]

        market_collection = mongo_db[
            MONGODB_COLLECTION
        ]

        create_indexes()

        print(
            "MongoDB connection successful."
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


def create_indexes():

    if market_collection is None:
        return

    # Main lookup index.
    market_collection.create_index(
        [
            ("crop", ASCENDING),
            ("district", ASCENDING),
            ("data_date", DESCENDING),
        ],
        name="crop_district_date"
    )

    # History queries.
    market_collection.create_index(
        [
            ("crop", ASCENDING),
            ("data_date", DESCENDING),
        ],
        name="crop_date"
    )

    # Prevent duplicate records.
    market_collection.create_index(
        [
            ("crop", ASCENDING),
            ("district", ASCENDING),
            ("data_date", ASCENDING),
        ],
        unique=True,
        name="unique_market_record"
    )


connect_mongodb()


# ============================================================
# SUPPORTED CROPS
# ============================================================

SUPPORTED_CROPS = {
    "onion",
    "wheat",
}


# ============================================================
# DATABASE HELPERS
# ============================================================

def mongodb_ready():

    return market_collection is not None


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

            result[key] = value.astimezone(
                timezone.utc
            ).isoformat()

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

    for record in records:

        now = datetime.now(
            timezone.utc
        )

        document = dict(record)

        document["updated_at"] = now

        if "created_at" not in document:

            document["created_at"] = now

        crop = document.get(
            "crop",
            ""
        )

        district = document.get(
            "district",
            ""
        )

        data_date = document.get(
            "data_date"
        )

        if not crop:
            raise ValueError(
                "Record is missing crop."
            )

        if not data_date:
            raise ValueError(
                "Record is missing data_date."
            )

        filter_query = {
            "crop": crop,
            "district": district,
            "data_date": data_date,
        }

        result = market_collection.update_one(
            filter_query,
            {
                "$set": document,
                "$setOnInsert": {
                    "created_at": now
                },
            },
            upsert=True
        )

        if result.upserted_id is not None:

            inserted += 1

        elif result.modified_count:

            updated += 1

    return {
        "inserted": inserted,
        "updated": updated,
        "total_processed": len(records),
    }


# ============================================================
# GET LATEST RECORD
# ============================================================

def get_latest_record(crop):

    if not mongodb_ready():
        return None

    document = market_collection.find_one(
        {
            "crop": crop
        },
        sort=[
            ("data_date", DESCENDING),
            ("updated_at", DESCENDING),
        ]
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

    cursor = market_collection.find(
        {
            "crop": crop
        },
        {
            "_id": 0
        }
    ).sort(
        [
            ("data_date", DESCENDING),
            ("updated_at", DESCENDING),
        ]
    ).limit(limit)

    return [
        serialize_document(
            document
        )
        for document in cursor
    ]


# ============================================================
# LAST SCRAPE
# ============================================================

def get_last_scraped(crop):

    if not mongodb_ready():
        return None

    document = market_collection.find_one(
        {
            "crop": crop
        },
        sort=[
            ("updated_at", DESCENDING)
        ]
    )

    if not document:
        return None

    return document.get(
        "updated_at"
    )


# ============================================================
# SCRAPE / REFRESH
# ============================================================

def refresh_crop(crop):

    print(
        f"Fetching Agmarknet data for {crop}..."
    )

    records = scrape_crop(
        crop
    )

    if not records:

        raise RuntimeError(
            f"Agmarknet returned no records for {crop}."
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

        last_scraped = last_scraped.replace(
            tzinfo=timezone.utc
        )

    age = (
        datetime.now(timezone.utc)
        - last_scraped
    )

    return (
        age
        >= timedelta(
            hours=SCRAPE_INTERVAL_HOURS
        )
    )


# ============================================================
# ENSURE LIVE DATA
# ============================================================

def ensure_crop_data(crop):

    latest = get_latest_record(
        crop
    )

    # Existing data is allowed only if it is
    # still inside the configured refresh interval.
    if (
        latest is not None
        and not should_refresh(crop)
    ):

        return latest, "database"

    # If refresh is required, we MUST successfully
    # contact the scraper. We do NOT silently return
    # a fallback/baseline value.
    result = refresh_crop(
        crop
    )

    if not result.get("latest"):

        raise RuntimeError(
            f"No current Agmarknet record available for {crop}."
        )

    return (
        result["latest"],
        "scraped"
    )


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

    if len(history) < 2:

        return {
            "trend": "Stable",
            "change": 0,
            "change_percent": 0,
        }

    previous_price = (
        history[1].get(
            "modal_price"
        )
        or history[1].get(
            "price"
        )
    )

    if previous_price is None:

        return {
            "trend": "Stable",
            "change": 0,
            "change_percent": 0,
        }

    previous_price = float(
        previous_price
    )

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
        7
    )

    prices = []

    for row in history:

        price = (
            row.get(
                "modal_price"
            )
            or row.get(
                "price"
            )
        )

        if price is not None:

            prices.append(
                float(price)
            )

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
            + movement * 0.5
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
            "Prices may increase based on "
            "recent market movement."
        )

    elif change_percent < -3:

        message = (
            "Prices may weaken based on "
            "recent market movement."
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
        current_price
        * 0.05
    )

    transport_value = (
        current_price
        - transport_cost
    )

    if forecast_price > current_price * 1.08:

        action = "Store"

        reason = (
            "The expected future price is "
            "significantly higher than the "
            "current market price."
        )

    elif current_price >= forecast_price * 0.98:

        action = "Sell Now"

        reason = (
            "The current market price is "
            "strong relative to the expected "
            "future price."
        )

    elif trend == "Increasing":

        action = "Store"

        reason = (
            "The recent market trend is "
            "increasing, so holding may "
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
                "MongoDB is not connected."
            ),
        }), 503

    try:

        market_data, status = (
            ensure_crop_data(
                crop
            )
        )

        current_price = (
            market_data.get(
                "modal_price"
            )
            or market_data.get(
                "price"
            )
        )

        if current_price is None:

            raise RuntimeError(
                "Agmarknet record has no modal price."
            )

        current_price = float(
            current_price
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

            "success": True,

            "crop": crop,

            "market": market_data.get(
                "market",
                market_data.get(
                    "district",
                    "Kopargaon"
                )
            ),

            "district": market_data.get(
                "district"
            ),

            "state": market_data.get(
                "state"
            ),

            "commodity": market_data.get(
                "commodity"
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
                "source",
                "Agmarknet CEDA API"
            ),

            "source_url": market_data.get(
                "source_url",
                AGMARKNET_API_URL
            ),

            "data_status": status,

            "message": (
                "Latest market data fetched "
                "from Agmarknet CEDA and saved "
                "to MongoDB."
                if status == "scraped"
                else
                "Showing the latest market "
                "record stored in MongoDB."
            ),

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
                "Unable to obtain current "
                "Agmarknet market data."
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

        "count": len(history),

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

        body = request.get_json(
            silent=True
        ) or {}

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

        crops = list(
            SUPPORTED_CROPS
        )

    results = {}

    for selected_crop in crops:

        try:

            results[
                selected_crop
            ] = refresh_crop(
                selected_crop
            )

        except Exception as exc:

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

    "commodity",

    "state",

    "district",

    "market",

    "variety",

    "min_price",

    "max_price",

    "modal_price",

    "price",

    "data_date",

    "source",

    "source_url",

    "scraped_at",

    "created_at",

    "updated_at",

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

    cursor = market_collection.find(
        query,
        {
            "_id": 0
        }
    ).sort(
        [
            ("crop", ASCENDING),
            ("data_date", DESCENDING),
        ]
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

        writer.writerow({

            field: row.get(
                field,
                ""
            )

            for field in CSV_FIELDS

        })

    output.seek(0)

    filename = (
        "smartagri_market"
        f"{'_' + crop if crop else ''}"
        ".csv"
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

    uploaded_file = request.files[
        "file"
    ]

    if not uploaded_file.filename:

        return jsonify({
            "success": False,
            "error": "No file selected.",
        }), 400

    try:

        text = (
            uploaded_file
            .read()
            .decode(
                "utf-8-sig"
            )
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

            modal_price = (
                row.get(
                    "modal_price"
                )
                or row.get(
                    "price"
                )
            )

            try:

                modal_price = float(
                    str(
                        modal_price
                    )
                    .replace(
                        ",",
                        ""
                    )
                    .replace(
                        "₹",
                        ""
                    )
                )

            except Exception:

                continue

            def optional_float(field):

                value = row.get(
                    field
                )

                if value in (
                    None,
                    ""
                ):

                    return None

                try:

                    return float(
                        str(value)
                        .replace(
                            ",",
                            ""
                        )
                        .replace(
                            "₹",
                            ""
                        )
                    )

                except Exception:

                    return None

            records.append({

                "crop": crop,

                "commodity": row.get(
                    "commodity",
                    ""
                ),

                "state": row.get(
                    "state",
                    ""
                ),

                "district": row.get(
                    "district",
                    ""
                ),

                "market": row.get(
                    "market",
                    ""
                ),

                "variety": row.get(
                    "variety",
                    ""
                ),

                "min_price":
                    optional_float(
                        "min_price"
                    ),

                "max_price":
                    optional_float(
                        "max_price"
                    ),

                "modal_price":
                    modal_price,

                "price":
                    modal_price,

                "data_date":
                    data_date,

                "source": row.get(
                    "source",
                    "CSV import"
                ),

                "source_url": row.get(
                    "source_url",
                    ""
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

        return jsonify({

            "success": False,

            "error": str(exc),

        }), 400


# ============================================================
# STATUS
# ============================================================

@app.route(
    "/api/status",
    methods=["GET"]
)
def status():

    latest = {

        "onion":
            get_latest_record(
                "onion"
            ),

        "wheat":
            get_latest_record(
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
            "Agmarknet CEDA API",

        "api_url":
            AGMARKNET_API_URL,

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

            "/api/market/import-csv",

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
# STARTUP
# ============================================================

if __name__ == "__main__":

    print(
        "=========================================="
    )

    print(
        " SmartAgri Kopargaon"
    )

    print(
        " Agmarknet CEDA + MongoDB"
    )

    print(
        "=========================================="
    )

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
        f"Agmarknet API: "
        f"{AGMARKNET_API_URL}"
    )

    print(
        "=========================================="
    )

    app.run(
        host="0.0.0.0",
        port=PORT,
        debug=False
    )
