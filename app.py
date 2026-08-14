from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS
import requests
from datetime import datetime, timezone
import os
import re


# ============================================================
# SMARTAGRI KOPARGAON
# ============================================================
# Live/latest external market data
#
# Supported crops:
#   - Onion
#   - Wheat
#
# Target market:
#   Kopargaon APMC
#   Ahilyanagar, Maharashtra
#
# No hardcoded prices.
# No fallback prices.
# ============================================================


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(
    __name__,
    static_folder=BASE_DIR
)

CORS(app)


# ============================================================
# MARKET SOURCE
# ============================================================

BASE_URL = (
    "https://mandipulse.com/"
    "mandi/maharashtra-ahilyanagar-kopargaon-apmc"
)

CROP_URLS = {
    "onion": f"{BASE_URL}/onion",
    "wheat": f"{BASE_URL}/wheat"
}


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/151.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,"
        "application/xml;q=0.9,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


# ============================================================
# TARGET MARKET
# ============================================================

MARKET_NAME = "Kopargaon APMC"
DISTRICT_NAME = "Ahilyanagar"
STATE_NAME = "Maharashtra"


# ============================================================
# CROP NAMES
# ============================================================

CROP_NAMES = {
    "onion": "Onion",
    "wheat": "Wheat"
}


# ============================================================
# NUMBER PARSER
# ============================================================

def extract_number(value):
    """
    Extract the first numeric value from text.

    Examples:
        ₹2,500
        2500
        Rs. 2500
    """

    if value is None:
        return None

    text = str(value)

    text = text.replace(",", "")

    match = re.search(
        r"\d+(?:\.\d+)?",
        text
    )

    if not match:
        return None

    number = float(match.group(0))

    if number.is_integer():
        return int(number)

    return number


# ============================================================
# FETCH MARKET PAGE
# ============================================================

def fetch_market_page(crop):

    if crop not in CROP_URLS:

        raise ValueError(
            "Unsupported crop. "
            "Use onion or wheat."
        )

    url = CROP_URLS[crop]

    print()
    print("=" * 60)
    print("SMARTAGRI MARKET REQUEST")
    print("=" * 60)
    print("Crop:", crop)
    print("URL:", url)
    print("=" * 60)

    response = requests.get(
        url,
        headers=HEADERS,
        timeout=30
    )

    print(
        "HTTP STATUS:",
        response.status_code
    )

    response.raise_for_status()

    return response.text, url


# ============================================================
# CLEAN TEXT
# ============================================================

def clean_text(text):

    if not text:
        return ""

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


# ============================================================
# FIND DATE
# ============================================================

def find_date(text):

    patterns = [

        r"Updated\s+on\s*:\s*"
        r"([0-9]{1,2}\s+[A-Za-z]{3}\s+[0-9]{4})",

        r"Updated\s*:\s*"
        r"([0-9]{1,2}\s+[A-Za-z]{3}\s+[0-9]{4})",

        r"([0-9]{1,2}\s+[A-Za-z]{3}\s+[0-9]{4})"
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:
            return match.group(1)

    return None


# ============================================================
# FIND MIN/MAX PRICE
# ============================================================

def find_min_max(text):

    patterns = [

        r"Min\s*:\s*₹?\s*([\d,]+)"
        r"\s*\|\s*"
        r"Max\s*:\s*₹?\s*([\d,]+)",

        r"Min\s*:\s*₹?\s*([\d,]+)"
        r"\s+Max\s*:\s*₹?\s*([\d,]+)",

        r"Minimum\s*:\s*₹?\s*([\d,]+)"
        r".{0,50}?"
        r"Maximum\s*:\s*₹?\s*([\d,]+)"
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:

            min_price = extract_number(
                match.group(1)
            )

            max_price = extract_number(
                match.group(2)
            )

            if (
                min_price is not None
                and max_price is not None
            ):

                return (
                    min_price,
                    max_price
                )

    return None, None


# ============================================================
# FIND MODAL PRICE
# ============================================================

def find_modal_price(text, crop):

    crop_name = CROP_NAMES[crop]

    patterns = [

        # Example:
        # Onion Price Today ₹2500/Quintal
        rf"{crop_name}\s+Price\s+Today"
        r".{0,150}?"
        r"₹\s*([\d,]+)"
        r"\s*/\s*Quintal",

        # Generic:
        # ₹2500/Quintal
        r"₹\s*([\d,]+)"
        r"\s*/\s*Quintal",

        # Rs. 2500 / Quintal
        r"(?:Rs\.?|INR)\s*"
        r"([\d,]+)"
        r"\s*/\s*Quintal"
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:

            value = extract_number(
                match.group(1)
            )

            if value is not None:
                return value

    return None


# ============================================================
# FIND VARIETY
# ============================================================

def find_variety(text):

    patterns = [

        r"Variety\s*:\s*"
        r"([^|]+)",

        r"Variety\s+"
        r"([A-Za-z0-9 ._-]+)"
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:

            value = match.group(1).strip()

            if value:
                return value

    return ""


# ============================================================
# FIND GRADE
# ============================================================

def find_grade(text):

    patterns = [

        r"Grade\s*:\s*"
        r"([^|]+)",

        r"Grade\s+"
        r"([A-Za-z0-9 ._-]+)"
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:

            value = match.group(1).strip()

            if value:
                return value

    return ""


# ============================================================
# PARSE MARKET PAGE
# ============================================================

def parse_market_page(
    html,
    crop,
    source_url
):

    # BeautifulSoup is intentionally not required.
    # This keeps the Render deployment simpler.

    text = re.sub(
        r"<script\b[^>]*>.*?</script>",
        " ",
        html,
        flags=re.IGNORECASE | re.DOTALL
    )

    text = re.sub(
        r"<style\b[^>]*>.*?</style>",
        " ",
        text,
        flags=re.IGNORECASE | re.DOTALL
    )

    text = re.sub(
        r"<[^>]+>",
        " ",
        text
    )

    text = clean_text(text)

    print()
    print("=" * 60)
    print("PARSING MARKET PAGE")
    print("=" * 60)

    # --------------------------------------------------------
    # DATE
    # --------------------------------------------------------

    arrival_date = find_date(text)

    # --------------------------------------------------------
    # MIN/MAX
    # --------------------------------------------------------

    min_price, max_price = find_min_max(text)

    # --------------------------------------------------------
    # MODAL
    # --------------------------------------------------------

    modal_price = find_modal_price(
        text,
        crop
    )

    # --------------------------------------------------------
    # VARIETY
    # --------------------------------------------------------

    variety = find_variety(text)

    # --------------------------------------------------------
    # GRADE
    # --------------------------------------------------------

    grade = find_grade(text)

    print("Date:", arrival_date)
    print("Minimum:", min_price)
    print("Maximum:", max_price)
    print("Modal:", modal_price)
    print("Variety:", variety)
    print("Grade:", grade)

    print("=" * 60)

    # --------------------------------------------------------
    # VALIDATION
    # --------------------------------------------------------

    if min_price is None:

        raise RuntimeError(
            "Could not find minimum price "
            "on the external market page."
        )

    if max_price is None:

        raise RuntimeError(
            "Could not find maximum price "
            "on the external market page."
        )

    if modal_price is None:

        raise RuntimeError(
            "Could not find modal price "
            "on the external market page."
        )

    # --------------------------------------------------------
    # RESULT
    # --------------------------------------------------------

    return {

        "success": True,

        "data_mode": "external_live",

        "source": (
            "MandiPulse / "
            "Agmarknet Government Market Data"
        ),

        "source_url": source_url,

        "market": MARKET_NAME,

        "district": DISTRICT_NAME,

        "state": STATE_NAME,

        "commodity": CROP_NAMES[crop],

        "variety": variety,

        "grade": grade,

        "arrival_date": arrival_date,

        "min_price": min_price,

        "max_price": max_price,

        "modal_price": modal_price,

        "unit": "Rs./Quintal",

        "retrieved_at": (
            datetime.now(
                timezone.utc
            ).isoformat()
        ),

        "fallback": False,

        "message": (
            "Latest available external "
            "market data retrieved successfully."
        )
    }


# ============================================================
# MARKET API
# ============================================================

@app.route("/api/market")
def market():

    crop = (
        request.args
        .get("crop", "")
        .strip()
        .lower()
    )

    print()
    print("=" * 60)
    print("SMARTAGRI MARKET ANALYSIS")
    print("=" * 60)
    print("Selected crop:", crop)
    print("Market:", MARKET_NAME)
    print("District:", DISTRICT_NAME)
    print("State:", STATE_NAME)
    print("=" * 60)

    # --------------------------------------------------------
    # CROP VALIDATION
    # --------------------------------------------------------

    if crop not in CROP_URLS:

        return jsonify({

            "success": False,

            "data_mode": "external_live",

            "fallback": False,

            "message": (
                "Unsupported crop. "
                "Use onion or wheat."
            )

        }), 400

    # --------------------------------------------------------
    # FETCH + PARSE
    # --------------------------------------------------------

    try:

        html, source_url = fetch_market_page(
            crop
        )

        result = parse_market_page(
            html,
            crop,
            source_url
        )

        print()
        print("=" * 60)
        print("LIVE MARKET DATA RECEIVED")
        print("=" * 60)
        print("Commodity:", result["commodity"])
        print("Market:", result["market"])
        print("Date:", result["arrival_date"])
        print("Minimum:", result["min_price"])
        print("Modal:", result["modal_price"])
        print("Maximum:", result["max_price"])
        print("=" * 60)

        return jsonify(
            result
        ), 200

    # --------------------------------------------------------
    # CONNECTION ERROR
    # --------------------------------------------------------

    except requests.RequestException as error:

        print()
        print("=" * 60)
        print("SOURCE CONNECTION ERROR")
        print("=" * 60)
        print(error)
        print("=" * 60)

        return jsonify({

            "success": False,

            "data_mode": "external_live",

            "fallback": False,

            "message": (
                "Unable to connect to the "
                "external market-price source."
            ),

            "error": str(error),

            "commodity": CROP_NAMES[crop],

            "market": MARKET_NAME,

            "district": DISTRICT_NAME,

            "state": STATE_NAME

        }), 502

    # --------------------------------------------------------
    # PARSING / OTHER ERROR
    # --------------------------------------------------------

    except Exception as error:

        print()
        print("=" * 60)
        print("MARKET DATA ERROR")
        print("=" * 60)
        print(error)
        print("=" * 60)

        return jsonify({

            "success": False,

            "data_mode": "external_live",

            "fallback": False,

            "message": (
                "The external market source "
                "did not return a usable "
                "price record."
            ),

            "error": str(error),

            "commodity": CROP_NAMES[crop],

            "market": MARKET_NAME,

            "district": DISTRICT_NAME,

            "state": STATE_NAME

        }), 502


# ============================================================
# HEALTH CHECK
# ============================================================

@app.route("/api/health")
def health():

    return jsonify({

        "success": True,

        "backend": "SmartAgri Flask",

        "market_source": (
            "MandiPulse / "
            "Agmarknet Government Market Data"
        ),

        "mode": "LATEST EXTERNAL DATA",

        "fallback": False,

        "supported_crops": [
            "onion",
            "wheat"
        ],

        "market": MARKET_NAME,

        "district": DISTRICT_NAME,

        "state": STATE_NAME
    })


# ============================================================
# FRONTEND
# ============================================================

@app.route("/")
def home():

    return send_from_directory(
        BASE_DIR,
        "index.html"
    )


@app.route("/<path:filename>")
def files(filename):

    return send_from_directory(
        BASE_DIR,
        filename
    )


# ============================================================
# START SERVER
# ============================================================

if __name__ == "__main__":

    print()
    print("=" * 60)
    print("SMARTAGRI KOPARGAON")
    print("=" * 60)
    print("LATEST EXTERNAL MARKET DATA MODE")
    print("NO FALLBACK DATA")
    print("-" * 60)
    print("Onion")
    print("Wheat")
    print("-" * 60)
    print("Market:", MARKET_NAME)
    print("District:", DISTRICT_NAME)
    print("State:", STATE_NAME)
    print("-" * 60)
    print("Server:")
    print("http://127.0.0.1:5000")
    print("=" * 60)
    print()

    port = int(
        os.environ.get(
            "PORT",
            5000
        )
    )

    app.run(
        host="0.0.0.0",
        port=port,
        debug=True
    )
