import os
from datetime import datetime, timedelta

from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import PyMongoError


# ============================================================
# SMARTAGRI KOPARGAON
# MongoDB Database Layer
# ============================================================

MONGODB_URI = os.getenv("MONGODB_URI")

DATABASE_NAME = os.getenv(
    "MONGODB_DATABASE",
    "SmartAgriKopargaon"
)

COLLECTION_NAME = os.getenv(
    "MONGODB_COLLECTION",
    "market_prices"
)


# ============================================================
# CONNECTION
# ============================================================

_client = None
_db = None
_collection = None


def connect_mongodb():
    """
    Connect to MongoDB Atlas.

    The application can still start if MongoDB is temporarily
    unavailable. Database operations will return useful errors
    instead of crashing the Flask application.
    """

    global _client
    global _db
    global _collection

    if not MONGODB_URI:
        print("WARNING: MONGODB_URI is not configured.")
        return False

    try:
        _client = MongoClient(
            MONGODB_URI,
            serverSelectionTimeoutMS=10000,
            connectTimeoutMS=10000,
            socketTimeoutMS=10000,
        )

        # Force connection test.
        _client.admin.command("ping")

        _db = _client[DATABASE_NAME]
        _collection = _db[COLLECTION_NAME]

        create_indexes()

        print(
            f"MongoDB connected successfully: "
            f"{DATABASE_NAME}.{COLLECTION_NAME}"
        )

        return True

    except PyMongoError as exc:

        print(
            "MongoDB connection failed:",
            repr(exc)
        )

        _client = None
        _db = None
        _collection = None

        return False


# ============================================================
# GET COLLECTION
# ============================================================

def get_collection():
    """
    Return the market_prices collection.

    Attempts to connect if it has not already been connected.
    """

    global _collection

    if _collection is None:

        if not connect_mongodb():
            return None

    return _collection


# ============================================================
# INDEXES
# ============================================================

def create_indexes():
    """
    Create indexes used by SmartAgri.

    A market record is uniquely identified by:

        crop
        market
        data_date
        variety

    This prevents the same daily market record from being
    inserted repeatedly.
    """

    if _collection is None:
        return False

    try:

        _collection.create_index(
            [
                ("crop", ASCENDING),
                ("market", ASCENDING),
                ("data_date", ASCENDING),
                ("variety", ASCENDING),
            ],
            unique=True,
            name="unique_market_record",
        )

        # Useful for latest-price queries.
        _collection.create_index(
            [
                ("crop", ASCENDING),
                ("market", ASCENDING),
                ("data_date", DESCENDING),
            ],
            name="latest_price_lookup",
        )

        # Useful for historical charts / prediction.
        _collection.create_index(
            [
                ("crop", ASCENDING),
                ("data_date", ASCENDING),
            ],
            name="historical_price_lookup",
        )

        return True

    except PyMongoError as exc:

        print(
            "MongoDB index creation failed:",
            repr(exc)
        )

        return False


# ============================================================
# DATE CONVERSION
# ============================================================

def normalize_date(value):
    """
    Convert supported date values into Python datetime.

    MongoDB should store data_date as an actual Date,
    not a string.
    """

    if value is None:
        return None

    if isinstance(value, datetime):
        return value

    if isinstance(value, str):

        formats = [
            "%Y-%m-%d",
            "%d-%m-%Y",
            "%d/%m/%Y",
            "%Y/%m/%d",
        ]

        for fmt in formats:

            try:

                return datetime.strptime(
                    value.strip(),
                    fmt
                )

            except ValueError:
                continue

    raise ValueError(
        f"Unsupported date value: {value}"
    )


# ============================================================
# NORMALIZE RECORD
# ============================================================

def normalize_record(record):
    """
    Normalize a scraper/CSV record before MongoDB storage.

    This also protects the unique index from null crop,
    market, data_date or variety values.
    """

    if not isinstance(record, dict):
        raise ValueError("Record must be a dictionary.")

    crop = str(
        record.get("crop") or ""
    ).strip().lower()

    market = str(
        record.get("market") or "Kopargaon"
    ).strip()

    district = str(
        record.get("district") or "Ahilyanagar"
    ).strip()

    state = str(
        record.get("state") or "Maharashtra"
    ).strip()

    commodity = str(
        record.get("commodity")
        or crop.title()
    ).strip()

    variety = str(
        record.get("variety") or ""
    ).strip()

    grade = str(
        record.get("grade") or ""
    ).strip()

    if not crop:
        raise ValueError(
            "Record is missing crop."
        )

    if not market:
        raise ValueError(
            "Record is missing market."
        )

    data_date = normalize_date(
        record.get("data_date")
    )

    if data_date is None:
        raise ValueError(
            "Record is missing data_date."
        )

    def number(value):

        if value is None:
            return None

        try:
            return float(value)

        except (TypeError, ValueError):
            return None

    min_price = number(
        record.get("min_price")
    )

    max_price = number(
        record.get("max_price")
    )

    modal_price = number(
        record.get("modal_price")
    )

    price = number(
        record.get("price")
    )

    if modal_price is None:
        modal_price = price

    if price is None:
        price = modal_price

    # We require at least one price.
    if (
        min_price is None
        and max_price is None
        and modal_price is None
        and price is None
    ):
        raise ValueError(
            "Record contains no valid price."
        )

    return {
        "crop": crop,
        "market": market,
        "district": district,
        "state": state,
        "commodity": commodity,
        "variety": variety,
        "grade": grade,
        "min_price": min_price,
        "max_price": max_price,
        "modal_price": modal_price,
        "price": price,
        "data_date": data_date,
        "source": record.get(
            "source",
            "Unknown"
        ),
        "source_name": record.get(
            "source_name",
            record.get("source", "Unknown")
        ),
        "source_url": record.get(
            "source_url"
        ),
        "updated_at": datetime.utcnow(),
    }


# ============================================================
# UPSERT ONE RECORD
# ============================================================

def upsert_market_price(record):
    """
    Insert a new market price or update an existing one.

    This is the main function that app.py will use after
    scraper.py retrieves today's NaPanta price.
    """

    collection = get_collection()

    if collection is None:

        return {
            "success": False,
            "error": "MongoDB is not connected."
        }

    try:

        normalized = normalize_record(
            record
        )

        query = {
            "crop": normalized["crop"],
            "market": normalized["market"],
            "data_date": normalized["data_date"],
            "variety": normalized["variety"],
        }

        result = collection.update_one(
            query,
            {
                "$set": normalized,
                "$setOnInsert": {
                    "created_at": datetime.utcnow()
                },
            },
            upsert=True,
        )

        if result.upserted_id is not None:

            action = "inserted"

        elif result.modified_count > 0:

            action = "updated"

        else:

            action = "unchanged"

        return {
            "success": True,
            "action": action,
            "record": normalized,
        }

    except (ValueError, PyMongoError) as exc:

        print(
            "MongoDB upsert failed:",
            repr(exc)
        )

        return {
            "success": False,
            "error": str(exc)
        }


# ============================================================
# UPSERT MANY RECORDS
# ============================================================

def upsert_market_prices(records):
    """
    Insert/update multiple historical or live records.

    Useful for:
        - CSV imports
        - NaPanta scraping
        - historical data loading
    """

    results = {
        "success": True,
        "inserted": 0,
        "updated": 0,
        "unchanged": 0,
        "failed": 0,
        "errors": [],
    }

    for record in records:

        result = upsert_market_price(
            record
        )

        if not result.get("success"):

            results["failed"] += 1

            results["errors"].append(
                result.get("error")
            )

            continue

        action = result.get("action")

        if action == "inserted":
            results["inserted"] += 1

        elif action == "updated":
            results["updated"] += 1

        else:
            results["unchanged"] += 1

    if results["failed"] > 0:
        results["success"] = False

    return results


# ============================================================
# LATEST PRICE
# ============================================================

def get_latest_price(
    crop,
    market="Kopargaon"
):
    """
    Get the latest available market price for a crop.
    """

    collection = get_collection()

    if collection is None:
        return None

    crop = str(
        crop or ""
    ).strip().lower()

    market = str(
        market or "Kopargaon"
    ).strip()

    try:

        record = collection.find_one(
            {
                "crop": crop,
                "market": market,
            },
            sort=[
                ("data_date", DESCENDING),
                ("updated_at", DESCENDING),
            ],
        )

        if record:

            record["_id"] = str(
                record["_id"]
            )

        return record

    except PyMongoError as exc:

        print(
            "Latest price query failed:",
            repr(exc)
        )

        return None


# ============================================================
# HISTORICAL PRICES
# ============================================================

def get_historical_prices(
    crop,
    market="Kopargaon",
    limit=365
):
    """
    Get historical prices for prediction/charts.

    Returns oldest → newest.
    """

    collection = get_collection()

    if collection is None:
        return []

    crop = str(
        crop or ""
    ).strip().lower()

    market = str(
        market or "Kopargaon"
    ).strip()

    try:

        cursor = (
            collection
            .find(
                {
                    "crop": crop,
                    "market": market,
                }
            )
            .sort(
                "data_date",
                ASCENDING
            )
            .limit(int(limit))
        )

        records = []

        for record in cursor:

            record["_id"] = str(
                record["_id"]
            )

            records.append(record)

        return records

    except PyMongoError as exc:

        print(
            "Historical price query failed:",
            repr(exc)
        )

        return []


# ============================================================
# DATE-RANGE HISTORY
# ============================================================

def get_prices_between(
    crop,
    start_date,
    end_date,
    market="Kopargaon"
):
    """
    Retrieve historical prices between two dates.

    Dates can be:
        YYYY-MM-DD
        datetime
    """

    collection = get_collection()

    if collection is None:
        return []

    crop = str(
        crop or ""
    ).strip().lower()

    market = str(
        market or "Kopargaon"
    ).strip()

    try:

        start = normalize_date(
            start_date
        )

        end = normalize_date(
            end_date
        )

        # Include the entire end date.
        end = end + timedelta(days=1)

        cursor = (
            collection
            .find(
                {
                    "crop": crop,
                    "market": market,
                    "data_date": {
                        "$gte": start,
                        "$lt": end,
                    },
                }
            )
            .sort(
                "data_date",
                ASCENDING
            )
        )

        records = []

        for record in cursor:

            record["_id"] = str(
                record["_id"]
            )

            records.append(record)

        return records

    except (ValueError, PyMongoError) as exc:

        print(
            "Date-range query failed:",
            repr(exc)
        )

        return []


# ============================================================
# COUNT RECORDS
# ============================================================

def count_prices(
    crop=None,
    market=None
):
    """
    Count records in market_prices.
    """

    collection = get_collection()

    if collection is None:
        return 0

    query = {}

    if crop:
        query["crop"] = str(
            crop
        ).strip().lower()

    if market:
        query["market"] = str(
            market
        ).strip()

    try:

        return collection.count_documents(
            query
        )

    except PyMongoError as exc:

        print(
            "MongoDB count failed:",
            repr(exc)
        )

        return 0


# ============================================================
# DATABASE HEALTH
# ============================================================

def database_health():
    """
    Return database connection status.
    """

    collection = get_collection()

    if collection is None:

        return {
            "connected": False,
            "database": DATABASE_NAME,
            "collection": COLLECTION_NAME,
            "records": 0,
        }

    try:

        count = collection.count_documents({})

        return {
            "connected": True,
            "database": DATABASE_NAME,
            "collection": COLLECTION_NAME,
            "records": count,
        }

    except PyMongoError as exc:

        return {
            "connected": False,
            "database": DATABASE_NAME,
            "collection": COLLECTION_NAME,
            "records": 0,
            "error": str(exc),
        }


# ============================================================
# STARTUP
# ============================================================

# Connect when the Flask application imports this module.
connect_mongodb()
