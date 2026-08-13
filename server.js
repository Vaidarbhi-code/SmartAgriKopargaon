const express = require("express");
const cors = require("cors");
const path = require("path");

const app = express();
const PORT = 3000;

const API_KEY = "579b464db66ec23bdd000001f96fc697a72546b44e0d868b22557c39";
const RESOURCE_ID = "9ef84268-d588-465a-a308-a864a43d0070";

app.use(cors());
app.use(express.json());

// Serve your HTML, CSS and JS files
app.use(express.static(__dirname));


// ==========================================
// LIVE MARKET API
// ==========================================

app.get("/api/market", async (req, res) => {

    try {

        const crop = req.query.crop;

        if (!crop) {
            return res.status(400).json({
                success: false,
                message: "Crop is required."
            });
        }

        const commodity =
            crop.toLowerCase() === "onion"
                ? "Onion"
                : crop.toLowerCase() === "wheat"
                    ? "Wheat"
                    : null;

        if (!commodity) {
            return res.status(400).json({
                success: false,
                message: "Only Onion and Wheat are supported."
            });
        }


        const url =
            `https://api.data.gov.in/resource/${RESOURCE_ID}` +
            `?api-key=${API_KEY}` +
            `&format=json` +
            `&limit=1000` +
            `&filters%5Bcommodity%5D=${encodeURIComponent(commodity)}`;


        console.log("--------------------------------------");
        console.log("LIVE MARKET REQUEST");
        console.log("Crop:", commodity);
        console.log("URL:", url);


        const response = await fetch(url);

        console.log("DATA.GOV STATUS:", response.status);


        if (!response.ok) {

            throw new Error(
                `data.gov.in returned HTTP ${response.status}`
            );

        }


        const result = await response.json();

        const records = result.records || [];

        console.log("Records received:", records.length);


        // ==========================================
        // FIND KOPARGAON
        // ==========================================

        const kopargaonRecords = records.filter(record => {

            const market = String(
                record.market ||
                record.Market ||
                ""
            ).trim().toLowerCase();

            return (
                market.includes("kopargaon")
            );

        });


        console.log(
            "Kopargaon records:",
            kopargaonRecords.length
        );


        if (kopargaonRecords.length === 0) {

            return res.json({
                success: false,
                message:
                    `No ${commodity} record for Kopargaon was found in the live API response.`,
                recordsReceived: records.length
            });

        }


        // ==========================================
        // TAKE MOST RECENT KOPARGAON RECORD
        // ==========================================

        const record = kopargaonRecords[0];


        const minPrice = Number(
            record.min_price ||
            record.Min_Price ||
            record.minprice ||
            0
        );

        const maxPrice = Number(
            record.max_price ||
            record.Max_Price ||
            record.maxprice ||
            0
        );

        const modalPrice = Number(
            record.modal_price ||
            record.Modal_Price ||
            record.modalprice ||
            0
        );


        if (!modalPrice) {

            return res.json({
                success: false,
                message: "Kopargaon record found but price is missing.",
                record
            });

        }


        // ==========================================
        // SEND CLEAN DATA TO FRONTEND
        // ==========================================

        res.json({

            success: true,

            source: "data.gov.in / Agmarknet",

            market:
                record.market ||
                record.Market ||
                "Kopargaon APMC",

            district:
                record.district ||
                record.District ||
                "Ahilyanagar",

            state:
                record.state ||
                record.State ||
                "Maharashtra",

            commodity: commodity,

            variety:
                record.variety ||
                record.Variety ||
                "",

            grade:
                record.grade ||
                record.Grade ||
                "",

            arrival_date:
                record.arrival_date ||
                record.Arrival_Date ||
                "",

            min_price: minPrice,

            max_price: maxPrice,

            modal_price: modalPrice

        });


    } catch (error) {

        console.error("BACKEND ERROR:", error);

        res.status(500).json({

            success: false,

            message: "Failed to fetch live market data.",

            error: error.message

        });

    }

});


// ==========================================
// START SERVER
// ==========================================

app.listen(PORT, () => {

    console.log("");
    console.log("====================================");
    console.log("🌾 SmartAgri Server Started");
    console.log("====================================");
    console.log(`http://localhost:${PORT}`);
    console.log("");

});