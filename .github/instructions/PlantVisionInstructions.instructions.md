---
applyTo: '**'
---
# Project Overview 🚀

This is a high-performance, real-time vision application for plant analysis. The system captures a live camera feed, performs image processing to analyze plant features (like leaf area), and streams the results over MQTT. A lightweight web interface provides a dashboard for live monitoring and configuration. The entire application is containerized with Docker for easy deployment and portability.

***

# Technology Stack 🛠️

* **Language:** C++17 or later
* **Build System:** CMake
* **Computer Vision:** OpenCV
* **Networking:**
    * **Web Server:** Crow (or cpp-httplib) for the REST API and serving static web files.
    * **MQTT Client:** Eclipse Paho MQTT C++
* **Containerization:** Docker (using a multi-stage build)

***

# Core Architecture 🧠

The application is a high-performance, multithreaded C++ executable with intelligent plant classification. The key components are:

* **Vision Thread (Producer):** Captures video frames from camera devices, performs adaptive image analysis based on detected plant types, and pushes classified results to thread-safe queues.

* **Classification Engine:** Determines whether detected vegetation is a sprout or mature plant based on size thresholds and morphological characteristics, then applies appropriate processing pipeline.

* **Web Server Thread (Consumer):** Runs a Crow web server with plant-specific dashboards, serving static files and REST APIs for both sprout and plant monitoring (`/api/sprouts`, `/api/plants`, `/api/video_feed`).

* **MQTT Thread (Consumer):** Publishes classified telemetry to hierarchical topics:
  - `plantvision/{room}/{area}/{camera}/sprout/{id}/telemetry` 
  - `plantvision/{room}/{area}/{camera}/plant/{id}/telemetry`

* **Data Management:** 
  - **Sprout Queue:** High-frequency updates (500ms) for rapid growth tracking
  - **Plant Queue:** Standard updates (1000ms) for established plant monitoring
  - **Shared Configuration:** Thread-safe plant type definitions and processing parameters

## Processing Pipeline Architecture

```
Frame Input → Size-based Classification → Specialized Processing → Data Output
     |                    |                        |                    |
     v                    v                        v                    v
Camera/File    Sprout Pipeline (<5000px)   →   Sprout Data Queue   →  MQTT/Web
               Plant Pipeline (≥5000px)    →   Plant Data Queue    →  MQTT/Web
```

***

# Coding Guidelines 📜

* **Style:** Adhere to a clean and consistent coding style, with a preference for modern C++ idioms.
* **Memory:** Use **smart pointers** (`std::unique_ptr`, `std::shared_ptr`) to manage memory and avoid leaks.
* **Concurrency:** All access to shared resources must be protected by mutexes or other concurrency primitives to prevent race conditions.
* **Error Handling:** Use exceptions for handling critical errors and check return values from library functions.
* **Comments:** Add comments to explain complex algorithms, multithreading logic, and API endpoints.

***

# Mission Statements for AI Agent 🤖

1.  **Code Generation:** When prompted, generate C++ code that is compatible with the specified libraries and adheres to the architecture described above.
2.  **Debugging:** Help identify and fix issues, especially related to concurrency, memory management, or library usage.
3.  **Refactoring:** Propose ways to optimize code for performance, readability, and maintainability.
4.  **Documentation:** Assist in writing comments and `README.md` sections to explain the project's setup and functionality.


***

# Plant Classification System 🧠

The application uses a two-tier classification system to differentiate between **sprouts** and **mature plants** based on size, morphological characteristics, and growth stage.

## Classification Criteria

### Sprout Classification (Early Growth Stage)
**Size Threshold:** Area < 5000 pixels, Height < 8 cm
**Characteristics:**
- Primary focus on leaf area and count
- Simple color analysis for health assessment
- Basic growth tracking
- Higher sensitivity to environmental changes

### Mature Plant Classification (Advanced Growth Stage)
**Size Threshold:** Area ≥ 5000 pixels, Height ≥ 8 cm
**Characteristics:**
- Complex morphological analysis (petals, buds, stems)
- Advanced health assessment with disease detection
- Growth stage estimation (vegetative, flowering, fruiting)
- Comprehensive environmental stress analysis

## Sprout Data Schema 🌱

* **Classification:** "sprout"
* **Leaf Area:** Calculated area of detected cotyledons/first leaves (cm²)
* **Leaf Count:** Number of distinct leaf structures
* **Color Metrics:** RGB analysis focusing on chlorophyll content
* **Bounding Box:** Detection boundary coordinates
* **Height:** Estimated height from soil surface (cm)
* **Position:** X,Y coordinates of sprout center
* **Health Score:** 0-100 based on color and leaf condition
* **Growth Rate:** Daily/weekly size increase tracking
* **Germination Stage:** cotyledon, first-leaves, early-vegetative
* **Timestamp:** Analysis timestamp
* **Image Data:** Base64 encoded crop image
* **MQTT Topic:** `plantvision/{room}/{area}/{camera}/sprout/{id}/telemetry`

## Mature Plant Data Schema 🌿

* **Classification:** "plant"
* **Leaf Area:** Total leaf surface area (cm²)
* **Petal Area:** Flower petal area if present (cm²)
* **Petal Count:** Number of flower petals
* **Stem Length:** Main stem/trunk length (cm)
* **Branch Count:** Number of main branches
* **Bud Count:** Flower/leaf buds detected
* **Fruit Count:** Visible fruits/seeds
* **Color Metrics:** Multi-spectrum RGB analysis
* **Contour Complexity:** Shape complexity index
* **Bounding Box:** Detection boundary coordinates  
* **Height/Width:** Plant dimensions (cm)
* **Position:** X,Y coordinates of plant base
* **Health Status:** healthy, stressed, diseased, pest-damaged
* **Growth Stage:** seedling, vegetative, flowering, fruiting, dormant
* **Disease Indicators:** Specific pathology markers
* **Stress Indicators:** Environmental stress markers
* **Timestamp:** Analysis timestamp
* **Image Data:** Base64 encoded crop and annotated images
* **MQTT Topic:** `plantvision/{room}/{area}/{camera}/plant/{id}/telemetry`

## Processing Pipeline Differentiation

### Sprout Processing Pipeline
1. **Fine-scale detection** with lower area thresholds
2. **Cotyledon identification** for germination tracking
3. **Simple color space analysis** (HSV green range)
4. **Basic health assessment** via color uniformity
5. **Growth rate calculation** from historical data

### Plant Processing Pipeline  
1. **Multi-scale detection** with advanced segmentation
2. **Morphological analysis** (watershed, contour hierarchy)
3. **Advanced color analysis** (LAB, multi-spectrum)
4. **Disease detection** via texture and color patterns
5. **Phenological stage assessment** based on structure
6. **Environmental stress analysis** via leaf condition

***



# Web Dashboard Features 
🌐

* **Real-time Monitoring:** Live display of plant data (e.g., leaf area, color metrics) with automatic updates.
* **Historical Trends:** Graphs and charts showing changes in plant metrics over time.
* **User Configuration:** Interface for users to adjust settings (e.g., MQTT broker address, camera parameters).
* **Image Gallery:** View snapshots of analyzed frames with the option to download.
* **Health Alerts:** Notifications for abnormal plant conditions (e.g., low leaf area, color changes).
