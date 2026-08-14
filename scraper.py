import re
from datetime import datetime
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


# ============================================================
# SMARTAGRI KOPARGAON
# NaPanta Daily Market Price Scraper
# ============================================================

BASE_URL = "https://www.napanta.com"

CROP_URLS = {
    "onion": "/commodity-agri-market/maharashtra/onion/kopargaon",
    "wheat": "/commodity-agri-market/maharashtra/wheat/kopargaon",
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/151.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,"
        "application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive",
}


SUPPORTED_CROPS = {
    "onion",
    "wheat",
}


# ============================================================
# TEXT HELPERS
# ============================================================

def clean_text(value):
    if value is None:
        return ""

    return " ".join(
        str(value)
        .replace("\xa0", " ")
        .split()
    )


def parse_price(value):
    if value is None:
        return None

    text = clean_text(value)

    text = (
        text
        .replace(",", "")
        .replace("₹", "")
        .replace("Rs.", "")
        .replace("Rs", "")
    )

    match = re.search(
        r"\d+(?:\.\d+)?",
        text
    )

    if not match:
        return None

    try:
        return float(match.group(0))
    except ValueError:
        return None


def parse_date(value):
    if not value:
        return None

    value = clean_text(value)

    formats = [
        "%d %b %Y",
        "%d %B %Y",
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%Y-%m-%d",
        "%d %b, %Y",
        "%d %B, %Y",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(
                value,
                fmt
            ).strftime("%Y-%m-%d")
        except ValueError:
            continue

    match = re.search(
        r"\b"
        r"(\d{1,2})\s+"
        r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"
        r"\s+(\d{4})"
        r"\b",
        value,
        re.IGNORECASE,
    )

    if match:
        try:
            parsed = datetime.strptime(
                match.group(0),
                "%d %b %Y"
            )

            return parsed.strftime(
                "%Y-%m-%d"
            )

        except ValueError:
            pass

    return None


# ============================================================
# HTTP
# ============================================================

def fetch_page(crop):
    crop = crop.lower().strip()

    if crop not in SUPPORTED_CROPS:
        raise ValueError(
            f"Unsupported crop: {crop}"
        )

    url = urljoin(
        BASE_URL,
        CROP_URLS[crop]
    )

    response = requests.get(
        url,
        headers=HEADERS,
        timeout=30
    )

    response.raise_for_status()

    return response.text, url


# ============================================================
# HEADER NORMALIZATION
# ============================================================

def normalize_header(value):
    value = clean_text(value).lower()

    value = (
        value
        .replace("/", " ")
        .replace("-", " ")
        .replace("_", " ")
        .replace("₹", "")
    )

    return re.sub(
        r"\s+",
        " ",
        value
    ).strip()


def find_column_index(headers, patterns):
    for index, header in enumerate(headers):

        normalized = normalize_header(
            header
        )

        for pattern in patterns:

            if pattern in normalized:
                return index

    return None


# ============================================================
# TABLE PARSER
# ============================================================

def parse_table(table, crop, source_url):
    rows = table.find_all("tr")

    if not rows:
        return []

    header_cells = rows[0].find_all(
        ["th", "td"]
    )

    headers = [
        clean_text(
            cell.get_text(
                " ",
                strip=True
            )
        )
        for cell in header_cells
    ]

    normalized_headers = [
        normalize_header(header)
        for header in headers
    ]

    date_index = find_column_index(
        normalized_headers,
        [
            "date",
            "arrival date",
            "arrival",
        ]
    )

    market_index = find_column_index(
        normalized_headers,
        [
            "market",
            "mandi",
        ]
    )

    district_index = find_column_index(
        normalized_headers,
        [
            "district",
        ]
    )

    commodity_index = find_column_index(
        normalized_headers,
        [
            "commodity",
            "crop",
        ]
    )

    variety_index = find_column_index(
        normalized_headers,
        [
            "variety",
        ]
    )

    grade_index = find_column_index(
        normalized_headers,
        [
            "grade",
        ]
    )

    max_index = find_column_index(
        normalized_headers,
        [
            "maximum price",
            "max price",
            "maximum",
            "max",
        ]
    )

    avg_index = find_column_index(
        normalized_headers,
        [
            "average price",
            "avg price",
            "average",
            "modal price",
            "modal",
        ]
    )

    min_index = find_column_index(
        normalized_headers,
        [
            "minimum price",
            "min price",
            "minimum",
            "min",
        ]
    )

    records = []

    for row in rows[1:]:

        cells = row.find_all(
            ["td", "th"]
        )

        values = [
            clean_text(
                cell.get_text(
                    " ",
                    strip=True
                )
            )
            for cell in cells
        ]

        if not values:
            continue

        row_text = " ".join(
            values
        )

        row_lower = row_text.lower()

        # We only want Kopargaon records.
        if (
            "kopargaon"
            not in row_lower
        ):
            continue

        # Verify crop where possible.
        if (
            crop.lower()
            not in row_lower
        ):
            # Some tables omit commodity from
            # individual rows. That is acceptable
            # when the page itself is crop-specific.
            pass

        def get_value(index):
            if (
                index is not None
                and index < len(values)
            ):
                return values[index]

            return ""

        # ----------------------------------------------------
        # DATE
        # ----------------------------------------------------

        data_date = None

        if date_index is not None:

            data_date = parse_date(
                get_value(date_index)
            )

        if data_date is None:

            for value in values:

                possible_date = parse_date(
                    value
                )

                if possible_date:
                    data_date = possible_date
                    break

        # Without a date this record is not useful
        # for our historical MongoDB dataset.
        if data_date is None:
            continue

        # ----------------------------------------------------
        # MARKET
        # ----------------------------------------------------

        market = (
            get_value(market_index)
            if market_index is not None
            else "Kopargaon"
        )

        if not market:
            market = "Kopargaon"

        # ----------------------------------------------------
        # DISTRICT
        # ----------------------------------------------------

        district = (
            get_value(district_index)
            if district_index is not None
            else "Ahilyanagar"
        )

        # ----------------------------------------------------
        # COMMODITY
        # ----------------------------------------------------

        commodity = (
            get_value(commodity_index)
            if commodity_index is not None
            else crop.title()
        )

        if not commodity:
            commodity = crop.title()

        # ----------------------------------------------------
        # VARIETY
        # ----------------------------------------------------

        variety = (
            get_value(variety_index)
            if variety_index is not None
            else ""
        )

        # ----------------------------------------------------
        # GRADE
        # ----------------------------------------------------

        grade = (
            get_value(grade_index)
            if grade_index is not None
            else ""
        )

        # ----------------------------------------------------
        # PRICES
        # ----------------------------------------------------

        min_price = None
        max_price = None
        modal_price = None

        if min_index is not None:
            min_price = parse_price(
                get_value(min_index)
            )

        if max_index is not None:
            max_price = parse_price(
                get_value(max_index)
            )

        if avg_index is not None:
            modal_price = parse_price(
                get_value(avg_index)
            )

        # ----------------------------------------------------
        # FALLBACK PRICE EXTRACTION
        # ----------------------------------------------------

        if (
            min_price is None
            or max_price is None
            or modal_price is None
        ):

            price_values = []

            for value in values:

                lower_value = value.lower()

                if (
                    "₹" in value
                    or "rs" in lower_value
                    or "quintal" in lower_value
                ):

                    price = parse_price(
                        value
                    )

                    if price is not None:
                        price_values.append(
                            price
                        )

            if len(price_values) >= 3:

                # NaPanta commonly presents:
                #
                # Maximum | Average | Minimum
                #
                # We use the last three detected
                # price values.
                fallback = (
                    price_values[-3:]
                )

                if max_price is None:
                    max_price = fallback[0]

                if modal_price is None:
                    modal_price = fallback[1]

                if min_price is None:
                    min_price = fallback[2]

        # Sometimes only the average/modal price
        # is available.
        if modal_price is None:

            candidates = []

            for value in values:

                price = parse_price(
                    value
                )

                if price is not None:
                    candidates.append(
                        price
                    )

            if candidates:

                modal_price = candidates[-1]

        if modal_price is None:
            continue

        # ----------------------------------------------------
        # RECORD
        # ----------------------------------------------------

        record = {
            "crop": crop,
            "market": clean_text(
                market
            ),
            "district": clean_text(
                district
            ),
            "state": "Maharashtra",
            "commodity": clean_text(
                commodity
            ),
            "variety": clean_text(
                variety
            ),
            "grade": clean_text(
                grade
            ),
            "min_price": min_price,
            "max_price": max_price,
            "modal_price": modal_price,
            "price": modal_price,
            "data_date": data_date,
            "source": "NaPanta",
            "source_name": "NaPanta",
            "source_url": source_url,
        }

        records.append(
            record
        )

    return records


# ============================================================
# PAGE-TEXT FALLBACK
# ============================================================

def extract_summary_from_page(
    html,
    crop,
    source_url
):
    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    text = clean_text(
        soup.get_text(
            " ",
            strip=True
        )
    )

    lower_text = text.lower()

    if "kopargaon" not in lower_text:
        return []

    if crop.lower() not in lower_text:
        return []

    average_match = re.search(
        r"average price for .*?"
        r"is\s*₹?\s*([\d,]+)",
        text,
        re.IGNORECASE
    )

    minimum_match = re.search(
        r"(?:lowest|minimum)"
        r".*?"
        r"(?:price|market price)"
        r".*?"
        r"₹?\s*([\d,]+)",
        text,
        re.IGNORECASE
    )

    maximum_match = re.search(
        r"(?:highest|maximum)"
        r".*?"
        r"(?:price|market price)"
        r".*?"
        r"₹?\s*([\d,]+)",
        text,
        re.IGNORECASE
    )

    date_match = re.search(
        r"(?:Price updated|updated)"
        r"\s*:?\s*"
        r"(\d{1,2}\s+"
        r"[A-Za-z]{3,9}"
        r"\s+\d{4})",
        text,
        re.IGNORECASE
    )

    if not average_match:
        return []

    modal_price = parse_price(
        average_match.group(1)
    )

    min_price = (
        parse_price(
            minimum_match.group(1)
        )
        if minimum_match
        else None
    )

    max_price = (
        parse_price(
            maximum_match.group(1)
        )
        if maximum_match
        else None
    )

    data_date = (
        parse_date(
            date_match.group(1)
        )
        if date_match
        else None
    )

    if (
        modal_price is None
        or data_date is None
    ):
        return []

    return [
        {
            "crop": crop,
            "market": "Kopargaon",
            "district": "Ahilyanagar",
            "state": "Maharashtra",
            "commodity": crop.title(),
            "variety": "",
            "grade": "",
            "min_price": min_price,
            "max_price": max_price,
            "modal_price": modal_price,
            "price": modal_price,
            "data_date": data_date,
            "source": "NaPanta",
            "source_name": "NaPanta",
            "source_url": source_url,
        }
    ]


# ============================================================
# DEDUPLICATION
# ============================================================

def deduplicate_records(records):
    unique = {}

    for record in records:

        key = (
            record.get("crop", ""),
            record.get("market", ""),
            record.get("data_date", ""),
            record.get("variety", ""),
        )

        unique[key] = record

    return list(
        unique.values()
    )


# ============================================================
# MAIN EXTRACTION
# ============================================================

def extract_daily_records(
    html,
    crop,
    source_url
):
    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    records = []

    # --------------------------------------------------------
    # TABLES
    # --------------------------------------------------------

    for table in soup.find_all(
        "table"
    ):

        try:

            table_records = parse_table(
                table,
                crop,
                source_url
            )

            records.extend(
                table_records
            )

        except Exception as exc:

            print(
                "Table parsing warning:",
                repr(exc)
            )

    records = deduplicate_records(
        records
    )

    # --------------------------------------------------------
    # FALLBACK
    # --------------------------------------------------------

    if not records:

        records = (
            extract_summary_from_page(
                html,
                crop,
                source_url
            )
        )

    records = deduplicate_records(
        records
    )

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
# PUBLIC API
# ============================================================

def scrape_crop(crop):
    """
    Scrape all available daily records for one crop.

    Supported:
        onion
        wheat

    Returns:
        list[dict]
    """

    crop = crop.lower().strip()

    if crop not in SUPPORTED_CROPS:

        raise ValueError(
            "Supported crops are onion and wheat"
        )

    html, source_url = fetch_page(
        crop
    )

    records = extract_daily_records(
        html,
        crop,
        source_url
    )

    if not records:

        raise RuntimeError(
            f"Could not extract daily "
            f"{crop} market data from NaPanta."
        )

    print(
        f"{crop}: extracted "
        f"{len(records)} daily records."
    )

    if records:

        print(
            f"{crop}: latest date = "
            f"{records[0].get('data_date')}"
        )

    return records


def scrape_all():
    """
    Scrape all supported crops.

    Returns:
        {
            "onion": [...],
            "wheat": [...]
        }
    """

    results = {}

    for crop in [
        "onion",
        "wheat",
    ]:

        try:

            results[crop] = scrape_crop(
                crop
            )

        except Exception as exc:

            print(
                f"ERROR scraping {crop}:",
                repr(exc)
            )

            results[crop] = []

    return results


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    print("=" * 70)
    print(
        "SmartAgri Kopargaon"
    )
    print(
        "NaPanta Daily Market Scraper"
    )
    print("=" * 70)

    results = scrape_all()

    for crop, records in results.items():

        print()
        print(
            f"{crop.upper()} "
            f"({len(records)} records)"
        )

        for record in records[:10]:

            print(
                record
            )

    print()
    print("=" * 70)
