/* =========================================================
   SMARTAGRI KOPARGAON
   FRONTEND APPLICATION
========================================================= */

"use strict";


/* =========================================================
   TRANSLATIONS
========================================================= */

const translations = {

    en: {

        location: "📍 Kopargaon",

        navDashboard: "Dashboard",
        navMarket: "Market",
        navForecast: "Forecast",
        navDecision: "Smart Decision",

        heroLabel: "DATA-DRIVEN AGRICULTURE",

        heroTitle:
            "Smarter Market Decisions.",

        heroTitleSecond:
            "Better Farm Returns.",

        heroDescription:
            "Agricultural market intelligence designed to help farmers in Kopargaon decide when, where and how to sell their produce.",

        tagMarket:
            "📊 Market Intelligence",

        tagAI:
            "🤖 AI Forecasting",

        tagLive:
            "📡 Market Data",

        selectCrop:
            "Select Your Crop",

        selectCropDescription:
            "Select a crop to analyze current market conditions in Kopargaon.",

        cropLabel:
            "Crop",

        onion:
            "🧅 Onion",

        wheat:
            "🌾 Wheat",

        analyzeMarket:
            "Analyze Market",

        analyzing:
            "Analyzing...",

        marketSnapshot:
            "Market Snapshot",

        marketSnapshotDescription:
            "Current market conditions for the selected crop.",

        currentPriceLabel:
            "Current Price",

        perQuintal:
            "Per Quintal",

        marketTrendLabel:
            "Market Trend",

        priceMovement:
            "Price movement",

        demandLabel:
            "Demand",

        marketIndicator:
            "Current market indicator",

        forecastTitle:
            "AI Price Forecast",

        forecastDescription:
            "Estimated future price based on recent market information.",

        expectedFuturePrice:
            "EXPECTED FUTURE PRICE",

        forecastInitialMessage:
            "Select a crop and analyze the market to generate a forecast.",

        marketComparison:
            "Market Comparison",

        marketComparisonDescription:
            "Kopargaon market information.",

        marketColumn:
            "Market",

        priceColumn:
            "Price / Quintal",

        statusColumn:
            "Status",

        waiting:
            "Waiting",

        live:
            "Live",

        fallback:
            "Fallback",

        smartSellingDecision:
            "Smart Selling Decision",

        smartSellingDescription:
            "Compare possible selling strategies using current market information.",

        sellNow:
            "Sell Now",

        currentPriceDecision:
            "Current Price",

        store:
            "Store",

        estimatedFuturePrice:
            "Estimated Future Price",

        transport:
            "Transport",

        estimatedPrice:
            "Estimated Price",

        smartRecommendation:
            "SMART RECOMMENDATION",

        recommendedAction:
            "Recommended Action",

        analyzeMarketFirst:
            "Analyze the market",

        recommendationInitialMessage:
            "The system will analyze market data and provide a recommendation.",

        liveDataConnection:
            "Market Data Connection",

        connectionReady:
            "Ready to connect to market data.",

        dataSourceDescription:
            "Market prices are retrieved through the SmartAgri backend.",

        loadingMessage:
            "Connecting to the SmartAgri market service...",

        successfulMessage:
            "Market analysis completed successfully.",

        connectionError:
            "Unable to connect to the SmartAgri backend.",

        invalidResponse:
            "The backend returned an invalid response.",

        footerFeatures:
            "Market Intelligence • Multilingual • Mobile-friendly",

        footerCopyright:
            "Smart Agriculture Market Intelligence System"

    },


    mr: {

        location: "📍 कोपरगाव",

        navDashboard: "डॅशबोर्ड",
        navMarket: "बाजार",
        navForecast: "अंदाज",
        navDecision: "स्मार्ट निर्णय",

        heroLabel: "डेटावर आधारित शेती",

        heroTitle:
            "अधिक स्मार्ट बाजार निर्णय.",

        heroTitleSecond:
            "शेतीतून अधिक उत्पन्न.",

        heroDescription:
            "कोपरगावमधील शेतकऱ्यांना त्यांच्या मालाची विक्री केव्हा, कुठे आणि कशी करावी याचा निर्णय घेण्यासाठी कृषी बाजार माहिती.",

        tagMarket:
            "📊 बाजार माहिती",

        tagAI:
            "🤖 AI किंमत अंदाज",

        tagLive:
            "📡 बाजार माहिती",

        selectCrop:
            "तुमचे पीक निवडा",

        selectCropDescription:
            "कोपरगावमधील सध्याच्या बाजार परिस्थितीचे विश्लेषण करण्यासाठी पीक निवडा.",

        cropLabel:
            "पीक",

        onion:
            "🧅 कांदा",

        wheat:
            "🌾 गहू",

        analyzeMarket:
            "बाजाराचे विश्लेषण करा",

        analyzing:
            "विश्लेषण सुरू आहे...",

        marketSnapshot:
            "बाजाराचा आढावा",

        marketSnapshotDescription:
            "निवडलेल्या पिकासाठी सध्याची बाजार परिस्थिती.",

        currentPriceLabel:
            "सध्याचा भाव",

        perQuintal:
            "प्रति क्विंटल",

        marketTrendLabel:
            "बाजारातील कल",

        priceMovement:
            "किंमतीतील बदल",

        demandLabel:
            "मागणी",

        marketIndicator:
            "सध्याचा बाजार निर्देशांक",

        forecastTitle:
            "AI किंमत अंदाज",

        forecastDescription:
            "अलीकडील बाजार माहितीवर आधारित अंदाजे भविष्यातील किंमत.",

        expectedFuturePrice:
            "अपेक्षित भविष्यातील किंमत",

        forecastInitialMessage:
            "अंदाज मिळवण्यासाठी पीक निवडा आणि बाजाराचे विश्लेषण करा.",

        marketComparison:
            "बाजार तुलना",

        marketComparisonDescription:
            "कोपरगाव बाजाराची माहिती.",

        marketColumn:
            "बाजार",

        priceColumn:
            "प्रति क्विंटल भाव",

        statusColumn:
            "स्थिती",

        waiting:
            "प्रतीक्षा",

        live:
            "थेट",

        fallback:
            "पर्यायी",

        smartSellingDecision:
            "स्मार्ट विक्री निर्णय",

        smartSellingDescription:
            "सध्याच्या बाजार माहितीच्या आधारे विक्रीच्या पर्यायांची तुलना करा.",

        sellNow:
            "आता विक्री करा",

        currentPriceDecision:
            "सध्याचा भाव",

        store:
            "साठवणूक",

        estimatedFuturePrice:
            "अंदाजे भविष्यातील भाव",

        transport:
            "वाहतूक",

        estimatedPrice:
            "अंदाजे भाव",

        smartRecommendation:
            "स्मार्ट शिफारस",

        recommendedAction:
            "शिफारस केलेली कृती",

        analyzeMarketFirst:
            "बाजाराचे विश्लेषण करा",

        recommendationInitialMessage:
            "सिस्टम बाजार माहितीचे विश्लेषण करून शिफारस देईल.",

        liveDataConnection:
            "बाजार डेटा कनेक्शन",

        connectionReady:
            "बाजार डेटाशी जोडण्यासाठी तयार.",

        dataSourceDescription:
            "बाजारातील भाव SmartAgri बॅकएंडद्वारे प्राप्त केले जातात.",

        loadingMessage:
            "SmartAgri बाजार सेवेशी जोडले जात आहे...",

        successfulMessage:
            "बाजार विश्लेषण यशस्वीरित्या पूर्ण झाले.",

        connectionError:
            "SmartAgri बॅकएंडशी कनेक्ट होता आले नाही.",

        invalidResponse:
            "बॅकएंडकडून चुकीचा प्रतिसाद मिळाला.",

        footerFeatures:
            "बाजार माहिती • बहुभाषिक • मोबाईल-अनुकूल",

        footerCopyright:
            "स्मार्ट कृषी बाजार माहिती प्रणाली"

    },


    hi: {

        location: "📍 कोपरगांव",

        navDashboard: "डैशबोर्ड",
        navMarket: "बाज़ार",
        navForecast: "पूर्वानुमान",
        navDecision: "स्मार्ट निर्णय",

        heroLabel: "डेटा आधारित कृषि",

        heroTitle:
            "बेहतर बाजार निर्णय।",

        heroTitleSecond:
            "बेहतर कृषि आय।",

        heroDescription:
            "कोपरगांव के किसानों को अपनी फसल कब, कहाँ और कैसे बेचनी है, इसका निर्णय लेने में मदद करने वाली कृषि बाजार जानकारी।",

        tagMarket:
            "📊 बाजार जानकारी",

        tagAI:
            "🤖 AI मूल्य पूर्वानुमान",

        tagLive:
            "📡 बाजार डेटा",

        selectCrop:
            "अपनी फसल चुनें",

        selectCropDescription:
            "कोपरगांव की वर्तमान बाजार स्थिति का विश्लेषण करने के लिए फसल चुनें।",

        cropLabel:
            "फसल",

        onion:
            "🧅 प्याज़",

        wheat:
            "🌾 गेहूं",

        analyzeMarket:
            "बाज़ार का विश्लेषण करें",

        analyzing:
            "विश्लेषण हो रहा है...",

        marketSnapshot:
            "बाज़ार का अवलोकन",

        marketSnapshotDescription:
            "चयनित फसल की वर्तमान बाजार स्थिति।",

        currentPriceLabel:
            "वर्तमान भाव",

        perQuintal:
            "प्रति क्विंटल",

        marketTrendLabel:
            "बाजार का रुझान",

        priceMovement:
            "कीमत में बदलाव",

        demandLabel:
            "मांग",

        marketIndicator:
            "वर्तमान बाजार संकेतक",

        forecastTitle:
            "AI मूल्य पूर्वानुमान",

        forecastDescription:
            "हाल की बाजार जानकारी पर आधारित अनुमानित भविष्य की कीमत।",

        expectedFuturePrice:
            "अपेक्षित भविष्य की कीमत",

        forecastInitialMessage:
            "पूर्वानुमान प्राप्त करने के लिए फसल चुनें और बाजार का विश्लेषण करें।",

        marketComparison:
            "बाज़ार तुलना",

        marketComparisonDescription:
            "कोपरगांव बाजार की जानकारी।",

        marketColumn:
            "बाज़ार",

        priceColumn:
            "प्रति क्विंटल भाव",

        statusColumn:
            "स्थिति",

        waiting:
            "प्रतीक्षा",

        live:
            "लाइव",

        fallback:
            "वैकल्पिक",

        smartSellingDecision:
            "स्मार्ट बिक्री निर्णय",

        smartSellingDescription:
            "वर्तमान बाजार जानकारी के आधार पर बिक्री विकल्पों की तुलना करें।",

        sellNow:
            "अभी बेचें",

        currentPriceDecision:
            "वर्तमान भाव",

        store:
            "भंडारण",

        estimatedFuturePrice:
            "अनुमानित भविष्य का भाव",

        transport:
            "परिवहन",

        estimatedPrice:
            "अनुमानित भाव",

        smartRecommendation:
            "स्मार्ट सिफारिश",

        recommendedAction:
            "अनुशंसित कार्रवाई",

        analyzeMarketFirst:
            "बाज़ार का विश्लेषण करें",

        recommendationInitialMessage:
            "सिस्टम बाजार जानकारी का विश्लेषण करके सिफारिश देगा।",

        liveDataConnection:
            "बाजार डेटा कनेक्शन",

        connectionReady:
            "बाजार डेटा से जुड़ने के लिए तैयार।",

        dataSourceDescription:
            "बाजार की कीमतें SmartAgri बैकएंड द्वारा प्राप्त की जाती हैं।",

        loadingMessage:
            "SmartAgri बाजार सेवा से जुड़ा जा रहा है...",

        successfulMessage:
            "बाजार विश्लेषण सफलतापूर्वक पूरा हुआ।",

        connectionError:
            "SmartAgri बैकएंड से कनेक्ट नहीं हो सका।",

        invalidResponse:
            "बैकएंड से गलत प्रतिक्रिया मिली।",

        footerFeatures:
            "बाजार जानकारी • बहुभाषी • मोबाइल-अनुकूल",

        footerCopyright:
            "स्मार्ट कृषि बाजार सूचना प्रणाली"

    }

};


/* =========================================================
   GLOBAL STATE
========================================================= */

let currentLanguage =
    localStorage.getItem("smartagri-language") || "en";

let isAnalyzing = false;


/* =========================================================
   DOM
========================================================= */

const languageSelect =
    document.getElementById("languageSelect");

const cropSelect =
    document.getElementById("crop");

const analyzeButton =
    document.getElementById("analyzeButton");

const analyzeButtonText =
    document.getElementById("analyzeButtonText");

const analysisStatus =
    document.getElementById("analysisStatus");

const currentPrice =
    document.getElementById("currentPrice");

const marketTrend =
    document.getElementById("marketTrend");

const demand =
    document.getElementById("demand");

const forecastPrice =
    document.getElementById("forecastPrice");

const forecastMessage =
    document.getElementById("forecastMessage");

const sellReturn =
    document.getElementById("sellReturn");

const storeReturn =
    document.getElementById("storeReturn");

const transportReturn =
    document.getElementById("transportReturn");

const bestAction =
    document.getElementById("bestAction");

const recommendationReason =
    document.getElementById("recommendationReason");

const marketTable =
    document.getElementById("marketTable");

const connectionStatus =
    document.getElementById("connectionStatus");

const dataStatus =
    document.getElementById("dataStatus");

const dataDate =
    document.getElementById("dataDate");

const dataSource =
    document.getElementById("dataSource");


/* =========================================================
   TRANSLATION HELPERS
========================================================= */

function getTranslation(key) {

    const dictionary =
        translations[currentLanguage] ||
        translations.en;

    return dictionary[key] !== undefined
        ? dictionary[key]
        : translations.en[key] || key;

}


function applyLanguage(language) {

    currentLanguage =
        translations[language]
            ? language
            : "en";

    document
        .querySelectorAll("[data-i18n]")
        .forEach((element) => {

            const key =
                element.getAttribute("data-i18n");

            const translated =
                getTranslation(key);

            if (translated !== undefined) {

                element.textContent =
                    translated;

            }

        });


    document.documentElement.lang =
        currentLanguage;


    localStorage.setItem(
        "smartagri-language",
        currentLanguage
    );


    if (!isAnalyzing) {

        analyzeButtonText.textContent =
            getTranslation("analyzeMarket");

    }

}


/* =========================================================
   LANGUAGE SELECTOR
========================================================= */

if (languageSelect) {

    languageSelect.value =
        translations[currentLanguage]
            ? currentLanguage
            : "en";

    languageSelect.addEventListener(
        "change",
        function () {

            applyLanguage(
                this.value
            );

        }
    );

}


applyLanguage(
    currentLanguage
);


/* =========================================================
   FORMAT PRICE
========================================================= */

function formatPrice(value) {

    if (
        value === null ||
        value === undefined ||
        value === "" ||
        Number.isNaN(Number(value))
    ) {

        return "--";

    }

    return (
        "₹" +
        Number(value).toLocaleString(
            "en-IN",
            {
                maximumFractionDigits: 0
            }
        )
    );

}


/* =========================================================
   TRANSLATE API VALUES
========================================================= */

function translateTrend(value) {

    if (currentLanguage === "mr") {

        if (value === "Increasing")
            return "वाढत आहे";

        if (value === "Decreasing")
            return "घटत आहे";

        return "स्थिर";

    }


    if (currentLanguage === "hi") {

        if (value === "Increasing")
            return "बढ़ रहा है";

        if (value === "Decreasing")
            return "गिर रहा है";

        return "स्थिर";

    }


    return value || "--";

}


function translateDemand(value) {

    if (currentLanguage === "mr") {

        if (value === "High")
            return "जास्त";

        if (value === "Moderate")
            return "मध्यम";

        return "स्थिर";

    }


    if (currentLanguage === "hi") {

        if (value === "High")
            return "उच्च";

        if (value === "Moderate")
            return "मध्यम";

        return "स्थिर";

    }


    return value || "--";

}


function translateAction(value) {

    if (currentLanguage === "mr") {

        if (value === "Sell Now")
            return "आता विक्री करा";

        if (value === "Store")
            return "साठवणूक";

    }


    if (currentLanguage === "hi") {

        if (value === "Sell Now")
            return "अभी बेचें";

        if (value === "Store")
            return "भंडारण";

    }


    return value || "--";

}


/* =========================================================
   STATUS
========================================================= */

function setStatus(
    message,
    type = ""
) {

    analysisStatus.textContent =
        message;

    analysisStatus.className =
        "analysis-status " +
        type;

}


/* =========================================================
   BUTTON STATE
========================================================= */

function setAnalyzingState(active) {

    isAnalyzing =
        active;


    analyzeButton.disabled =
        active;


    if (active) {

        analyzeButtonText.textContent =
            getTranslation("analyzing");

    } else {

        analyzeButtonText.textContent =
            getTranslation("analyzeMarket");

    }

}


/* =========================================================
   UPDATE CONNECTION
========================================================= */

function updateConnection(
    message,
    success = false
) {

    connectionStatus.textContent =
        message;

    connectionStatus.style.color =
        success
            ? "var(--leaf-green)"
            : "var(--charcoal-light)";

}


/* =========================================================
   UPDATE TABLE
========================================================= */

function updateMarketTable(data) {

    const marketName =
        data.market ||
        "Kopargaon APMC";

    const status =
        data.data_status === "live"
            ? getTranslation("live")
            : getTranslation("fallback");

    const statusClass =
        data.data_status === "live"
            ? "live"
            : "fallback";


    marketTable.innerHTML = `

        <tr>

            <td>
                📍 ${escapeHtml(marketName)}
            </td>

            <td>
                <strong>
                    ${formatPrice(data.current_price)}
                </strong>
            </td>

            <td>

                <span class="status-pill ${statusClass}">
                    ${escapeHtml(status)}
                </span>

            </td>

        </tr>

    `;

}


/* =========================================================
   UPDATE UI
========================================================= */

function updateDashboard(data) {

    currentPrice.textContent =
        formatPrice(
            data.current_price
        );


    marketTrend.textContent =
        translateTrend(
            data.trend
        );


    demand.textContent =
        translateDemand(
            data.demand
        );


    forecastPrice.textContent =
        formatPrice(
            data.forecast_price
        );


    forecastMessage.textContent =
        data.forecast_message ||
        "--";


    sellReturn.textContent =
        formatPrice(
            data.sell_now
        );


    storeReturn.textContent =
        formatPrice(
            data.store
        );


    transportReturn.textContent =
        formatPrice(
            data.transport
        );


    bestAction.textContent =
        translateAction(
            data.best_action ||
            data.recommendation
        );


    recommendationReason.textContent =
        data.recommendation_reason ||
        "--";


    dataStatus.textContent =
        "Data status: " +
        (
            data.data_status ||
            "--"
        );


    dataDate.textContent =
        "Date: " +
        (
            data.latest_date ||
            data.data_date ||
            "--"
        );


    dataSource.textContent =
        "Source: " +
        (
            data.source ||
            "--"
        );


    updateMarketTable(
        data
    );


    updateConnection(
        data.message ||
        getTranslation("successfulMessage"),
        true
    );

}


/* =========================================================
   ESCAPE HTML
========================================================= */

function escapeHtml(value) {

    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");

}


/* =========================================================
   API REQUEST
========================================================= */

async function analyzeMarket() {

    if (isAnalyzing) {

        return;

    }


    const crop =
        cropSelect.value;


    if (!crop) {

        setStatus(
            "Please select a crop.",
            "error"
        );

        return;

    }


    setAnalyzingState(
        true
    );


    setStatus(
        getTranslation(
            "loadingMessage"
        ),
        "loading"
    );


    updateConnection(
        getTranslation(
            "loadingMessage"
        ),
        false
    );


    try {

        /*
         * IMPORTANT:
         *
         * We intentionally use a relative URL.
         *
         * This means:
         *
         * https://your-render-site.onrender.com
         *
         * automatically calls:
         *
         * https://your-render-site.onrender.com/api/market
         *
         * No localhost.
         * No hardcoded Render URL.
         * No separate frontend/backend URL.
         */

        const url =
            `/api/market?crop=${encodeURIComponent(crop)}`;


        console.log(
            "SmartAgri API request:",
            url
        );


        const response =
            await fetch(
                url,
                {
                    method: "GET",
                    headers: {
                        "Accept":
                            "application/json"
                    },
                    cache:
                        "no-store"
                }
            );


        console.log(
            "SmartAgri API status:",
            response.status
        );


        if (!response.ok) {

            throw new Error(
                `HTTP ${response.status}`
            );

        }


        const data =
            await response.json();


        console.log(
            "SmartAgri API response:",
            data
        );


        if (
            !data ||
            data.success !== true
        ) {

            throw new Error(
                data?.error ||
                getTranslation(
                    "invalidResponse"
                )
            );

        }


        updateDashboard(
            data
        );


        setStatus(
            getTranslation(
                "successfulMessage"
            ),
            "success"
        );


        /*
         * Move the user to the results.
         */

        document
            .getElementById("market")
            .scrollIntoView({
                behavior: "smooth",
                block: "start"
            });


    } catch (error) {

        console.error(
            "SmartAgri analysis error:",
            error
        );


        setStatus(
            `${getTranslation("connectionError")} ${error.message}`,
            "error"
        );


        updateConnection(
            `${getTranslation("connectionError")} ${error.message}`,
            false
        );


        /*
         * Do not erase previous values if a request
         * fails after the user already has data.
         */

    } finally {

        setAnalyzingState(
            false
        );

    }

}


/* =========================================================
   ANALYZE BUTTON
========================================================= */

if (analyzeButton) {

    analyzeButton.addEventListener(
        "click",
        function (event) {

            event.preventDefault();

            console.log(
                "Analyze Market button clicked"
            );

            analyzeMarket();

        }
    );

}


/* =========================================================
   ENTER / KEYBOARD SUPPORT
========================================================= */

if (cropSelect) {

    cropSelect.addEventListener(
        "keydown",
        function (event) {

            if (
                event.key === "Enter"
            ) {

                event.preventDefault();

                analyzeMarket();

            }

        }
    );

}


/* =========================================================
   OPTIONAL INITIAL BACKEND CHECK
========================================================= */

async function checkBackend() {

    try {

        const response =
            await fetch(
                "/health",
                {
                    method: "GET",
                    cache: "no-store"
                }
            );


        if (response.ok) {

            updateConnection(
                getTranslation(
                    "connectionReady"
                ),
                true
            );

            console.log(
                "SmartAgri backend is reachable."
            );

        } else {

            throw new Error(
                `HTTP ${response.status}`
            );

        }

    } catch (error) {

        console.warn(
            "Backend health check failed:",
            error
        );

        updateConnection(
            getTranslation(
                "connectionError"
            ),
            false
        );

    }

}


/* =========================================================
   START
========================================================= */

document.addEventListener(
    "DOMContentLoaded",
    function () {

        console.log(
            "SmartAgri frontend initialized."
        );

        console.log(
            "Current crop:",
            cropSelect?.value
        );

        console.log(
            "Current language:",
            currentLanguage
        );

        checkBackend();

    }
);
