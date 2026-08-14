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

from scraper import scrape_crop

from database import (
    database_health,
    get_latest_price,
    get_historical_prices,
    get_prices_between,
    upsert_market_prices,
)


# ============================================================
# SMARTAGRI KOPARGAON
# MongoDB + NaPanta + CSV BACKEND
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

SCRAPE_INTERVAL_HOURS = float(
    os.environ.get(
        "SCRAPE_INTERVAL_HOURS",
        "6"
    )
)

SUPPORTED_CROPS = {
    "onion",
    "wheat",
}

DEFAULT_MARKET = "Kopargaon"


# ============================================================
# HELPERS
# ============================================================

def normalize_crop(crop):
    if not crop:
        return ""

    return str(
        crop
    ).strip().lower()


def json_safe(value):
    """
    Convert MongoDB/Python values into JSON-safe values.
    """

    if isinstance(value, datetime):

        if value.tzinfo is None:
            value = value.replace(
                tzinfo=timezone.utc
            )

        return value.astimezone(
            timezone.utc
        ).isoformat()

    if isinstance(value, dict):

        return {
            key: json_safe(item)
            for key, item in value.items()
        }

    if isinstance(value, list):

        return [
            json_safe(item)
            for item in value
        ]

    return value


def clean_record(record):
    if not record:
        return None

    return json_safe(
        dict(record)
    )


def get_price(record):
    if not record:
        return None

    price = (
        record.get("modal_price")
        or record.get("price")
    )

    if price is None:
        return None

    try:
        return float(price)

    except (
        TypeError,
        ValueError
    ):
        return None


# ============================================================
# MONGODB STATUS
# ============================================================

def mongodb_ready():
    health = database_health()

    return bool(
        health.get("connected")
    )


# ============================================================
# SCRAPER / LIVE DATA
# ============================================================

def refresh_crop(crop):
    """
    Scrape NaPanta and save all returned daily records
    into MongoDB.

    scraper.py returns a list of records.
    """

    crop = normalize_crop(crop)

    if crop not in SUPPORTED_CROPS:
        raise ValueError(
            "Supported crops are onion and wheat."
        )

    print(
        f"Refreshing live market data for {crop}..."
    )

    records = scrape_crop(
        crop
    )

    if not records:
        raise RuntimeError(
            f"No market data returned for {crop}."
        )

    # Make absolutely sure every record has the crop.
    normalized_records = []

    for record in records:

        record = dict(record)

        record["crop"] = crop

        if not record.get("market"):
            record["market"] = DEFAULT_MARKET

        normalized_records.append(
            record
        )

    result = upsert_market_prices(
        normalized_records
    )

    latest = get_latest_price(
        crop,
        DEFAULT_MARKET
    )

    return {
        "success": True,
        "crop": crop,
        "scraped_records": len(
            normalized_records
        ),
        "database": result,
        "latest": clean_record(
            latest
        ),
    }


# ============================================================
# CHECK WHETHER LIVE DATA SHOULD BE REFRESHED
# ============================================================

def should_refresh(crop):
    """
    Determine whether the MongoDB data is older than the
    configured refresh interval.
    """

    latest = get_latest_price(
        crop,
        DEFAULT_MARKET
    )

    if latest is None:
        return True

    updated_at = latest.get(
        "updated_at"
    )

    if updated_at is None:
        return True

    if isinstance(
        updated_at,
        str
    ):
        try:
            updated_at = datetime.fromisoformat(
                updated_at.replace(
                    "Z",
                    "+00:00"
                )
            )
        except ValueError:
            return True

    if updated_at.tzinfo is None:

        updated_at = updated_at.replace(
            tzinfo=timezone.utc
        )

    age = (
        datetime.now(timezone.utc)
        - updated_at
    )

    return (
        age
        >= timedelta(
            hours=SCRAPE_INTERVAL_HOURS
        )
    )


# ============================================================
# ENSURE CURRENT DATA
# ============================================================

def ensure_crop_data(crop):
    """
    Main live-data logic.

    1. Look in MongoDB first.
    2. If data is recent, return MongoDB data.
    3. If data is old/missing, scrape NaPanta.
    4. Save scraper data into MongoDB.
    5. Return the latest MongoDB record.
    """

    crop = normalize_crop(crop)

    latest = get_latest_price(
        crop,
        DEFAULT_MARKET
    )

    # MongoDB has recent data.
    if (
        latest is not None
        and not should_refresh(crop)
    ):

        return (
            latest,
            "database"
        )

    # MongoDB data is missing/stale.
    refreshed = refresh_crop(
        crop
    )

    latest = refreshed.get(
        "latest"
    )

    if not latest:
        raise RuntimeError(
            f"No current market data available for {crop}."
        )

    return (
        latest,
        "scraped"
    )


# ============================================================
# TREND
# ============================================================

def calculate_trend(
    crop,
    current_price
):
    """
    Calculate trend using MongoDB historical data.
    """

    history = get_historical_prices(
        crop,
        DEFAULT_MARKET,
        10
    )

    if len(history) < 2:

        return {
            "trend": "Stable",
            "change": 0,
            "change_percent": 0,
        }

    # get_historical_prices returns oldest -> newest.
    previous_price = get_price(
        history[-2]
    )

    if previous_price is None:
        return {
            "trend": "Stable",
            "change": 0,
            "change_percent": 0,
        }

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
    Simple forecast based on MongoDB historical data.

    This is NOT the final ML prediction model.
    It keeps the existing frontend working until we connect
    the actual prediction model.
    """

    history = get_historical_prices(
        crop,
        DEFAULT_MARKET,
        7
    )

    prices = []

    for row in history:

        price = get_price(
            row
        )

        if price is not None:
            prices.append(
                price
            )

    if len(prices) < 2:

        forecast = current_price

    else:

        average = (
            sum(prices)
            / len(prices)
        )

        # history is oldest -> newest.
        previous_price = prices[-2]

        movement = (
            current_price
            - previous_price
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

    crop = normalize_crop(
        request.args.get(
            "crop",
            "onion"
        )
    )

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

        market_data, data_status = (
            ensure_crop_data(
                crop
            )
        )

        current_price = get_price(
            market_data
        )

        if current_price is None:

            raise RuntimeError(
                "MongoDB record has no valid price."
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

        source = market_data.get(
            "source",
            "NaPanta"
        )

        return jsonify({
            "success": True,

            "crop": crop,

            "market": market_data.get(
                "market",
                DEFAULT_MARKET
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

            "latest_date": json_safe(
                market_data.get(
                    "data_date"
                )
            ),

            "data_date": json_safe(
                market_data.get(
                    "data_date"
                )
            ),

            "source": source,

            "source_url": market_data.get(
                "source_url"
            ),

            "data_status": data_status,

            "message": (
                "Latest market data fetched "
                "from NaPanta and saved to MongoDB."
                if data_status == "scraped"
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
                "market data."
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

    crop = normalize_crop(
        request.args.get(
            "crop",
            "onion"
        )
    )

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

    history = get_historical_prices(
        crop,
        DEFAULT_MARKET,
        limit
    )

    history = [
        clean_record(
            record
        )
        for record in history
    ]

    return jsonify({
        "success": True,
        "crop": crop,
        "market": DEFAULT_MARKET,
        "count": len(history),
        "history": history,
    })


# ============================================================
# DATE RANGE HISTORY API
# ============================================================

@app.route(
    "/api/market/history/range",
    methods=["GET"]
)
def market_history_range():

    crop = normalize_crop(
        request.args.get(
            "crop",
            "onion"
        )
    )

    start_date = request.args.get(
        "start"
    )

    end_date = request.args.get(
        "end"
    )

    if crop not in SUPPORTED_CROPS:

        return jsonify({
            "success": False,
            "error": "Unsupported crop.",
        }), 400

    if not start_date or not end_date:

        return jsonify({
            "success": False,
            "error": (
                "Provide start and end dates."
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

        history = get_prices_between(
            crop,
            start_date,
            end_date,
            DEFAULT_MARKET
        )

        history = [
            clean_record(
                record
            )
            for record in history
        ]

        return jsonify({
            "success": True,
            "crop": crop,
            "market": DEFAULT_MARKET,
            "start": start_date,
            "end": end_date,
            "count": len(history),
            "history": history,
        })

    except Exception as exc:

        return jsonify({
            "success": False,
            "error": str(exc),
        }), 400


# ============================================================
# MANUAL LIVE REFRESH
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

        crop = normalize_crop(
            crop
        )

        if crop not in SUPPORTED_CROPS:

            return jsonify({
                "success": False,
                "error": (
                    "Supported crops: "
                    "onion, wheat"
                ),
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
        "results": json_safe(
            results
        ),
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
    "grade",
    "min_price",
    "max_price",
    "modal_price",
    "price",
    "data_date",
    "source",
    "source_name",
    "source_url",
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

        crop = normalize_crop(
            crop
        )

        if crop not in SUPPORTED_CROPS:

            return jsonify({
                "success": False,
                "error": "Unsupported crop.",
            }), 400

    if not mongodb_ready():

        return jsonify({
            "success": False,
            "error": (
                "MongoDB is not connected."
            ),
        }), 503

    # Get a sufficiently large historical dataset.
    if crop:

        records = get_historical_prices(
            crop,
            DEFAULT_MARKET,
            100000
        )

    else:

        records = []

        for selected_crop in [
            "onion",
            "wheat",
        ]:

            records.extend(
                get_historical_prices(
                    selected_crop,
                    DEFAULT_MARKET,
                    100000
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

    for record in records:

        row = clean_record(
            record
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

            crop = normalize_crop(
                row.get(
                    "crop"
                )
            )

            if crop not in SUPPORTED_CROPS:
                continue

            data_date = (
                row.get(
                    "data_date"
                )
                or ""
            ).strip()

            if not data_date:
                continue

            market = (
                row.get(
                    "market"
                )
                or DEFAULT_MARKET
            ).strip()

            commodity = (
                row.get(
                    "commodity"
                )
                or crop.title()
            ).strip()

            district = (
                row.get(
                    "district"
                )
                or "Ahilyanagar"
            ).strip()

            state = (
                row.get(
                    "state"
                )
                or "Maharashtra"
            ).strip()

            variety = (
                row.get(
                    "variety"
                )
                or ""
            ).strip()

            grade = (
                row.get(
                    "grade"
                )
                or ""
            ).strip()

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
                        .strip()
                    )

                except (
                    TypeError,
                    ValueError
                ):

                    return None

            modal_price = (
                row.get(
                    "modal_price"
                )
                or row.get(
                    "price"
                )
            )

            if modal_price in (
                None,
                ""
            ):

                continue

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
                    .strip()
                )

            except (
                TypeError,
                ValueError
            ):

                continue

            records.append({
                "crop": crop,
                "commodity": commodity,
                "state": state,
                "district": district,
                "market": market,
                "variety": variety,
                "grade": grade,
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
                        "source"
                    )
                    or "CSV import",
                "source_name":
                    row.get(
                        "source_name"
                    )
                    or "CSV import",
                "source_url":
                    row.get(
                        "source_url"
                    )
                    or "",
            })

        if not records:

            return jsonify({
                "success": False,
                "error": (
                    "No valid market records "
                    "were found in the CSV."
                ),
            }), 400

        result = upsert_market_prices(
            records
        )

        return jsonify({
            "success": bool(
                result.get(
                    "success"
                )
            ),
            "message": (
                "CSV records imported "
                "into MongoDB."
            ),
            "records": result,
        })

    except Exception as exc:

        print(
            "CSV IMPORT ERROR:",
            repr(exc)
        )

        return jsonify({
            "success": False,
            "error": str(exc),
        }), 400


# ============================================================
# DATABASE STATUS
# ============================================================

@app.route(
    "/api/status",
    methods=["GET"]
)
def status():

    health = database_health()

    latest = {
        "onion": clean_record(
            get_latest_price(
                "onion",
                DEFAULT_MARKET
            )
        ),

        "wheat": clean_record(
            get_latest_price(
                "wheat",
                DEFAULT_MARKET
            )
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
                if health.get(
                    "connected"
                )
                else
                "MongoDB not connected"
            ),

        "mongodb_connected":
            health.get(
                "connected",
                False
            ),

        "database_name":
            health.get(
                "database"
            ),

        "collection":
            health.get(
                "collection"
            ),

        "database_records":
            health.get(
                "records",
                0
            ),

        "scraper":
            "NaPanta",

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

    health_data = database_health()

    return jsonify({
        "status":
            "healthy",

        "service":
            "SmartAgri Kopargaon",

        "mongodb_connected":
            health_data.get(
                "connected",
                False
            ),
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
                else
                "MongoDB not connected"
            ),

        "endpoints": [
            "/api/market?crop=onion",
            "/api/market?crop=wheat",

            "/api/market/history?crop=onion",
            "/api/market/history?crop=wheat",

            "/api/market/history/range"
            "?crop=onion"
            "&start=2026-08-01"
            "&end=2026-08-31",

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
        " MongoDB + NaPanta"
    )

    print(
        "=========================================="
    )

    health_data = database_health()

    print(
        "MongoDB connected:",
        health_data.get(
            "connected"
        )
    )

    print(
        "Database:",
        health_data.get(
            "database"
        )
    )

    print(
        "Collection:",
        health_data.get(
            "collection"
        )
    )

    print(
        "Records:",
        health_data.get(
            "records"
        )
    )

    print(
        "=========================================="
    )

    app.run(
        host="0.0.0.0",
        port=PORT,
        debug=False
    )
