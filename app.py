Microsoft Windows [Version 10.0.26200.9168]
(c) Microsoft Corporation. All rights reserved.

C:\Users\tejph\OneDrive\Desktop\SmartAgriKopargaon>curl "http://127.0.0.1:5000/api/market?crop=onion"
{
  "analysis": {
    "average_price": 2650.0,
    "highest_price": 2650.0,
    "lowest_price": 2650.0,
    "moving_average_14": 2650.0,
    "moving_average_3": 2650.0,
    "moving_average_7": 2650.0,
    "prediction": {
      "confidence": "low",
      "direction": "insufficient_data",
      "estimated_price": null,
      "reason": "At least 3 historical price records are recommended for a trend-based estimate.",
      "unit": "Rs./Quintal"
    },
    "trend": {
      "change_percent": null,
      "current_price": 2650.0,
      "direction": "insufficient_data",
      "previous_price": null,
      "strength": "insufficient_data"
    }
  },
  "data_mode": "external_live_plus_history",
  "district": "Ahilyanagar",
  "fallback": false,
  "history_count": 1,
  "latest": {
    "arrival_date": "2026-08-12",
    "commodity": "Onion",
    "crop": "onion",
    "district": "Ahilyanagar",
    "grade": "Local Onion Unhali variety price in Kopargaon APMC mandi Ahilyanagar, Maharashtra Change from yester",
    "market": "Kopargaon APMC",
    "max_price": 3071.0,
    "min_price": 1000.0,
    "modal_price": 2650.0,
    "retrieved_at": "2026-08-14T04:28:13.225484+00:00",
    "source": "MandiPulse / Agmarknet Government Market Data",
    "source_url": "https://mandipulse.com/mandi/maharashtra-ahilyanagar-kopargaon-apmc/onion",
    "state": "Maharashtra",
    "stored": true,
    "unit": "Rs./Quintal",
    "variety": "Unhali"
  },
  "market": "Kopargaon APMC",
  "message": "Latest market data retrieved, stored, and analyzed against available historical records.",
  "state": "Maharashtra",
  "success": true
}

C:\Users\tejph\OneDrive\Desktop\SmartAgriKopargaon>curl "http://127.0.0.1:5000/api/market?crop=wheat"
{
  "analysis": {
    "average_price": 2713.0,
    "highest_price": 2713.0,
    "lowest_price": 2713.0,
    "moving_average_14": 2713.0,
    "moving_average_3": 2713.0,
    "moving_average_7": 2713.0,
    "prediction": {
      "confidence": "low",
      "direction": "insufficient_data",
      "estimated_price": null,
      "reason": "At least 3 historical price records are recommended for a trend-based estimate.",
      "unit": "Rs./Quintal"
    },
    "trend": {
      "change_percent": null,
      "current_price": 2713.0,
      "direction": "insufficient_data",
      "previous_price": null,
      "strength": "insufficient_data"
    }
  },
  "data_mode": "external_live_plus_history",
  "district": "Ahilyanagar",
  "fallback": false,
  "history_count": 1,
  "latest": {
    "arrival_date": "2026-08-12",
    "commodity": "Wheat",
    "crop": "wheat",
    "district": "Ahilyanagar",
    "grade": "FAQ Wheat Other variety price in Kopargaon APMC mandi Ahilyanagar, Maharashtra Change from yesterday",
    "market": "Kopargaon APMC",
    "max_price": 2826.0,
    "min_price": 2675.0,
    "modal_price": 2713.0,
    "retrieved_at": "2026-08-14T04:28:25.381359+00:00",
    "source": "MandiPulse / Agmarknet Government Market Data",
    "source_url": "https://mandipulse.com/mandi/maharashtra-ahilyanagar-kopargaon-apmc/wheat",
    "state": "Maharashtra",
    "stored": true,
    "unit": "Rs./Quintal",
    "variety": "Other"
  },
  "market": "Kopargaon APMC",
  "message": "Latest market data retrieved, stored, and analyzed against available historical records.",
  "state": "Maharashtra",
  "success": true
}

C:\Users\tejph\OneDrive\Desktop\SmartAgriKopargaon>curl "http://127.0.0.1:5000/api/history?crop=onion"
{
  "analysis": {
    "average_price": 2650.0,
    "highest_price": 2650.0,
    "lowest_price": 2650.0,
    "moving_average_14": 2650.0,
    "moving_average_3": 2650.0,
    "moving_average_7": 2650.0,
    "prediction": {
      "confidence": "low",
      "direction": "insufficient_data",
      "estimated_price": null,
      "reason": "At least 3 historical price records are recommended for a trend-based estimate.",
      "unit": "Rs./Quintal"
    },
    "trend": {
      "change_percent": null,
      "current_price": 2650.0,
      "direction": "insufficient_data",
      "previous_price": null,
      "strength": "insufficient_data"
    }
  },
  "commodity": "Onion",
  "count": 1,
  "crop": "onion",
  "district": "Ahilyanagar",
  "market": "Kopargaon APMC",
  "records": [
    {
      "arrival_date": "2026-08-12",
      "commodity": "Onion",
      "created_at": "2026-08-14T04:28:13.225934+00:00",
      "crop": "onion",
      "district": "Ahilyanagar",
      "grade": "Local Onion Unhali variety price in Kopargaon APMC mandi Ahilyanagar, Maharashtra Change from yester",
      "id": 1,
      "market": "Kopargaon APMC",
      "max_price": 3071.0,
      "min_price": 1000.0,
      "modal_price": 2650.0,
      "retrieved_at": "2026-08-14T04:28:13.225484+00:00",
      "source": "MandiPulse / Agmarknet Government Market Data",
      "source_url": "https://mandipulse.com/mandi/maharashtra-ahilyanagar-kopargaon-apmc/onion",
      "state": "Maharashtra",
      "unit": "Rs./Quintal",
      "variety": "Unhali"
    }
  ],
  "state": "Maharashtra",
  "success": true
}

C:\Users\tejph\OneDrive\Desktop\SmartAgriKopargaon>curl "http://127.0.0.1:5000/api/collect?crop=onion"
{
  "analysis": {
    "average_price": 2650.0,
    "highest_price": 2650.0,
    "lowest_price": 2650.0,
    "moving_average_14": 2650.0,
    "moving_average_3": 2650.0,
    "moving_average_7": 2650.0,
    "prediction": {
      "confidence": "low",
      "direction": "insufficient_data",
      "estimated_price": null,
      "reason": "At least 3 historical price records are recommended for a trend-based estimate.",
      "unit": "Rs./Quintal"
    },
    "trend": {
      "change_percent": null,
      "current_price": 2650.0,
      "direction": "insufficient_data",
      "previous_price": null,
      "strength": "insufficient_data"
    }
  },
  "message": "Market data fetched and processed successfully.",
  "record": {
    "arrival_date": "2026-08-12",
    "commodity": "Onion",
    "crop": "onion",
    "district": "Ahilyanagar",
    "grade": "Local Onion Unhali variety price in Kopargaon APMC mandi Ahilyanagar, Maharashtra Change from yester",
    "market": "Kopargaon APMC",
    "max_price": 3071.0,
    "min_price": 1000.0,
    "modal_price": 2650.0,
    "retrieved_at": "2026-08-14T04:29:50.401296+00:00",
    "source": "MandiPulse / Agmarknet Government Market Data",
    "source_url": "https://mandipulse.com/mandi/maharashtra-ahilyanagar-kopargaon-apmc/onion",
    "state": "Maharashtra",
    "stored": true,
    "unit": "Rs./Quintal",
    "variety": "Unhali"
  },
  "stored": true,
  "success": true
}

C:\Users\tejph\OneDrive\Desktop\SmartAgriKopargaon>curl "http://127.0.0.1:5000/api/collect?crop=wheat"
{
  "analysis": {
    "average_price": 2713.0,
    "highest_price": 2713.0,
    "lowest_price": 2713.0,
    "moving_average_14": 2713.0,
    "moving_average_3": 2713.0,
    "moving_average_7": 2713.0,
    "prediction": {
      "confidence": "low",
      "direction": "insufficient_data",
      "estimated_price": null,
      "reason": "At least 3 historical price records are recommended for a trend-based estimate.",
      "unit": "Rs./Quintal"
    },
    "trend": {
      "change_percent": null,
      "current_price": 2713.0,
      "direction": "insufficient_data",
      "previous_price": null,
      "strength": "insufficient_data"
    }
  },
  "message": "Market data fetched and processed successfully.",
  "record": {
    "arrival_date": "2026-08-12",
    "commodity": "Wheat",
    "crop": "wheat",
    "district": "Ahilyanagar",
    "grade": "FAQ Wheat Other variety price in Kopargaon APMC mandi Ahilyanagar, Maharashtra Change from yesterday",
    "market": "Kopargaon APMC",
    "max_price": 2826.0,
    "min_price": 2675.0,
    "modal_price": 2713.0,
    "retrieved_at": "2026-08-14T04:29:56.550635+00:00",
    "source": "MandiPulse / Agmarknet Government Market Data",
    "source_url": "https://mandipulse.com/mandi/maharashtra-ahilyanagar-kopargaon-apmc/wheat",
    "state": "Maharashtra",
    "stored": true,
    "unit": "Rs./Quintal",
    "variety": "Other"
  },
  "stored": true,
  "success": true
}

C:\Users\tejph\OneDrive\Desktop\SmartAgriKopargaon>curl "http://127.0.0.1:5000/api/health"
{
  "backend": "SmartAgri Flask",
  "database": "SQLite",
  "database_path": "C:\\Users\\tejph\\OneDrive\\Desktop\\SmartAgriKopargaon\\smartagri.db",
  "district": "Ahilyanagar",
  "fallback": false,
  "market": "Kopargaon APMC",
  "market_source": "MandiPulse / Agmarknet",
  "onion_records": 1,
  "state": "Maharashtra",
  "success": true,
  "supported_crops": [
    "onion",
    "wheat"
  ],
  "total_history_records": 2,
  "wheat_records": 1
}

C:\Users\tejph\OneDrive\Desktop\SmartAgriKopargaon>
