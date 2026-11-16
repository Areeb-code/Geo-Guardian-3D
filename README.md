<img width="1024" height="434" alt="image" src="https://github.com/user-attachments/assets/08bba73e-2ca9-454a-b32d-b7b8b6303e36" />

<div align="center">

# 🌍 GeoGuardian 3D
### Global Urban Expansion & Atmospheric Smog Intelligence Platform

[![Python](https://img.shields.io/badge/Python-3.13-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Google Earth Engine](https://img.shields.io/badge/Google_Earth_Engine-GeoAI-4285F4?style=for-the-badge&logo=googleearth&logoColor=white)](https://earthengine.google.com)
[![CesiumJS](https://img.shields.io/badge/CesiumJS-3D_WebGL_Globe-6CADDF?style=for-the-badge&logo=cesium&logoColor=white)](https://cesium.com/platform/cesiumjs/)
[![License: MIT](https://img.shields.io/badge/License-MIT-10B981?style=for-the-badge)](LICENSE)

**An autonomous, full-stack GeoAI platform that combines multi-decadal satellite harmonization (1984–2026), on-the-fly Random Forest land-cover classification, and daily atmospheric aerosol tracking inside an interactive 3D WebGL Earth globe.**

[Features](#-key-features) • [System Architecture](#-system-architecture) • [Satellite Pipeline](#-multi-sensor-harmonization--ml-pipeline) • [Quick Start](#-quick-start--installation) • [API Reference](#-api-reference) • [Evaluation & Outputs](#-evaluation--validation)

</div>

---

## 📖 Overview

Rapid, unregulated urban sprawl and seasonal atmospheric smog present critical environmental challenges across South Asia and rapidly developing metropolitan regions worldwide. **GeoGuardian 3D** (originally developed with a baseline focus on **Lahore District, Pakistan**[cite: 2, 3]) eliminates static, notebook-bound GIS workflows by connecting a live **FastAPI + Google Earth Engine (GEE)** compute engine directly to a glassmorphic **CesiumJS 3D Globe**.

Users can query **any city, district, or province worldwide**, dynamically train a localized machine learning classifier adapted to that region's terrain, quantify agricultural-to-urban land conversion in square kilometers[cite: 2, 3], and inspect daily UV Aerosol Index smog plumes in real time[cite: 2, 3].

<img width="1363" height="606" alt="image" src="https://github.com/user-attachments/assets/504ba0c8-0107-4e52-b1f8-d5f4b1ead0bf" />


---

## ✨ Key Features

* **🌐 Global On-Demand Geocoding & AOI Extraction:** Search any city or region worldwide via integrated Open-Meteo and Nominatim geocoding, automatically generating an optimized bounding box and flying the 3D camera directly to the target coordinates.
* **🛰️ 40+ Year Multi-Satellite Harmonization (1984–2026):** Seamlessly bridges historical **Landsat 5, 7, and 8** (30m) archives with modern **Sentinel-2** (10m) optical composites by normalizing surface reflectance scales and spectral indices (`NDVI`, `NDBI`).
* **🧠 Self-Adapting Local Random Forest Classifier:** Dynamically samples stratified ground-truth training pixels from **ESA WorldCover 10m** (`ESA/WorldCover/v200`) inside the active region and trains an 80–100 tree `smileRandomForest` classifier on the fly.
* **⚡ Dual Operational Modes:**
  * **Live Monitor Mode:** Tracks the latest cloud-free optical land cover alongside live **Sentinel-5P TROPOMI** UV Aerosol Index smog plumes (including single-date historical smog lookup)[cite: 2, 3].
  * **Historical Comparison Mode:** Compares any two arbitrary years between `1984` and `2026`, generating a binary red change-detection mask highlighting vegetation converted into built-up urban infrastructure[cite: 2, 3].
* **💎 Modern 3D Glassmorphic UI:** Built on **CesiumJS** with frosted-glass docks (`backdrop-filter: blur(24px)`), spring-animated tab switchers, collapsible cinema-mode floating action buttons (FABs), 3D horizon tilt (`-42°` pitch), and real-time layer opacity sliders[cite: 2, 3].
* **🚀 Thread-Safe Caching & Single-Pass Reduction:** Combines all 6 area masks into a single multi-band `ee.Image.cat()` reduction call, reducing GEE latency by 3x and serving repeat queries in `<10ms` from an in-memory cache.

---

## 🏗️ System Architecture

```mermaid
graph LR
    subgraph Frontend ["3D WebGL Frontend (CesiumJS)"]
        UI["Glassmorphic UI Docks\n(Live & Compare Modes)"]
        Globe["CesiumJS 3D Globe\n(XYZ Tile Renderer)"]
    end

    subgraph Backend ["FastAPI Backend (Python 3.13)"]
        API["REST Endpoints\n(/api/metrics, /api/tiles)"]
        Geo["Global Geocoder\n(Open-Meteo + Nominatim)"]
        Cache["Thread-Safe\nIn-Memory Cache"]
    end

    subgraph GEE ["Google Earth Engine Cloud Compute"]
        Opt["Optical Harmonizer\n(Landsat 5/7/8 + Sentinel-2)"]
        WC["ESA WorldCover 10m\n(Stratified Auto-Sampling)"]
        RF["Random Forest (80-100 Trees)\n(B2, B3, B4, B8, B11, NDVI, NDBI)"]
        S5P["Sentinel-5P TROPOMI\n(UV Aerosol Index L3_AER_AI)"]
    end

    UI -->|Query Params| API
    API --> Geo
    API --> Cache
    Cache -->|Cache Miss| Opt
    Opt --> WC
    WC --> RF
    RF -->|Area Stats + XYZ URLs| API
    S5P -->|Smog Stats + XYZ URLs| API
    API -->|JSON Telemetry| UI
    API -->|XYZ Tile Streams| Globe
