# 🌾 SmartAgri Kopargaon

SmartAgri Kopargaon is a web-based agricultural market intelligence platform designed to help farmers and users understand crop market conditions and make better selling decisions.

The application focuses on **Kopargaon market data** for crops such as **onion and wheat**. It collects market-price information from NaPanta, stores historical records in MongoDB Atlas, calculates market trends, generates short-term price estimates, and provides a simple selling recommendation.

## 🚀 Live Application

**SmartAgri Kopargaon:**
https://smartagrikopargaon.onrender.com

## 📦 Source Code

**GitHub Repository:**
https://github.com/Vaidarbhi-code/SmartAgriKopargaon

---

## 🎯 Project Objective

Farmers often need to decide whether to sell their produce immediately or hold it for a better price.

SmartAgri Kopargaon aims to provide a simple decision-support system by combining:

* Current market prices
* Historical market data
* Market-price trends
* Short-term price estimation
* Demand indication
* Selling vs. storing comparison
* Transport-adjusted value
* Automated market-data collection

The goal is to convert raw agricultural market information into information that is easier to understand and use.

---

## ✨ Features

### 🌾 Crop Selection

The application currently supports:

* Onion
* Wheat

The backend validates supported crops before processing market requests.

### 💰 Current Market Price

The application retrieves the latest available market record and displays the modal/current price per quintal.

Market information can include:

* Market
* District
* State
* Commodity
* Variety
* Minimum price
* Maximum price
* Modal price
* Data date
* Data source

### 📈 Market Trend

The backend compares recent market prices to determine whether the price trend is:

* Increasing
* Decreasing
* Stable

The application also calculates the corresponding price change and percentage change.

### 🔥 Demand Indicator

A simple demand indicator is generated from the market trend:

* Increasing → High
* Decreasing → Moderate
* Stable → Stable

### 🤖 Price Forecast

SmartAgri generates a conservative short-term price estimate using recent historical market prices.

The forecast uses:

* Recent market-price history
* A recent weighted/average price
* Recent price movement
* Conservative upper and lower boundaries

The forecast is intended as a decision-support estimate rather than a guaranteed future price.

### 🧠 Smart Selling Decision

The application compares the current market price with the estimated future price and generates a recommendation:

* **Sell Now**
* **Store**

It also considers the recent market trend and an estimated transport-cost adjustment.

### 🏪 Market Comparison

The frontend provides a market-information section focused on the Kopargaon market/APMC.

### 🗄️ Historical Data

Market records are stored in MongoDB Atlas so that previous observations can be used for:

* Historical market views
* Trend calculation
* Forecasting
* Fallback data
* CSV export

### 🔄 Automatic Data Refresh

The backend checks the age of stored data and refreshes the crop data when the configured scraping interval has passed.

If recent MongoDB data is available, it can be used without unnecessarily scraping the external source.

### 🛡️ Historical Fallback

If a live NaPanta refresh fails but MongoDB contains an earlier market record, SmartAgri uses the stored record instead of completely failing the request.

This allows the application to continue providing the last available market information during temporary scraping or source outages.

---

## 🏗️ System Architecture

```text
                    ┌─────────────────────┐
                    │   User / Browser    │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │   SmartAgri Web UI  │
                    │ HTML / CSS / JS     │
                    └──────────┬──────────┘
                               │
                         HTTP / REST API
                               │
                               ▼
                    ┌─────────────────────┐
                    │     Flask API       │
                    │       app.py        │
                    └───────┬─────┬───────┘
                            │     │
                  ┌─────────┘     └──────────┐
                  ▼                          ▼
        ┌─────────────────┐        ┌─────────────────┐
        │    scraper.py   │        │   database.py   │
        │  NaPanta data   │        │ MongoDB Atlas   │
        └────────┬────────┘        └────────┬────────┘
                 │                          │
                 ▼                          ▼
        ┌─────────────────┐        ┌─────────────────┐
        │     NaPanta     │        │ Market History  │
        │ Market Source   │        │ & Current Data  │
        └─────────────────┘        └─────────────────┘
```

---

## 🧩 Main Components

### `app.py`

The main Flask application.

It handles:

* Flask server configuration
* CORS
* MongoDB initialization
* Market API endpoints
* Data refresh
* Trend calculation
* Forecast calculation
* Selling decisions
* Historical data
* CSV import/export
* Health/status endpoints
* Frontend serving

### `scraper.py`

Responsible for collecting agricultural market information from NaPanta.

The scraper extracts market records for supported crops and identifies the latest available market date.

### `database.py`

Provides MongoDB-related database operations, including:

* MongoDB connection
* Collection access
* Market-price insertion
* Market-price updates
* Upsert operations
* Latest-price retrieval
* Historical data access

The repository includes MongoDB upsert functionality for both live scraped records and historical data.

### `index.html`

The main frontend page.

The interface includes sections for:

* Market snapshot
* Current price
* Market trend
* Demand
* Forecast
* Market comparison
* Smart selling decision
* Recommendation

The current frontend explicitly displays current price, trend, demand, data status, date, and source information.

### `script.js`

Handles frontend interaction and communication with the backend APIs.

### `style.css`

Provides the visual design and responsive styling for the SmartAgri interface.

### `requirements.txt`

The Python backend dependencies currently include Flask, Flask-CORS, PyMongo, dnspython, certifi, requests, BeautifulSoup, and Gunicorn.

---

## 🔌 API Endpoints

### Get Market Data

```text
GET /api/market?crop=onion
GET /api/market?crop=wheat
```

Returns the latest market information together with:

* Current price
* Market information
* Trend
* Demand
* Forecast
* Selling recommendation
* Data status
* Source information

### Get Market History

```text
GET /api/market/history?crop=onion
GET /api/market/history?crop=wheat
```

Optional:

```text
GET /api/market/history?crop=onion&limit=30
```

### Refresh Market Data

```text
POST /api/market/refresh?crop=onion
POST /api/market/refresh?crop=wheat
```

A refresh can also be requested without specifying a crop to process the supported crops.

### Export CSV

```text
GET /api/market/export-csv
```

For a specific crop:

```text
GET /api/market/export-csv?crop=onion
```

### Import CSV

```text
POST /api/market/import-csv
```

The CSV file should be uploaded using the form field:

```text
file
```

### Database Statistics

```text
GET /api/market/stats
```

### Service Status

```text
GET /api/status
```

### Health Check

```text
GET /health
```

---

## 🗃️ MongoDB

SmartAgri uses **MongoDB Atlas** for persistent market data storage.

The application uses environment variables for database configuration.

### Environment Variables

```text
MONGODB_URI
MONGODB_DB_NAME
MONGODB_COLLECTION
```

Optional scraping configuration:

```text
SCRAPE_INTERVAL_HOURS
```

Example:

```text
MONGODB_DB_NAME=SmartAgriKopargaon
MONGODB_COLLECTION=Prices
SCRAPE_INTERVAL_HOURS=6
```

The MongoDB connection string should **never be committed to GitHub**.

Use environment variables in deployment platforms such as Render.

---

## 🖥️ Running Locally

### 1. Clone the repository

```bash
git clone https://github.com/Vaidarbhi-code/SmartAgriKopargaon.git
cd SmartAgriKopargaon
```

### 2. Create a virtual environment

Windows:

```bash
python -m venv venv
venv\Scripts\activate
```

Linux/macOS:

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure MongoDB

Set the required environment variables:

```text
MONGODB_URI=<your-mongodb-atlas-connection-string>
MONGODB_DB_NAME=SmartAgriKopargaon
MONGODB_COLLECTION=Prices
```

### 5. Run the application

```bash
python app.py
```

Or with Gunicorn:

```bash
gunicorn app:app
```

The application can then be accessed locally through:

```text
http://localhost:5000
```

---

## ☁️ Deployment

The current application is deployed using **Render**.

The deployment runs the Flask application with Gunicorn:

```text
gunicorn app:app
```

The live application is available at:

```text
https://smartagrikopargaon.onrender.com
```

MongoDB Atlas is used as the production database.

---

## 🔐 Security

Sensitive configuration should be stored in environment variables rather than source code.

Do not commit:

```text
MONGODB_URI
```

or any other credentials, API keys, passwords, or private configuration files.

If a database credential is accidentally exposed, it should be changed immediately.

---

## 📊 Data Flow

When a user requests market information:

```text
1. User selects a crop
          ↓
2. Frontend requests /api/market
          ↓
3. Flask checks MongoDB
          ↓
4. Backend determines whether refresh is required
          ↓
5. scraper.py retrieves available NaPanta records
          ↓
6. Records are saved/updated in MongoDB
          ↓
7. Latest market record is selected
          ↓
8. Trend is calculated
          ↓
9. Price forecast is calculated
          ↓
10. Selling decision is calculated
          ↓
11. JSON response is returned
          ↓
12. Frontend displays the result
```

If live scraping fails:

```text
NaPanta refresh fails
        ↓
MongoDB contains previous data?
        ↓
      Yes
        ↓
Use historical MongoDB record
        ↓
Return historical fallback status
```

The fallback mechanism is explicitly implemented in the current backend.

---

## ⚠️ Important Note About Forecasts

The price forecast is a **decision-support estimate** generated from recent market history.

It should not be interpreted as a guaranteed future market price.

Actual agricultural prices can be affected by:

* Supply and demand
* Weather
* Crop production
* Government policies
* Transportation
* Local arrivals
* Seasonal conditions
* Market fluctuations

Farmers should consider local market conditions and other relevant information before making financial decisions.

---

## 🌱 Future Improvements

Possible future development areas include:

* Additional crops
* More agricultural markets
* More historical market sources
* Improved forecasting models
* Weather integration
* Regional market comparison
* Farmer-specific alerts
* Price notifications
* Mobile/PWA improvements
* Authentication and farmer profiles
* Advanced market analytics
* Interactive historical price charts
* Improved multilingual support

---

## 📁 Repository Structure

```text
SmartAgriKopargaon/
│
├── app.py
├── database.py
├── scraper.py
├── import_csv.py
│
├── index.html
├── script.js
├── style.css
│
├── package.json
├── package-lock.json
├── requirements.txt
│
└── server.js
```

---

## 🛠️ Technology Stack

### Frontend

* HTML5
* CSS3
* JavaScript

### Backend

* Python
* Flask
* Flask-CORS
* Gunicorn

### Data Collection

* Python Requests
* BeautifulSoup
* NaPanta market data

### Database

* MongoDB Atlas
* PyMongo

### Deployment

* Render
* GitHub

---

## 👥 Project

**SmartAgri Kopargaon**

An agricultural market intelligence and decision-support platform focused on helping users understand crop prices and make informed selling decisions.

### Supported Crops

* Onion
* Wheat

### Primary Market

* Kopargaon

### Data Source

* NaPanta

### Production Database

* MongoDB Atlas

### Hosting

* Render

---

## 📜 Disclaimer

SmartAgri Kopargaon is an educational and decision-support project.

Market prices and forecasts may change, and the application does not guarantee future prices or financial outcomes.

Always verify important market information with current local sources before making financial or agricultural decisions.

---

## ⭐ Repository

https://github.com/Vaidarbhi-code/SmartAgriKopargaon

