/* =========================================================
   SMART AGRI KOPARGAON
   COMPLETE FRONTEND JAVASCRIPT
========================================================= */

"use strict";

/* =========================================================
   CONFIGURATION
========================================================= */

const API_BASE_URL = "";

const MARKET_API = `${API_BASE_URL}/api/market`;

const REFRESH_INTERVAL = 5 * 60 * 1000;

const STORAGE_KEY = "smartAgriMarketHistory";

const FALLBACK_PRICES = {
    onion: {
        price: 2800,
        min: 2400,
        max: 3200,
        unit: "₹/quintal"
    },

    wheat: {
        price: 2650,
        min: 2400,
        max: 2900,
        unit: "₹/quintal"
    }
};


/* =========================================================
   TRANSLATIONS
========================================================= */

const translations = {

    en: {

        dashboard: "Dashboard",
        market: "Market",
        forecast: "Forecast",
        decision: "Smart Decision",

        heroLabel: "DATA-DRIVEN AGRICULTURE",

        heroTitle: "Smarter Market Decisions.",
        heroTitleSpan: "Better Farm Returns.",

        heroDescription:
            "Agricultural market intelligence designed to help farmers in Kopargaon decide when, where and how to sell their produce.",

        marketIntelligence: "📊 Market Intelligence",
        aiForecasting: "🤖 AI Forecasting",
        liveData: "📡 Live Data",

        selectCrop: "Select Your Crop",

        selectCropDescription:
            "Select a crop to analyze current market conditions in Kopargaon.",

        crop: "Crop",

        onion: "🧅 Onion",
        wheat: "🌾 Wheat",

        analyzeMarket: "Analyze Market",

        marketSnapshot: "Market Snapshot",

        currentMarketConditions:
            "Current market conditions for the selected crop.",

        currentPrice: "Current Price",
        marketTrend: "Market Trend",
        demand: "Demand",

        perQuintal: "Per Quintal",
        priceMovement: "Price movement",
        currentMarketIndicator: "Current market indicator",

        rising: "Rising",
        falling: "Falling",
        stable: "Stable",

        high: "High",
        medium: "Medium",
        low: "Low",

        aiPriceForecast: "AI Price Forecast",

        forecastDescription:
            "Estimated future price based on current market information.",

        expectedFuturePrice: "EXPECTED FUTURE PRICE",

        forecastWaiting:
            "Select a crop and analyze the market to generate a forecast.",

        marketComparison: "Market Comparison",

        liveKopargaon:
            "Latest available Kopargaon market information.",

        marketName: "Market",
        pricePerQuintal: "Price / Quintal",
        status: "Status",

        latest: "Latest",
        estimated: "Estimated",

        smartSellingDecision: "Smart Selling Decision",

        decisionDescription:
            "Compare possible selling strategies using current market information.",

        sellNow: "Sell Now",
        store: "Store",
        transport: "Transport",

        currentPriceLabel: "Current Price",
        estimatedFuturePrice: "Estimated Future Price",
        estimatedPrice: "Estimated Price",

        smartRecommendation: "SMART RECOMMENDATION",
        recommendedAction: "Recommended Action",

        analyzeMarketMessage:
            "The system will analyze the latest market data and provide a recommendation.",

        sellRecommendation:
            "Selling now is recommended because the current market price is favorable.",

        storeRecommendation:
            "Storing may provide a better return if the expected price increase continues.",

        transportRecommendation:
            "Transporting to another market may provide a better estimated return.",

        liveConnection: "Live Data Connection",

        readyConnection:
            "Ready to connect to live market data.",

        liveConnected:
            "Live market data connected successfully.",

        fallbackConnection:
            "Government market data is temporarily unavailable. Showing the latest stored/estimated market value.",

        lastUpdated: "Latest data",

        today: "Today",

        priceUp:
            "Price increased compared with the previous recorded price.",

        priceDown:
            "Price decreased compared with the previous recorded price.",

        priceStable:
            "Price is stable compared with the previous recorded price.",

        dataSource:
            "Market prices are retrieved through the SmartAgri backend from data.gov.in / Agmarknet.",

        latestStored:
            "Latest stored value",

        fallbackValue:
            "Estimated reference value",

        connectionError:
            "Live API connection failed. Latest available value is being displayed."
    },


    mr: {

        dashboard: "डॅशबोर्ड",
        market: "बाजार",
        forecast: "अंदाज",
        decision: "स्मार्ट निर्णय",

        heroLabel: "डेटा-आधारित शेती",

        heroTitle: "स्मार्ट बाजार निर्णय.",
        heroTitleSpan: "चांगला शेती नफा.",

        heroDescription:
            "कोपरगावमधील शेतकऱ्यांना त्यांचा माल कधी, कुठे आणि कसा विकायचा याचा निर्णय घेण्यास मदत करणारी कृषी बाजार माहिती प्रणाली.",

        marketIntelligence: "📊 बाजार माहिती",
        aiForecasting: "🤖 AI अंदाज",
        liveData: "📡 थेट माहिती",

        selectCrop: "तुमचे पीक निवडा",

        selectCropDescription:
            "कोपरगावमधील सध्याची बाजार परिस्थिती पाहण्यासाठी पीक निवडा.",

        crop: "पीक",

        onion: "🧅 कांदा",
        wheat: "🌾 गहू",

        analyzeMarket: "बाजाराचे विश्लेषण करा",

        marketSnapshot: "बाजार स्थिती",

        currentMarketConditions:
            "निवडलेल्या पिकाची सध्याची बाजार परिस्थिती.",

        currentPrice: "सध्याचा भाव",
        marketTrend: "बाजाराचा कल",
        demand: "मागणी",

        perQuintal: "प्रति क्विंटल",
        priceMovement: "भावातील बदल",
        currentMarketIndicator: "सध्याचा बाजार निर्देशक",

        rising: "वाढता",
        falling: "घटता",
        stable: "स्थिर",

        high: "जास्त",
        medium: "मध्यम",
        low: "कमी",

        aiPriceForecast: "AI भाव अंदाज",

        forecastDescription:
            "सध्याच्या बाजार माहितीवर आधारित भविष्यातील अंदाजे भाव.",

        expectedFuturePrice: "अपेक्षित भविष्यातील भाव",

        forecastWaiting:
            "अंदाज मिळवण्यासाठी पीक निवडा आणि बाजाराचे विश्लेषण करा.",

        marketComparison: "बाजार तुलना",

        liveKopargaon:
            "कोपरगाव बाजाराची उपलब्ध नवीनतम माहिती.",

        marketName: "बाजार",
        pricePerQuintal: "भाव / क्विंटल",
        status: "स्थिती",

        latest: "नवीनतम",
        estimated: "अंदाजे",

        smartSellingDecision: "स्मार्ट विक्री निर्णय",

        decisionDescription:
            "सध्याच्या बाजार माहितीच्या आधारे विविध विक्री पर्यायांची तुलना करा.",

        sellNow: "आत्ताच विक्री",
        store: "साठवणूक",
        transport: "वाहतूक",

        currentPriceLabel: "सध्याचा भाव",
        estimatedFuturePrice: "अंदाजे भविष्यातील भाव",
        estimatedPrice: "अंदाजे भाव",

        smartRecommendation: "स्मार्ट शिफारस",
        recommendedAction: "शिफारस केलेली कृती",

        analyzeMarketMessage:
            "प्रणाली नवीनतम बाजार माहितीचे विश्लेषण करून शिफारस देईल.",

        sellRecommendation:
            "सध्याचा बाजार भाव चांगला असल्यामुळे आत्ताच विक्री करणे योग्य आहे.",

        storeRecommendation:
            "भाव वाढण्याची शक्यता असल्यामुळे साठवणूक केल्यास अधिक परतावा मिळू शकतो.",

        transportRecommendation:
            "इतर बाजारपेठेत वाहतूक केल्यास अधिक अंदाजे परतावा मिळू शकतो.",

        liveConnection: "थेट माहिती कनेक्शन",

        readyConnection:
            "थेट बाजार माहितीशी जोडण्यासाठी तयार.",

        liveConnected:
            "थेट बाजार माहिती यशस्वीपणे जोडली आहे.",

        fallbackConnection:
            "सरकारी बाजार माहिती सध्या उपलब्ध नाही. नवीनतम संग्रहित/अंदाजे बाजार मूल्य दाखवले जात आहे.",

        lastUpdated: "नवीनतम माहिती",

        today: "आज",

        priceUp:
            "मागील नोंदवलेल्या भावाच्या तुलनेत भाव वाढला आहे.",

        priceDown:
            "मागील नोंदवलेल्या भावाच्या तुलनेत भाव कमी झाला आहे.",

        priceStable:
            "मागील नोंदवलेल्या भावाच्या तुलनेत भाव स्थिर आहे.",

        dataSource:
            "बाजार भाव SmartAgri backend मार्फत data.gov.in / Agmarknet मधून मिळवले जातात.",

        latestStored:
            "नवीनतम संग्रहित मूल्य",

        fallbackValue:
            "अंदाजे संदर्भ मूल्य",

        connectionError:
            "थेट API कनेक्शन अयशस्वी झाले. उपलब्ध नवीनतम मूल्य दाखवले जात आहे."
    },


    hi: {

        dashboard: "डैशबोर्ड",
        market: "बाज़ार",
        forecast: "पूर्वानुमान",
        decision: "स्मार्ट निर्णय",

        heroLabel: "डेटा आधारित कृषि",

        heroTitle: "स्मार्ट बाजार निर्णय.",
        heroTitleSpan: "बेहतर कृषि लाभ.",

        heroDescription:
            "कोपरगांव के किसानों को अपनी फसल कब, कहां और कैसे बेचनी है, इसका निर्णय लेने में मदद करने वाली कृषि बाजार जानकारी प्रणाली।",

        marketIntelligence: "📊 बाजार जानकारी",
        aiForecasting: "🤖 AI पूर्वानुमान",
        liveData: "📡 लाइव डेटा",

        selectCrop: "अपनी फसल चुनें",

        selectCropDescription:
            "कोपरगांव की वर्तमान बाजार स्थिति देखने के लिए फसल चुनें।",

        crop: "फसल",

        onion: "🧅 प्याज",
        wheat: "🌾 गेहूं",

        analyzeMarket: "बाजार का विश्लेषण करें",

        marketSnapshot: "बाजार स्थिति",

        currentMarketConditions:
            "चयनित फसल की वर्तमान बाजार स्थिति।",

        currentPrice: "वर्तमान भाव",
        marketTrend: "बाजार का रुझान",
        demand: "मांग",

        perQuintal: "प्रति क्विंटल",
        priceMovement: "भाव में बदलाव",
        currentMarketIndicator: "वर्तमान बाजार संकेतक",

        rising: "बढ़ता",
        falling: "गिरता",
        stable: "स्थिर",

        high: "उच्च",
        medium: "मध्यम",
        low: "कम",

        aiPriceForecast: "AI मूल्य पूर्वानुमान",

        forecastDescription:
            "वर्तमान बाजार जानकारी के आधार पर अनुमानित भविष्य का भाव।",

        expectedFuturePrice: "अपेक्षित भविष्य का भाव",

        forecastWaiting:
            "पूर्वानुमान प्राप्त करने के लिए फसल चुनें और बाजार का विश्लेषण करें।",

        marketComparison: "बाजार तुलना",

        liveKopargaon:
            "कोपरगांव बाजार की नवीनतम उपलब्ध जानकारी।",

        marketName: "बाजार",
        pricePerQuintal: "भाव / क्विंटल",
        status: "स्थिति",

        latest: "नवीनतम",
        estimated: "अनुमानित",

        smartSellingDecision: "स्मार्ट बिक्री निर्णय",

        decisionDescription:
            "वर्तमान बाजार जानकारी के आधार पर विभिन्न बिक्री विकल्पों की तुलना करें।",

        sellNow: "अभी बेचें",
        store: "भंडारण",
        transport: "परिवहन",

        currentPriceLabel: "वर्तमान भाव",
        estimatedFuturePrice: "अनुमानित भविष्य का भाव",
        estimatedPrice: "अनुमानित भाव",

        smartRecommendation: "स्मार्ट सिफारिश",
        recommendedAction: "अनुशंसित कार्रवाई",

        analyzeMarketMessage:
            "सिस्टम नवीनतम बाजार जानकारी का विश्लेषण करके सिफारिश देगा।",

        sellRecommendation:
            "वर्तमान बाजार भाव अच्छा है, इसलिए अभी बेचना उचित है।",

        storeRecommendation:
            "यदि भाव बढ़ने की संभावना बनी रहती है तो भंडारण से बेहतर लाभ मिल सकता है।",

        transportRecommendation:
            "दूसरे बाजार में परिवहन करने से बेहतर अनुमानित लाभ मिल सकता है।",

        liveConnection: "लाइव डेटा कनेक्शन",

        readyConnection:
            "लाइव बाजार डेटा से जुड़ने के लिए तैयार।",

        liveConnected:
            "लाइव बाजार डेटा सफलतापूर्वक जुड़ गया है।",

        fallbackConnection:
            "सरकारी बाजार डेटा फिलहाल उपलब्ध नहीं है। नवीनतम संग्रहीत/अनुमानित बाजार मूल्य दिखाया जा रहा है।",

        lastUpdated: "नवीनतम डेटा",

        today: "आज",

        priceUp:
            "पिछले रिकॉर्ड किए गए भाव की तुलना में भाव बढ़ा है।",

        priceDown:
            "पिछले रिकॉर्ड किए गए भाव की तुलना में भाव कम हुआ है।",

        priceStable:
            "पिछले रिकॉर्ड किए गए भाव की तुलना में भाव स्थिर है।",

        dataSource:
            "बाजार भाव SmartAgri backend के माध्यम से data.gov.in / Agmarknet से प्राप्त किए जाते हैं।",

        latestStored:
            "नवीनतम संग्रहीत मूल्य",

        fallbackValue:
            "अनुमानित संदर्भ मूल्य",

        connectionError:
            "लाइव API कनेक्शन विफल हुआ। उपलब्ध नवीनतम मूल्य दिखाया जा रहा है।"
    }
};


/* =========================================================
   STATE
========================================================= */

let currentLanguage = localStorage.getItem("smartAgriLanguage") || "en";

let selectedCrop = "onion";

let currentMarketData = null;


/* =========================================================
   DOM HELPERS
========================================================= */

function getElement(id) {
    return document.getElementById(id);
}


function setText(id, value) {

    const element = getElement(id);

    if (element) {
        element.textContent = value;
    }
}


function getTranslation(key) {

    return (
        translations[currentLanguage] &&
        translations[currentLanguage][key]
    ) || translations.en[key] || key;
}


/* =========================================================
   NUMBER FORMATTING
========================================================= */

function formatPrice(value) {

    const number = Number(value);

    if (!Number.isFinite(number)) {
        return "₹0";
    }

    return "₹" + Math.round(number).toLocaleString("en-IN");
}


/* =========================================================
   DATE FORMATTING
========================================================= */

function formatDate(dateValue) {

    let date;

    if (dateValue) {
        date = new Date(dateValue);
    } else {
        date = new Date();
    }

    if (Number.isNaN(date.getTime())) {
        date = new Date();
    }

    return date.toLocaleDateString(
        currentLanguage === "mr"
            ? "mr-IN"
            : currentLanguage === "hi"
                ? "hi-IN"
                : "en-IN",
        {
            day: "numeric",
            month: "short",
            year: "numeric"
        }
    );
}


/* =========================================================
   STORAGE
========================================================= */

function getMarketHistory() {

    try {

        const stored = localStorage.getItem(STORAGE_KEY);

        if (!stored) {
            return {};
        }

        const parsed = JSON.parse(stored);

        return parsed && typeof parsed === "object"
            ? parsed
            : {};

    } catch (error) {

        console.error("History read error:", error);

        return {};
    }
}


function saveMarketHistory(history) {

    try {

        localStorage.setItem(
            STORAGE_KEY,
            JSON.stringify(history)
        );

    } catch (error) {

        console.error("History save error:", error);
    }
}


function savePriceRecord(crop, price, source, date) {

    const history = getMarketHistory();

    if (!history[crop]) {
        history[crop] = [];
    }

    const numericPrice = Number(price);

    if (!Number.isFinite(numericPrice)) {
        return;
    }

    const dateKey = new Date(date || Date.now())
        .toISOString()
        .split("T")[0];

    const existingIndex = history[crop].findIndex(
        record => record.date === dateKey
    );

    const record = {
        date: dateKey,
        price: numericPrice,
        source: source || "estimated"
    };

    if (existingIndex >= 0) {
        history[crop][existingIndex] = record;
    } else {
        history[crop].push(record);
    }

    history[crop].sort(
        (a, b) =>
            new Date(a.date) - new Date(b.date)
    );

    /* Keep approximately one year of local records */

    if (history[crop].length > 365) {

        history[crop] =
            history[crop].slice(-365);
    }

    saveMarketHistory(history);
}


function getPreviousPrice(crop, currentDate) {

    const history = getMarketHistory();

    const records = history[crop] || [];

    if (!records.length) {
        return null;
    }

    const currentTimestamp =
        new Date(currentDate || Date.now()).getTime();

    const previousRecords = records
        .filter(record => {

            const timestamp =
                new Date(record.date).getTime();

            return timestamp < currentTimestamp;
        })
        .sort(
            (a, b) =>
                new Date(b.date) -
                new Date(a.date)
        );

    if (!previousRecords.length) {
        return null;
    }

    return Number(previousRecords[0].price);
}


/* =========================================================
   FALLBACK DATA
========================================================= */

function getFallbackData(crop) {

    const fallback =
        FALLBACK_PRICES[crop] ||
        FALLBACK_PRICES.onion;

    const history =
        getMarketHistory();

    const records =
        history[crop] || [];

    if (records.length) {

        const latest =
            records[records.length - 1];

        if (
            latest &&
            Number.isFinite(Number(latest.price))
        ) {

            return {

                crop,

                price: Number(latest.price),

                minPrice:
                    Number(latest.price) * 0.9,

                maxPrice:
                    Number(latest.price) * 1.1,

                date:
                    latest.date,

                source:
                    "stored",

                market:
                    "Kopargaon APMC"
            };
        }
    }

    return {

        crop,

        price: fallback.price,

        minPrice: fallback.min,

        maxPrice: fallback.max,

        date: new Date().toISOString(),

        source: "estimated",

        market: "Kopargaon APMC"
    };
}


/* =========================================================
   API VALUE EXTRACTION
========================================================= */

function extractPrice(data) {

    if (!data || typeof data !== "object") {
        return null;
    }

    const possibleValues = [

        data.price,
        data.current_price,
        data.currentPrice,
        data.modal_price,
        data.modalPrice,
        data.latest_price,
        data.latestPrice,
        data.average_price,
        data.averagePrice,
        data.market_price,
        data.marketPrice,

        data.data?.price,
        data.data?.current_price,
        data.data?.currentPrice,
        data.data?.modal_price,
        data.data?.modalPrice,
        data.data?.latest_price,
        data.data?.latestPrice,

        data.result?.price,
        data.result?.current_price,
        data.result?.modal_price

    ];

    for (const value of possibleValues) {

        const number = Number(value);

        if (Number.isFinite(number) && number > 0) {
            return number;
        }
    }

    return null;
}


function extractDate(data) {

    if (!data || typeof data !== "object") {
        return null;
    }

    const possibleDates = [

        data.date,
        data.price_date,
        data.priceDate,
        data.arrival_date,
        data.arrivalDate,
        data.updated_at,
        data.updatedAt,
        data.last_updated,
        data.lastUpdated,

        data.data?.date,
        data.data?.price_date,
        data.data?.updated_at,

        data.result?.date,
        data.result?.price_date

    ];

    for (const value of possibleDates) {

        if (!value) {
            continue;
        }

        const parsed =
            new Date(value);

        if (!Number.isNaN(parsed.getTime())) {
            return parsed.toISOString();
        }
    }

    return null;
}


function extractMarketName(data) {

    if (!data || typeof data !== "object") {
        return "Kopargaon APMC";
    }

    return (

        data.market ||
        data.market_name ||
        data.marketName ||
        data.apmc ||
        data.market_center ||
        data.marketCenter ||
        data.data?.market ||
        data.data?.market_name ||
        "Kopargaon APMC"

    );
}


/* =========================================================
   FETCH MARKET DATA
========================================================= */

async function fetchMarketData(crop) {

    const url =
        `${MARKET_API}?crop=${encodeURIComponent(crop)}`;

    try {

        const controller =
            new AbortController();

        const timeout =
            setTimeout(
                () => controller.abort(),
                10000
            );

        const response =
            await fetch(
                url,
                {
                    method: "GET",
                    headers: {
                        "Accept": "application/json"
                    },
                    signal: controller.signal,
                    cache: "no-store"
                }
            );

        clearTimeout(timeout);

        if (!response.ok) {

            throw new Error(
                `Market API returned ${response.status}`
            );
        }

        const data =
            await response.json();

        const price =
            extractPrice(data);

        if (!Number.isFinite(price) || price <= 0) {

            throw new Error(
                "API response did not contain a valid price"
            );
        }

        const date =
            extractDate(data) ||
            new Date().toISOString();

        const market =
            extractMarketName(data);

        const result = {

            crop,

            price,

            minPrice:
                Number(
                    data.min_price ??
                    data.minPrice ??
                    data.data?.min_price ??
                    price * 0.9
                ),

            maxPrice:
                Number(
                    data.max_price ??
                    data.maxPrice ??
                    data.data?.max_price ??
                    price * 1.1
                ),

            date,

            source: "live",

            market
        };

        savePriceRecord(
            crop,
            price,
            "live",
            date
        );

        return result;

    } catch (error) {

        console.warn(
            "Live market fetch failed:",
            error
        );

        return null;
    }
}


/* =========================================================
   LOAD MARKET DATA
========================================================= */

async function loadMarketData(crop) {

    setConnectionStatus(
        getTranslation("readyConnection")
    );

    const liveData =
        await fetchMarketData(crop);

    let data;

    if (liveData) {

        data = liveData;

        setConnectionStatus(
            getTranslation("liveConnected")
        );

    } else {

        data =
            getFallbackData(crop);

        setConnectionStatus(
            getTranslation("fallbackConnection")
        );
    }

    currentMarketData = data;

    updateMarketUI(data);

    return data;
}


/* =========================================================
   MARKET UI
========================================================= */

function updateMarketUI(data) {

    if (!data) {
        return;
    }

    const price =
        Number(data.price);

    const previousPrice =
        getPreviousPrice(
            data.crop,
            data.date
        );

    const trend =
        calculateTrend(
            price,
            previousPrice
        );

    setText(
        "currentPrice",
        formatPrice(price)
    );

    setText(
        "marketTrend",
        trend.label
    );

    setText(
        "demand",
        calculateDemand(
            price,
            data.crop
        )
    );

    updateForecast(
        data,
        trend
    );

    updateMarketTable(
        data
    );

    updateDecision(
        data,
        trend
    );

    updateLatestDate(
        data
    );
}


/* =========================================================
   TREND
========================================================= */

function calculateTrend(current, previous) {

    if (
        !Number.isFinite(current) ||
        !Number.isFinite(previous) ||
        previous <= 0
    ) {

        return {

            direction: "stable",

            percentage: 0,

            label:
                getTranslation("stable"),

            explanation:
                getTranslation("priceStable")
        };
    }

    const percentage =
        ((current - previous) /
            previous) *
        100;

    if (percentage > 2) {

        return {

            direction: "up",

            percentage,

            label:
                `${getTranslation("rising")} ↑ ${Math.abs(percentage).toFixed(1)}%`,

            explanation:
                getTranslation("priceUp")
        };
    }

    if (percentage < -2) {

        return {

            direction: "down",

            percentage,

            label:
                `${getTranslation("falling")} ↓ ${Math.abs(percentage).toFixed(1)}%`,

            explanation:
                getTranslation("priceDown")
        };
    }

    return {

        direction: "stable",

        percentage,

        label:
            getTranslation("stable"),

        explanation:
            getTranslation("priceStable")
    };
}


/* =========================================================
   DEMAND
========================================================= */

function calculateDemand(price, crop) {

    const fallback =
        FALLBACK_PRICES[crop] ||
        FALLBACK_PRICES.onion;

    const reference =
        fallback.price;

    if (price >= reference * 1.08) {

        return getTranslation("high");

    }

    if (price <= reference * 0.92) {

        return getTranslation("low");

    }

    return getTranslation("medium");
}


/* =========================================================
   FORECAST
========================================================= */

function calculateForecast(price, trend) {

    let change = 0;

    if (trend.direction === "up") {
        change = 0.06;
    } else if (trend.direction === "down") {
        change = -0.025;
    } else {
        change = 0.02;
    }

    return Math.round(
        price * (1 + change)
    );
}


function updateForecast(data, trend) {

    const forecast =
        calculateForecast(
            data.price,
            trend
        );

    setText(
        "forecastPrice",
        formatPrice(forecast)
    );

    setText(
        "forecastMessage",
        `${trend.explanation} ${getTranslation("lastUpdated")}: ${formatDate(data.date)}.`
    );
}


/* =========================================================
   MARKET TABLE
========================================================= */

function updateMarketTable(data) {

    const table =
        getElement("marketTable");

    if (!table) {
        return;
    }

    const status =
        data.source === "live"
            ? getTranslation("latest")
            : data.source === "stored"
                ? getTranslation("latestStored")
                : getTranslation("estimated");

    table.innerHTML = `

        <tr>

            <td>
                📍 ${escapeHTML(
                    data.market ||
                    "Kopargaon APMC"
                )}
            </td>

            <td>
                <strong>
                    ${formatPrice(data.price)}
                </strong>
            </td>

            <td>
                ${status}
            </td>

        </tr>

    `;
}


/* =========================================================
   LATEST DATE
========================================================= */

function updateLatestDate(data) {

    const section =
        getElement("market");

    if (!section) {
        return;
    }

    let dateElement =
        getElement("latestMarketDate");

    if (!dateElement) {

        dateElement =
            document.createElement("div");

        dateElement.id =
            "latestMarketDate";

        dateElement.style.marginTop =
            "14px";

        dateElement.style.fontSize =
            "13px";

        dateElement.style.color =
            "#667278";

        section.appendChild(
            dateElement
        );
    }

    dateElement.textContent =
        `${getTranslation("lastUpdated")}: ${formatDate(data.date)}`;
}


/* =========================================================
   DECISION ENGINE
========================================================= */

function updateDecision(data, trend) {

    const currentPrice =
        Number(data.price);

    const futurePrice =
        calculateForecast(
            currentPrice,
            trend
        );

    const transportPrice =
        Math.round(
            currentPrice *
            getTransportMultiplier(
                trend
            )
        );

    setText(
        "sellReturn",
        formatPrice(currentPrice)
    );

    setText(
        "storeReturn",
        formatPrice(futurePrice)
    );

    setText(
        "transportReturn",
        formatPrice(transportPrice)
    );

    const decision =
        decideBestAction(
            currentPrice,
            futurePrice,
            transportPrice,
            trend
        );

    setText(
        "bestAction",
        decision.action
    );

    setText(
        "recommendationReason",
        decision.reason
    );
}


function getTransportMultiplier(trend) {

    if (trend.direction === "up") {
        return 1.04;
    }

    if (trend.direction === "down") {
        return 0.98;
    }

    return 1.02;
}


function decideBestAction(
    currentPrice,
    futurePrice,
    transportPrice,
    trend
) {

    if (futurePrice >
        currentPrice * 1.04) {

        return {

            action:
                getTranslation("store"),

            reason:
                getTranslation(
                    "storeRecommendation"
                )
        };
    }

    if (transportPrice >
        currentPrice * 1.03) {

        return {

            action:
                getTranslation("transport"),

            reason:
                getTranslation(
                    "transportRecommendation"
                )
        };
    }

    return {

        action:
            getTranslation("sellNow"),

        reason:
            getTranslation(
                "sellRecommendation"
            )
    };
}


/* =========================================================
   CONNECTION STATUS
========================================================= */

function setConnectionStatus(message) {

    setText(
        "connectionStatus",
        message
    );
}


/* =========================================================
   LANGUAGE
========================================================= */

function applyLanguage(language) {

    if (!translations[language]) {
        language = "en";
    }

    currentLanguage =
        language;

    localStorage.setItem(
        "smartAgriLanguage",
        language
    );

    document.documentElement.lang =
        language;

    applyStaticTranslations();

    if (currentMarketData) {

        updateMarketUI(
            currentMarketData
        );

    } else {

        setConnectionStatus(
            getTranslation(
                "readyConnection"
            )
        );
    }
}


function applyStaticTranslations() {

    const language =
        currentLanguage;

    const t =
        translations[language];

    /* Navigation */

    const navLinks =
        document.querySelectorAll(
            "nav a"
        );

    if (navLinks.length >= 4) {

        navLinks[0].textContent =
            t.dashboard;

        navLinks[1].textContent =
            t.market;

        navLinks[2].textContent =
            t.forecast;

        navLinks[3].textContent =
            t.decision;
    }

    /* Hero */

    const heroLabel =
        document.querySelector(
            ".hero-label"
        );

    if (heroLabel) {
        heroLabel.textContent =
            t.heroLabel;
    }

    const heroTitle =
        document.querySelector(
            "#dashboard h1"
        );

    if (heroTitle) {

        heroTitle.innerHTML =
            `${t.heroTitle}
             <span>${t.heroTitleSpan}</span>`;
    }

    const heroDescription =
        document.querySelector(
            "#dashboard p"
        );

    if (heroDescription) {
        heroDescription.textContent =
            t.heroDescription;
    }

    const heroTags =
        document.querySelectorAll(
            ".hero-tags span"
        );

    if (heroTags.length >= 3) {

        heroTags[0].textContent =
            t.marketIntelligence;

        heroTags[1].textContent =
            t.aiForecasting;

        heroTags[2].textContent =
            t.liveData;
    }

    /* Crop Selection */

    setHeading(
        "#crop-selection",
        t.selectCrop,
        t.selectCropDescription
    );

    const cropLabel =
        document.querySelector(
            'label[for="crop"]'
        );

    if (cropLabel) {
        cropLabel.textContent =
            t.crop;
    }

    const cropSelect =
        getElement("crop");

    if (cropSelect) {

        if (cropSelect.options.length >= 2) {

            cropSelect.options[0].text =
                t.onion;

            cropSelect.options[1].text =
                t.wheat;
        }
    }

    const analyzeButton =
        getElement("analyzeButton");

    if (analyzeButton) {

        analyzeButton.childNodes[0].textContent =
            t.analyzeMarket + " ";
    }

    /* Market */

    setHeading(
        "#market",
        t.marketSnapshot,
        t.currentMarketConditions
    );

    setCardText(
        "#market",
        0,
        t.currentPrice,
        t.perQuintal
    );

    setCardText(
        "#market",
        1,
        t.marketTrend,
        t.priceMovement
    );

    setCardText(
        "#market",
        2,
        t.demand,
        t.currentMarketIndicator
    );

    /* Forecast */

    setHeading(
        "#forecast",
        t.aiPriceForecast,
        t.forecastDescription
    );

    const forecastLabel =
        document.querySelector(
            ".forecast-label"
        );

    if (forecastLabel) {
        forecastLabel.textContent =
            t.expectedFuturePrice;
    }

    if (!currentMarketData) {

        setText(
            "forecastMessage",
            t.forecastWaiting
        );
    }

    /* Market Comparison */

    setHeading(
        "#market-comparison",
        t.marketComparison,
        t.liveKopargaon
    );

    const headers =
        document.querySelectorAll(
            "#market-comparison th"
        );

    if (headers.length >= 3) {

        headers[0].textContent =
            t.marketName;

        headers[1].textContent =
            t.pricePerQuintal;

        headers[2].textContent =
            t.status;
    }

    /* Decision */

    setHeading(
        "#decision",
        t.smartSellingDecision,
        t.decisionDescription
    );

    const decisionCards =
        document.querySelectorAll(
            ".decision-card"
        );

    if (decisionCards.length >= 3) {

        decisionCards[0].querySelector("h3").textContent =
            t.sellNow;

        decisionCards[0].querySelector("p").textContent =
            t.currentPriceLabel;

        decisionCards[1].querySelector("h3").textContent =
            t.store;

        decisionCards[1].querySelector("p").textContent =
            t.estimatedFuturePrice;

        decisionCards[2].querySelector("h3").textContent =
            t.transport;

        decisionCards[2].querySelector("p").textContent =
            t.estimatedPrice;
    }

    const recommendationLabel =
        document.querySelector(
            ".recommendation-label"
        );

    if (recommendationLabel) {

        recommendationLabel.textContent =
            t.smartRecommendation;
    }

    const recommendationTitle =
        document.querySelector(
            "#recommendation h2"
        );

    if (recommendationTitle) {

        recommendationTitle.textContent =
            t.recommendedAction;
    }

    if (!currentMarketData) {

        setText(
            "bestAction",
            t.analyzeMarket
        );

        setText(
            "recommendationReason",
            t.analyzeMarketMessage
        );
    }

    /* Connection */

    const connectionHeading =
        document.querySelector(
            "#offline-status h2"
        );

    if (connectionHeading) {

        connectionHeading.textContent =
            t.liveConnection;
    }

    const connectionSource =
        document.querySelector(
            "#offline-status span"
        );

    if (connectionSource) {

        connectionSource.textContent =
            t.dataSource;
    }
}


/* =========================================================
   HEADING HELPER
========================================================= */

function setHeading(
    sectionSelector,
    title,
    description
) {

    const section =
        document.querySelector(
            sectionSelector
        );

    if (!section) {
        return;
    }

    const heading =
        section.querySelector(
            ".section-heading"
        );

    if (!heading) {
        return;
    }

    const titleElement =
        heading.querySelector("h2");

    const descriptionElement =
        heading.querySelector("p");

    if (titleElement) {
        titleElement.textContent =
            title;
    }

    if (descriptionElement) {
        descriptionElement.textContent =
            description;
    }
}


function setCardText(
    sectionSelector,
    index,
    title,
    description
) {

    const section =
        document.querySelector(
            sectionSelector
        );

    if (!section) {
        return;
    }

    const cards =
        section.querySelectorAll(
            ".card"
        );

    const card =
        cards[index];

    if (!card) {
        return;
    }

    const titleElement =
        card.querySelector("h3");

    const descriptionElement =
        card.querySelector(
            ".card-description"
        );

    if (titleElement) {
        titleElement.textContent =
            title;
    }

    if (descriptionElement) {
        descriptionElement.textContent =
            description;
    }
}


/* =========================================================
   ESCAPE HTML
========================================================= */

function escapeHTML(value) {

    return String(value)

        .replace(
            /&/g,
            "&amp;"
        )

        .replace(
            /</g,
            "&lt;"
        )

        .replace(
            />/g,
            "&gt;"
        )

        .replace(
            /"/g,
            "&quot;"
        )

        .replace(
            /'/g,
            "&#039;"
        );
}


/* =========================================================
   ANALYZE BUTTON
========================================================= */

async function analyzeMarket() {

    const cropSelect =
        getElement("crop");

    if (!cropSelect) {
        return;
    }

    selectedCrop =
        cropSelect.value ||
        "onion";

    const button =
        getElement("analyzeButton");

    if (button) {

        button.disabled = true;

        button.style.opacity =
            "0.7";

        button.style.cursor =
            "wait";
    }

    try {

        const data =
            await loadMarketData(
                selectedCrop
            );

        if (data) {

            const marketSection =
                getElement("market");

            if (marketSection) {

                marketSection.scrollIntoView({
                    behavior: "smooth",
                    block: "start"
                });
            }
        }

    } finally {

        if (button) {

            button.disabled = false;

            button.style.opacity =
                "1";

            button.style.cursor =
                "pointer";
        }
    }
}


/* =========================================================
   AUTO REFRESH
========================================================= */

async function refreshCurrentMarket() {

    if (!selectedCrop) {
        return;
    }

    const data =
        await fetchMarketData(
            selectedCrop
        );

    if (data) {

        currentMarketData =
            data;

        updateMarketUI(
            data
        );

        setConnectionStatus(
            getTranslation(
                "liveConnected"
            )
        );

    }
}


/* =========================================================
   EVENT LISTENERS
========================================================= */

function initializeEvents() {

    const languageSelect =
        getElement("languageSelect");

    if (languageSelect) {

        languageSelect.value =
            currentLanguage;

        languageSelect.addEventListener(
            "change",
            event => {

                applyLanguage(
                    event.target.value
                );
            }
        );
    }


    const cropSelect =
        getElement("crop");

    if (cropSelect) {

        selectedCrop =
            cropSelect.value ||
            "onion";

        cropSelect.addEventListener(
            "change",
            event => {

                selectedCrop =
                    event.target.value;

                currentMarketData =
                    null;

                setText(
                    "currentPrice",
                    "--"
                );

                setText(
                    "marketTrend",
                    "--"
                );

                setText(
                    "demand",
                    "--"
                );

                setText(
                    "forecastPrice",
                    "--"
                );

                setText(
                    "forecastMessage",
                    getTranslation(
                        "forecastWaiting"
                    )
                );
            }
        );
    }


    const analyzeButton =
        getElement("analyzeButton");

    if (analyzeButton) {

        analyzeButton.addEventListener(
            "click",
            analyzeMarket
        );
    }
}


/* =========================================================
   INITIALIZATION
========================================================= */

async function initializeApp() {

    initializeEvents();

    applyLanguage(
        currentLanguage
    );

    selectedCrop =
        getElement("crop")?.value ||
        "onion";

    /*
       Automatically load the selected crop.
       This means the page does not remain
       empty until the user clicks Analyze.
    */

    await loadMarketData(
        selectedCrop
    );

    /*
       Automatically check for a newer price
       every five minutes.
    */

    setInterval(
        refreshCurrentMarket,
        REFRESH_INTERVAL
    );
}


/* =========================================================
   START APPLICATION
========================================================= */

document.addEventListener(
    "DOMContentLoaded",
    initializeApp
);
