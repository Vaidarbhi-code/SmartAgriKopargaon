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

from pymongo import (
    MongoClient,
    ASCENDING,
    DESCENDING,
)

from pymongo.errors import (
    PyMongoError,
    OperationFailure,
)

from scraper import scrape_crop


# ============================================================
# SMARTAGRI KOPARGAON
# FLASK + MONGODB + AGMARKNET CEDA
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

# ------------------------------------------------------------
# MongoDB
#
# MONGODB_URI is REQUIRED on Render.
#
# MONGODB_DB_NAME is optional.
#
# MONGODB_COLLECTION is optional.
# If you don't create it in Render, the application uses:
#
# market_prices
# ------------------------------------------------------------

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


# ------------------------------------------------------------
# Scraper refresh interval
# ------------------------------------------------------------

SCRAPE_INTERVAL_HOURS = float(
    os.environ.get(
        "SCRAPE_INTERVAL_HOURS",
        "6"
    )
)


# ------------------------------------------------------------
# Agmarknet API
# ------------------------------------------------------------

AGMARKNET_API_URL = (
    "https://agmarknet.ceda.ashoka.edu.in/api/prices"
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
    Connect to MongoDB.

    Only MONGODB_URI is required.

    Database and collection are automatically selected
    using the defaults above if environment variables are
    not provided.
    """

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
            serverSelectionTimeoutMS=10000,
            connectTimeoutMS=10000,
            socketTimeoutMS=10000,
        )

        # Force connection test.
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

        print(
            "MongoDB connection failed:",
            repr(exc)
        )

        mongo_client = None
        mongo_db = None
        market_collection = None

        return False


# ============================================================
# MONGODB INDEXES
# ============================================================

def create_indexes():
    """
    Create indexes safely.

    Important:
    MongoDB may already contain an index such as:

        crop_1_data_date_-1

    with a different name than the one requested here.

    Therefore IndexOptionsConflict is ignored instead of
    making the entire MongoDB connection fail.
    """

    if market_collection is None:
        return

    indexes = [

        (
            [
                ("crop", ASCENDING),
                ("market", ASCENDING),
                ("data_date", DESCENDING),
            ],
            {
                "name": "market_latest_lookup"
            }
        ),

        (
            [
                ("crop", ASCENDING),
                ("data_date", DESCENDING),
            ],
            {
                "name": "crop_history_lookup"
            }
        ),

        (
            [
                ("crop", ASCENDING),
                ("market", ASCENDING),
                ("data_date", ASCENDING),
                ("variety", ASCENDING),
            ],
            {
                "name": "unique_market_record",
                "unique": True,
            }
        ),
    ]

    for keys, options in indexes:

        try:

            market_collection.create_index(
                keys,
                **options
            )

        except OperationFailure as exc:

            # MongoDB error 85:
            # IndexOptionsConflict
            if getattr(
                exc,
                "code",
                None
            ) == 85:

                print(
                    "MongoDB index already exists "
                    "with different options/name. "
                    f"Continuing: {options.get('name')}"
                )

                continue

            print(
                "MongoDB index creation warning:",
                repr(exc)
            )


# ============================================================
# START MONGODB
# ============================================================

connect_mongodb()


# ============================================================
# DATABASE STATUS
# ============================================================

def mongodb_ready():

    return (
        market_collection is not None
    )


# ============================================================
# DATE HELPERS
# ============================================================

def normalize_date(value):
    """
    Normalize dates from scraper/API into YYYY-MM-DD.

    Examples:

        2025-10
        2025-10-01
        2025-10-15

    are converted to a consistent date string.
    """

    if value is None:
        return None

    value = str(value).strip()

    if not value:
        return None

    # Monthly Agmarknet data.
    if len(value) == 7:
        try:

            datetime.strptime(
                value,
                "%Y-%m"
            )

            return f"{value}-01"

        except ValueError:
            pass

    # ISO datetime.
    try:

        parsed = datetime.fromisoformat(
            value.replace(
                "Z",
                "+00:00"
            )
        )

        return parsed.strftime(
            "%Y-%m-%d"
        )

    except ValueError:
        pass

    # Date only.
    for fmt in (
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%d %b %Y",
        "%d %B %Y",
    ):

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

    return value


# ============================================================
# DOCUMENT SERIALIZATION
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
                value.astimezone(
                    timezone.utc
                ).isoformat()
            )

    return result


# ============================================================
# RECORD NORMALIZATION
# ============================================================

def normalize_record(
    record,
    requested_crop=None
):
    """
    Convert scraper/API records into the MongoDB schema.

    Supports both:

        {
            "crop": "wheat",
            ...
        }

    and Agmarknet-style:

        {
            "t": "2025-10",
            "cmdty": "Wheat",
            "p_min": ...,
            "p_max": ...,
            "p_modal": ...
        }
    """

    if not isinstance(
        record,
        dict
    ):

        return None

    crop = (
        record.get("crop")
        or record.get("cmdty")
        or requested_crop
        or ""
    )

    crop = str(
        crop
    ).strip().lower()

    if crop not in SUPPORTED_CROPS:
        return None

    # --------------------------------------------------------
    # Date
    # --------------------------------------------------------

    data_date = (
        record.get("data_date")
        or record.get("arrival_date")
        or record.get("t")
        or record.get("date")
    )

    data_date = normalize_date(
        data_date
    )

    if not data_date:
        return None

    # --------------------------------------------------------
    # Market
    # --------------------------------------------------------

    market = (
        record.get("market")
        or "Kopargaon"
    )

    market = str(
        market
    ).strip()

    # --------------------------------------------------------
    # Prices
    # --------------------------------------------------------

    def to_float(value):

        if value is None:
            return None

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

        except Exception:
            return None

    min_price = to_float(
        record.get(
            "min_price",
            record.get(
                "p_min"
            )
        )
    )

    max_price = to_float(
        record.get(
            "max_price",
            record.get(
                "p_max"
            )
        )
    )

    modal_price = to_float(
        record.get(
            "modal_price",
            record.get(
                "p_modal",
                record.get(
                    "price"
                )
            )
        )
    )

    if modal_price is None:

        # If modal is unavailable, use average
        # when scraper supplies it.
        modal_price = to_float(
            record.get(
                "average_price"
            )
        )

    if modal_price is None:
        return None

    # --------------------------------------------------------
    # Metadata
    # --------------------------------------------------------

    district = (
        record.get(
            "district"
        )
        or "Ahmadnagar"
    )

    commodity = (
        record.get(
            "commodity"
        )
        or record.get(
            "cmdty"
        )
        or crop.title()
    )

    variety = (
        record.get(
            "variety"
        )
        or ""
    )

    source_url = (
        record.get(
            "source_url"
        )
        or AGMARKNET_API_URL
    )

    now = datetime.now(
        timezone.utc
    )

    return {

        "crop": crop,

        "market": market,

        "district": district,

        "commodity": commodity,

        "variety": variety,

        "min_price": min_price,

        "max_price": max_price,

        "modal_price": modal_price,

        # Keep compatibility with existing frontend.
        "price": modal_price,

        "data_date": data_date,

        "source": "Agmarknet CEDA API",

        "source_name": "Agmarknet CEDA API",

        "source_url": source_url,

        "scraped_at": now,

        "updated_at": now,

    }


# ============================================================
# NORMALIZE SCRAPER RESULT
# ============================================================

def normalize_scraper_result(
    result,
    crop
):
    """
    The scraper may return:

        dict

    or:

        list[dict]

    Normalize both into a list.
    """

    if result is None:
        return []

    if isinstance(
        result,
        dict
    ):

        # Some scrapers return:
        #
        # {"data": [...]}
        #
        if isinstance(
            result.get("data"),
            list
        ):

            result = result[
                "data"
            ]

        else:

            result = [
                result
            ]

    if not isinstance(
        result,
        list
    ):

        return []

    records = []

    for item in result:

        normalized = normalize_record(
            item,
            crop
        )

        if normalized:

            records.append(
                normalized
            )

    return records


# ============================================================
# SAVE HISTORICAL RECORDS
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

        document = dict(
            record
        )

        document[
            "updated_at"
        ] = now

        # ----------------------------------------------------
        # Unique identity:
        #
        # crop + market + date + variety
        #
        # This means every month's market price becomes a
        # historical MongoDB record.
        # ----------------------------------------------------

        filter_query = {

            "crop": record[
                "crop"
            ],

            "market": record[
                "market"
            ],

            "data_date": record[
                "data_date"
            ],

            "variety": record.get(
                "variety",
                ""
            ),
        }

        update_result = (
            market_collection.update_one(
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

        if (
            update_result.upserted_id
            is not None
        ):

            inserted += 1

        elif update_result.modified_count:

            updated += 1

    return {

        "inserted": inserted,

        "updated": updated,

        "total_processed":
            len(records),

    }


# ============================================================
# GET LATEST RECORD
# ============================================================

def get_latest_record(
    crop
):

    if not mongodb_ready():
        return None

    document = (
        market_collection.find_one(
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
# GET HISTORICAL DATA
# ============================================================

def get_history(
    crop,
    limit=30
):

    if not mongodb_ready():
        return []

    cursor = (
        market_collection.find(
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
# GET LAST SCRAPE TIME
# ============================================================

def get_last_scraped(
    crop
):

    if not mongodb_ready():
        return None

    document = (
        market_collection.find_one(
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

def refresh_crop(
    crop
):
    """
    Scrape the crop and save ALL returned historical
    records into MongoDB.
    """

    print(
        f"Refreshing {crop} market history..."
    )

    scraper_result = scrape_crop(
        crop
    )

    records = normalize_scraper_result(
        scraper_result,
        crop
    )

    if not records:

        raise RuntimeError(
            f"Scraper returned no valid "
            f"historical records for {crop}."
        )

    database_result = save_records(
        records
    )

    latest = get_latest_record(
        crop
    )

    return {

        "crop": crop,

        "scraped_records":
            len(records),

        "database":
            database_result,

        "latest":
            latest,

    }


# ============================================================
# SHOULD REFRESH
# ============================================================

def should_refresh(
    crop
):

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


# ============================================================
# ENSURE DATA
# ============================================================

def ensure_crop_data(
    crop
):

    latest = get_latest_record(
        crop
    )

    # --------------------------------------------------------
    # Existing MongoDB data is available and fresh.
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
    # Try live scrape.
    # --------------------------------------------------------

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
            f"Scraper error for {crop}:",
            repr(exc)
        )

        # ----------------------------------------------------
        # IMPORTANT:
        #
        # If API is temporarily unavailable, continue using
        # historical MongoDB data.
        # ----------------------------------------------------

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
        f"No market data available for {crop}."
    )


# ============================================================
# HISTORICAL PRICE EXTRACTION
# ============================================================

def extract_prices(
    history
):

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

        if price is None:
            continue

        try:

            prices.append(
                float(price)
            )

        except (
            TypeError,
            ValueError
        ):

            continue

    return prices


# ============================================================
# TREND
# ============================================================

def calculate_trend(
    crop,
    current_price
):

    history = get_history(
        crop,
        12
    )

    prices = extract_prices(
        history
    )

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
    """
    Forecast future price using historical MongoDB data.

    This is intentionally a simple conservative model.

    It uses:

    1. Historical average
    2. Recent price movement
    3. Recent trend

    The important point is that the prediction is based on
    the historical dataset stored in MongoDB.
    """

    history = get_history(
        crop,
        12
    )

    prices = extract_prices(
        history
    )

    if len(prices) == 0:

        return {

            "forecast_price":
                round(current_price),

            "forecast_change_percent":
                0,

            "message":
                "Not enough historical data "
                "for a forecast.",

            "history_points": 0,

        }

    # --------------------------------------------------------
    # One record only.
    # --------------------------------------------------------

    if len(prices) == 1:

        forecast = current_price

    else:

        # Most recent prices are first because MongoDB sorts
        # descending.
        #
        # Example:
        #
        # prices[0] = latest
        # prices[1] = previous month
        # prices[2] = two months ago
        # ...

        recent_prices = prices[
            :6
        ]

        historical_average = (
            sum(recent_prices)
            / len(recent_prices)
        )

        previous_price = prices[
            1
        ]

        # Recent movement.
        movement = (
            current_price
            - previous_price
        )

        # Trend component.
        #
        # 0.35 means only part of the latest movement
        # is projected forward.
        trend_component = (
            movement
            * 0.35
        )

        # Average component.
        average_component = (
            historical_average
            * 0.65
        )

        forecast = (
            average_component
            + trend_component
        )

    # --------------------------------------------------------
    # Conservative safety boundaries.
    #
    # Prevent a bad/outlier record from generating an absurd
    # forecast.
    # --------------------------------------------------------

    lower_bound = (
        current_price
        * 0.75
    )

    upper_bound = (
        current_price
        * 1.35
    )

    forecast = max(
        lower_bound,
        min(
            forecast,
            upper_bound
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
            "Prices may increase based on "
            "recent historical market movement."
        )

    elif change_percent < -3:

        message = (
            "Prices may weaken based on "
            "recent historical market movement."
        )

    else:

        message = (
            "Prices are expected to remain "
            "relatively stable based on "
            "recent historical data."
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

        "history_points":
            len(prices),

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
# FARMER DECISION
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
            "Historical market data indicates "
            "that the expected future price is "
            "significantly higher than the "
            "current market price."
        )

    elif (
        current_price
        >= forecast_price * 0.98
    ):

        action = "Sell Now"

        reason = (
            "The current market price is strong "
            "relative to the estimated future price."
        )

    elif trend == "Increasing":

        action = "Store"

        reason = (
            "The historical market trend is "
            "increasing, so holding may provide "
            "an opportunity."
        )

    else:

        action = "Sell Now"

        reason = (
            "The expected improvement is not "
            "large enough to clearly justify "
            "waiting."
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

            "success": False,

            "error":
                "Supported crops: onion, wheat",

        }), 400

    if not mongodb_ready():

        return jsonify({

            "success": False,

            "error":
                "MongoDB is not connected.",

            "database":
                "MongoDB not connected",

        }), 503

    try:

        market_data, status = (
            ensure_crop_data(
                crop
            )
        )

        current_price = float(
            market_data.get(
                "modal_price"
            )
            or market_data.get(
                "price"
            )
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
            trend_data[
                "trend"
            ]
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

        if status == "scraped":

            message = (
                "Latest market data was "
                "retrieved from Agmarknet CEDA "
                "and historical records were "
                "saved to MongoDB."
            )

        elif status == "historical_fallback":

            message = (
                "Live market retrieval was "
                "temporarily unavailable. "
                "Using the latest historical "
                "record stored in MongoDB."
            )

        else:

            message = (
                "Using the latest market record "
                "stored in MongoDB."
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

            "source_url":
                market_data.get(
                    "source_url",
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

            "history_points":
                forecast_data[
                    "history_points"
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

            "success":
                False,

            "error":
                "Unable to obtain real "
                "market data.",

            "details":
                str(exc),

        }), 500


# ============================================================
# HISTORICAL DATA API
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
            365
        )
    )

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
                "MongoDB is not connected.",

        }), 503

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

    })


# ============================================================
# DATABASE SUMMARY
# ============================================================

@app.route(
    "/api/market/database",
    methods=["GET"]
)
def market_database():

    if not mongodb_ready():

        return jsonify({

            "success":
                False,

            "mongodb_connected":
                False,

            "error":
                "MongoDB is not connected.",

        }), 503

    result = {}

    for crop in SUPPORTED_CROPS:

        count = (
            market_collection.count_documents(
                {
                    "crop": crop
                }
            )
        )

        latest = get_latest_record(
            crop
        )

        result[crop] = {

            "records":
                count,

            "latest":
                latest,

        }

    return jsonify({

        "success":
            True,

        "database":
            MONGODB_DB_NAME,

        "collection":
            MONGODB_COLLECTION,

        "crops":
            result,

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
                    "Unsupported crop",

            }), 400

        crops = [
            crop
        ]

    else:

        crops = list(
            SUPPORTED_CROPS
        )

    if not mongodb_ready():

        return jsonify({

            "success":
                False,

            "error":
                "MongoDB is not connected.",

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
                f"Refresh failed for "
                f"{selected_crop}:",
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

    })


# ============================================================
# CSV EXPORT
# ============================================================

CSV_FIELDS = [

    "crop",

    "market",

    "district",

    "commodity",

    "variety",

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
                "MongoDB is not connected.",

        }), 503

    query = {}

    if crop:

        query[
            "crop"
        ] = crop

    cursor = (
        market_collection.find(
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
            io.StringIO(text)
        )

        records = []

        for row in reader:

            normalized = normalize_record(
                row
            )

            if normalized:

                records.append(
                    normalized
                )

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
                "Historical CSV records imported "
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

    database_counts = {}

    if mongodb_ready():

        for crop in SUPPORTED_CROPS:

            database_counts[
                crop
            ] = (
                market_collection
                .count_documents(
                    {
                        "crop": crop
                    }
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
            (
                "MongoDB"
                if mongodb_ready()
                else "MongoDB not connected"
            ),

        "mongodb_connected":
            mongodb_ready(),

        "database_name":
            MONGODB_DB_NAME,

        "collection":
            MONGODB_COLLECTION,

        "database_records":
            database_counts,

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

        "endpoints": [

            "/api/market?crop=onion",

            "/api/market?crop=wheat",

            "/api/market/history?crop=onion",

            "/api/market/history?crop=wheat",

            "/api/market/database",

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

        "error":
            "Not Found"

    }), 404


# ============================================================
# STARTUP
# ============================================================

if __name__ == "__main__":

    print(
        "=" * 60
    )

    print(
        " SmartAgri Kopargaon"
    )

    print(
        " Agmarknet CEDA + MongoDB"
    )

    print(
        "=" * 60
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
        "=" * 60
    )

    app.run(
        host="0.0.0.0",
        port=PORT,
        debug=False
    )
