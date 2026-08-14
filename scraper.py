import requests
from datetime import datetime, timezone


# ============================================================
# SMARTAGRI AGMARKNET SCRAPER
# ============================================================

API_URL = "https://agmarknet.ceda.ashoka.edu.in/api/prices"


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 "
        "(Windows NT 10.0; Win64; x64) "
        "Chrome/151 Safari/537.36"
    ),
    "Accept": "application/json",
}


SUPPORTED_CROPS = {
    "onion": "Onion",
    "wheat": "Wheat",
}


# ============================================================
# FETCH API
# ============================================================

def fetch_prices():

    response = requests.get(
        API_URL,
        headers=HEADERS,
        timeout=20
    )

    response.raise_for_status()

    return response.json()



# ============================================================
# CLEAN NUMBER
# ============================================================

def clean_price(value):

    if value is None:
        return None

    try:
        return round(float(value))
    except Exception:
        return None



# ============================================================
# PARSE API DATA
# ============================================================

def parse_records(data, crop):

    records = []

    commodity_name = SUPPORTED_CROPS[crop]


    for item in data.get("data", []):

        cmdty = (
            item.get("cmdty")
            or ""
        )


        if cmdty.lower() != commodity_name.lower():

            continue


        record = {

            "crop": crop,

            "commodity": cmdty,


            "district":
                item.get(
                    "district",
                    ""
                ),


            "state":
                item.get(
                    "state",
                    ""
                ),


            "market":
                item.get(
                    "district",
                    "Kopargaon"
                ),


            "data_date":
                item.get(
                    "t"
                ),


            "min_price":
                clean_price(
                    item.get(
                        "p_min"
                    )
                ),


            "max_price":
                clean_price(
                    item.get(
                        "p_max"
                    )
                ),


            "modal_price":
                clean_price(
                    item.get(
                        "p_modal"
                    )
                ),


            "price":
                clean_price(
                    item.get(
                        "p_modal"
                    )
                ),


            "source":
                "Agmarknet CEDA API",


            "source_url":
                API_URL,


            "scraped_at":
                datetime.now(
                    timezone.utc
                )

        }


        records.append(record)


    return records



# ============================================================
# MAIN FUNCTION USED BY APP.PY
# ============================================================

def scrape_crop(crop):

    crop = crop.lower().strip()


    if crop not in SUPPORTED_CROPS:

        raise ValueError(
            "Supported crops: onion, wheat"
        )


    api_response = fetch_prices()


    records = parse_records(
        api_response,
        crop
    )


    if not records:

        raise RuntimeError(
            f"No Agmarknet data found for {crop}"
        )


    return records



# ============================================================
# SCRAPE ALL
# ============================================================

def scrape_all():

    result = {}


    for crop in SUPPORTED_CROPS:

        try:

            result[crop] = scrape_crop(
                crop
            )

        except Exception as e:

            result[crop] = {
                "success": False,
                "error": str(e)
            }


    return result



# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":


    print(
        "SmartAgri Agmarknet Scraper"
    )


    output = scrape_all()


    for crop, records in output.items():

        print("\n")
        print(
            crop.upper()
        )


        if isinstance(records, list):

            for r in records:

                print(
                    r
                )

        else:

            print(records)
