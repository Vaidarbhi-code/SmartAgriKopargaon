import re
import time
from datetime import datetime, timezone
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


# ============================================================
# SMARTAGRI KOPARGAON
# MARKET DATA SCRAPER
# ============================================================

BASE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/151.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,"
        "application/xml;q=0.9,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


SOURCE_URLS = {
    "onion": (
        "https://www.napanta.com/"
        "commodity-agri-market/maharashtra/onion/kopargaon"
    ),
    "wheat": (
        "https://www.napanta.com/"
        "commodity-agri-market/maharashtra/wheat/kopargaon"
    ),
}


REQUEST_TIMEOUT = 20


# ============================================================
# HELPERS
# ============================================================

def clean_text(value):
    if value is None:
        return ""

    return re.sub(
        r"\s+",
        " ",
        str(value)
    ).strip()


def parse_price(value):
    if value is None:
        return None

    text = clean_text(value)

    text = (
        text
        .replace("₹", "")
        .replace("Rs.", "")
        .replace("Rs", "")
        .replace(",", "")
    )

    match = re.search(
        r"-?\d+(?:\.\d+)?",
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

    text = clean_text(value)

    formats = [
        "%d %b %Y",
        "%d-%b-%Y",
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%Y-%m-%d",
        "%d %B %Y",
        "%d/%m/%y",
        "%d-%m-%y",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(
                text,
                fmt
            ).strftime("%Y-%m-%d")
        except ValueError:
            continue

    # Sometimes text contains extra information.
    match = re.search(
        r"(\d{1,2}[-/ ](?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|"
        r"Sep|Oct|Nov|Dec)[a-z]*[-/ ]\d{4})",
        text,
        re.IGNORECASE
    )

    if match:
        candidate = match.group(1)

        for fmt in [
            "%d-%b-%Y",
            "%d %b %Y",
            "%d-%B-%Y",
            "%d %B %Y",
        ]:
            try:
                return datetime.strptime(
                    candidate,
                    fmt
                ).strftime("%Y-%m-%d")
            except ValueError:
                continue

    return None


def normalize_header(value):
    return (
        clean_text(value)
        .lower()
        .replace("\n", " ")
        .replace("  ", " ")
    )


# ============================================================
# TABLE DETECTION
# ============================================================

def find_market_table(soup):
    """
    Find the table containing the market-price columns.

    Expected columns include combinations of:
        Last Updated Date
        District
        Market
        Commodity
        Variety
        Maximum Price
        Average Price
        Minimum Price
    """

    for table in soup.find_all("table"):

        headers = []

        header_row = table.find("tr")

        if header_row:
            for cell in header_row.find_all(
                ["th", "td"]
            ):
                headers.append(
                    normalize_header(
                        cell.get_text(" ", strip=True)
                    )
                )

        joined = " | ".join(headers)

        required_signals = [
            "market",
            "commodity",
            "maximum price",
            "minimum price",
        ]

        matches = sum(
            1
            for signal in required_signals
            if signal in joined
        )

        if matches >= 3:
            return table

    return None


# ============================================================
# TABLE PARSER
# ============================================================

def parse_market_table(
    table,
    crop,
    source_url
):
    rows = table.find_all("tr")

    if not rows:
        return []

    header_cells = rows[0].find_all(
        ["th", "td"]
    )

    headers = [
        normalize_header(
            cell.get_text(" ", strip=True)
        )
        for cell in header_cells
    ]

    column_map = {}

    for index, header in enumerate(headers):

        if "last updated" in header:
            column_map["date"] = index

        elif header == "district":
            column_map["district"] = index

        elif header == "market":
            column_map["market"] = index

        elif header == "commodity":
            column_map["commodity"] = index

        elif header == "variety":
            column_map["variety"] = index

        elif (
            "maximum price" in header
            or "max price" in header
        ):
            column_map["max_price"] = index

        elif (
            "average price" in header
            or "modal price" in header
            or "avg price" in header
        ):
            column_map["modal_price"] = index

        elif (
            "minimum price" in header
            or "min price" in header
        ):
            column_map["min_price"] = index

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

        if len(values) < 5:
            continue

        def get_value(key):
            index = column_map.get(key)

            if index is None:
                return ""

            if index >= len(values):
                return ""

            return values[index]

        market = get_value("market")
        commodity = get_value("commodity")

        if not market:
            continue

        # Make sure we really got Kopargaon.
        if "kopargaon" not in market.lower():
            continue

        data_date = parse_date(
            get_value("date")
        )

        min_price = parse_price(
            get_value("min_price")
        )

        max_price = parse_price(
            get_value("max_price")
        )

        modal_price = parse_price(
            get_value("modal_price")
        )

        if modal_price is None:

            # If no average/modal column exists,
            # use the midpoint as a last parsing fallback.
            if (
                min_price is not None
                and max_price is not None
            ):
                modal_price = (
                    min_price + max_price
                ) / 2

        if modal_price is None:
            continue

        if not data_date:
            continue

        record = {
            "crop": crop,
            "market": market,
            "district": get_value("district"),
            "commodity": commodity,
            "variety": get_value("variety"),
            "min_price": min_price,
            "max_price": max_price,
            "modal_price": modal_price,
            "price": modal_price,
            "data_date": data_date,
            "source": source_url,
            "source_name": "Napanta",
            "scraped_at": datetime.now(
                timezone.utc
            ),
        }

        records.append(record)

    return records


# ============================================================
# SINGLE CROP SCRAPER
# ============================================================

def scrape_crop(crop):
    crop = crop.lower().strip()

    if crop not in SOURCE_URLS:
        raise ValueError(
            f"Unsupported crop: {crop}"
        )

    url = SOURCE_URLS[crop]

    response = requests.get(
        url,
        headers=BASE_HEADERS,
        timeout=REQUEST_TIMEOUT
    )

    response.raise_for_status()

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    table = find_market_table(soup)

    if table is None:
        raise RuntimeError(
            f"Market table was not found for {crop}"
        )

    records = parse_market_table(
        table,
        crop,
        url
    )

    if not records:
        raise RuntimeError(
            f"No Kopargaon {crop} records were found"
        )

    # Newest first.
    records.sort(
        key=lambda row: row["data_date"],
        reverse=True
    )

    return records


# ============================================================
# ALL CROPS
# ============================================================

def scrape_all():
    results = {}

    for crop in SOURCE_URLS:

        try:

            records = scrape_crop(crop)

            results[crop] = {
                "success": True,
                "count": len(records),
                "records": records,
                "error": None,
            }

        except Exception as exc:

            results[crop] = {
                "success": False,
                "count": 0,
                "records": [],
                "error": str(exc),
            }

        # Small delay between sources.
        time.sleep(1)

    return results


# ============================================================
# COMMAND LINE TEST
# ============================================================

if __name__ == "__main__":

    print(
        "=========================================="
    )
    print(
        " SmartAgri Kopargaon Scraper"
    )
    print(
        "=========================================="
    )

    results = scrape_all()

    for crop, result in results.items():

        print()
        print(
            f"{crop.upper()}:"
        )

        if not result["success"]:

            print(
                "ERROR:",
                result["error"]
            )

            continue

        print(
            "Records:",
            result["count"]
        )

        for record in result["records"][:5]:

            print(
                record["data_date"],
                "|",
                record["market"],
                "|",
                record["modal_price"]
            )

    print()
    print(
        "=========================================="
    )
