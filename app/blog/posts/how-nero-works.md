---
title: "How Nero Works: Building a Water Monitoring Dashboard"
slug: "how-nero-works"
date: "2026-03-05"
description: "A behind-the-scenes look at how Nero collects, stores, and displays dam level data for Cyprus. From API ingestion to interactive charts."
author: "Nero Team"
---

Nero is a live dashboard that tracks water levels across all 17 major dams in Cyprus, updated every six hours. But how does it actually work? This post takes you behind the scenes of the data pipeline, from the government API that provides the raw numbers to the interactive charts you see on screen.

## Where the data comes from

All of Nero's data originates from the **Water Development Department of Cyprus** (WDD), which publishes reservoir readings through a public API. The WDD maintains monitoring equipment at each dam and records storage volumes, inflow rates, and capacity figures at regular intervals.

The API is hosted at `cyprus-water.appspot.com/api` and provides two main endpoints: one that lists all dams with their current metadata (capacity, location, height, river name), and another that returns historical date-by-date statistics for the entire system. The data is published under a Creative Commons Attribution 2.0 licence, which permits anyone to reuse it with attribution.

Nero consumes this API using an HTTP client and transforms the raw JSON responses into structured data that can be stored and queried efficiently.

## The sync pipeline

When Nero starts for the first time, it performs an **initial seed** — a one-time download of the full historical dataset going back to October 2009. This gives every dam its complete trend line from day one, without having to accumulate data over months of operation.

After the initial seed, Nero switches to **incremental syncs** that run every six hours via a background scheduler. Each sync fetches only the latest readings, compares them against what is already stored, and inserts any new data points. This keeps the dashboard current without re-downloading the entire history every time.

The sync pipeline includes automatic retry logic. If the upstream API is temporarily unavailable — which happens occasionally — Nero retries up to three times with increasing delays between attempts. If all retries fail, the existing data continues to be served to users, and the sync tries again at the next scheduled interval. A failed sync never causes the dashboard to go down.

## How data is stored

Nero uses **SQLite** as its database — a lightweight, file-based database that requires no separate server process. The entire dataset for 17 dams over 15+ years fits comfortably in a single file under 50 megabytes. SQLite is configured in WAL (Write-Ahead Logging) mode, which allows the background sync process to write new data without blocking the web server from reading and serving pages simultaneously.

Each dam reading is stored as a row with the dam name, date, storage volume in MCM (Million Cubic Metres), total capacity, and the percentage full. The database also stores dam metadata — coordinates, height, river name, construction year — which powers the map and detail pages.

Percentage values are stored internally as decimals between 0 and 1 (so 14% is stored as 0.14). When rendering charts and templates, these are converted to the 0–100 scale that users expect.

## Rendering the dashboard

Nero is a **server-rendered** application built with Python's FastAPI framework and Jinja2 templates. When you visit the dashboard, the server reads the latest data from SQLite, computes severity labels (critical, warning, or healthy) for each dam, and renders a complete HTML page that is sent to your browser.

There is no client-side state management, no React, no single-page application framework. Every page load fetches fresh data from the database and renders it server-side. This approach is simple, fast, and works perfectly on every device without requiring JavaScript for the initial page load.

The interactive charts are powered by **Chart.js**, a JavaScript library that renders the trend lines and year-on-year comparisons in your browser. The raw data is embedded in the page as a JSON array, and Chart.js converts it into the visual charts you see. The year-on-year comparison feature lets you overlay two different years against each other, using either daily, monthly, or yearly granularity.

The [interactive map](/map) uses **Leaflet.js** with OpenStreetMap tiles. Each dam is plotted at its real geographic coordinates with a colour-coded marker indicating its severity level.

## Severity thresholds

Nero uses a simple three-tier system to classify dam health:

- **Critical (red)**: below 20% capacity — immediate risk to supply security
- **Warning (amber)**: 20 to 40% — reduced reserves, conservation advised
- **Healthy (green)**: above 40% — normal operations

These thresholds are based on operational norms in Cyprus water management. Below 20%, evaporation losses accelerate (shallower water has a higher surface-to-volume ratio), water quality degrades from sediment concentration, and some dams approach their "dead storage" — the volume below the lowest outlet that cannot be physically extracted.

## Why open data matters

Nero exists because the Water Development Department chose to publish its data openly. Without that decision, building this dashboard would have required screen-scraping, reverse engineering, or freedom of information requests — all of which are brittle and slow.

Open data is the foundation of civic technology. When governments publish data in machine-readable formats under permissive licences, developers and journalists can build tools that make that data genuinely useful to the public. Nero is one example; there should be more.

If you are interested in the technical details, the Nero codebase follows test-driven development with over 850 automated tests across 13 European countries. You can explore the dashboard at [nero.cy](/) or visit individual dam pages like [Kouris](/dam/Kouris) and [Asprokremmos](/dam/Asprokremmos) to see the data in action.

*Data sourced from the Water Development Department of Cyprus. Updated every 6 hours.*
