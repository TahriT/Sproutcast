from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import os
import threading
import time
import json as pyjson
import paho.mqtt.client as mqtt
from typing import Any, Dict

app = FastAPI(title="SproutCast Web UI")

app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/frames", StaticFiles(directory="/app/data"), name="frames")
app.mount("/plants", StaticFiles(directory="/app/data/plants"), name="plants")

CONFIG_PATH = "/app/data/config.json"
AI_METRICS_PATH = "/app/data/ai_metrics.json"
OVERRIDE_PATH = "/app/data/classes_overrides.json"

default_config: Dict[str, Any] = {
    "mqtt": {
        "host": os.getenv("MQTT_HOST", "localhost"),
        "port": int(os.getenv("MQTT_PORT", "1883")),
    },
    "uns": {
        "room": "room-1",
        "area": "area-1",
        "camera_id": os.getenv("CAMERA_ID", "0"),
        "plant_id": "plant-1",
    },
    "processing": {
        "threshold": int(os.getenv("THRESHOLD", "100")),
        "publish_interval_ms": int(os.getenv("PUBLISH_INTERVAL_MS", "1000")),
        "scale_px_per_cm": float(os.getenv("SCALE_PX_PER_CM", "0")),
        "input_mode": os.getenv("INPUT_MODE", "IMAGE"),
        "input_path": os.getenv("INPUT_PATH", "/samples/plant.jpg"),
    },
}

def load_config() -> Dict[str, Any]:
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return pyjson.load(f)
    except Exception:
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            pyjson.dump(default_config, f, indent=2)
        return default_config

state: Dict[str, Any] = {"latest": None, "config": load_config()}

def mqtt_thread():
    host = state["config"]["mqtt"]["host"]
    port = int(state["config"]["mqtt"]["port"])
    uns = state["config"]["uns"]
    topic = f"sproutcast/{uns['room']}/{uns['area']}/{uns['camera_id']}/{uns['plant_id']}/telemetry"

    def on_message(_client, _userdata, msg):
        try:
            state["latest"] = msg.payload.decode("utf-8")
        except Exception:
            pass

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_message = on_message
    client.connect(host, port, 60)
    client.subscribe(topic)
    client.loop_forever()

threading.Thread(target=mqtt_thread, daemon=True).start()

# Single Page Application Route
@app.get("/", response_class=HTMLResponse)
@app.get("/{page}", response_class=HTMLResponse)
def unified_app(request: Request, page: str = "dashboard"):
    html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>SproutCast - Plant Monitoring System</title>
        <style>
            :root { 
                --bg:#0b1220; --fg:#e8eefb; --card:#111a2e; --accent:#4f8cff; 
                --sprout:#10b981; --plant:#059669; --border:#223; --success:#10b981; 
                --error:#ef4444; --warning:#f59e0b; 
            }
            
            * { box-sizing: border-box; }
            body { 
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                margin: 0; background: var(--bg); color: var(--fg); line-height: 1.6;
            }
            
            /* Navigation Header */
            header.nav { 
                display:flex; align-items:center; gap:1rem; padding:.75rem 1rem; 
                border-bottom:1px solid var(--border); position:sticky; top:0; 
                background:rgba(11,18,32,.95); backdrop-filter: blur(6px); z-index: 100;
            }
            header.nav h2 { margin:0; font-size:1.2rem; }
            header.nav .spacer { flex:1; }
            header.nav .nav-links { display: flex; gap: 0.5rem; }
            header.nav .nav-links a { 
                padding:.5rem 1rem; color: var(--fg); text-decoration:none; 
                border-radius:8px; transition: all 0.2s; opacity: 0.8;
            }
            header.nav .nav-links a:hover, 
            header.nav .nav-links a.active { 
                background: var(--accent); opacity: 1; 
            }
            header.nav select { 
                background:#0f172a; color:var(--fg); border:1px solid var(--border); 
                border-radius:8px; padding:.4rem .6rem; 
            }
            
            /* Status indicators */
            .status-indicator { 
                display:inline-block; width:12px; height:12px; 
                border-radius:50%; margin-right:0.5rem; 
            }
            .status-online { background: var(--success); }
            .status-offline { background: var(--error); }
            
            /* Main content area */
            main { padding: 1rem; max-width: 1400px; margin: 0 auto; }
            .page-content { display: none; }
            .page-content.active { display: block; }
            
            /* Common components */
            .card { 
                background: var(--card); border:1px solid var(--border); 
                border-radius:10px; padding:1rem; margin-bottom: 1rem; 
            }
            .grid2 { display:grid; grid-template-columns: 1fr 1fr; gap:1rem; }
            .grid3 { display:grid; grid-template-columns: repeat(3, 1fr); gap:1rem; }
            .grid4 { display:grid; grid-template-columns: repeat(4, 1fr); gap:1rem; }
            
            /* Summary cards */
            .summary-cards { 
                display:grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); 
                gap:1rem; margin-bottom:2rem; 
            }
            .summary-card { 
                background: var(--card); border:1px solid var(--border); 
                border-radius:10px; padding:1.5rem; text-align:center; 
            }
            .summary-card h3 { margin:0 0 1rem; font-size:0.9rem; opacity:0.8; }
            .summary-card .value { font-size:2.5rem; font-weight:bold; margin:0; color: var(--accent); }
            .summary-card.sprouts .value { color: var(--sprout); }
            .summary-card.plants .value { color: var(--plant); }
            
            /* Image containers */
            .img-wrap { 
                width:100%; height:300px; display:flex; align-items:center; 
                justify-content:center; border:1px solid var(--border); 
                border-radius:8px; cursor:pointer; transition: all 0.2s;
            }
            .img-wrap:hover { border-color: var(--accent); }
            .img-wrap img { 
                max-width:100%; max-height:100%; border-radius:8px; 
                object-fit: contain; 
            }
            
            /* Plant gallery */
            .gallery { 
                display:grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); 
                gap:1rem; 
            }
            .plant-thumb { 
                background: var(--card); border:2px solid var(--border); 
                border-radius:8px; overflow:hidden; cursor:pointer; 
                transition: all 0.2s; 
            }
            .plant-thumb:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.3); }
            .plant-thumb img { width:100%; height:120px; object-fit:cover; }
            .plant-thumb .info { padding:0.75rem; }
            .plant-thumb .info h4 { margin:0 0 0.5rem; font-size:0.9rem; }
            .plant-thumb .stats { font-size:0.8rem; opacity:0.8; }
            .plant-thumb.sprout { border-color: var(--sprout); }
            .plant-thumb.plant { border-color: var(--plant); }
            .plant-thumb.unknown { border-color: #666; opacity: 0.7; }
            .plant-thumb.hidden { display: none; }
            
            /* Health indicators */
            .health-excellent { border-left: 4px solid var(--success); }
            .health-good { border-left: 4px solid #84cc16; }
            .health-fair { border-left: 4px solid var(--warning); }
            .health-poor { border-left: 4px solid var(--error); }
            
            /* Tabs */
            .tabs { 
                display: flex; gap: 0.5rem; margin-bottom: 1rem; 
                border-bottom: 1px solid var(--border); 
            }
            .tab { 
                padding: 0.75rem 1rem; cursor: pointer; 
                border-bottom: 2px solid transparent; transition: all 0.2s; 
            }
            .tab:hover { background: rgba(79, 140, 255, 0.1); }
            .tab.active { border-bottom-color: var(--accent); color: var(--accent); }
            .tab-content { display: none; }
            .tab-content.active { display: block; }
            
            /* Controls */
            button { 
                padding: .6rem 1rem; background: var(--accent); color: white; 
                border: none; border-radius: 8px; cursor: pointer; 
                transition: all 0.2s; margin: 0.25rem; 
            }
            button:hover { opacity: 0.9; transform: translateY(-1px); }
            button:disabled { opacity: 0.5; cursor: not-allowed; transform: none; }
            
            input, select, textarea { 
                width: 100%; padding: 0.6rem; background: #0f172a; 
                color: var(--fg); border: 1px solid var(--border); 
                border-radius: 6px; 
            }
            
            /* Toggle switch */
            .toggle { 
                position: relative; display: inline-block; 
                width: 50px; height: 24px; 
            }
            .toggle input { opacity: 0; width: 0; height: 0; }
            .toggle .slider { 
                position: absolute; cursor: pointer; top: 0; left: 0; 
                right: 0; bottom: 0; background-color: #ccc; 
                transition: .4s; border-radius: 24px; 
            }
            .toggle .slider:before { 
                position: absolute; content: ""; height: 18px; width: 18px; 
                left: 3px; bottom: 3px; background-color: white; 
                transition: .4s; border-radius: 50%; 
            }
            .toggle input:checked + .slider { background-color: var(--accent); }
            .toggle input:checked + .slider:before { transform: translateX(26px); }
            
            /* Modal */
            .modal { 
                display: none; position: fixed; z-index: 2000; left: 0; top: 0; 
                width: 100%; height: 100%; background: rgba(0,0,0,0.8); 
            }
            .modal-content { 
                background: var(--card); margin: 2% auto; padding: 2rem; 
                border: 1px solid var(--border); border-radius: 10px; 
                width: 90%; max-width: 900px; max-height: 90vh; overflow: auto; 
                position: relative;
            }
            .close { 
                position: absolute; top: 1rem; right: 1.5rem; 
                font-size: 28px; font-weight: bold; cursor: pointer; 
                color: #aaa; 
            }
            .close:hover { color: var(--fg); }
            
            .muted { opacity: 0.8; }
            .text-center { text-align: center; }
            .mt-1 { margin-top: 1rem; }
            .mb-1 { margin-bottom: 1rem; }
        </style>
    </head>
    <body>
        <!-- Navigation Header -->
        <header class="nav">
            <div>🌿</div>
            <h2>SproutCast</h2>
            <div class="spacer"></div>
            
            <!-- Connection Status -->
            <div class="status-indicator status-online" id="connection-status"></div>
            <span class="muted" id="connection-text">Connected</span>
            
            <!-- Camera Selector -->
            <label class="muted">Camera</label>
            <select id="cam-select"></select>
            
            <!-- Navigation Links -->
            <nav class="nav-links">
                <a href="#" onclick="showPage('dashboard')" id="nav-dashboard" class="active">🏠 Dashboard</a>
                <a href="#" onclick="showPage('setup')" id="nav-setup">🔧 Setup</a>
                <a href="#" onclick="showPage('settings')" id="nav-settings">⚙️ Settings</a>
            </nav>
        </header>
        
        <main>
            <!-- Dashboard Page -->
            <div id="dashboard-page" class="page-content active">
                <!-- Summary Cards -->
                <div class="summary-cards">
                    <div class="summary-card sprouts">
                        <h3>Active Sprouts</h3>
                        <p class="value" id="sprout-count">0</p>
                    </div>
                    <div class="summary-card plants">
                        <h3>Mature Plants</h3>
                        <p class="value" id="plant-count">0</p>
                    </div>
                    <div class="summary-card">
                        <h3>Total Coverage</h3>
                        <p class="value" id="total-area">0 cm²</p>
                    </div>
                    <div class="summary-card">
                        <h3>Health Average</h3>
                        <p class="value" id="avg-health">0%</p>
                    </div>
                </div>

                <!-- Live Feed -->
                <div class="grid2">
                    <div class="card">
                        <h3 class="muted">Raw Camera Feed</h3>
                        <div class="img-wrap" onclick="showFullFrame('raw')">
                            <img id="img-raw" src="/frames/frame_raw.jpg" />
                        </div>
                    </div>
                    <div class="card">
                        <h3 class="muted">Analysis View</h3>
                        <div class="img-wrap" onclick="showFullFrame('annotated')">
                            <img id="img-ann" src="/frames/frame_annotated.jpg" />
                        </div>
                    </div>
                </div>

                <!-- Plant Gallery with Controls -->
                <div class="card">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
                        <h3 class="muted">Plant Monitoring Dashboard</h3>
                        <div style="display: flex; align-items: center; gap: 1rem;">
                            <label style="display: flex; align-items: center; gap: 0.5rem;">
                                <span>Show Unknown Plants</span>
                                <div class="toggle">
                                    <input type="checkbox" id="show-unknown" checked>
                                    <span class="slider"></span>
                                </div>
                            </label>
                        </div>
                    </div>
                    
                    <div class="tabs">
                        <div class="tab active" onclick="switchTab('all')">All Plants</div>
                        <div class="tab" onclick="switchTab('sprouts')">Sprouts (🌱)</div>
                        <div class="tab" onclick="switchTab('plants')">Mature Plants (🌿)</div>
                    </div>
                    
                    <div id="tab-all" class="tab-content active">
                        <div id="gallery-all" class="gallery"></div>
                    </div>
                    
                    <div id="tab-sprouts" class="tab-content">
                        <h4 class="muted">Sprout Monitoring</h4>
                        <p class="muted">Early growth stage plants requiring close monitoring</p>
                        <div id="gallery-sprouts" class="gallery"></div>
                    </div>
                    
                    <div id="tab-plants" class="tab-content">
                        <h4 class="muted">Mature Plant Monitoring</h4>
                        <p class="muted">Established plants with advanced analysis</p>
                        <div id="gallery-plants" class="gallery"></div>
                    </div>
                </div>
            </div>
            
            <!-- Setup Page -->
            <div id="setup-page" class="page-content">
                <div class="card">
                    <h3>Initial Plant Analysis</h3>
                    <p class="muted">Take a snapshot and run AI analysis to identify plants, their types, size, leaf count, and health metrics.</p>
                    <div class="grid2">
                        <div>
                            <label class="muted">Active Camera</label>
                            <select id="setup-cam-select" style="margin-bottom:.5rem;"></select>
                            <h4>Current Camera View</h4>
                            <div class="img-wrap">
                                <img id="setup-raw-img" src="/frames/frame_raw.jpg" />
                            </div>
                            <button onclick="takeSnapshot()" id="snapshot-btn">📸 Take Snapshot</button>
                            <button onclick="runAnalysis()" id="analyze-btn" disabled>🔍 Run AI Analysis</button>
                        </div>
                        <div>
                            <h4>Analysis Results</h4>
                            <div id="analysis-status" class="card" style="padding: 1rem; background: #1e3a8a; border: 1px solid #3b82f6;">Ready to take snapshot</div>
                            <div id="analysis-progress" style="display:none;">
                                <div>Processing...</div>
                                <div id="progress-text">Initializing AI models...</div>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="card" id="plant-results" style="display:none;">
                    <h3>Detected Plants</h3>
                    <div id="plant-analysis-grid" class="gallery"></div>
                    <div style="margin-top:1rem;">
                        <button onclick="saveAnalysis()" id="save-btn">💾 Save Analysis</button>
                        <button onclick="resetAnalysis()" id="reset-btn">🔄 Reset</button>
                    </div>
                </div>
            </div>
            
            <!-- Settings Page -->
            <div id="settings-page" class="page-content">
                <div class="card">
                    <h3>System Configuration</h3>
                    <div class="grid2">
                        <div>
                            <h4 class="muted">MQTT Settings</h4>
                            <label>MQTT Host</label>
                            <input type="text" id="mqtt-host" placeholder="localhost">
                            <label>MQTT Port</label>
                            <input type="number" id="mqtt-port" placeholder="1883">
                        </div>
                        <div>
                            <h4 class="muted">Processing Settings</h4>
                            <label>Detection Threshold</label>
                            <input type="number" id="threshold" placeholder="100">
                            <label>Scale (px/cm)</label>
                            <input type="number" id="scale-px-cm" placeholder="10.5" step="0.1">
                        </div>
                    </div>
                    <button onclick="saveSettings()">💾 Save Settings</button>
                </div>
                
                <div class="card">
                    <h3>Camera Management</h3>
                    <div style="margin-bottom: 1rem;">
                        <label>Select Camera</label>
                        <select id="settings-cam-select"></select>
                        <button onclick="addCamera()">➕ Add Camera</button>
                        <button onclick="deleteCamera()" style="background: var(--error);">🗑️ Delete</button>
                    </div>
                    
                    <div class="grid2">
                        <div>
                            <label>Camera Name</label>
                            <input type="text" id="camera-name" placeholder="Camera 0">
                            <label>Camera ID</label>
                            <input type="text" id="camera-id" placeholder="0">
                        </div>
                        <div>
                            <label>Input Mode</label>
                            <select id="input-mode">
                                <option value="IMAGE">Static Image</option>
                                <option value="CAMERA">Live Camera</option>
                                <option value="NETWORK">Network Stream</option>
                            </select>
                            <label>Input Path/URL</label>
                            <input type="text" id="input-path" placeholder="/samples/plant.jpg">
                        </div>
                    </div>
                    <button onclick="saveCameraSettings()">💾 Save Camera Settings</button>
                </div>
            </div>
        </main>
        
        <!-- Detail Modal -->
        <div id="detailModal" class="modal">
            <div class="modal-content">
                <span class="close" onclick="closeDetailModal()">&times;</span>
                <h2 id="modal-title">Plant Details</h2>
                <div id="modal-content"></div>
            </div>
        </div>

        <script>
            // Global state
            let CAM_INDEX = 0;
            let cameras = [];
            let allInstances = [];
            let sproutInstances = [];
            let plantInstances = [];
            let showUnknownPlants = true;
            let currentAnalysisResults = [];

            // Page navigation
            function showPage(pageName) {
                // Hide all pages
                document.querySelectorAll('.page-content').forEach(p => p.classList.remove('active'));
                document.querySelectorAll('.nav-links a').forEach(a => a.classList.remove('active'));
                
                // Show selected page
                document.getElementById(pageName + '-page').classList.add('active');
                document.getElementById('nav-' + pageName).classList.add('active');
                
                // Initialize page-specific functionality
                if (pageName === 'setup') {
                    initSetupPage();
                } else if (pageName === 'settings') {
                    initSettingsPage();
                }
            }

            // Tab switching
            function switchTab(tabName) {
                document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
                document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
                event.target.classList.add('active');
                document.getElementById('tab-' + tabName).classList.add('active');
            }

            // Unknown plants visibility toggle
            function toggleUnknownPlants() {
                showUnknownPlants = document.getElementById('show-unknown').checked;
                updatePlantGalleries();
            }

            // Plant card creation
            function createInstanceCard(instance, index) {
                const card = document.createElement('div');
                card.className = `plant-thumb ${instance.type || 'plant'}`;

                // Health classification
                const health = instance.health_score || 0;
                if (health >= 90) card.classList.add('health-excellent');
                else if (health >= 75) card.classList.add('health-good');
                else if (health >= 50) card.classList.add('health-fair');
                else card.classList.add('health-poor');

                // Unknown plant handling
                const classification = instance.classification || instance.label || 'unknown';
                if (classification === 'unknown') {
                    card.classList.add('unknown');
                    if (!showUnknownPlants) {
                        card.classList.add('hidden');
                    }
                }

                const typeIcon = instance.type === 'sprout' ? '🌱' : '🌿';
                const basePath = instance.type === 'sprout' ? 'sprouts' : 'plants';
                const instanceId = index.toString().padStart(3, '0');

                card.innerHTML = `
                    <img src="/${basePath}/${instance.type}_${instanceId}/crop.jpg"
                         onerror="this.src='/frames/plant_${index}_crop.jpg'" />
                    <div class="info">
                        <h4>${typeIcon} ${classification} ${index}</h4>
                        <div class="stats">
                            <div>❤️ ${Math.round(health)}%</div>
                            <div>🍃 ${instance.leaf_count || 0} leaves</div>
                            <div>📏 ${instance.height_cm ? Math.round(instance.height_cm*10)/10 + 'cm' : 'N/A'}</div>
                        </div>
                    </div>
                `;

                card.onclick = () => showInstanceDetails(instance, index);
                return card;
            }

            // Plant details modal
            function showInstanceDetails(instance, index) {
                const modal = document.getElementById('detailModal');
                const title = document.getElementById('modal-title');
                const content = document.getElementById('modal-content');

                const typeIcon = instance.type === 'sprout' ? '🌱' : '🌿';
                const classification = instance.classification || instance.label || 'unknown';
                title.textContent = `${typeIcon} ${classification.charAt(0).toUpperCase() + classification.slice(1)} ${index}`;

                const basePath = instance.type === 'sprout' ? 'sprouts' : 'plants';
                const instanceId = index.toString().padStart(3, '0');

                content.innerHTML = `
                    <div class="grid2" style="margin-bottom: 1rem;">
                        <div>
                            <h4>Original Image</h4>
                            <img src="/${basePath}/${instance.type}_${instanceId}/crop.jpg"
                                 onerror="this.src='/frames/plant_${index}_crop.jpg'" 
                                 style="width:100%; max-height:300px; object-fit:contain; border-radius:8px;" />
                        </div>
                        <div>
                            <h4>Analysis View</h4>
                            <img src="/${basePath}/${instance.type}_${instanceId}/highlight.jpg"
                                 onerror="this.src='/frames/plant_${index}_highlight.jpg'" 
                                 style="width:100%; max-height:300px; object-fit:contain; border-radius:8px;" />
                        </div>
                    </div>
                    <div class="grid2">
                        <div>
                            <strong>Type:</strong> ${instance.type || 'plant'}<br>
                            <strong>Classification:</strong> ${classification}<br>
                            <strong>Health Score:</strong> ${Math.round(instance.health_score || 0)}%<br>
                            <strong>Growth Stage:</strong> ${getGrowthStageName(instance.growth_stage)}<br>
                        </div>
                        <div>
                            <strong>Leaf Count:</strong> ${instance.leaf_count || 0}<br>
                            <strong>Area:</strong> ${Math.round(instance.area_cm2 || 0)} cm²<br>
                            <strong>Dimensions:</strong> ${instance.height_cm ? Math.round(instance.height_cm*10)/10 : 'N/A'}×${instance.width_cm ? Math.round(instance.width_cm*10)/10 : 'N/A'} cm<br>
                            <strong>Last Updated:</strong> ${new Date(instance.timestamp || Date.now()).toLocaleTimeString()}<br>
                        </div>
                    </div>
                    <div style="margin-top: 1rem;">
                        <h4>Raw Telemetry</h4>
                        <pre style="background:#0f172a; border:1px solid var(--border); padding:1rem; border-radius:8px; max-height:200px; overflow:auto; white-space:pre-wrap; word-break:break-word;">${JSON.stringify(instance, null, 2)}</pre>
                    </div>
                `;

                modal.style.display = 'block';
            }

            function getGrowthStageName(stage) {
                const stages = ['Cotyledon', 'First Leaves', 'Early Vegetative', 'Vegetative', 'Flowering', 'Fruiting', 'Dormant'];
                return stages[stage] || 'Unknown';
            }

            function closeDetailModal() {
                document.getElementById('detailModal').style.display = 'none';
            }

            function showFullFrame(type) {
                const modal = document.getElementById('detailModal');
                const title = document.getElementById('modal-title');
                const content = document.getElementById('modal-content');

                title.textContent = type === 'raw' ? 'Raw Camera Feed' : 'Analysis View';
                content.innerHTML = `
                    <img src="/frames/frame_${type}.jpg?t=${Date.now()}"
                         style="width:100%; max-height:80vh; object-fit:contain; border-radius:8px;" />
                `;

                modal.style.display = 'block';
            }

            // Data refresh functions
            async function refreshTelemetry() {
                try {
                    const r = await fetch('/api/latest');
                    const d = await r.json();
                    const txt = (d && d.latest) ? d.latest : '{}';
                    const data = JSON.parse(txt);

                    sproutInstances = data.sprouts || [];
                    plantInstances = data.plants || [];
                    allInstances = [...sproutInstances, ...plantInstances];

                    updateSummary();
                    updatePlantGalleries();

                    document.getElementById('connection-status').className = 'status-indicator status-online';
                    document.getElementById('connection-text').textContent = 'Connected';

                } catch (e) {
                    document.getElementById('connection-status').className = 'status-indicator status-offline';
                    document.getElementById('connection-text').textContent = 'Connection Error';
                }
            }

            function updateSummary() {
                document.getElementById('sprout-count').textContent = sproutInstances.length;
                document.getElementById('plant-count').textContent = plantInstances.length;

                const totalArea = allInstances.reduce((sum, inst) => sum + (inst.area_cm2 || 0), 0);
                document.getElementById('total-area').textContent = Math.round(totalArea) + ' cm²';

                const avgHealth = allInstances.length > 0 ? 
                    allInstances.reduce((sum, inst) => sum + (inst.health_score || 0), 0) / allInstances.length : 0;
                document.getElementById('avg-health').textContent = Math.round(avgHealth) + '%';
            }

            function updatePlantGalleries() {
                const allGallery = document.getElementById('gallery-all');
                const sproutGallery = document.getElementById('gallery-sprouts');
                const plantGallery = document.getElementById('gallery-plants');

                allGallery.innerHTML = '';
                sproutGallery.innerHTML = '';
                plantGallery.innerHTML = '';

                allInstances.forEach((instance, index) => {
                    const card = createInstanceCard(instance, index);
                    allGallery.appendChild(card.cloneNode(true));

                    if (instance.type === 'sprout') {
                        sproutGallery.appendChild(card.cloneNode(true));
                    } else {
                        plantGallery.appendChild(card.cloneNode(true));
                    }
                });

                // Re-attach click handlers
                document.querySelectorAll('.plant-thumb').forEach((card, index) => {
                    const instanceIndex = parseInt(card.querySelector('h4').textContent.match(/\d+$/)[0]);
                    const instance = allInstances[instanceIndex];
                    card.onclick = () => showInstanceDetails(instance, instanceIndex);
                });
            }

            function refreshImages() {
                const t = Date.now();
                const rawImg = document.getElementById('img-raw');
                const annImg = document.getElementById('img-ann');
                const setupImg = document.getElementById('setup-raw-img');
                
                if (rawImg) rawImg.src = '/frames/frame_raw.jpg?t=' + t;
                if (annImg) annImg.src = '/frames/frame_annotated.jpg?t=' + t;
                if (setupImg) setupImg.src = '/frames/frame_raw.jpg?t=' + t;
            }

            // Camera management
            async function loadCameras() {
                try {
                    const r = await fetch('/api/config');
                    const cfg = await r.json();
                    cameras = cfg.cameras || [{ id: cfg.uns?.camera_id || '0', name: 'Camera 0' }];
                    
                    const selectors = ['cam-select', 'setup-cam-select', 'settings-cam-select'];
                    selectors.forEach(selectorId => {
                        const sel = document.getElementById(selectorId);
                        if (sel) {
                            sel.innerHTML = '';
                            cameras.forEach((c, idx) => {
                                const opt = document.createElement('option');
                                opt.value = idx;
                                opt.textContent = c.name || `Camera ${idx}`;
                                sel.appendChild(opt);
                            });
                            sel.value = cfg.active_camera_index || 0;
                        }
                    });
                    
                    CAM_INDEX = parseInt(document.getElementById('cam-select')?.value || '0');
                    
                    // Camera change handler
                    document.getElementById('cam-select').onchange = async () => {
                        CAM_INDEX = parseInt(document.getElementById('cam-select').value || '0');
                        await fetch('/api/set-active-camera', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ index: CAM_INDEX })
                        });
                        refreshTelemetry();
                        refreshImages();
                    };

                } catch (e) {
                    console.error('Failed to load cameras:', e);
                }
            }

            // Setup page functions
            function initSetupPage() {
                loadCameras();
            }

            async function takeSnapshot() {
                const statusDiv = document.getElementById('analysis-status');
                statusDiv.textContent = 'Taking snapshot...';
                statusDiv.style.background = '#1e3a8a';
                
                try {
                    await fetch('/api/set-active-camera', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ index: CAM_INDEX })
                    });
                    
                    refreshImages();
                    document.getElementById('analyze-btn').disabled = false;
                    statusDiv.textContent = 'Snapshot ready! Click "Run AI Analysis" to proceed.';
                    statusDiv.style.background = '#0f4c3a';
                } catch (e) {
                    statusDiv.textContent = 'Failed to take snapshot: ' + e.message;
                    statusDiv.style.background = '#4c1d1d';
                }
            }

            async function runAnalysis() {
                const statusDiv = document.getElementById('analysis-status');
                statusDiv.textContent = 'Running AI analysis...';
                statusDiv.style.background = '#1e3a8a';
                
                try {
                    // Simulate analysis process
                    await new Promise(resolve => setTimeout(resolve, 2000));
                    
                    // Get current plant data or simulate some results
                    const response = await fetch('/api/latest');
                    const data = await response.json();
                    let plants = [];
                    
                    if (data.latest) {
                        const parsed = JSON.parse(data.latest);
                        plants = [...(parsed.sprouts || []), ...(parsed.plants || [])];
                    }
                    
                    // If no real data, create some sample results
                    if (plants.length === 0) {
                        plants = Array.from({length: Math.floor(Math.random() * 5) + 1}, (_, i) => ({
                            id: i,
                            type: Math.random() > 0.5 ? 'sprout' : 'plant',
                            classification: ['basil', 'mint', 'lettuce', 'unknown'][Math.floor(Math.random() * 4)],
                            health_score: Math.floor(Math.random() * 40) + 60,
                            leaf_count: Math.floor(Math.random() * 15) + 5,
                            area_cm2: Math.random() * 50 + 10,
                            height_cm: Math.random() * 20 + 5
                        }));
                    }
                    
                    currentAnalysisResults = plants;
                    displayAnalysisResults();
                    statusDiv.textContent = `Analysis complete! Found ${plants.length} plants.`;
                    statusDiv.style.background = '#0f4c3a';
                    
                } catch (e) {
                    statusDiv.textContent = 'Analysis failed: ' + e.message;
                    statusDiv.style.background = '#4c1d1d';
                }
            }

            function displayAnalysisResults() {
                const container = document.getElementById('plant-analysis-grid');
                container.innerHTML = '';
                
                currentAnalysisResults.forEach((plant, index) => {
                    const card = document.createElement('div');
                    card.className = 'plant-thumb';
                    card.innerHTML = `
                        <img src="/frames/plant_${index}_crop.jpg" onerror="this.src='/frames/frame_raw.jpg'" />
                        <div class="info">
                            <h4>${plant.type === 'sprout' ? '🌱' : '🌿'} ${plant.classification}</h4>
                            <div class="stats">
                                <div>Health: ${plant.health_score}%</div>
                                <div>Leaves: ${plant.leaf_count}</div>
                            </div>
                            <select onchange="updatePlantType(${index}, this.value)" style="width: 100%; margin-top: 0.5rem;">
                                <option value="unknown" ${plant.classification === 'unknown' ? 'selected' : ''}>Unknown</option>
                                <option value="basil" ${plant.classification === 'basil' ? 'selected' : ''}>Basil</option>
                                <option value="mint" ${plant.classification === 'mint' ? 'selected' : ''}>Mint</option>
                                <option value="lettuce" ${plant.classification === 'lettuce' ? 'selected' : ''}>Lettuce</option>
                                <option value="spinach" ${plant.classification === 'spinach' ? 'selected' : ''}>Spinach</option>
                            </select>
                        </div>
                    `;
                    container.appendChild(card);
                });
                
                document.getElementById('plant-results').style.display = 'block';
            }

            function updatePlantType(plantIndex, newType) {
                if (currentAnalysisResults[plantIndex]) {
                    currentAnalysisResults[plantIndex].classification = newType;
                }
            }

            async function saveAnalysis() {
                try {
                    for (const [index, plant] of currentAnalysisResults.entries()) {
                        await fetch('/api/plant-class', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ index, label: plant.classification })
                        });
                    }
                    
                    const statusDiv = document.getElementById('analysis-status');
                    statusDiv.textContent = 'Analysis saved successfully!';
                    statusDiv.style.background = '#0f4c3a';
                } catch (e) {
                    const statusDiv = document.getElementById('analysis-status');
                    statusDiv.textContent = 'Failed to save analysis: ' + e.message;
                    statusDiv.style.background = '#4c1d1d';
                }
            }

            function resetAnalysis() {
                document.getElementById('analyze-btn').disabled = true;
                document.getElementById('plant-results').style.display = 'none';
                document.getElementById('analysis-status').textContent = 'Ready to take snapshot';
                document.getElementById('analysis-status').style.background = '#1e3a8a';
                currentAnalysisResults = [];
            }

            // Settings page functions
            function initSettingsPage() {
                loadSettingsData();
                loadCameras();
            }

            async function loadSettingsData() {
                try {
                    const response = await fetch('/api/config');
                    const config = await response.json();
                    
                    document.getElementById('mqtt-host').value = config.mqtt?.host || 'localhost';
                    document.getElementById('mqtt-port').value = config.mqtt?.port || 1883;
                    document.getElementById('threshold').value = config.processing?.threshold || 100;
                    document.getElementById('scale-px-cm').value = config.processing?.scale_px_per_cm || 0;
                    
                } catch (e) {
                    console.error('Failed to load settings:', e);
                }
            }

            async function saveSettings() {
                try {
                    const config = {
                        mqtt: {
                            host: document.getElementById('mqtt-host').value,
                            port: parseInt(document.getElementById('mqtt-port').value)
                        },
                        processing: {
                            threshold: parseInt(document.getElementById('threshold').value),
                            scale_px_per_cm: parseFloat(document.getElementById('scale-px-cm').value)
                        }
                    };
                    
                    await fetch('/api/config', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(config)
                    });
                    
                    alert('Settings saved successfully!');
                } catch (e) {
                    alert('Failed to save settings: ' + e.message);
                }
            }

            // Modal event handlers
            window.onclick = function(event) {
                const modal = document.getElementById('detailModal');
                if (event.target === modal) {
                    modal.style.display = 'none';
                }
            }

            // Toggle event handler
            document.getElementById('show-unknown').onchange = toggleUnknownPlants;

            // Initialize application
            document.addEventListener('DOMContentLoaded', function() {
                loadCameras();
                refreshTelemetry();
                refreshImages();
                
                // Set up refresh intervals
                setInterval(refreshTelemetry, 1200);
                setInterval(refreshImages, 2000);
                setInterval(loadCameras, 10000);
            });
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html)

# API Routes
@app.get("/api/latest")
def api_latest():
    return JSONResponse(content={"latest": state["latest"]})

@app.get("/api/config")
def api_config_get():
    return JSONResponse(content=state["config"])

@app.post("/api/config")
async def api_config_set(payload: Dict[str, Any]):
    for k, v in payload.items():
        if isinstance(v, dict) and k in state["config"] and isinstance(state["config"][k], dict):
            state["config"][k].update(v)
        else:
            state["config"][k] = v
    try:
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            pyjson.dump(state["config"], f, indent=2)
    except Exception:
        pass
    return JSONResponse(content={"ok": True, "config": state["config"]})

@app.post("/api/set-active-camera")
async def api_set_active_camera(payload: Dict[str, Any]):
    try:
        idx = int(payload.get('index', 0))
        cfg = {}
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                cfg = pyjson.load(f)
        cfg['active_camera_index'] = idx
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            pyjson.dump(cfg, f, indent=2)
        return JSONResponse(content={"ok": True, "active_camera_index": idx})
    except Exception as e:
        return JSONResponse(content={"ok": False, "error": str(e)}, status_code=500)

@app.get("/api/ai")
def api_ai():
    try:
        with open(AI_METRICS_PATH, 'r', encoding='utf-8') as f:
            return JSONResponse(content=pyjson.load(f))
    except Exception:
        return JSONResponse(content={})

@app.get("/api/sprouts")
def api_sprouts():
    """Get all detected sprouts"""
    try:
        with open("/app/data/sprouts/summary.json", 'r', encoding='utf-8') as f:
            return JSONResponse(content=pyjson.load(f))
    except Exception:
        return JSONResponse(content={"sprouts": [], "count": 0})

@app.get("/api/plants") 
def api_plants():
    """Get all detected mature plants"""
    try:
        with open("/app/data/plants/summary.json", 'r', encoding='utf-8') as f:
            return JSONResponse(content=pyjson.load(f))
    except Exception:
        return JSONResponse(content={"plants": [], "count": 0})

@app.get("/api/instance/{instance_type}/{instance_id}")
def api_instance_data(instance_type: str, instance_id: int):
    """Get specific instance data (sprout or plant)"""
    try:
        if instance_type not in ['sprout', 'plant', 'sprouts', 'plants']:
            return JSONResponse(content={"error": "Invalid instance type"}, status_code=400)
        
        normalized_type = 'sprout' if instance_type in ['sprout', 'sprouts'] else 'plant'
        instance_id_str = f"{instance_id:03d}"
        
        data_path = f"/app/data/{normalized_type}s/{normalized_type}_{instance_id_str}/data.json"
        if os.path.exists(data_path):
            with open(data_path, 'r', encoding='utf-8') as f:
                return JSONResponse(content=pyjson.load(f))
        
        legacy_path = f"/app/data/plant_{instance_id}.json"
        if os.path.exists(legacy_path):
            with open(legacy_path, 'r', encoding='utf-8') as f:
                return JSONResponse(content=pyjson.load(f))
        
        return JSONResponse(content={"error": "Instance not found"}, status_code=404)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.get("/api/plant-data/{plant_id}")
def api_plant_data(plant_id: int):
    return api_instance_data("plant", plant_id)

@app.post("/api/plant-class")
async def api_plant_class(payload: Dict[str, Any]):
    try:
        idx = str(payload.get('index'))
        label = str(payload.get('label', 'unknown'))
        overrides = {}
        if os.path.exists(OVERRIDE_PATH):
            with open(OVERRIDE_PATH, 'r', encoding='utf-8') as f:
                overrides = pyjson.load(f)
        if idx not in overrides:
            overrides[idx] = {}
        overrides[idx]['label'] = label
        os.makedirs(os.path.dirname(OVERRIDE_PATH), exist_ok=True)
        with open(OVERRIDE_PATH, 'w', encoding='utf-8') as f:
            pyjson.dump(overrides, f, indent=2)
        return JSONResponse(content={"ok": True, "overrides": overrides})
    except Exception as e:
        return JSONResponse(content={"ok": False, "error": str(e)}, status_code=500)
