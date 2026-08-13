from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import re

app = Flask(__name__, static_folder=".")
CORS(app)

# ============================================================
# SMARTAGRI KOPARGAON
# LATEST MARKET DATA
#
# Source:
# MandiPulse
# Data is compiled from Agmarknet / Government market data.
#
# NO HARDCODED PRICES
# NO FALLBACK PRICES
# ============================================================

BASE_URL = "https://mandipulse.com/mandi/maharashtra-ahilyanagar-kopargaon-apmc"

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
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


# ============================================================
# NUMBER EXTRACTION
# ============================================================

def extract_number(text):
    if not text:
        return None

    text = text.replace(",", "")

    match = re.search(r"₹?\s*(\d+(?:\.\d+)?)", text)

    if not match:
        return None

    value = float(match.group(1))

    if value.is_integer():
        return int(value)

    return value


# ============================================================
# FETCH PAGE
# ============================================================

def fetch_market_page(crop):

    if crop not in CROP_URLS:
        raise ValueError(
            "Unsupported crop. Use onion or wheat."
        )

    url = CROP_URLS[crop]

    print()
    print("======================================")
    print("SMARTAGRI MARKET REQUEST")
    print("Crop:", crop)
    print("Source:", url)
    print("======================================")

    response = requests.get(
        url,
        headers=HEADERS,
        timeout=20
    )

    response.raise_for_status()

    return response.text, url


# ============================================================
# PARSE MARKET PAGE
# ============================================================

def parse_market_page(html, crop, source_url):

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    # Get all visible page text.
    text = soup.get_text(
        " ",
        strip=True
    )

    # --------------------------------------------------------
    # DATE
    # --------------------------------------------------------

    date_match = re.search(
        r"Updated on:\s*([0-9]{1,2}\s+[A-Za-z]{3}\s+[0-9]{4})",
        text,
        re.IGNORECASE
    )

    arrival_date = (
        date_match.group(1)
        if date_match
        else None
    )

    # --------------------------------------------------------
    # MIN / MAX
    # --------------------------------------------------------

    range_match = re.search(
        r"Min:\s*₹?\s*([\d,]+)"
        r"\s*\|\s*Max:\s*₹?\s*([\d,]+)",
        text,
        re.IGNORECASE
    )

    if not range_match:
        raise RuntimeError(
            "Could not find min/max price on the market page."
        )

    min_price = extract_number(
        range_match.group(1)
    )

    max_price = extract_number(
        range_match.group(2)
    )

    # --------------------------------------------------------
    # MODAL PRICE
    #
    # The main price shown in the page title/body is the
    # reported modal/latest price.
    # --------------------------------------------------------

    modal_match = re.search(
        r"#?\s*"
        + (
            "Onion"
            if crop == "onion"
            else "Wheat"
        )
        + r"\s+Price\s+Today.*?"
        r"₹\s*([\d,]+)\s*/Quintal",
        text,
        re.IGNORECASE
    )

    if not modal_match:

        # Secondary method:
        # Search the heading/body around "Price Today".
        modal_match = re.search(
            r"₹\s*([\d,]+)\s*/Quintal",
            text,
            re.IGNORECASE
        )

    if not modal_match:
        raise RuntimeError(
            "Could not find modal price on the market page."
        )

    modal_price = extract_number(
        modal_match.group(1)
    )

    # --------------------------------------------------------
    # VARIETY
    # --------------------------------------------------------

    variety_match = re.search(
        r"Variety:\s*([^|]+)",
        text,
        re.IGNORECASE
    )

    variety = (
        variety_match.group(1).strip()
        if variety_match
        else ""
    )

    # --------------------------------------------------------
    # GRADE
    # --------------------------------------------------------

    grade_match = re.search(
        r"Grade:\s*([^|]+)",
        text,
        re.IGNORECASE
    )

    grade = (
        grade_match.group(1).strip()
        if grade_match
        else ""
    )

    # --------------------------------------------------------
    # VALIDATE
    # --------------------------------------------------------

    if (
        min_price is None
        or max_price is None
        or modal_price is None
    ):
        raise RuntimeError(
            "Market page did not contain complete price data."
        )

    # --------------------------------------------------------
    # RETURN
    # --------------------------------------------------------

    result = {
        "success": True,

        "data_mode": "external_live",

        "source": "MandiPulse / Agmarknet Government Market Data",

        "source_url": source_url,

        "market": "Kopargaon APMC",

        "district": "Ahilyanagar",

        "state": "Maharashtra",

        "commodity": (
            "Onion"
            if crop == "onion"
            else "Wheat"
        ),

        "variety": variety,

        "grade": grade,

        "arrival_date": arrival_date,

        "min_price": min_price,

        "max_price": max_price,

        "modal_price": modal_price,

        "unit": "Rs./Quintal",

        "message": (
            "Latest available Kopargaon APMC "
            "market price retrieved from the external "
            "market-data source."
        )
    }

    return result


# ============================================================
# MARKET API
# ============================================================

@app.route("/api/market")
def market():

    crop = request.args.get(
        "crop",
        ""
    ).strip().lower()

    print()
    print("======================================")
    print("🌾 SMARTAGRI MARKET ANALYSIS")
    print("Selected crop:", crop)
    print("======================================")

    if crop not in CROP_URLS:

        return jsonify({
            "success": False,
            "message": (
                "Unsupported crop. "
                "Use onion or wheat."
            )
        }), 400

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
        print("======================================")
        print("✅ MARKET DATA RECEIVED")
        print("Crop:", result["commodity"])
        print("Minimum:", result["min_price"])
        print("Maximum:", result["max_price"])
        print("Modal:", result["modal_price"])
        print("Date:", result["arrival_date"])
        print("======================================")
        print()

        return jsonify(result)

    except requests.RequestException as error:

        print()
        print("❌ SOURCE CONNECTION ERROR")
        print(error)

        return jsonify({
            "success": False,
            "data_mode": "external_live",
            "message": (
                "Unable to connect to the external "
                "market-price source."
            ),
            "error": str(error)
        }), 502

    except Exception as error:

        print()
        print("❌ MARKET DATA ERROR")
        print(error)

        return jsonify({
            "success": False,
            "data_mode": "external_live",
            "message": (
                "The external market source did not "
                "return a usable price record."
            ),
            "error": str(error)
        }), 502


# ============================================================
# HEALTH CHECK
# ============================================================

@app.route("/api/health")
def health():

    return jsonify({
        "success": True,
        "backend": "SmartAgri Flask",
        "market_source": "MandiPulse / Agmarknet",
        "mode": "LATEST EXTERNAL DATA",
        "fallback": False
    })


# ============================================================
# SERVE FRONTEND
# ============================================================

@app.route("/")
def home():

    return send_from_directory(
        ".",
        "index.html"
    )


@app.route("/<path:filename>")
def files(filename):

    return send_from_directory(
        ".",
        filename
    )


# ============================================================
# START SERVER
# ============================================================

if __name__ == "__main__":

    print()
    print("======================================")
    print("🌾 SMARTAGRI KOPARGAON")
    print("======================================")
    print("LATEST EXTERNAL MARKET DATA MODE")
    print("NO FALLBACK DATA")
    print("--------------------------------------")
    print("🧅 Onion")
    print("🌾 Wheat")
    print("--------------------------------------")
    print("Server:")
    print("http://127.0.0.1:5000")
    print("======================================")
    print()

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )