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


# ============================================================
# SMARTAGRI KOPARGAON
# AGMARKNET CEDA API + MONGODB BACKEND
# ============================================================

try:
    from scraper import scrape_crop
except Exception as exc:
    scrape_crop = None
    SCRAPER_IMPORT_ERROR = str(exc)
else:
    SCRAPER_IMPORT_ERROR = None


# ============================================================
# FLASK
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
        "5000"
    )
)

# Agmarknet CEDA API
AGMARKNET_API_URL = (
    "https://agmarknet.ceda.ashoka.edu.in/api/prices"
)

# MongoDB is optional.
#
# IMPORTANT:
# You only need to configure MONGODB_URI in Render if you
# want persistent database storage/history.
#
# MONGODB_COLLECTION is NOT required as an environment variable.
# It automatically uses "market_prices".
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
# MONGODB STATE
# ============================================================

mongo_client = None
mongo_db = None
market_collection = None
mongodb_error = None


# ============================================================
# MONGODB CONNECTION
# ============================================================

def connect_mongodb():
    """
    MongoDB is optional.

    If MONGODB_URI is missing or MongoDB cannot be reached,
    the application continues running and uses live scraper
    data instead.
    """

    global mongo_client
    global mongo_db
    global market_collection
    global mongodb_error

    mongo_client = None
    mongo_db = None
    market_collection = None
    mongodb_error = None

    if not MONGODB_URI:

        mongodb_error = (
            "MONGODB_URI is not configured. "
            "Running without MongoDB."
        )

        print(
            "INFO:",
            mongodb_error
        )

        return False

    try:

        mongo_client = MongoClient(
            MONGODB_URI,
            serverSelectionTimeoutMS=10000
        )

        # Test connection.
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

        print(
            f"Database: {MONGODB_DB_NAME}"
        )

        print(
            f"Collection: {MONGODB_COLLECTION}"
        )

        return True

    except Exception as exc:

        mongodb_error = str(exc)

        print(
            "WARNING: MongoDB connection failed:"
        )

        print(
            repr(exc)
        )

        # IMPORTANT:
        # Do not prevent Flask from starting.
        mongo_client = None
        mongo_db = None
        market_collection = None

        return False


def create_indexes():

    if market_collection is None:
        return

    try:

        market_collection.create_index(
            [
                ("crop", ASCENDING),
                ("market", ASCENDING),
                ("data_date", DESCENDING),
            ],
            name="crop_market_date"
        )

    except Exception as exc:

        print(
            "Index creation warning:",
            repr(exc)
        )

    try:

        market_collection.create_index(
            [
                ("crop", ASCENDING),
                ("data_date", DESCENDING),
            ],
            name="crop_date"
        )

    except Exception as exc:

        print(
            "Index creation warning:",
            repr(exc)
        )


# Connect when application starts.
connect_mongodb()


# ============================================================
# DATABASE STATUS
# ============================================================

def mongodb_ready():

    return (
        market_collection is not None
    )


# ============================================================
# SERIALIZATION
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

        value = result.get(
            key
        )

        if isinstance(
            value,
            datetime
        ):

            if value.tzinfo is None:

                value = value.replace(
                    tzinfo=timezone.utc
                )

            result[key] = (
                value
                .astimezone(
                    timezone.utc
                )
                .isoformat()
            )

    return result


# ============================================================
# SCRAPER DATA NORMALIZATION
# ============================================================

def normalize_record(
    record,
    requested_crop
):
    """
    Converts different possible scraper outputs into the
    standard format used by the application.

    Supports fields from the Agmarknet CEDA API:

        t
        cmdty
        district
        state
        p_min
        p_max
        p_modal
    """

    if not isinstance(
        record,
        dict
    ):

        return None

    crop = str(
        record.get(
            "crop"
        )
        or record.get(
            "cmdty"
        )
        or requested_crop
    ).strip().lower()

    if crop not in SUPPORTED_CROPS:

        crop = requested_crop

    data_date = (
        record.get(
            "data_date"
        )
        or record.get(
            "t"
        )
    )

    if data_date:

        data_date = str(
            data_date
        ).strip()

    def number(*keys):

        for key in keys:

            value = record.get(
                key
            )

            if value is None:
                continue

            try:

                if isinstance(
                    value,
                    str
                ):

                    value = (
                        value
                        .replace(
                            ",",
                            ""
                        )
                        .replace(
                            "₹",
                            ""
                        )
                        .replace(
                            "Rs.",
                            ""
                        )
                        .replace(
                            "Rs",
                            ""
                        )
                        .strip()
                    )

                return float(
                    value
                )

            except (
                TypeError,
                ValueError
            ):

                continue

        return None

    min_price = number(
        "min_price",
        "p_min"
    )

    max_price = number(
        "max_price",
        "p_max"
    )

    modal_price = number(
        "modal_price",
        "p_modal",
        "price"
    )

    if modal_price is None:

        # If the API did not provide modal price,
        # calculate a reasonable midpoint from min/max.
        if (
            min_price is not None
            and max_price is not None
        ):

            modal_price = (
                min_price
                + max_price
            ) / 2

    if modal_price is None:

        return None

    district = (
        record.get(
            "district"
        )
        or "Ahmadnagar"
    )

    state = (
        record.get(
            "state"
        )
        or "Maharashtra"
    )

    market = (
        record.get(
            "market"
        )
        or "Kopargaon"
    )

    commodity = (
        record.get(
            "commodity"
        )
        or record.get(
            "cmdty"
        )
        or requested_crop.title()
    )

    source_url = (
        record.get(
            "source_url"
        )
        or AGMARKNET_API_URL
    )

    source_name = (
        record.get(
            "source_name"
        )
        or record.get(
            "source"
        )
        or "Agmarknet CEDA API"
    )

    return {

        "crop": crop,

        "market": str(
            market
        ),

        "district": str(
            district
        ),

        "state": str(
            state
        ),

        "commodity": str(
            commodity
        ),

        "variety": str(
            record.get(
                "variety",
                ""
            )
        ),

        "min_price": min_price,

        "max_price": max_price,

        "modal_price": modal_price,

        "price": modal_price,

        "data_date": data_date,

        "source": source_url,

        "source_name": source_name,

        "scraped_at": datetime.now(
            timezone.utc
        ),

    }


def normalize_scraper_result(
    scraper_result,
    crop
):
    """
    Accept either:

        dict
        list[dict]
        {"data": [...]}

    This makes app.py compatible with different versions
    of scraper.py.
    """

    if scraper_result is None:

        return []

    if isinstance(
        scraper_result,
        dict
    ):

        # API-style response:
        # {"data": [...]}
        if isinstance(
            scraper_result.get(
                "data"
            ),
            list
        ):

            scraper_result = (
                scraper_result[
                    "data"
                ]
            )

        else:

            scraper_result = [
                scraper_result
            ]

    if not isinstance(
        scraper_result,
        list
    ):

        return []

    normalized = []

    for record in scraper_result:

        item = normalize_record(
            record,
            crop
        )

        if item:

            normalized.append(
                item
            )

    return normalized


# ============================================================
# DATABASE SAVE
# ============================================================

def save_records(
    records
):
    """
    Save records when MongoDB is available.

    If MongoDB is unavailable, this function does not crash.
    """

    if not mongodb_ready():

        return {
            "inserted": 0,
            "updated": 0,
            "total_processed": len(
                records
            ),
            "mongodb_saved": False,
        }

    inserted = 0
    updated = 0

    for record in records:

        now = datetime.now(
            timezone.utc
        )

        document = {
            **record,
            "updated_at": now,
        }

        if "created_at" not in document:

            document[
                "created_at"
            ] = now

        filter_query = {

            "crop":
                record.get(
                    "crop"
                ),

            "market":
                record.get(
                    "market",
                    ""
                ),

            "data_date":
                record.get(
                    "data_date"
                ),

            "variety":
                record.get(
                    "variety",
                    ""
                ),

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

            elif result.modified_count:

                updated += 1

        except Exception as exc:

            print(
                "MongoDB save error:",
                repr(exc)
            )

    return {

        "inserted":
            inserted,

        "updated":
            updated,

        "total_processed":
            len(records),

        "mongodb_saved":
            True,

    }


# ============================================================
# DATABASE READ
# ============================================================

def get_latest_record(
    crop
):

    if not mongodb_ready():
        return None

    try:

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

    except Exception as exc:

        print(
            "MongoDB read error:",
            repr(exc)
        )

        return None


def get_history(
    crop,
    limit=30
):

    if not mongodb_ready():
        return []

    try:

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
            .limit(
                limit
            )
        )

        return [
            serialize_document(
                document
            )
            for document in cursor
        ]

    except Exception as exc:

        print(
            "MongoDB history error:",
            repr(exc)
        )

        return []


def get_last_scraped(
    crop
):

    if not mongodb_ready():
        return None

    try:

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

    except Exception:

        return None


# ============================================================
# LIVE SCRAPER
# ============================================================

def scrape_live_crop(
    crop
):

    if scrape_crop is None:

        raise RuntimeError(
            "scraper.py could not be imported: "
            f"{SCRAPER_IMPORT_ERROR}"
        )

    print(
        f"Fetching live {crop} data "
        f"from Agmarknet CEDA..."
    )

    raw_result = scrape_crop(
        crop
    )

    records = normalize_scraper_result(
        raw_result,
        crop
    )

    if not records:

        raise RuntimeError(
            f"No valid {crop} market "
            "records were returned "
            "by scraper.py."
        )

    # Newest date first.
    records.sort(
        key=lambda item: (
            item.get(
                "data_date"
            )
            or ""
        ),
        reverse=True
    )

    return records


# ============================================================
# REFRESH
# ============================================================

def refresh_crop(
    crop
):

    records = scrape_live_crop(
        crop
    )

    database_result = save_records(
        records
    )

    latest = records[0]

    return {

        "crop":
            crop,

        "scraped_records":
            len(records),

        "database":
            database_result,

        "latest":
            latest,

        "records":
            records,

    }


def should_refresh(
    crop
):

    if not mongodb_ready():

        # Without MongoDB, fetch live data.
        return True

    last_scraped = get_last_scraped(
        crop
    )

    if last_scraped is None:

        return True

    if last_scraped.tzinfo is None:

        last_scraped = (
            last_scraped
            .replace(
                tzinfo=timezone.utc
            )
        )

    age = (
        datetime.now(
            timezone.utc
        )
        - last_scraped
    )

    return (
        age
        >= timedelta(
            hours=SCRAPE_INTERVAL_HOURS
        )
    )


def ensure_crop_data(
    crop
):

    latest = get_latest_record(
        crop
    )

    # MongoDB cache is usable.
    if (
        latest is not None
        and not should_refresh(
            crop
        )
    ):

        return (
            latest,
            "database"
        )

    # Try live API.
    try:

        result = refresh_crop(
            crop
        )

        if result.get(
            "latest"
        ):

            return (
                result[
                    "latest"
                ],
                "scraped"
            )

    except Exception as exc:

        print(
            f"Live scraper error for "
            f"{crop}:"
        )

        print(
            repr(exc)
        )

        # Use MongoDB fallback if available.
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

    # If MongoDB has no history, we cannot calculate
    # a historical trend reliably.
    if len(history) < 2:

        return {

            "trend":
                "Stable",

            "change":
                0,

            "change_percent":
                0,

        }

    previous_price = (
        history[1].get(
            "modal_price"
        )
    )

    if previous_price is None:

        previous_price = (
            history[1].get(
                "price"
            )
        )

    if previous_price is None:

        return {

            "trend":
                "Stable",

            "change":
                0,

            "change_percent":
                0,

        }

    try:

        previous_price = float(
            previous_price
        )

    except (
        TypeError,
        ValueError
    ):

        return {

            "trend":
                "Stable",

            "change":
                0,

            "change_percent":
                0,

        }

    if previous_price <= 0:

        return {

            "trend":
                "Stable",

            "change":
                0,

            "change_percent":
                0,

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

            try:

                prices.append(
                    float(price)
                )

            except (
                TypeError,
                ValueError
            ):

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
            + movement * 0.5
        )

    # Conservative range.
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

    if current_price > 0:

        change_percent = (
            (
                forecast
                - current_price
            )
            / current_price
        ) * 100

    else:

        change_percent = 0

    if change_percent > 3:

        message = (
            "Prices may increase based "
            "on recent market movement."
        )

    elif change_percent < -3:

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
                change_percent,
                2
            ),

        "message":
            message,

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

        "sell_now":
            round(
                current_price
            ),

        "store":
            round(
                forecast_price
            ),

        "transport":
            round(
                transport_value
            ),

        "best_action":
            action,

        "reason":
            reason,

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

            "success":
                False,

            "error":
                "Supported crops: "
                "onion, wheat",

        }), 400

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
                "Market record does not "
                "contain a modal price."
            )

        current_price = float(
            current_price
        )

        trend_data = calculate_trend(
            crop,
            current_price
        )

        forecast_data = (
            calculate_forecast(
                crop,
                current_price
            )
        )

        demand = calculate_demand(
            trend_data[
                "trend"
            ]
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

        if status == "scraped":

            message = (
                "Latest market data was "
                "retrieved from the "
                "Agmarknet CEDA API."
            )

        elif status == "database":

            message = (
                "Showing the latest market "
                "record stored in MongoDB."
            )

        elif status == "historical_fallback":

            message = (
                "Live market retrieval was "
                "temporarily unavailable. "
                "Showing the latest stored "
                "market record."
            )

        else:

            message = (
                "Showing available market data."
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

            "district":
                market_data.get(
                    "district",
                    "Ahmadnagar"
                ),

            "state":
                market_data.get(
                    "state",
                    "Maharashtra"
                ),

            "commodity":
                market_data.get(
                    "commodity",
                    crop.title()
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
                market_data.get(
                    "data_date"
                ),

            "data_date":
                market_data.get(
                    "data_date"
                ),

            "source":
                market_data.get(
                    "source_name",
                    "Agmarknet CEDA API"
                ),

            "source_name":
                market_data.get(
                    "source_name",
                    "Agmarknet CEDA API"
                ),

            "source_url":
                market_data.get(
                    "source",
                    AGMARKNET_API_URL
                ),

            "api_url":
                AGMARKNET_API_URL,

            "data_status":
                status,

            "message":
                message,

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
                ],

            "mongodb_connected":
                mongodb_ready(),

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
                "Unable to obtain real "
                "market data.",

            "details":
                str(exc),

            "crop":
                crop,

            "api_url":
                AGMARKNET_API_URL,

            "mongodb_connected":
                mongodb_ready(),

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

            "success":
                False,

            "error":
                "Supported crops: "
                "onion, wheat",

        }), 400

    history = get_history(
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
            history,

        "mongodb_connected":
            mongodb_ready(),

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

                "success":
                    False,

                "error":
                    "Supported crops: "
                    "onion, wheat",

            }), 400

        crops = [
            crop
        ]

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

            print(
                f"Refresh error "
                f"for {selected_crop}:",
                repr(exc)
            )

            results[
                selected_crop
            ] = {

                "success":
                    False,

                "error":
                    str(exc),

            }

    return jsonify({

        "success":
            True,

        "results":
            results,

        "mongodb_connected":
            mongodb_ready(),

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
    "min_price",
    "max_price",
    "modal_price",
    "price",
    "data_date",
    "source",
    "source_name",
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

                "success":
                    False,

                "error":
                    "Unsupported crop",

            }), 400

    if not mongodb_ready():

        return jsonify({

            "success":
                False,

            "error":
                "MongoDB is not connected. "
                "CSV export requires stored "
                "MongoDB records.",

        }), 503

    query = {}

    if crop:

        query[
            "crop"
        ] = crop

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

        writer.writerow({

            field:
                row.get(
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
            output
            .getvalue()
            .encode(
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

            "success":
                False,

            "error":
                "MongoDB is not connected.",

        }), 503

    if "file" not in request.files:

        return jsonify({

            "success":
                False,

            "error":
                "Attach a CSV file using "
                "the form field 'file'.",

        }), 400

    uploaded_file = request.files[
        "file"
    ]

    if not uploaded_file.filename:

        return jsonify({

            "success":
                False,

            "error":
                "No file selected.",

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
            io.StringIO(
                text
            )
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

            market = (
                row.get(
                    "market",
                    "Kopargaon"
                )
                .strip()
            )

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

            def optional_float(
                field
            ):

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

                "crop":
                    crop,

                "market":
                    market,

                "district":
                    row.get(
                        "district",
                        "Ahmadnagar"
                    ),

                "state":
                    row.get(
                        "state",
                        "Maharashtra"
                    ),

                "commodity":
                    row.get(
                        "commodity",
                        crop.title()
                    ),

                "variety":
                    row.get(
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

                "source":
                    row.get(
                        "source",
                        AGMARKNET_API_URL
                    ),

                "source_name":
                    row.get(
                        "source_name",
                        "Agmarknet CEDA API"
                    ),

                "scraped_at":
                    datetime.now(
                        timezone.utc
                    ),

            })

        if not records:

            return jsonify({

                "success":
                    False,

                "error":
                    "No valid market records "
                    "were found in the CSV.",

            }), 400

        result = save_records(
            records
        )

        return jsonify({

            "success":
                True,

            "message":
                "CSV records imported "
                "into MongoDB.",

            "records":
                result,

        })

    except Exception as exc:

        return jsonify({

            "success":
                False,

            "error":
                str(exc),

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

        "success":
            True,

        "service":
            "SmartAgri Kopargaon",

        "status":
            "online",

        "database":
            (
                "MongoDB"
                if mongodb_ready()
                else "MongoDB not connected"
            ),

        "mongodb_connected":
            mongodb_ready(),

        "mongodb_error":
            mongodb_error,

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

        "scraper_available":
            scrape_crop is not None,

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

    if os.path.exists(
        index_path
    ):

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
                else "MongoDB not connected"
            ),

        "scraper":
            "Agmarknet CEDA API",

        "api_url":
            AGMARKNET_API_URL,

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
def static_files(
    filename
):

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

        "error":
            "Not Found"

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
        " Agmarknet CEDA API + MongoDB"
    )

    print(
        "=========================================="
    )

    print(
        f"Agmarknet API: "
        f"{AGMARKNET_API_URL}"
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

    if mongodb_error:

        print(
            f"MongoDB info: "
            f"{mongodb_error}"
        )

    print(
        "=========================================="
    )

    app.run(
        host="0.0.0.0",
        port=PORT,
        debug=False
    )
