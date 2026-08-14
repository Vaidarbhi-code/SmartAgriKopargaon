/* =========================================================
   SMART AGRI KOPARGAON
   FRONTEND JAVASCRIPT
========================================================= */

document.addEventListener("DOMContentLoaded", () => {

    /* =====================================================
       ELEMENTS
    ===================================================== */

    const languageSelect = document.getElementById("languageSelect");
    const cropSelect = document.getElementById("crop");
    const analyzeButton = document.getElementById("analyzeButton");

    const currentPrice = document.getElementById("currentPrice");
    const marketTrend = document.getElementById("marketTrend");
    const demand = document.getElementById("demand");

    const forecastPrice = document.getElementById("forecastPrice");
    const forecastMessage = document.getElementById("forecastMessage");

    const marketTable = document.getElementById("marketTable");

    const sellReturn = document.getElementById("sellReturn");
    const storeReturn = document.getElementById("storeReturn");
    const transportReturn = document.getElementById("transportReturn");

    const bestAction = document.getElementById("bestAction");
    const recommendationReason =
        document.getElementById("recommendationReason");

    const connectionStatus =
        document.getElementById("connectionStatus");


    /* =====================================================
       CONFIGURATION
    ===================================================== */

    const API_URL = "/api/market";

    const REFRESH_INTERVAL = 5 * 60 * 1000;

    let currentLanguage = "en";

    let latestMarketData = null;


    /* =====================================================
       LANGUAGE TRANSLATIONS
    ===================================================== */

    const translations = {

        en: {

            dashboard: "Dashboard",
            market: "Market",
            forecast: "Forecast",
            decision: "Smart Decision",

            location: "📍 Kopargaon",

            heroLabel: "DATA-DRIVEN AGRICULTURE",

            heroTitle1: "Smarter Market Decisions.",
            heroTitle2: "Better Farm Returns.",

            heroDescription:
                "Agricultural market intelligence designed to help farmers in Kopargaon decide when, where and how to sell their produce.",

            marketIntelligence: "📊 Market Intelligence",
            aiForecasting: "🤖 AI Forecasting",
            liveData: "📡 Live Data",

            selectCrop: "Select Your Crop",

            selectCropDescription:
                "Select a crop to analyze current live market conditions in Kopargaon.",

            crop: "Crop",

            onion: "🧅 Onion",
            wheat: "🌾 Wheat",

            analyze: "Analyze Market",

            marketSnapshot: "Market Snapshot",

            marketSnapshotDescription:
                "Current market conditions for the selected crop.",

            currentPrice: "Current Price",
            perQuintal: "Per Quintal",

            marketTrend: "Market Trend",
            priceMovement: "Price movement",

            demand: "Demand",
            currentMarketIndicator: "Current market indicator",

            aiPriceForecast: "AI Price Forecast",

            aiForecastDescription:
                "Estimated future price based on current market information.",

            expectedFuturePrice: "EXPECTED FUTURE PRICE",

            forecastDefault:
                "Select a crop and analyze the market to generate a forecast.",

            marketComparison: "Market Comparison",

            marketComparisonDescription:
                "Latest Kopargaon market information.",

            marketName: "Market",
            pricePerQuintal: "Price / Quintal",
            status: "Status",

            kopargaonAPMC: "📍 Kopargaon APMC",

            smartSellingDecision: "Smart Selling Decision",

            smartSellingDescription:
                "Compare possible selling strategies using current market information.",

            sellNow: "Sell Now",
            currentPriceLabel: "Current Price",

            store: "Store",
            estimatedFuturePrice: "Estimated Future Price",

            transport: "Transport",
            estimatedPrice: "Estimated Price",

            smartRecommendation: "SMART RECOMMENDATION",
            recommendedAction: "Recommended Action",

            analyzeMarket:
                "Analyze the market to receive a recommendation.",

            liveDataConnection: "Live Data Connection",

            readyConnection:
                "Ready to connect to live market data.",

            connectionDescription:
                "Market prices are retrieved through the SmartAgri backend from data.gov.in / Agmarknet.",

            waiting: "Waiting",
            live: "Live",
            latest: "Latest",
            cached: "Cached",
            estimated: "Estimated",

            increasing: "Increasing",
            decreasing: "Decreasing",
            stable: "Stable",

            high: "High",
            medium: "Medium",
            low: "Low",

            sell: "Sell Now",
            storeAction: "Store",
            transportAction: "Transport",

            priceUnavailable:
                "Using the latest saved market value.",

            apiError:
                "Live source temporarily unavailable. Showing the latest saved market value.",

            noSavedData:
                "No saved price exists yet. Please try again after the market source becomes available.",

            lastUpdated: "Latest data",

            forecastUp:
                "Prices are showing positive movement. Holding may provide a better return if the trend continues.",

            forecastDown:
                "Prices are showing downward movement. Selling sooner may reduce risk.",

            forecastStable:
                "Prices are relatively stable. The best action depends on your storage and transport costs.",

            recommendationSell:
                "Selling now is the strongest option based on the current price.",

            recommendationStore:
                "Storing may provide a better return if the expected price increase continues.",

            recommendationTransport:
                "Transporting to another market may provide a better estimated return.",

            recommendationStable:
                "The market is relatively stable. Compare storage and transport costs before deciding.",

            footerDescription:
                "Live Market Data • Multilingual • Mobile-friendly",

            footerCopyright:
                "Smart Agriculture Market Intelligence System"

        },


        mr: {

            dashboard: "डॅशबोर्ड",
            market: "बाजार",
            forecast: "अंदाज",
            decision: "स्मार्ट निर्णय",

            location: "📍 कोपरगाव",

            heroLabel: "डेटावर आधारित शेती",

            heroTitle1: "स्मार्ट बाजार निर्णय.",
            heroTitle2: "शेतीत चांगला नफा.",

            heroDescription:
                "कोपरगावमधील शेतकऱ्यांना माल कधी, कुठे आणि कसा विकायचा याचा निर्णय घेण्यासाठी कृषी बाजार माहिती.",

            marketIntelligence: "📊 बाजार माहिती",
            aiForecasting: "🤖 AI अंदाज",
            liveData: "📡 थेट माहिती",

            selectCrop: "पिक निवडा",

            selectCropDescription:
                "कोपरगावमधील निवडलेल्या पिकाच्या सध्याच्या बाजार परिस्थितीचे विश्लेषण करा.",

            crop: "पिक",

            onion: "🧅 कांदा",
            wheat: "🌾 गहू",

            analyze: "बाजाराचे विश्लेषण करा",

            marketSnapshot: "बाजार स्थिती",

            marketSnapshotDescription:
                "निवडलेल्या पिकाची सध्याची बाजार परिस्थिती.",

            currentPrice: "सध्याचा भाव",
            perQuintal: "प्रति क्विंटल",

            marketTrend: "बाजार कल",
            priceMovement: "भावातील बदल",

            demand: "मागणी",
            currentMarketIndicator: "सध्याचे बाजार संकेत",

            aiPriceForecast: "AI भाव अंदाज",

            aiForecastDescription:
                "सध्याच्या बाजार माहितीवर आधारित अंदाजे भविष्यातील भाव.",

            expectedFuturePrice: "अपेक्षित भविष्यातील भाव",

            forecastDefault:
                "अंदाज तयार करण्यासाठी पिक निवडा आणि बाजाराचे विश्लेषण करा.",

            marketComparison: "बाजार तुलना",

            marketComparisonDescription:
                "कोपरगावमधील नवीनतम बाजार माहिती.",

            marketName: "बाजार",
            pricePerQuintal: "भाव / क्विंटल",
            status: "स्थिती",

            kopargaonAPMC: "📍 कोपरगाव APMC",

            smartSellingDecision: "स्मार्ट विक्री निर्णय",

            smartSellingDescription:
                "सध्याच्या बाजार माहितीवर आधारित विविध विक्री पर्यायांची तुलना करा.",

            sellNow: "आता विक्री करा",
            currentPriceLabel: "सध्याचा भाव",

            store: "साठवणूक करा",
            estimatedFuturePrice: "अंदाजे भविष्यातील भाव",

            transport: "वाहतूक करा",
            estimatedPrice: "अंदाजे भाव",

            smartRecommendation: "स्मार्ट शिफारस",
            recommendedAction: "शिफारस केलेली कृती",

            analyzeMarket:
                "शिफारस मिळवण्यासाठी बाजाराचे विश्लेषण करा.",

            liveDataConnection: "थेट डेटा कनेक्शन",

            readyConnection:
                "थेट बाजार माहितीशी जोडण्यासाठी तयार.",

            connectionDescription:
                "बाजार भाव SmartAgri backend द्वारे data.gov.in / Agmarknet मधून घेतले जातात.",

            waiting: "प्रतीक्षा",
            live: "थेट",
            latest: "नवीनतम",
            cached: "साठवलेला",
            estimated: "अंदाजे",

            increasing: "वाढत आहे",
            decreasing: "घटत आहे",
            stable: "स्थिर",

            high: "जास्त",
            medium: "मध्यम",
            low: "कमी",

            sell: "आता विक्री",
            storeAction: "साठवणूक",
            transportAction: "वाहतूक",

            priceUnavailable:
                "नवीनतम जतन केलेला बाजार भाव दाखवत आहे.",

            apiError:
                "थेट बाजार स्रोत सध्या उपलब्ध नाही. नवीनतम जतन केलेला भाव दाखवत आहे.",

            noSavedData:
                "अद्याप कोणताही भाव जतन केलेला नाही. बाजार स्रोत उपलब्ध झाल्यावर पुन्हा प्रयत्न करा.",

            lastUpdated: "नवीनतम माहिती",

            forecastUp:
                "भाव वाढण्याचा कल दिसत आहे. हा कल कायम राहिल्यास साठवणूक केल्याने चांगला परतावा मिळू शकतो.",

            forecastDown:
                "भाव कमी होण्याचा कल दिसत आहे. जोखीम कमी करण्यासाठी लवकर विक्री करणे योग्य ठरू शकते.",

            forecastStable:
                "भाव तुलनेने स्थिर आहेत. साठवणूक आणि वाहतूक खर्चाचा विचार करून निर्णय घ्या.",

            recommendationSell:
                "सध्याच्या भावानुसार आत्ताच विक्री करणे चांगला पर्याय आहे.",

            recommendationStore:
                "भाव वाढण्याचा अंदाज कायम राहिल्यास साठवणूक केल्याने अधिक परतावा मिळू शकतो.",

            recommendationTransport:
                "दुसऱ्या बाजारात वाहतूक केल्यास अधिक अंदाजे परतावा मिळू शकतो.",

            recommendationStable:
                "बाजार तुलनेने स्थिर आहे. निर्णय घेण्यापूर्वी साठवणूक आणि वाहतूक खर्च तपासा.",

            footerDescription:
                "थेट बाजार माहिती • बहुभाषिक • मोबाइलसाठी योग्य",

            footerCopyright:
                "स्मार्ट कृषी बाजार माहिती प्रणाली"

        },


        hi: {

            dashboard: "डैशबोर्ड",
            market: "बाज़ार",
            forecast: "पूर्वानुमान",
            decision: "स्मार्ट निर्णय",

            location: "📍 कोपरगांव",

            heroLabel: "डेटा आधारित कृषि",

            heroTitle1: "स्मार्ट बाजार निर्णय।",
            heroTitle2: "बेहतर कृषि लाभ।",

            heroDescription:
                "कोपरगांव के किसानों को अपनी फसल कब, कहाँ और कैसे बेचनी है इसका निर्णय लेने में मदद करने वाली कृषि बाजार जानकारी।",

            marketIntelligence: "📊 बाजार जानकारी",
            aiForecasting: "🤖 AI पूर्वानुमान",
            liveData: "📡 लाइव डेटा",

            selectCrop: "फसल चुनें",

            selectCropDescription:
                "कोपरगांव में चुनी गई फसल की वर्तमान बाजार स्थिति का विश्लेषण करें।",

            crop: "फसल",

            onion: "🧅 प्याज़",
            wheat: "🌾 गेहूं",

            analyze: "बाज़ार का विश्लेषण करें",

            marketSnapshot: "बाज़ार स्थिति",

            marketSnapshotDescription:
                "चुनी गई फसल की वर्तमान बाजार स्थिति।",

            currentPrice: "वर्तमान भाव",
            perQuintal: "प्रति क्विंटल",

            marketTrend: "बाज़ार रुझान",
            priceMovement: "भाव में बदलाव",

            demand: "मांग",
            currentMarketIndicator: "वर्तमान बाजार संकेत",

            aiPriceForecast: "AI भाव पूर्वानुमान",

            aiForecastDescription:
                "वर्तमान बाजार जानकारी के आधार पर अनुमानित भविष्य का भाव।",

            expectedFuturePrice: "अनुमानित भविष्य का भाव",

            forecastDefault:
                "पूर्वानुमान बनाने के लिए फसल चुनें और बाजार का विश्लेषण करें।",

            marketComparison: "बाज़ार तुलना",

            marketComparisonDescription:
                "कोपरगांव की नवीनतम बाजार जानकारी।",

            marketName: "बाज़ार",
            pricePerQuintal: "भाव / क्विंटल",
            status: "स्थिति",

            kopargaonAPMC: "📍 कोपरगांव APMC",

            smartSellingDecision: "स्मार्ट बिक्री निर्णय",

            smartSellingDescription:
                "वर्तमान बाजार जानकारी के आधार पर बिक्री के विकल्पों की तुलना करें।",

            sellNow: "अभी बेचें",
            currentPriceLabel: "वर्तमान भाव",

            store: "भंडारण करें",
            estimatedFuturePrice: "अनुमानित भविष्य का भाव",

            transport: "परिवहन करें",
            estimatedPrice: "अनुमानित भाव",

            smartRecommendation: "स्मार्ट सिफारिश",
            recommendedAction: "अनुशंसित कार्रवाई",

            analyzeMarket:
                "सिफारिश प्राप्त करने के लिए बाजार का विश्लेषण करें।",

            liveDataConnection: "लाइव डेटा कनेक्शन",

            readyConnection:
                "लाइव बाजार डेटा से जुड़ने के लिए तैयार।",

            connectionDescription:
                "बाजार भाव SmartAgri backend के माध्यम से data.gov.in / Agmarknet से प्राप्त किए जाते हैं।",

            waiting: "प्रतीक्षा",
            live: "लाइव",
            latest: "नवीनतम",
            cached: "सहेजा हुआ",
            estimated: "अनुमानित",

            increasing: "बढ़ रहा है",
            decreasing: "घट रहा है",
            stable: "स्थिर",

            high: "उच्च",
            medium: "मध्यम",
            low: "कम",

            sell: "अभी बेचें",
            storeAction: "भंडारण",
            transportAction: "परिवहन",

            priceUnavailable:
                "नवीनतम सहेजा हुआ बाजार भाव दिखाया जा रहा है।",

            apiError:
                "लाइव बाजार स्रोत अभी उपलब्ध नहीं है। नवीनतम सहेजा हुआ भाव दिखाया जा रहा है।",

            noSavedData:
                "अभी कोई भाव सहेजा नहीं गया है। बाजार स्रोत उपलब्ध होने पर फिर प्रयास करें।",

            lastUpdated: "नवीनतम डेटा",

            forecastUp:
                "भाव बढ़ने का रुझान दिखाई दे रहा है। यह रुझान जारी रहने पर भंडारण से बेहतर लाभ मिल सकता है।",

            forecastDown:
                "भाव कम होने का रुझान दिखाई दे रहा है। जोखिम कम करने के लिए जल्दी बिक्री बेहतर हो सकती है।",

            forecastStable:
                "भाव अपेक्षाकृत स्थिर हैं। भंडारण और परिवहन लागत को ध्यान में रखकर निर्णय लें।",

            recommendationSell:
                "वर्तमान भाव के आधार पर अभी बेचना सबसे अच्छा विकल्प है।",

            recommendationStore:
                "यदि भाव बढ़ने का अनुमान जारी रहता है तो भंडारण से बेहतर लाभ मिल सकता है।",

            recommendationTransport:
                "दूसरे बाजार में परिवहन करने से बेहतर अनुमानित लाभ मिल सकता है।",

            recommendationStable:
                "बाजार अपेक्षाकृत स्थिर है। निर्णय लेने से पहले भंडारण और परिवहन लागत की तुलना करें।",

            footerDescription:
                "लाइव बाजार डेटा • बहुभाषी • मोबाइल-अनुकूल",

            footerCopyright:
                "स्मार्ट कृषि बाजार सूचना प्रणाली"

        }

    };


    /* =====================================================
       HELPER: TEXT
    ===================================================== */

    function t(key) {

        return translations[currentLanguage]?.[key]
            || translations.en[key]
            || key;

    }


    /* =====================================================
       APPLY LANGUAGE
    ===================================================== */

    function applyLanguage() {

        const lang = translations[currentLanguage];

        if (!lang) return;


        /* Navigation */

        const navLinks = document.querySelectorAll("nav a");

        if (navLinks[0]) navLinks[0].textContent = t("dashboard");
        if (navLinks[1]) navLinks[1].textContent = t("market");
        if (navLinks[2]) navLinks[2].textContent = t("forecast");
        if (navLinks[3]) navLinks[3].textContent = t("decision");


        /* Location */

        const locationElement =
            document.querySelector(".location");

        if (locationElement) {
            locationElement.textContent = t("location");
        }


        /* Hero */

        const heroLabel =
            document.querySelector(".hero-label");

        if (heroLabel) {
            heroLabel.textContent = t("heroLabel");
        }


        const heroTitle =
            document.querySelector("#dashboard h1");

        if (heroTitle) {

            heroTitle.innerHTML =
                `${t("heroTitle1")} <span>${t("heroTitle2")}</span>`;

        }


        const heroDescription =
            document.querySelector("#dashboard p");

        if (heroDescription) {
            heroDescription.textContent =
                t("heroDescription");
        }


        const heroTags =
            document.querySelectorAll(".hero-tags span");

        if (heroTags[0]) heroTags[0].textContent =
            t("marketIntelligence");

        if (heroTags[1]) heroTags[1].textContent =
            t("aiForecasting");

        if (heroTags[2]) heroTags[2].textContent =
            t("liveData");


        /* Crop selection */

        const cropHeading =
            document.querySelector("#crop-selection h2");

        if (cropHeading)
            cropHeading.textContent = t("selectCrop");


        const cropDescription =
            document.querySelector("#crop-selection .section-heading p");

        if (cropDescription)
            cropDescription.textContent =
                t("selectCropDescription");


        const cropLabel =
            document.querySelector('label[for="crop"]');

        if (cropLabel)
            cropLabel.textContent = t("crop");


        if (cropSelect) {

            cropSelect.options[0].textContent = t("onion");
            cropSelect.options[1].textContent = t("wheat");

        }


        if (analyzeButton) {

            analyzeButton.childNodes[0].nodeValue =
                t("analyze") + " ";

        }


        /* Market */

        const marketHeading =
            document.querySelector("#market h2");

        if (marketHeading)
            marketHeading.textContent =
                t("marketSnapshot");


        const marketDescription =
            document.querySelector("#market .section-heading p");

        if (marketDescription)
            marketDescription.textContent =
                t("marketSnapshotDescription");


        const cards =
            document.querySelectorAll("#market .card");


        if (cards[0]) {

            cards[0].querySelector("h3").textContent =
                t("currentPrice");

            cards[0].querySelector(".card-description").textContent =
                t("perQuintal");

        }


        if (cards[1]) {

            cards[1].querySelector("h3").textContent =
                t("marketTrend");

            cards[1].querySelector(".card-description").textContent =
                t("priceMovement");

        }


        if (cards[2]) {

            cards[2].querySelector("h3").textContent =
                t("demand");

            cards[2].querySelector(".card-description").textContent =
                t("currentMarketIndicator");

        }


        /* Forecast */

        const forecastHeading =
            document.querySelector("#forecast h2");

        if (forecastHeading)
            forecastHeading.textContent =
                t("aiPriceForecast");


        const forecastDescription =
            document.querySelector("#forecast .section-heading p");

        if (forecastDescription)
            forecastDescription.textContent =
                t("aiForecastDescription");


        const forecastLabel =
            document.querySelector(".forecast-label");

        if (forecastLabel)
            forecastLabel.textContent =
                t("expectedFuturePrice");


        /* Market comparison */

        const comparisonHeading =
            document.querySelector("#market-comparison h2");

        if (comparisonHeading)
            comparisonHeading.textContent =
                t("marketComparison");


        const comparisonDescription =
            document.querySelector("#market-comparison .section-heading p");

        if (comparisonDescription)
            comparisonDescription.textContent =
                t("marketComparisonDescription");


        const tableHeaders =
            document.querySelectorAll("#market-comparison th");

        if (tableHeaders[0])
            tableHeaders[0].textContent = t("marketName");

        if (tableHeaders[1])
            tableHeaders[1].textContent = t("pricePerQuintal");

        if (tableHeaders[2])
            tableHeaders[2].textContent = t("status");


        /* Decision */

        const decisionHeading =
            document.querySelector("#decision h2");

        if (decisionHeading)
            decisionHeading.textContent =
                t("smartSellingDecision");


        const decisionDescription =
            document.querySelector("#decision .section-heading p");

        if (decisionDescription)
            decisionDescription.textContent =
                t("smartSellingDescription");


        const decisionCards =
            document.querySelectorAll(".decision-card");


        if (decisionCards[0]) {

            decisionCards[0].querySelector("h3").textContent =
                t("sellNow");

            decisionCards[0].querySelector("p").textContent =
                t("currentPriceLabel");

        }


        if (decisionCards[1]) {

            decisionCards[1].querySelector("h3").textContent =
                t("store");

            decisionCards[1].querySelector("p").textContent =
                t("estimatedFuturePrice");

        }


        if (decisionCards[2]) {

            decisionCards[2].querySelector("h3").textContent =
                t("transport");

            decisionCards[2].querySelector("p").textContent =
                t("estimatedPrice");

        }


        /* Recommendation */

        const recommendationLabel =
            document.querySelector(".recommendation-label");

        if (recommendationLabel)
            recommendationLabel.textContent =
                t("smartRecommendation");


        const recommendationHeading =
            document.querySelector("#recommendation h2");

        if (recommendationHeading)
            recommendationHeading.textContent =
                t("recommendedAction");


        /* Offline */

        const offlineHeading =
            document.querySelector("#offline-status h2");

        if (offlineHeading)
            offlineHeading.textContent =
                t("liveDataConnection");


        const offlineDescription =
            document.querySelector("#offline-status span");

        if (offlineDescription)
            offlineDescription.textContent =
                t("connectionDescription");


        /* Footer */

        const footerParagraphs =
            document.querySelectorAll("footer p");

        if (footerParagraphs[0])
            footerParagraphs[0].textContent =
                t("footerDescription");

        if (footerParagraphs[1])
            footerParagraphs[1].textContent =
                t("footerCopyright");


        /* Refresh dynamic values */

        if (latestMarketData) {

            renderMarketData(
                latestMarketData,
                true
            );

        } else {

            forecastMessage.textContent =
                t("forecastDefault");

            bestAction.textContent =
                t("analyzeMarket");

            recommendationReason.textContent =
                t("analyzeMarket");

        }

    }


    /* =====================================================
       LANGUAGE EVENT
    ===================================================== */

    if (languageSelect) {

        languageSelect.addEventListener("change", () => {

            currentLanguage =
                languageSelect.value || "en";

            localStorage.setItem(
                "smartAgriLanguage",
                currentLanguage
            );

            applyLanguage();

        });

    }


    /* =====================================================
       LOAD SAVED LANGUAGE
    ===================================================== */

    const savedLanguage =
        localStorage.getItem("smartAgriLanguage");

    if (
        savedLanguage &&
        translations[savedLanguage]
    ) {

        currentLanguage = savedLanguage;

        if (languageSelect)
            languageSelect.value =
                savedLanguage;

    }


    /* =====================================================
       NUMBER NORMALIZATION
    ===================================================== */

    function toNumber(value) {

        if (
            value === null ||
            value === undefined ||
            value === ""
        ) {
            return null;
        }

        if (typeof value === "number") {

            return Number.isFinite(value)
                ? value
                : null;

        }

        const cleaned =
            String(value)
                .replace(/,/g, "")
                .replace(/[^\d.-]/g, "");

        const number =
            parseFloat(cleaned);

        return Number.isFinite(number)
            ? number
            : null;

    }


    /* =====================================================
       PRICE FORMAT
    ===================================================== */

    function formatPrice(value) {

        const number = toNumber(value);

        if (number === null)
            return "--";

        return (
            "₹" +
            number.toLocaleString(
                "en-IN",
                {
                    maximumFractionDigits: 0
                }
            )
        );

    }


    /* =====================================================
       DATE FORMAT
    ===================================================== */

    function formatDate(dateValue) {

        if (!dateValue)
            return null;

        const date =
            new Date(dateValue);

        if (Number.isNaN(date.getTime()))
            return String(dateValue);

        return date.toLocaleDateString(
            "en-IN",
            {
                day: "2-digit",
                month: "short",
                year: "numeric"
            }
        );

    }


    /* =====================================================
       CACHE KEY
    ===================================================== */

    function getCacheKey(crop) {

        return `smartAgriMarket_${crop}`;

    }


    /* =====================================================
       SAVE MARKET DATA
    ===================================================== */

    function saveMarketData(crop, data) {

        try {

            localStorage.setItem(
                getCacheKey(crop),
                JSON.stringify({
                    ...data,
                    cachedAt: new Date().toISOString()
                })
            );

        } catch (error) {

            console.warn(
                "Unable to save market data:",
                error
            );

        }

    }


    /* =====================================================
       LOAD MARKET CACHE
    ===================================================== */

    function loadMarketData(crop) {

        try {

            const saved =
                localStorage.getItem(
                    getCacheKey(crop)
                );

            if (!saved)
                return null;

            return JSON.parse(saved);

        } catch (error) {

            console.warn(
                "Unable to load cached market data:",
                error
            );

            return null;

        }

    }


    /* =====================================================
       NORMALIZE API RESPONSE
    ===================================================== */

    function normalizeMarketResponse(raw, crop) {

        /*
           The backend may return different field names.
           This function accepts several common formats.
        */

        let data = raw;

        if (
            raw &&
            typeof raw === "object" &&
            raw.data &&
            typeof raw.data === "object"
        ) {

            data = raw.data;

        }


        if (
            Array.isArray(data)
        ) {

            data = data[0] || {};

        }


        const price =
            toNumber(
                data.price ??
                data.modal_price ??
                data.modalPrice ??
                data.current_price ??
                data.currentPrice ??
                data.min_price ??
                data.minPrice ??
                data.avg_price ??
                data.average_price ??
                data.value
            );


        const previousPrice =
            toNumber(
                data.previous_price ??
                data.previousPrice ??
                data.prev_price ??
                data.last_price ??
                data.lastPrice
            );


        const date =
            data.date ??
            data.price_date ??
            data.priceDate ??
            data.arrival_date ??
            data.arrivalDate ??
            data.updated_at ??
            data.updatedAt ??
            data.last_updated ??
            data.lastUpdated ??
            null;


        const trend =
            data.trend ??
            data.market_trend ??
            data.marketTrend ??
            null;


        const demandValue =
            data.demand ??
            data.demand_level ??
            data.demandLevel ??
            null;


        const market =
            data.market ??
            data.market_name ??
            data.marketName ??
            "Kopargaon APMC";


        return {

            crop,

            price,

            previousPrice,

            date,

            trend,

            demand: demandValue,

            market,

            raw

        };

    }


    /* =====================================================
       CALCULATE TREND
    ===================================================== */

    function calculateTrend(data) {

        if (data.trend) {

            const value =
                String(data.trend).toLowerCase();

            if (
                value.includes("up") ||
                value.includes("increase") ||
                value.includes("rise") ||
                value.includes("वाढ") ||
                value.includes("बढ़")
            ) {

                return "up";

            }

            if (
                value.includes("down") ||
                value.includes("decrease") ||
                value.includes("fall") ||
                value.includes("घट") ||
                value.includes("कम")
            ) {

                return "down";

            }

        }


        if (
            data.price !== null &&
            data.previousPrice !== null
        ) {

            if (data.price > data.previousPrice)
                return "up";

            if (data.price < data.previousPrice)
                return "down";

        }


        return "stable";

    }


    /* =====================================================
       CALCULATE DEMAND
    ===================================================== */

    function calculateDemand(data, trend) {

        if (data.demand) {

            const value =
                String(data.demand).toLowerCase();

            if (
                value.includes("high") ||
                value.includes("जास्त") ||
                value.includes("उच्च")
            ) {

                return "high";

            }

            if (
                value.includes("low") ||
                value.includes("कमी") ||
                value.includes("कम")
            ) {

                return "low";

            }

            return "medium";

        }


        if (trend === "up")
            return "high";

        if (trend === "down")
            return "low";

        return "medium";

    }


    /* =====================================================
       FORECAST CALCULATION
    ===================================================== */

    function calculateForecast(price, trend) {

        if (price === null)
            return null;


        let multiplier = 1;


        if (trend === "up") {

            multiplier = 1.08;

        } else if (trend === "down") {

            multiplier = 0.95;

        } else {

            multiplier = 1.02;

        }


        return Math.round(
            price * multiplier
        );

    }


    /* =====================================================
       TRANSPORT ESTIMATE
    ===================================================== */

    function calculateTransport(price) {

        if (price === null)
            return null;


        /*
           This is an estimated comparison value,
           not a live second-market quotation.
        */

        return Math.round(
            price * 1.04
        );

    }


    /* =====================================================
       DECISION ENGINE
    ===================================================== */

    function makeDecision(
        current,
        forecast,
        transport
    ) {

        if (
            current === null ||
            forecast === null
        ) {

            return {
                action: "unknown",
                reason: t("analyzeMarket")
            };

        }


        const sell = current;

        const store = forecast;

        const transportValue =
            transport ?? current;


        const values = [

            {
                action: "sell",
                value: sell
            },

            {
                action: "store",
                value: store
            },

            {
                action: "transport",
                value: transportValue
            }

        ];


        values.sort(
            (a, b) =>
                b.value - a.value
        );


        const winner =
            values[0];


        if (winner.action === "sell") {

            return {

                action: "sell",

                reason:
                    t("recommendationSell")

            };

        }


        if (winner.action === "store") {

            return {

                action: "store",

                reason:
                    t("recommendationStore")

            };

        }


        if (winner.action === "transport") {

            return {

                action: "transport",

                reason:
                    t("recommendationTransport")

            };

        }


        return {

            action: "sell",

            reason:
                t("recommendationStable")

        };

    }


    /* =====================================================
       TREND TEXT
    ===================================================== */

    function getTrendText(trend) {

        if (trend === "up")
            return "↗ " + t("increasing");

        if (trend === "down")
            return "↘ " + t("decreasing");

        return "→ " + t("stable");

    }


    /* =====================================================
       DEMAND TEXT
    ===================================================== */

    function getDemandText(level) {

        if (level === "high")
            return "🔥 " + t("high");

        if (level === "low")
            return "↓ " + t("low");

        return "• " + t("medium");

    }


    /* =====================================================
       RENDER MARKET DATA
    ===================================================== */

    function renderMarketData(
        data,
        fromCache = false
    ) {

        if (!data)
            return;


        const price =
            toNumber(data.price);


        if (price === null) {

            currentPrice.textContent = "--";

            return;

        }


        const trend =
            calculateTrend(data);


        const demandLevel =
            calculateDemand(
                data,
                trend
            );


        const forecast =
            calculateForecast(
                price,
                trend
            );


        const transport =
            calculateTransport(
                price
            );


        const decision =
            makeDecision(
                price,
                forecast,
                transport
            );


        /* Current price */

        currentPrice.textContent =
            formatPrice(price);


        /* Trend */

        marketTrend.textContent =
            getTrendText(trend);


        /* Demand */

        demand.textContent =
            getDemandText(demandLevel);


        /* Forecast */

        if (forecast !== null) {

            forecastPrice.textContent =
                formatPrice(forecast);

        } else {

            forecastPrice.textContent =
                "--";

        }


        if (trend === "up") {

            forecastMessage.textContent =
                t("forecastUp");

        } else if (trend === "down") {

            forecastMessage.textContent =
                t("forecastDown");

        } else {

            forecastMessage.textContent =
                t("forecastStable");

        }


        /* Decision values */

        sellReturn.textContent =
            formatPrice(price);


        storeReturn.textContent =
            formatPrice(forecast);


        transportReturn.textContent =
            formatPrice(transport);


        /* Recommendation */

        if (decision.action === "sell") {

            bestAction.textContent =
                t("sell");

        } else if (decision.action === "store") {

            bestAction.textContent =
                t("storeAction");

        } else if (
            decision.action === "transport"
        ) {

            bestAction.textContent =
                t("transportAction");

        } else {

            bestAction.textContent =
                t("analyzeMarket");

        }


        recommendationReason.textContent =
            decision.reason;


        /* Market table */

        const dateText =
            formatDate(data.date);


        const sourceLabel =
            fromCache
                ? t("cached")
                : t("live");


        marketTable.innerHTML = `

            <tr>

                <td>
                    📍 ${data.market || t("kopargaonAPMC")}
                </td>

                <td>

                    <strong>
                        ${formatPrice(price)}
                    </strong>

                </td>

                <td>

                    <span>
                        ${sourceLabel}
                    </span>

                    ${
                        dateText
                        ? `
                            <br>
                            <small>
                                ${t("lastUpdated")}: ${dateText}
                            </small>
                          `
                        : ""
                    }

                </td>

            </tr>

        `;


        /* Connection */

        if (fromCache) {

            connectionStatus.textContent =
                t("priceUnavailable");

        } else {

            connectionStatus.textContent =
                `${t("live")} • ${dateText || t("latest")}`;

        }

    }


    /* =====================================================
       LOADING STATE
    ===================================================== */

    function setLoadingState() {

        if (analyzeButton) {

            analyzeButton.disabled = true;

            analyzeButton.style.opacity =
                "0.7";

            analyzeButton.style.cursor =
                "wait";

            analyzeButton.childNodes[0].nodeValue =
                "Analyzing... ";

        }

        connectionStatus.textContent =
            "Connecting to market data...";

    }


    /* =====================================================
       RESET BUTTON
    ===================================================== */

    function resetButton() {

        if (!analyzeButton)
            return;


        analyzeButton.disabled = false;

        analyzeButton.style.opacity =
            "1";

        analyzeButton.style.cursor =
            "pointer";


        analyzeButton.childNodes[0].nodeValue =
            t("analyze") + " ";

    }


    /* =====================================================
       FETCH MARKET DATA
    ===================================================== */

    async function fetchMarketData(
        crop
    ) {

        const url =
            `${API_URL}?crop=${encodeURIComponent(crop)}`;


        const response =
            await fetch(
                url,
                {
                    method: "GET",

                    headers: {
                        "Accept":
                            "application/json"
                    },

                    cache: "no-store"
                }
            );


        if (!response.ok) {

            throw new Error(
                `Market API returned ${response.status}`
            );

        }


        const raw =
            await response.json();


        const normalized =
            normalizeMarketResponse(
                raw,
                crop
            );


        if (
            normalized.price === null
        ) {

            throw new Error(
                "API response did not contain a valid price."
            );

        }


        return normalized;

    }


    /* =====================================================
       ANALYZE MARKET
    ===================================================== */

    async function analyzeMarket() {

        const crop =
            cropSelect?.value || "onion";


        setLoadingState();


        try {

            const data =
                await fetchMarketData(
                    crop
                );


            latestMarketData =
                data;


            saveMarketData(
                crop,
                data
            );


            renderMarketData(
                data,
                false
            );


        } catch (error) {

            console.error(
                "MARKET API ERROR:",
                error
            );


            /*
               IMPORTANT:
               Do not leave the interface showing
               "data unavailable" if we have an older
               successful value.
            */

            const cached =
                loadMarketData(
                    crop
                );


            if (cached) {

                latestMarketData =
                    cached;


                renderMarketData(
                    cached,
                    true
                );


                connectionStatus.textContent =
                    t("apiError");


            } else {

                /*
                   No cached value exists yet.
                   We still give the user a useful
                   explanation rather than leaving
                   every card blank.
                */

                currentPrice.textContent =
                    "--";

                marketTrend.textContent =
                    t("stable");

                demand.textContent =
                    t("medium");

                forecastPrice.textContent =
                    "--";

                sellReturn.textContent =
                    "--";

                storeReturn.textContent =
                    "--";

                transportReturn.textContent =
                    "--";

                bestAction.textContent =
                    t("analyzeMarket");

                recommendationReason.textContent =
                    t("noSavedData");

                forecastMessage.textContent =
                    t("noSavedData");


                marketTable.innerHTML = `

                    <tr>

                        <td>
                            📍 ${t("kopargaonAPMC")}
                        </td>

                        <td>
                            --
                        </td>

                        <td>
                            ${t("waiting")}
                        </td>

                    </tr>

                `;


                connectionStatus.textContent =
                    t("noSavedData");

            }

        } finally {

            resetButton();

        }

    }


    /* =====================================================
       BUTTON
    ===================================================== */

    if (analyzeButton) {

        analyzeButton.addEventListener(
            "click",
            analyzeMarket
        );

    }


    /* =====================================================
       CROP CHANGE
    ===================================================== */

    if (cropSelect) {

        cropSelect.addEventListener(
            "change",
            () => {

                const crop =
                    cropSelect.value;


                const cached =
                    loadMarketData(
                        crop
                    );


                if (cached) {

                    latestMarketData =
                        cached;


                    renderMarketData(
                        cached,
                        true
                    );

                } else {

                    latestMarketData =
                        null;

                    currentPrice.textContent =
                        "--";

                    marketTrend.textContent =
                        "--";

                    demand.textContent =
                        "--";

                    forecastPrice.textContent =
                        "--";

                    sellReturn.textContent =
                        "--";

                    storeReturn.textContent =
                        "--";

                    transportReturn.textContent =
                        "--";

                    bestAction.textContent =
                        t("analyzeMarket");

                    recommendationReason.textContent =
                        t("analyzeMarket");

                }

            }
        );

    }


    /* =====================================================
       AUTOMATIC REFRESH
    ===================================================== */

    setInterval(
        () => {

            const crop =
                cropSelect?.value || "onion";

            /*
               Refresh silently.
               The existing cached value stays visible
               while the new request is happening.
            */

            fetchMarketData(crop)
                .then(data => {

                    latestMarketData =
                        data;

                    saveMarketData(
                        crop,
                        data
                    );

                    renderMarketData(
                        data,
                        false
                    );

                })
                .catch(error => {

                    console.warn(
                        "Automatic market refresh failed:",
                        error
                    );

                });

        },
        REFRESH_INTERVAL
    );


    /* =====================================================
       INITIALIZATION
    ===================================================== */

    applyLanguage();


    /*
       Load saved data immediately.
       This means the dashboard can show the
       previous successful price before the API responds.
    */

    const initialCrop =
        cropSelect?.value || "onion";


    const initialCached =
        loadMarketData(
            initialCrop
        );


    if (initialCached) {

        latestMarketData =
            initialCached;


        renderMarketData(
            initialCached,
            true
        );

    }


    /*
       Then try to get today's/latest live value.
    */

    analyzeMarket();

});
