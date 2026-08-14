// ============================================================
// SMARTAGRI KOPARGAON
// FRONTEND JAVASCRIPT
// ============================================================


const cropSelect =
    document.getElementById("crop");

const analyzeButton =
    document.getElementById("analyzeButton");

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

const marketTable =
    document.getElementById("marketTable");

const sellReturn =
    document.getElementById("sellReturn");

const storeReturn =
    document.getElementById("storeReturn");

const transportReturn =
    document.getElementById("transportReturn");

const bestAction =
    document.getElementById("bestAction");

const recommendationReason =
    document.getElementById(
        "recommendationReason"
    );

const connectionStatus =
    document.getElementById(
        "connectionStatus"
    );

const languageSelect =
    document.getElementById(
        "languageSelect"
    );


// ============================================================
// TRANSLATIONS
// ============================================================

const translations = {

    en: {

        dashboard:
            "Dashboard",

        market:
            "Market",

        forecast:
            "Forecast",

        decision:
            "Smart Decision",

        cropTitle:
            "Select Your Crop",

        cropDescription:
            "Select a crop to analyze current market conditions in Kopargaon.",

        analyze:
            "Analyze Market",

        snapshot:
            "Market Snapshot",

        snapshotDescription:
            "Current market conditions for the selected crop.",

        currentPrice:
            "Current Price",

        marketTrend:
            "Market Trend",

        demand:
            "Demand",

        forecastTitle:
            "AI Price Forecast",

        forecastDescription:
            "Estimated future price based on recent market information.",

        comparison:
            "Market Comparison",

        decisionTitle:
            "Smart Selling Decision",

        sellNow:
            "Sell Now",

        store:
            "Store",

        transport:
            "Transport",

        recommendation:
            "SMART RECOMMENDATION",

        recommendedAction:
            "Recommended Action",

        connection:
            "Live Data Connection"

    },

    mr: {

        dashboard:
            "डॅशबोर्ड",

        market:
            "बाजार",

        forecast:
            "अंदाज",

        decision:
            "स्मार्ट निर्णय",

        cropTitle:
            "तुमचे पीक निवडा",

        cropDescription:
            "कोपरगावमधील बाजारभाव पाहण्यासाठी पीक निवडा.",

        analyze:
            "बाजाराचे विश्लेषण करा",

        snapshot:
            "बाजार स्थिती",

        snapshotDescription:
            "निवडलेल्या पिकाची सध्याची बाजार स्थिती.",

        currentPrice:
            "सध्याचा भाव",

        marketTrend:
            "बाजार कल",

        demand:
            "मागणी",

        forecastTitle:
            "AI भाव अंदाज",

        forecastDescription:
            "अलीकडील बाजार माहितीवर आधारित भविष्यातील अंदाज.",

        comparison:
            "बाजार तुलना",

        decisionTitle:
            "स्मार्ट विक्री निर्णय",

        sellNow:
            "आता विक्री करा",

        store:
            "साठवून ठेवा",

        transport:
            "वाहतूक",

        recommendation:
            "स्मार्ट शिफारस",

        recommendedAction:
            "शिफारस केलेली कृती",

        connection:
            "थेट डेटा कनेक्शन"

    },

    hi: {

        dashboard:
            "डैशबोर्ड",

        market:
            "बाज़ार",

        forecast:
            "पूर्वानुमान",

        decision:
            "स्मार्ट निर्णय",

        cropTitle:
            "अपनी फसल चुनें",

        cropDescription:
            "कोपरगांव की बाजार स्थिति देखने के लिए फसल चुनें।",

        analyze:
            "बाज़ार का विश्लेषण करें",

        snapshot:
            "बाज़ार स्थिति",

        snapshotDescription:
            "चयनित फसल की वर्तमान बाजार स्थिति।",

        currentPrice:
            "वर्तमान भाव",

        marketTrend:
            "बाज़ार रुझान",

        demand:
            "मांग",

        forecastTitle:
            "AI मूल्य पूर्वानुमान",

        forecastDescription:
            "हाल की बाजार जानकारी के आधार पर भविष्य का अनुमान।",

        comparison:
            "बाज़ार तुलना",

        decisionTitle:
            "स्मार्ट बिक्री निर्णय",

        sellNow:
            "अभी बेचें",

        store:
            "भंडारण करें",

        transport:
            "परिवहन",

        recommendation:
            "स्मार्ट सुझाव",

        recommendedAction:
            "अनुशंसित कार्रवाई",

        connection:
            "लाइव डेटा कनेक्शन"

    }
};


// ============================================================
// LANGUAGE
// ============================================================

function changeLanguage(language) {

    const t =
        translations[language];

    if (!t) {
        return;
    }


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


    const cropHeading =
        document.querySelector(
            "#crop-selection h2"
        );

    if (cropHeading) {
        cropHeading.textContent =
            t.cropTitle;
    }


    const cropDescription =
        document.querySelector(
            "#crop-selection .section-heading p"
        );

    if (cropDescription) {
        cropDescription.textContent =
            t.cropDescription;
    }


    analyzeButton.innerHTML =
        `${t.analyze} <span>→</span>`;


    const marketHeading =
        document.querySelector(
            "#market h2"
        );

    if (marketHeading) {
        marketHeading.textContent =
            t.snapshot;
    }


    const marketDescription =
        document.querySelector(
            "#market .section-heading p"
        );

    if (marketDescription) {
        marketDescription.textContent =
            t.snapshotDescription;
    }


    const cardTitles =
        document.querySelectorAll(
            "#market .card h3"
        );

    if (cardTitles.length >= 3) {

        cardTitles[0].textContent =
            t.currentPrice;

        cardTitles[1].textContent =
            t.marketTrend;

        cardTitles[2].textContent =
            t.demand;
    }


    const forecastHeading =
        document.querySelector(
            "#forecast h2"
        );

    if (forecastHeading) {
        forecastHeading.textContent =
            t.forecastTitle;
    }


    const forecastDescription =
        document.querySelector(
            "#forecast .section-heading p"
        );

    if (forecastDescription) {
        forecastDescription.textContent =
            t.forecastDescription;
    }


    const comparisonHeading =
        document.querySelector(
            "#market-comparison h2"
        );

    if (comparisonHeading) {
        comparisonHeading.textContent =
            t.comparison;
    }


    const decisionHeading =
        document.querySelector(
            "#decision h2"
        );

    if (decisionHeading) {
        decisionHeading.textContent =
            t.decisionTitle;
    }


    const decisionCards =
        document.querySelectorAll(
            ".decision-card h3"
        );

    if (decisionCards.length >= 3) {

        decisionCards[0].textContent =
            t.sellNow;

        decisionCards[1].textContent =
            t.store;

        decisionCards[2].textContent =
            t.transport;
    }


    const recommendationLabel =
        document.querySelector(
            ".recommendation-label"
        );

    if (recommendationLabel) {

        recommendationLabel.textContent =
            t.recommendation;
    }


    const recommendationTitle =
        document.querySelector(
            "#recommendation h2"
        );

    if (recommendationTitle) {

        recommendationTitle.textContent =
            t.recommendedAction;
    }


    const connectionHeading =
        document.querySelector(
            "#offline-status h2"
        );

    if (connectionHeading) {

        connectionHeading.textContent =
            t.connection;
    }


    localStorage.setItem(
        "smartagri-language",
        language
    );
}


// ============================================================
// LOAD SAVED LANGUAGE
// ============================================================

const savedLanguage =
    localStorage.getItem(
        "smartagri-language"
    );

if (savedLanguage) {

    languageSelect.value =
        savedLanguage;

    changeLanguage(
        savedLanguage
    );
}


// ============================================================
// LANGUAGE EVENT
// ============================================================

languageSelect.addEventListener(
    "change",
    function () {

        changeLanguage(
            this.value
        );

    }
);


// ============================================================
// FORMAT MONEY
// ============================================================

function formatMoney(value) {

    if (
        value === null ||
        value === undefined ||
        value === ""
    ) {

        return "--";
    }

    return (
        "₹" +
        Number(value).toLocaleString(
            "en-IN"
        )
    );
}


// ============================================================
// FORMAT DATE
// ============================================================

function formatDate(dateValue) {

    if (!dateValue) {
        return "--";
    }

    const date =
        new Date(
            dateValue + "T00:00:00"
        );

    if (
        Number.isNaN(
            date.getTime()
        )
    ) {

        return dateValue;
    }

    return date.toLocaleDateString(
        "en-IN",
        {
            day: "2-digit",
            month: "short",
            year: "numeric"
        }
    );
}


// ============================================================
// ANALYZE MARKET
// ============================================================

async function analyzeMarket() {

    const crop =
        cropSelect.value;

    analyzeButton.disabled =
        true;

    analyzeButton.innerHTML =
        "Analyzing...";


    connectionStatus.textContent =
        "Connecting to SmartAgri market service...";


    try {

        const response =
            await fetch(
                `/api/market?crop=${encodeURIComponent(crop)}`
            );


        if (!response.ok) {

            throw new Error(
                `HTTP ${response.status}`
            );
        }


        const data =
            await response.json();


        if (!data.success) {

            throw new Error(
                data.error ||
                "Market request failed"
            );
        }


        updateDashboard(
            data
        );


        connectionStatus.textContent =
            `Latest data: ${formatDate(
                data.latest_date
            )} • ${data.source}`;


    } catch (error) {

        console.error(
            "SmartAgri error:",
            error
        );


        connectionStatus.textContent =
            "Unable to refresh market data. Showing the latest recorded value.";
    }


    analyzeButton.disabled =
        false;


    analyzeButton.innerHTML =
        "Analyze Market <span>→</span>";
}


// ============================================================
// UPDATE DASHBOARD
// ============================================================

function updateDashboard(data) {

    currentPrice.textContent =
        formatMoney(
            data.current_price
        );


    marketTrend.textContent =
        `${data.trend} ${
            data.change_percent > 0
                ? "+" + data.change_percent + "%"
                : data.change_percent + "%"
        }`;


    demand.textContent =
        data.demand;


    forecastPrice.textContent =
        formatMoney(
            data.forecast_price
        );


    forecastMessage.textContent =
        data.forecast_message;


    sellReturn.textContent =
        formatMoney(
            data.sell_now
        );


    storeReturn.textContent =
        formatMoney(
            data.store
        );


    transportReturn.textContent =
        formatMoney(
            data.transport
        );


    bestAction.textContent =
        data.best_action;


    recommendationReason.textContent =
        data.recommendation_reason;


    // --------------------------------------------------------
    // Market table
    // --------------------------------------------------------

    marketTable.innerHTML = `

        <tr>

            <td>
                📍 ${data.market}
            </td>

            <td>
                ${formatMoney(
                    data.current_price
                )}
            </td>

            <td>
                ${data.trend}
            </td>

        </tr>

        <tr>

            <td>
                Latest Data Date
            </td>

            <td colspan="2">

                ${formatDate(
                    data.latest_date
                )}

            </td>

        </tr>

        <tr>

            <td>
                Source
            </td>

            <td colspan="2">

                ${data.source}

            </td>

        </tr>

    `;


    // --------------------------------------------------------
    // Status
    // --------------------------------------------------------

    if (
        data.data_status === "live"
    ) {

        connectionStatus.textContent =
            `Live market data • ${formatDate(
                data.latest_date
            )}`;

    } else if (
        data.data_status === "baseline"
    ) {

        connectionStatus.textContent =
            `SmartAgri baseline • ${formatDate(
                data.latest_date
            )}`;

    } else {

        connectionStatus.textContent =
            `Latest recorded price • ${formatDate(
                data.latest_date
            )}`;
    }
}


// ============================================================
// BUTTON
// ============================================================

analyzeButton.addEventListener(
    "click",
    analyzeMarket
);


// ============================================================
// AUTOMATIC INITIAL LOAD
// ============================================================

window.addEventListener(
    "DOMContentLoaded",
    function () {

        analyzeMarket();

    }
);
