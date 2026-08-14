import re
from datetime import datetime
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


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
    "Accept-Language": "en-US,en;q=0.9",
}


def clean_text(value):
    if value is None:
        return ""

    return " ".join(
        str(value).replace("\xa0", " ").split()
    )


def parse_price(value):
    if value is None:
        return None

    text = clean_text(value)

    # Remove ₹, Rs, commas and other non-numeric characters.
    text = text.replace(",", "")
    text = text.replace("₹", "")
    text = text.replace("Rs.", "")
    text = text.replace("Rs", "")

    match = re.search(r"\d+(?:\.\d+)?", text)

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

    # Try extracting a date from larger text.
    match = re.search(
        r"(\d{1,2})\s+"
        r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"
        r"\s+(\d{4})",
        value,
        re.IGNORECASE,
    )

    if match:
        try:
            parsed = datetime.strptime(
                match.group(0),
                "%d %b %Y",
            )

            return parsed.strftime("%Y-%m-%d")

        except ValueError:
            pass

    return None


def fetch_page(crop):
    if crop not in CROP_URLS:
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
        timeout=20,
    )

    response.raise_for_status()

    return response.text, url


def extract_from_tables(html, crop):
    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    candidates = []

    tables = soup.find_all("table")

    for table in tables:

        rows = table.find_all("tr")

        headers = []

        if rows:

            header_cells = rows[0].find_all(
                ["th", "td"]
            )

            headers = [
                clean_text(cell.get_text(" ", strip=True)).lower()
                for cell in header_cells
            ]

        # We are especially interested in tables containing
        # maximum / average / minimum / date information.
        header_text = " ".join(headers)

        table_has_price_fields = (
            "maximum price" in header_text
            and "average price" in header_text
            and "minimum price" in header_text
        )

        for row in rows:

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

            if len(values) < 4:
                continue

            row_text = " ".join(values).lower()

            # Kopargaon verification.
            if "kopargaon" not in row_text:
                continue

            # Commodity verification.
            if crop.lower() not in row_text:
                continue

            # --------------------------------------------------
            # Preferred table format:
            #
            # Date | District | Market | Commodity | Variety |
            # Maximum | Average | Minimum
            # --------------------------------------------------

            data_date = None
            max_price = None
            avg_price = None
            min_price = None

            for value in values:

                possible_date = parse_date(value)

                if possible_date:
                    data_date = possible_date

            # Find prices from the row.
            numeric_prices = []

            for value in values:
                price = parse_price(value)

                if price is not None:
                    numeric_prices.append(price)

            # The Kopargaon table normally contains three
            # market prices. We need to avoid treating dates
            # as prices, so only numeric price-looking cells
            # are considered.
            price_values = []

            for value in values:

                if "₹" in value or "rs" in value.lower():

                    price = parse_price(value)

                    if price is not None:
                        price_values.append(price)

            if len(price_values) >= 3:

                # Table order is normally:
                # Maximum, Average, Minimum
                max_price = price_values[-3]
                avg_price = price_values[-2]
                min_price = price_values[-1]

            # If exact column mapping exists, use it.
            if table_has_price_fields:

                normalized_headers = [
                    h.replace(" ", "")
                    for h in headers
                ]

                try:

                    max_index = next(
                        i
                        for i, h in enumerate(normalized_headers)
                        if "maximumprice" in h
                    )

                    avg_index = next(
                        i
                        for i, h in enumerate(normalized_headers)
                        if "averageprice" in h
                    )

                    min_index = next(
                        i
                        for i, h in enumerate(normalized_headers)
                        if "minimumprice" in h
                    )

                    if max_index < len(values):
                        max_price = parse_price(
                            values[max_index]
                        )

                    if avg_index < len(values):
                        avg_price = parse_price(
                            values[avg_index]
                        )

                    if min_index < len(values):
                        min_price = parse_price(
                            values[min_index]
                        )

                except StopIteration:
                    pass

            if avg_price is None:
                continue

            candidates.append(
                {
                    "crop": crop,
                    "market": "Kopargaon",
                    "price": avg_price,
                    "modal_price": avg_price,
                    "min_price": min_price,
                    "max_price": max_price,
                    "data_date": data_date,
                    "source": "NaPanta",
                    "source_url": urljoin(
                        BASE_URL,
                        CROP_URLS[crop]
                    ),
                }
            )

    return candidates


def extract_from_page_text(html, crop):
    """
    Backup parser.

    Used if table extraction fails but the page's text
    contains the summary values.
    """

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    text = clean_text(
        soup.get_text(" ", strip=True)
    )

    lower_text = text.lower()

    if "kopargaon" not in lower_text:
        return None

    if crop.lower() not in lower_text:
        return None

    # Example:
    # average price for Onion is ₹2275/Quintal
    average_match = re.search(
        r"average price for .*?"
        r"is\s*₹?\s*([\d,]+)",
        text,
        re.IGNORECASE,
    )

    minimum_match = re.search(
        r"lowest market price is\s*₹?\s*([\d,]+)",
        text,
        re.IGNORECASE,
    )

    maximum_match = re.search(
        r"Highest market price is\s*₹?\s*([\d,]+)",
        text,
        re.IGNORECASE,
    )

    date_match = re.search(
        r"Price updated:\s*"
        r"(\d{1,2}\s+[A-Za-z]{3}\s+\d{4})",
        text,
        re.IGNORECASE,
    )

    if not average_match:
        return None

    average = parse_price(
        average_match.group(1)
    )

    minimum = (
        parse_price(minimum_match.group(1))
        if minimum_match
        else None
    )

    maximum = (
        parse_price(maximum_match.group(1))
        if maximum_match
        else None
    )

    data_date = (
        parse_date(date_match.group(1))
        if date_match
        else None
    )

    if average is None:
        return None

    return {
        "crop": crop,
        "market": "Kopargaon",
        "price": average,
        "modal_price": average,
        "min_price": minimum,
        "max_price": maximum,
        "data_date": data_date,
        "source": "NaPanta",
        "source_url": urljoin(
            BASE_URL,
            CROP_URLS[crop]
        ),
    }


def scrape_crop(crop):
    """
    Main scraper function.

    Supports:
        onion
        wheat
    """

    crop = crop.lower().strip()

    if crop not in CROP_URLS:
        raise ValueError(
            "Supported crops are onion and wheat"
        )

    html, url = fetch_page(crop)

    candidates = extract_from_tables(
        html,
        crop
    )

    if candidates:

        # Remove candidates without dates when possible.
        dated = [
            item
            for item in candidates
            if item.get("data_date")
        ]

        if dated:
            candidates = dated

            candidates.sort(
                key=lambda item: item["data_date"],
                reverse=True
            )

        result = candidates[0]

        result["source_url"] = url

        return result

    # Backup extraction.
    result = extract_from_page_text(
        html,
        crop
    )

    if result:
        result["source_url"] = url
        return result

    raise RuntimeError(
        f"Could not extract {crop} "
        f"market data from NaPanta."
    )


def scrape_all():
    """
    Scrape both crops.
    """

    results = {}

    for crop in ["onion", "wheat"]:

        try:

            results[crop] = scrape_crop(
                crop
            )

        except Exception as exc:

            results[crop] = {
                "crop": crop,
                "success": False,
                "error": str(exc),
            }

    return results


if __name__ == "__main__":

    print("=" * 60)
    print("SmartAgri Kopargaon Scraper")
    print("=" * 60)

    results = scrape_all()

    for crop, result in results.items():

        print()
        print(crop.upper())

        if result.get("success") is False:

            print(
                "ERROR:",
                result["error"]
            )

        else:

            print(
                "Price:",
                result.get("price")
            )

            print(
                "Minimum:",
                result.get("min_price")
            )

            print(
                "Maximum:",
                result.get("max_price")
            )

            print(
                "Date:",
                result.get("data_date")
            )

            print(
                "Source:",
                result.get("source")
            )

    print()
    print("=" * 60)
