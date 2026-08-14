import os
import requests
from datetime import datetime


CEDA_API_URL = "https://agmarknet.ceda.ashoka.edu.in/api/prices"

CEDA_API_KEY = os.getenv("CEDA_API_KEY")


CROPS = {
    "onion": "Onion",
    "wheat": "Wheat"
}


def get_headers():
    """
    CEDA API authentication.
    """

    headers = {
        "Accept": "application/json"
    }

    if CEDA_API_KEY:
        headers["Authorization"] = f"Bearer {CEDA_API_KEY}"

    return headers



def fetch_ceda_prices(crop):

    params = {
        "cmdty": CROPS[crop]
    }


    response = requests.get(
        CEDA_API_URL,
        headers=get_headers(),
        params=params,
        timeout=30
    )


    response.raise_for_status()


    return response.json()



def parse_latest_price(crop):

    data = fetch_ceda_prices(crop)


    records = data.get(
        "data",
        []
    )


    if not records:
        raise Exception(
            f"No CEDA data found for {crop}"
        )


    # API returns newest first
    latest = records[0]


    return {

        "crop": crop,

        "commodity": latest.get(
            "cmdty"
        ),

        "market": "Kopargaon",

        "state": latest.get(
            "state",
            "Maharashtra"
        ),

        "district": latest.get(
            "district",
            "Ahmadnagar"
        ),


        "data_date": latest.get(
            "t"
        ),


        "min_price": latest.get(
            "p_min"
        ),

        "max_price": latest.get(
            "p_max"
        ),

        "modal_price": latest.get(
            "p_modal"
        ),

        "price": latest.get(
            "p_modal"
        ),


        "source": "CEDA Agmarknet",

        "source_url": CEDA_API_URL,

        "updated_at": datetime.utcnow()

    }



def scrape_crop(crop):

    crop = crop.lower()

    if crop not in CROPS:
        raise ValueError(
            "Supported crops: onion, wheat"
        )


    return parse_latest_price(
        crop
    )



def scrape_all():

    result = {}


    for crop in CROPS:

        try:

            result[crop] = scrape_crop(
                crop
            )


        except Exception as error:

            result[crop] = {

                "crop": crop,

                "success": False,

                "error": str(error)

            }


    return result



if __name__ == "__main__":


    print(
        "SmartAgri CEDA Scraper"
    )


    data = scrape_all()


    for crop, value in data.items():

        print("\n")
        print(
            crop.upper()
        )

        print(
            value
        )
