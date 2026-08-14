```python
import os
import sys
from datetime import datetime, timezone

import pandas as pd
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import PyMongoError


# ============================================================
# SMARTAGRI KOPARGAON
# HISTORICAL EXCEL -> MONGODB IMPORTER
# ============================================================

# Excel file to import.
DEFAULT_FILE = "Historical_data.csv.xlsx"


# ============================================================
# MONGODB CONFIGURATION
# ============================================================

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


# ============================================================
# SUPPORTED CROPS
# ============================================================

SUPPORTED_CROPS = {
    "onion",
    "wheat",
}


# ============================================================
# HELPERS
# ============================================================

def clean_text(value):
    """
    Convert a value to clean text.
    """
    if pd.isna(value):
        return ""

    return str(value).strip()


def clean_float(value):
    """
    Convert price values into float.
    Handles values such as:
        2100
        "2,100"
        "₹2100"
        "₹ 2,100"
    """

    if pd.isna(value):
        return None

    value = str(value).strip()

    value = value.replace(
        ",",
        ""
    )

    value = value.replace(
        "₹",
        ""
    )

    value = value.strip()

    if not value:
        return None

    try:
        return float(value)

    except ValueError:
        return None


def clean_date(value):
    """
    Convert Excel date into YYYY-MM-DD.
    """

    if pd.isna(value):
        return None

    try:

        date_value = pd.to_datetime(
            value
        )

        return date_value.strftime(
            "%Y-%m-%d"
        )

    except Exception:

        return None


# ============================================================
# CREATE INDEXES
# ============================================================

def create_indexes(collection):

    print(
        "Creating/checking MongoDB indexes..."
    )

    collection.create_index(
        [
            ("crop", ASCENDING),
            ("market", ASCENDING),
            ("data_date", DESCENDING),
        ],
        name="crop_market_date"
    )

    collection.create_index(
        [
            ("crop", ASCENDING),
            ("data_date", DESCENDING),
        ],
        name="crop_date"
    )

    # Prevent duplicate historical records.
    #
    # One record is uniquely identified by:
    # crop + market + data_date + variety
    #
    collection.create_index(
        [
            ("crop", ASCENDING),
            ("market", ASCENDING),
            ("data_date", ASCENDING),
            ("variety", ASCENDING),
        ],
        unique=True,
        name="unique_market_record"
    )

    print(
        "MongoDB indexes ready."
    )


# ============================================================
# READ EXCEL
# ============================================================

def read_excel_file(filename):

    print(
        "Reading Excel file:"
    )

    print(
        f"  {filename}"
    )

    if not os.path.exists(filename):

        raise FileNotFoundError(
            f"Excel file not found: {filename}"
        )

    try:

        dataframe = pd.read_excel(
            filename
        )

    except Exception as exc:

        raise RuntimeError(
            f"Unable to read Excel file: {exc}"
        )

    if dataframe.empty:

        raise RuntimeError(
            "The Excel file contains no data."
        )

    print(
        f"Rows found: {len(dataframe)}"
    )

    print(
        "Columns found:"
    )

    for column in dataframe.columns:

        print(
            f"  - {column}"
        )

    return dataframe


# ============================================================
# NORMALIZE EXCEL COLUMNS
# ============================================================

def normalize_columns(dataframe):

    # Remove accidental spaces from column names.
    #
    # Your file currently contains:
    #
    # "District "
    #
    # This converts it to:
    #
    # "District"
    #
    dataframe.columns = [
        str(column).strip()
        for column in dataframe.columns
    ]

    # Make column matching case-insensitive.
    column_map = {}

    for column in dataframe.columns:

        normalized = (
            str(column)
            .strip()
            .lower()
        )

        column_map[
            normalized
        ] = column

    required_columns = [
        "crop",
        "market",
        "district",
        "state",
        "commodity",
        "min_price",
        "max_price",
        "modal_price",
        "data_date",
    ]

    missing = []

    for required in required_columns:

        if required not in column_map:

            missing.append(
                required
            )

    if missing:

        raise RuntimeError(
            "Missing required columns: "
            + ", ".join(missing)
        )

    # Rename everything to our standard names.
    rename_map = {}

    for normalized, original in column_map.items():

        rename_map[
            original
        ] = normalized

    dataframe = dataframe.rename(
        columns=rename_map
    )

    return dataframe


# ============================================================
# CONVERT EXCEL ROWS TO MONGODB DOCUMENTS
# ============================================================

def convert_records(dataframe):

    records = []

    skipped = 0

    for index, row in dataframe.iterrows():

        excel_row = index + 2

        crop = clean_text(
            row.get(
                "crop"
            )
        ).lower()

        if crop not in SUPPORTED_CROPS:

            print(
                f"Skipping Excel row {excel_row}: "
                f"unsupported crop '{crop}'."
            )

            skipped += 1

            continue

        market = clean_text(
            row.get(
                "market"
            )
        )

        district = clean_text(
            row.get(
                "district"
            )
        )

        state = clean_text(
            row.get(
                "state"
            )
        )

        commodity = clean_text(
            row.get(
                "commodity"
            )
        )

        data_date = clean_date(
            row.get(
                "data_date"
            )
        )

        min_price = clean_float(
            row.get(
                "min_price"
            )
        )

        max_price = clean_float(
            row.get(
                "max_price"
            )
        )

        modal_price = clean_float(
            row.get(
                "modal_price"
            )
        )

        # Required values.
        if not market:

            print(
                f"Skipping Excel row {excel_row}: "
                "market is missing."
            )

            skipped += 1

            continue

        if not data_date:

            print(
                f"Skipping Excel row {excel_row}: "
                "invalid data_date."
            )

            skipped += 1

            continue

        if modal_price is None:

            print(
                f"Skipping Excel row {excel_row}: "
                "modal_price is missing."
            )

            skipped += 1

            continue

        # Our application uses variety as part of the
        # MongoDB uniqueness key.
        #
        # Your current historical file does not have
        # a variety column, so we use an empty string.
        variety = ""

        now = datetime.now(
            timezone.utc
        )

        record = {

            "crop": crop,

            "market": market,

            "district": district,

            "state": state,

            "commodity": commodity,

            "variety": variety,

            "min_price": min_price,

            "max_price": max_price,

            "modal_price": modal_price,

            # Keep "price" as an alias because the
            # existing app.py supports both fields.
            "price": modal_price,

            "data_date": data_date,

            "source": (
                "https://agmarknet.ceda.ashoka.edu.in/api/prices"
            ),

            "source_name": (
                "Agmarknet CEDA API"
            ),

            "scraped_at": now,

            "imported_at": now,

            "updated_at": now,

        }

        records.append(
            record
        )

    print(
        f"Valid records prepared: {len(records)}"
    )

    print(
        f"Rows skipped: {skipped}"
    )

    return records


# ============================================================
# INSERT / UPDATE MONGODB
# ============================================================

def import_records(
    collection,
    records
):

    inserted = 0
    updated = 0
    unchanged = 0

    for record in records:

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

        # Do not overwrite created_at every time.
        update_document = {

            "$set": {

                "crop": record[
                    "crop"
                ],

                "market": record[
                    "market"
                ],

                "district": record[
                    "district"
                ],

                "state": record[
                    "state"
                ],

                "commodity": record[
                    "commodity"
                ],

                "variety": record.get(
                    "variety",
                    ""
                ),

                "min_price": record[
                    "min_price"
                ],

                "max_price": record[
                    "max_price"
                ],

                "modal_price": record[
                    "modal_price"
                ],

                "price": record[
                    "price"
                ],

                "data_date": record[
                    "data_date"
                ],

                "source": record[
                    "source"
                ],

                "source_name": record[
                    "source_name"
                ],

                "scraped_at": record[
                    "scraped_at"
                ],

                "imported_at": record[
                    "imported_at"
                ],

                "updated_at": record[
                    "updated_at"
                ],

            },

            "$setOnInsert": {

                "created_at": record[
                    "imported_at"
                ],

            },

        }

        result = collection.update_one(
            filter_query,
            update_document,
            upsert=True
        )

        if result.upserted_id is not None:

            inserted += 1

            print(
                "INSERTED:",
                record["crop"],
                record["data_date"],
                record["modal_price"]
            )

        elif result.modified_count > 0:

            updated += 1

            print(
                "UPDATED:",
                record["crop"],
                record["data_date"],
                record["modal_price"]
            )

        else:

            unchanged += 1

            print(
                "UNCHANGED:",
                record["crop"],
                record["data_date"],
                record["modal_price"]
            )

    return {
        "inserted": inserted,
        "updated": updated,
        "unchanged": unchanged,
        "total": len(records),
    }


# ============================================================
# DISPLAY IMPORTED DATA
# ============================================================

def show_latest_data(collection):

    print()
    print(
        "=========================================="
    )

    print(
        "LATEST MONGODB DATA"
    )

    print(
        "=========================================="
    )

    for crop in sorted(
        SUPPORTED_CROPS
    ):

        documents = list(
            collection.find(
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
                    )
                ]
            )
            .limit(10)
        )

        print()
        print(
            f"{crop.upper()}:"
        )

        if not documents:

            print(
                "  No records."
            )

            continue

        for document in documents:

            print(
                f"  {document.get('data_date')} "
                f"| {document.get('market')} "
                f"| min={document.get('min_price')} "
                f"| max={document.get('max_price')} "
                f"| modal={document.get('modal_price')}"
            )


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print(
        "=========================================="
    )

    print(
        " SmartAgri Kopargaon"
    )

    print(
        " Historical Excel -> MongoDB Import"
    )

    print(
        "=========================================="
    )

    print(
        f"Database: {MONGODB_DB_NAME}"
    )

    print(
        f"Collection: {MONGODB_COLLECTION}"
    )

    print(
        "=========================================="
    )

    # --------------------------------------------------------
    # MongoDB URI check
    # --------------------------------------------------------

    if not MONGODB_URI:

        print()
        print(
            "ERROR: MONGODB_URI is not configured."
        )

        print()
        print(
            "Set MONGODB_URI before running this script."
        )

        sys.exit(1)

    # --------------------------------------------------------
    # Excel filename
    # --------------------------------------------------------

    filename = DEFAULT_FILE

    if len(sys.argv) > 1:

        filename = sys.argv[1]

    # --------------------------------------------------------
    # Connect MongoDB
    # --------------------------------------------------------

    mongo_client = None

    try:

        print()
        print(
            "Connecting to MongoDB..."
        )

        mongo_client = MongoClient(
            MONGODB_URI,
            serverSelectionTimeoutMS=10000
        )

        mongo_client.admin.command(
            "ping"
        )

        print(
            "MongoDB connection successful."
        )

        database = mongo_client[
            MONGODB_DB_NAME
        ]

        collection = database[
            MONGODB_COLLECTION
        ]

        # ----------------------------------------------------
        # Indexes
        # ----------------------------------------------------

        create_indexes(
            collection
        )

        # ----------------------------------------------------
        # Read Excel
        # ----------------------------------------------------

        dataframe = read_excel_file(
            filename
        )

        # ----------------------------------------------------
        # Normalize columns
        # ----------------------------------------------------

        dataframe = normalize_columns(
            dataframe
        )

        # ----------------------------------------------------
        # Convert records
        # ----------------------------------------------------

        records = convert_records(
            dataframe
        )

        if not records:

            print()
            print(
                "ERROR: No valid records to import."
            )

            sys.exit(1)

        # ----------------------------------------------------
        # Import
        # ----------------------------------------------------

        print()
        print(
            "Importing records into MongoDB..."
        )

        result = import_records(
            collection,
            records
        )

        # ----------------------------------------------------
        # Show result
        # ----------------------------------------------------

        print()
        print(
            "=========================================="
        )

        print(
            "IMPORT COMPLETE"
        )

        print(
            "=========================================="
        )

        print(
            f"Inserted : {result['inserted']}"
        )

        print(
            f"Updated  : {result['updated']}"
        )

        print(
            f"Unchanged: {result['unchanged']}"
        )

        print(
            f"Total    : {result['total']}"
        )

        # ----------------------------------------------------
        # Verify
        # ----------------------------------------------------

        show_latest_data(
            collection
        )

        print()
        print(
            "MongoDB historical market data is ready."
        )

    except PyMongoError as exc:

        print()
        print(
            "MONGODB ERROR:"
        )

        print(
            repr(exc)
        )

        sys.exit(1)

    except Exception as exc:

        print()
        print(
            "IMPORT ERROR:"
        )

        print(
            repr(exc)
        )

        sys.exit(1)

    finally:

        if mongo_client is not None:

            mongo_client.close()

            print()
            print(
                "MongoDB connection closed."
            )


if __name__ == "__main__":

    main()
```
