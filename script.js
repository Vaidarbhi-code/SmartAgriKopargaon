document.addEventListener("DOMContentLoaded", () => {

    console.log("================================");
    console.log("🌾 SMARTAGRI KOPARGAON");
    console.log("Frontend connected");
    console.log("================================");


    // =====================================================
    // HTML ELEMENTS
    // =====================================================

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


    // =====================================================
    // CHECK HTML
    // =====================================================

    if (!cropSelect) {
        console.error("❌ Crop select (#crop) not found.");
        return;
    }

    if (!analyzeButton) {
        console.error("❌ Analyze button (#analyzeButton) not found.");
        return;
    }


    // =====================================================
    // FLASK API
    // =====================================================

    const API_URL = "/api/market";


    // =====================================================
    // RUPEE FORMAT
    // =====================================================

    function formatCurrency(value) {

        const number = Number(value);

        if (!Number.isFinite(number)) {
            return "₹--";
        }

        return "₹" + number.toLocaleString("en-IN");
    }


    // =====================================================
    // HTML ESCAPE
    // =====================================================

    function escapeHTML(value) {

        return String(value)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }


    // =====================================================
    // SHOW ERROR
    // =====================================================

    function showError(message) {

        console.error("❌", message);

        if (currentPrice) {
            currentPrice.textContent = "Unavailable";
        }

        if (marketTrend) {
            marketTrend.textContent = "--";
        }

        if (demand) {
            demand.textContent = "--";
        }

        if (forecastPrice) {
            forecastPrice.textContent = "--";
        }

        if (forecastMessage) {
            forecastMessage.textContent = message;
        }

        if (sellReturn) {
            sellReturn.textContent = "--";
        }

        if (storeReturn) {
            storeReturn.textContent = "--";
        }

        if (transportReturn) {
            transportReturn.textContent = "--";
        }

        if (bestAction) {
            bestAction.textContent = "Unable to analyze";
        }

        if (recommendationReason) {
            recommendationReason.textContent = message;
        }

        if (connectionStatus) {
            connectionStatus.textContent =
                "Unable to connect to market data.";
        }
    }


    // =====================================================
    // ANALYZE BUTTON
    // =====================================================

    analyzeButton.addEventListener("click", async () => {

        const crop = cropSelect.value;

        console.log("");
        console.log("================================");
        console.log("🌾 SMARTAGRI MARKET ANALYSIS");
        console.log("Selected crop:", crop);
        console.log("================================");


        // -------------------------------------------------
        // ONLY TWO CROPS
        // -------------------------------------------------

        if (crop !== "onion" && crop !== "wheat") {

            showError(
                "Please select Onion or Wheat."
            );

            return;
        }


        // -------------------------------------------------
        // BUTTON LOADING
        // -------------------------------------------------

        analyzeButton.disabled = true;

        analyzeButton.innerHTML =
            "Loading market data...";


        // -------------------------------------------------
        // RESET
        // -------------------------------------------------

        currentPrice.textContent = "--";
        marketTrend.textContent = "--";
        demand.textContent = "--";
        forecastPrice.textContent = "--";


        try {

            // =================================================
            // CALL FLASK
            // =================================================

            console.log(
                "Requesting:",
                `${API_URL}?crop=${crop}`
            );


            const response = await fetch(
                `${API_URL}?crop=${encodeURIComponent(crop)}`
            );


            console.log(
                "HTTP status:",
                response.status
            );


            // =================================================
            // CHECK RESPONSE
            // =================================================

            if (!response.ok) {

                throw new Error(
                    `Server returned HTTP ${response.status}`
                );
            }


            // =================================================
            // READ JSON
            // =================================================

            const data = await response.json();


            console.log(
                "Backend response:",
                data
            );


            // =================================================
            // CHECK SUCCESS
            // =================================================

            if (!data.success) {

                throw new Error(
                    data.message ||
                    "Market data unavailable."
                );
            }


            // =================================================
            // UPDATE DASHBOARD
            // =================================================

            updateDashboard(data);


        }
        catch (error) {

            console.error(
                "❌ MARKET DATA ERROR:",
                error
            );


            showError(
                "Failed to fetch market data. " +
                error.message
            );

        }
        finally {

            analyzeButton.disabled = false;

            analyzeButton.innerHTML =
                `Analyze Market <span>→</span>`;
        }

    });


    // =====================================================
    // UPDATE DASHBOARD
    // =====================================================

    function updateDashboard(data) {

        console.log("");
        console.log("🌾 MARKET DATA");
        console.log("----------------------------");
        console.log("Crop:", data.commodity);
        console.log("Market:", data.market);
        console.log("Minimum:", data.min_price);
        console.log("Maximum:", data.max_price);
        console.log("Modal:", data.modal_price);
        console.log("Mode:", data.data_mode);
        console.log("----------------------------");


        // =================================================
        // PRICES
        // =================================================

        const minPrice = Number(data.min_price);
        const maxPrice = Number(data.max_price);
        const modalPrice = Number(data.modal_price);


        if (!Number.isFinite(modalPrice)) {

            throw new Error(
                "Backend returned an invalid modal price."
            );
        }


        // =================================================
        // CURRENT PRICE
        // =================================================

        currentPrice.textContent =
            formatCurrency(modalPrice);


        // =================================================
        // MARKET TREND
        // =================================================

        let trend = "Stable";


        if (
            Number.isFinite(minPrice) &&
            Number.isFinite(maxPrice)
        ) {

            const range =
                maxPrice - minPrice;


            const rangePercentage =
                modalPrice > 0
                    ? (range / modalPrice) * 100
                    : 0;


            if (rangePercentage >= 15) {

                trend = "Active";

            }
            else if (rangePercentage >= 5) {

                trend = "Moderate";

            }
            else {

                trend = "Stable";
            }
        }


        marketTrend.textContent = trend;


        // =================================================
        // DEMAND
        // =================================================

        let demandLevel = "Medium";


        if (
            Number.isFinite(minPrice) &&
            Number.isFinite(maxPrice) &&
            maxPrice > minPrice
        ) {

            const position =
                (modalPrice - minPrice) /
                (maxPrice - minPrice);


            if (position >= 0.70) {

                demandLevel = "High";

            }
            else if (position >= 0.40) {

                demandLevel = "Medium";

            }
            else {

                demandLevel = "Low";
            }
        }


        demand.textContent = demandLevel;


        // =================================================
        // FORECAST
        // =================================================

        let forecast = modalPrice;


        if (
            Number.isFinite(minPrice) &&
            Number.isFinite(maxPrice)
        ) {

            const range =
                maxPrice - minPrice;


            /*
             Simple forecast:
             modal price + 10% of today's market range
            */

            forecast =
                Math.round(
                    modalPrice + (range * 0.10)
                );
        }


        console.log(
            "Forecast:",
            forecast
        );


        forecastPrice.textContent =
            formatCurrency(forecast);


        forecastMessage.textContent =
            `${data.commodity} currently has a modal market price of ${formatCurrency(modalPrice)} per quintal. The estimated future price is ${formatCurrency(forecast)} per quintal.`;


        // =================================================
        // MARKET COMPARISON TABLE
        // =================================================

        marketTable.innerHTML = `

            <tr>

                <td>
                    📍 ${escapeHTML(
                        data.market || "Kopargaon APMC"
                    )}
                </td>

                <td>
                    ${formatCurrency(modalPrice)}
                </td>

                <td>
                    ${formatCurrency(modalPrice)}
                </td>

            </tr>


            <tr>

                <td>
                    Minimum Market Price
                </td>

                <td>
                    ${formatCurrency(minPrice)}
                </td>

                <td>
                    ${formatCurrency(minPrice)}
                </td>

            </tr>


            <tr>

                <td>
                    Maximum Market Price
                </td>

                <td>
                    ${formatCurrency(maxPrice)}
                </td>

                <td>
                    ${formatCurrency(maxPrice)}
                </td>

            </tr>

        `;


        // =================================================
        // SMART SELLING DECISION
        // =================================================

        /*
         Sell Now:
         Current modal price

         Store:
         Forecast price

         Transport:
         Maximum current market price
        */

        const sellPrice =
            modalPrice;


        const storePrice =
            forecast;


        const transportPrice =
            Number.isFinite(maxPrice)
                ? maxPrice
                : modalPrice;


        sellReturn.textContent =
            `${formatCurrency(sellPrice)} / Quintal`;


        storeReturn.textContent =
            `${formatCurrency(storePrice)} / Quintal`;


        transportReturn.textContent =
            `${formatCurrency(transportPrice)} / Quintal`;


        // =================================================
        // BEST ACTION
        // =================================================

        if (storePrice > sellPrice) {

            bestAction.textContent =
                "Consider Storing";


            recommendationReason.textContent =
                `The estimated future price is ${formatCurrency(storePrice)} per quintal, which is higher than the current price of ${formatCurrency(sellPrice)} per quintal.`;

        }
        else {

            bestAction.textContent =
                "Consider Selling Now";


            recommendationReason.textContent =
                `The current modal price is ${formatCurrency(sellPrice)} per quintal.`;

        }


        // =================================================
        // CONNECTION STATUS
        // =================================================

        if (data.data_mode === "live") {

            connectionStatus.textContent =
                `Live market data • ${data.market} • ${data.arrival_date}`;

        }
        else {

            connectionStatus.textContent =
                `Verified market data • ${data.market} • ${data.arrival_date}`;

        }


        // =================================================
        // FINAL CONSOLE OUTPUT
        // =================================================

        console.log("");
        console.log("================================");
        console.log("✅ ANALYSIS COMPLETE");
        console.log("Crop:", data.commodity);
        console.log("Minimum:", minPrice);
        console.log("Maximum:", maxPrice);
        console.log("Modal:", modalPrice);
        console.log("Forecast:", forecast);
        console.log("================================");

    }


    // =====================================================
    // INITIAL PAGE STATE
    // =====================================================

    currentPrice.textContent = "--";
    marketTrend.textContent = "--";
    demand.textContent = "--";
    forecastPrice.textContent = "--";


    if (connectionStatus) {

        connectionStatus.textContent =
            "Select a crop and analyze the market.";
    }


    console.log(
        "✅ SmartAgri frontend ready."
    );

});