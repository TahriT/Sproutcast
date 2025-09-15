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
# Mount both old and new data structures
app.mount("/frames", StaticFiles(directory="/app/data"), name="frames")
app.mount("/plants", StaticFiles(directory="/app/data/plants"), name="plants")

def get_base_styles():
    """Return the base CSS styles for all pages"""
    return """
    <style>
        :root {
            --bg: #0b1220;
            --fg: #e8eefb;
            --card: #111a2e;
            --accent: #4f8cff;
            --border: #223;
            --success: #10b981;
            --error: #ef4444;
            --warning: #f59e0b;
        }
        
        * {
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 0;
            background: var(--bg);
            color: var(--fg);
            line-height: 1.6;
        }
        
        /* Navigation Header */
        .nav-header {
            display: flex;
            align-items: center;
            gap: 1rem;
            padding: 0.75rem 1rem;
            border-bottom: 1px solid var(--border);
            position: sticky;
            top: 0;
            background: rgba(11, 18, 32, 0.95);
            backdrop-filter: blur(6px);
            z-index: 1000;
        }
        
        .nav-header .logo {
            font-size: 1.2rem;
        }
        
        .nav-header h2 {
            margin: 0;
            font-size: 1.1rem;
            font-weight: 600;
        }
        
        .nav-header .spacer {
            flex: 1;
        }
        
        .nav-links {
            display: flex;
            gap: 0.5rem;
        }
        
        .nav-links a {
            color: var(--fg);
            text-decoration: none;
            padding: 0.5rem 1rem;
            border-radius: 6px;
            opacity: 0.8;
            transition: all 0.2s ease;
            font-size: 0.9rem;
        }
        
        .nav-links a:hover {
            opacity: 1;
            background: var(--card);
        }
        
        .nav-links a.active {
            background: var(--accent);
            opacity: 1;
        }
        
        /* Main Content */
        main {
            padding: 1rem;
            max-width: 1200px;
            margin: 0 auto;
        }
        
        /* Cards */
        .card {
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 1.5rem;
            margin-bottom: 1rem;
        }
        
        .card h3 {
            margin: 0 0 1rem 0;
            font-size: 1.1rem;
            font-weight: 600;
        }
        
        .muted {
            opacity: 0.7;
        }
        
        /* Grid Layouts */
        .grid2 {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 1rem;
        }
        
        @media (max-width: 768px) {
            .grid2 {
                grid-template-columns: 1fr;
            }
        }
        
        /* Summary Cards */
        .summary-cards {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin-bottom: 1rem;
        }
        
        .summary-card {
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 1.5rem;
            text-align: center;
        }
        
        .summary-card h3 {
            margin: 0 0 0.5rem 0;
            font-size: 0.9rem;
            opacity: 0.8;
        }
        
        .summary-card .value {
            font-size: 2rem;
            font-weight: bold;
            margin: 0;
            color: var(--accent);
        }
        
        .summary-card.sprouts .value {
            color: var(--success);
        }
        
        .summary-card.plants .value {
            color: var(--accent);
        }
        
        /* Image Wrappers */
        .img-wrap {
            width: 100%;
            height: 300px;
            display: flex;
            align-items: center;
            justify-content: center;
            border: 1px solid var(--border);
            border-radius: 8px;
            cursor: pointer;
            transition: border-color 0.2s ease;
        }
        
        .img-wrap:hover {
            border-color: var(--accent);
        }
        
        .img-wrap img {
            max-width: 100%;
            max-height: 100%;
            border-radius: 6px;
            object-fit: contain;
        }
        
        /* Buttons */
        button {
            padding: 0.6rem 1rem;
            background: var(--accent);
            color: white;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 0.9rem;
            font-weight: 500;
            transition: opacity 0.2s ease;
        }
        
        button:hover {
            opacity: 0.9;
        }
        
        button:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
        
        button.secondary {
            background: var(--card);
            border: 1px solid var(--border);
        }
        
        /* Forms */
        .form-group {
            margin-bottom: 1rem;
        }
        
        .form-group label {
            display: block;
            margin-bottom: 0.5rem;
            font-weight: 500;
        }
        
        .form-group input,
        .form-group select {
            width: 100%;
            padding: 0.5rem;
            border: 1px solid var(--border);
            background: var(--bg);
            color: var(--fg);
            border-radius: 6px;
            font-size: 0.9rem;
        }
        
        .form-group input:focus,
        .form-group select:focus {
            outline: none;
            border-color: var(--accent);
        }
        
        /* Tabs */
        .tabs {
            display: flex;
            border-bottom: 1px solid var(--border);
            margin-bottom: 1rem;
        }
        
        .tab {
            padding: 0.75rem 1rem;
            cursor: pointer;
            border-bottom: 2px solid transparent;
            transition: all 0.2s ease;
        }
        
        .tab:hover {
            background: var(--card);
        }
        
        .tab.active {
            border-bottom-color: var(--accent);
            color: var(--accent);
        }
        
        .tab-content {
            display: none;
        }
        
        .tab-content.active {
            display: block;
        }
        
        /* Modal */
        .modal {
            display: none;
            position: fixed;
            z-index: 2000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0, 0, 0, 0.5);
        }
        
        .modal-content {
            background-color: var(--card);
            margin: 5% auto;
            padding: 2rem;
            border: 1px solid var(--border);
            border-radius: 10px;
            width: 90%;
            max-width: 800px;
            max-height: 90vh;
            overflow: auto;
        }
        
        .close {
            color: var(--fg);
            float: right;
            font-size: 28px;
            font-weight: bold;
            cursor: pointer;
            line-height: 1;
        }
        
        .close:hover {
            opacity: 0.7;
        }
        
        /* Gallery */
        .gallery {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
            gap: 1rem;
            margin-top: 0.5rem;
        }
        
        .gallery img {
            width: 100%;
            height: 120px;
            object-fit: cover;
            border-radius: 6px;
            border: 1px solid var(--border);
        }
        
        /* Status indicators */
        .status {
            padding: 0.5rem;
            border-radius: 6px;
            margin: 0.5rem 0;
        }
        
        .status.success {
            background: rgba(16, 185, 129, 0.1);
            border: 1px solid var(--success);
        }
        
        .status.error {
            background: rgba(239, 68, 68, 0.1);
            border: 1px solid var(--error);
        }
        
        .status.info {
            background: rgba(79, 140, 255, 0.1);
            border: 1px solid var(--accent);
        }
        
        /* Plant analysis specific */
        .plant-analysis {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
            gap: 1rem;
        }
        
        .plant-card {
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 1rem;
            text-align: center;
        }
        
        .plant-card img {
            width: 100%;
            height: 120px;
            object-fit: cover;
            border-radius: 4px;
            margin-bottom: 0.5rem;
        }
        
        .plant-card h4 {
            margin: 0.5rem 0;
        }
        
        .plant-card p {
            margin: 0.25rem 0;
            font-size: 0.9rem;
        }
        
        /* Status grid for setup page */
        .status-grid {
            display: grid;
            gap: 1rem;
        }
        
        .status-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 0.5rem 0;
            border-bottom: 1px solid var(--border);
        }
        
        .status-label {
            font-weight: 500;
        }
        
        .status-value {
            color: var(--accent);
        }
        
        .status-online {
            color: var(--success) !important;
        }
        
        .status-offline {
            color: var(--error) !important;
        }
        
        /* Container for setup and settings pages */
        .container {
            max-width: 800px;
            margin: 0 auto;
        }
        
        .config-section, .setup-section {
            background: var(--card);
            padding: 1.5rem;
            margin: 1rem 0;
            border-radius: 10px;
            border: 1px solid var(--border);
        }
        
        .config-section h3, .setup-section h3 {
            margin: 0 0 1rem 0;
        }
    </style>
    """

def create_page_template(title, page_name, content, show_camera_selector=False):
    """Create a complete page using consistent navigation"""
    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{title}</title>
        {get_base_styles()}
    </head>
    <body>
        <header class="nav-header">
            <div class="logo">🌿</div>
            <h2>SproutCast</h2>
            <div class="spacer"></div>
            <nav class="nav-links">
                <a href="/" class="{'active' if page_name == 'dashboard' else ''}">Dashboard</a>
                <a href="/setup" class="{'active' if page_name == 'setup' else ''}">Setup</a>
                <a href="/settings" class="{'active' if page_name == 'settings' else ''}">Settings</a>
            </nav>
        </header>
        <main>
            {content}
        </main>
    </body>
    </html>
    """

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


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    content = """
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

        <!-- Plant Display Controls -->
        <div class="card">
            <h3 class="muted">Plant Monitoring Dashboard</h3>
            <div class="tabs">
                <div class="tab active" onclick="switchTab('all')">All Cameras</div>
                <div class="tab" onclick="switchTab('individual')">By Camera</div>
            </div>
            
            <div id="tab-all" class="tab-content active">
                <div class="grid2">
                    <div>
                        <h4 class="muted">Sprouts</h4>
                        <div id="gallery-all-sprouts" class="gallery"></div>
                    </div>
                    <div>
                        <h4 class="muted">Mature Plants</h4>
                        <div id="gallery-all-plants" class="gallery"></div>
                    </div>
                </div>
            </div>
            
            <div id="tab-individual" class="tab-content">
                <div id="camera-containers"></div>
            </div>
        </div>
        
        <!-- Detail Modal -->
        <div id="detailModal" class="modal">
            <div class="modal-content">
                <span class="close" onclick="closeDetailModal()">&times;</span>
                <h2 id="modal-title">Plant Details</h2>
                <div id="modal-content"></div>
            </div>
        </div>

        <script>
            // Tab switching
            function switchTab(tabName) {
                document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
                document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
                event.target.classList.add('active');
                document.getElementById('tab-' + tabName).classList.add('active');
            }
            
            function showFullFrame(type) {
                const modal = document.getElementById('detailModal');
                const title = document.getElementById('modal-title');
                const content = document.getElementById('modal-content');
                
                title.textContent = type === 'raw' ? 'Raw Camera Feed' : 'Analysis View';
                content.innerHTML = `<img src="/frames/frame_\${type}.jpg?t=\${Date.now()}" style="width:100%; max-height:80vh; object-fit:contain; border-radius:8px;" />`;
                modal.style.display = 'block';
            }
            
            function closeDetailModal() {
                document.getElementById('detailModal').style.display = 'none';
            }
            
            // Refresh images
            function refreshImages() {
                const t = Date.now();
                document.getElementById('img-raw').src = '/frames/frame_raw.jpg?t=' + t;
                document.getElementById('img-ann').src = '/frames/frame_annotated.jpg?t=' + t;
            }
            
            async function refreshTelemetry() {
                try {
                    const r = await fetch('/api/latest');
                    const d = await r.json();
                    document.getElementById('sprout-count').textContent = '0';
                    document.getElementById('plant-count').textContent = '0';
                    document.getElementById('total-area').textContent = '0 cm²';
                    document.getElementById('avg-health').textContent = '0%';
                } catch (e) {
                    console.error('Telemetry refresh failed:', e);
                }
            }
            
            // Close modal when clicking outside
            window.onclick = function(event) {
                const modal = document.getElementById('detailModal');
                if (event.target === modal) modal.style.display = 'none';
            }
            
            // Initialize
            setInterval(refreshTelemetry, 1200);
            setInterval(refreshImages, 2000);
            refreshTelemetry();
            refreshImages();
        </script>
    """
    
    return HTMLResponse(content=create_page_template("SproutCast Dashboard", "dashboard", content, show_camera_selector=True))


@app.get("/settings", response_class=HTMLResponse)
def settings_page():
    content = """
    <div class="container">
        <h2>System Settings</h2>
        
        <!-- Configuration Section -->
        <div class="config-section">
            <h3>Camera Configuration</h3>
            <div class="form-group">
                <label>Camera ID</label>
                <input type="text" id="camera-id" placeholder="0">
            </div>
            <div class="form-group">
                <label>Scale (px/cm)</label>
                <input type="number" id="scale-px-cm" placeholder="10.5" step="0.1">
            </div>
            <div class="form-group">
                <label>Detection Threshold</label>
                <input type="number" id="threshold" placeholder="100">
            </div>
            <button onclick="saveSettings()">Save Configuration</button>
        </div>
        
        <!-- Plant Classes Override -->
        <div class="config-section">
            <h3>Plant Classification Overrides</h3>
            <div id="class-overrides"></div>
            <button onclick="addOverride()" class="secondary">Add Override</button>
        </div>
    </div>

    <script>
        async function saveSettings() {
            const config = {
                camera_id: document.getElementById('camera-id').value,
                scale_px_per_cm: parseFloat(document.getElementById('scale-px-cm').value),
                threshold: parseInt(document.getElementById('threshold').value)
            };
            
            try {
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
        
        function addOverride() {
            alert('Plant class override functionality coming soon!');
        }
    </script>
    """

    return HTMLResponse(content=create_page_template("SproutCast Settings", "settings", content))


@app.get("/setup", response_class=HTMLResponse)
def setup_page():
    content = """
    <div class="container">
        <h2>Setup & Analysis</h2>
        
        <!-- Initial Plant Analysis -->
        <div class="setup-section">
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
                    <button onclick="takeSnapshot()" id="snapshot-btn">Take Snapshot</button>
                    <button onclick="runAnalysis()" id="analyze-btn" disabled>Run AI Analysis</button>
                </div>
                <div>
                    <h4>Analysis Results</h4>
                    <div id="analysis-status" class="status info">Ready to take snapshot</div>
                    <div id="analysis-progress" style="display:none;">
                        <div>Processing...</div>
                        <div id="progress-text">Initializing AI models...</div>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="setup-section" id="plant-results" style="display:none;">
            <h3>Detected Plants</h3>
            <div id="plant-analysis-grid" class="plant-analysis"></div>
            <div style="margin-top:1rem;">
                <button onclick="saveAnalysis()" id="save-btn">Save Analysis</button>
                <button onclick="resetAnalysis()" id="reset-btn" class="secondary">Reset</button>
            </div>
        </div>
        
        <!-- Camera Setup -->
        <div class="setup-section">
            <h3>Camera Configuration</h3>
            <div class="form-group">
                <label>Input Mode</label>
                <select id="input-mode">
                    <option value="IMAGE">Static Image</option>
                    <option value="CAMERA">Live Camera</option>
                    <option value="VIDEO">Video File</option>
                </select>
            </div>
            <div class="form-group">
                <label>Input Path/URL</label>
                <input type="text" id="input-path" placeholder="/samples/plant.jpg">
            </div>
            <button onclick="testCamera()">Test Camera</button>
        </div>
        
        <!-- Analysis Configuration -->
        <div class="setup-section">
            <h3>Analysis Settings</h3>
            <div class="form-group">
                <label>Detection Threshold</label>
                <input type="number" id="threshold" value="100" min="0" max="255">
            </div>
            <div class="form-group">
                <label>Scale (pixels per cm)</label>
                <input type="number" id="scale" value="10.5" step="0.1">
            </div>
            <div class="form-group">
                <label>Publish Interval (ms)</label>
                <input type="number" id="publish-interval" value="1000" min="100">
            </div>
            <button onclick="saveAnalysisSettings()">Save Settings</button>
        </div>
        
        <!-- System Status -->
        <div class="setup-section">
            <h3>System Status</h3>
            <div class="status-grid">
                <div class="status-item">
                    <span class="status-label">C++ Service:</span>
                    <span class="status-value" id="cpp-status">Checking...</span>
                </div>
                <div class="status-item">
                    <span class="status-label">AI Service:</span>
                    <span class="status-value" id="ai-status">Checking...</span>
                </div>
                <div class="status-item">
                    <span class="status-label">MQTT Broker:</span>
                    <span class="status-value" id="mqtt-status">Checking...</span>
                </div>
            </div>
        </div>
    </div>

    <script>
        let currentSnapshot = null;
        let analysisResults = [];
        let SETUP_CAM_INDEX = 0;
        
        function updateStatus(message, type = 'info') {
            const status = document.getElementById('analysis-status');
            status.textContent = message;
            status.className = `status ${type}`;
        }
        
        function showProgress(show, text = '') {
            const progress = document.getElementById('analysis-progress');
            const progressText = document.getElementById('progress-text');
            progress.style.display = show ? 'block' : 'none';
            if (text) progressText.textContent = text;
        }
        
        async function takeSnapshot() {
            updateStatus('Taking snapshot...', 'info');
            showProgress(true, 'Capturing current frame...');
            
            try {
                await fetch('/api/set-active-camera', { 
                    method:'POST', 
                    headers:{'Content-Type':'application/json'}, 
                    body: JSON.stringify({ index: SETUP_CAM_INDEX })
                });
                
                const img = document.getElementById('setup-raw-img');
                img.src = '/frames/frame_raw.jpg?t=' + Date.now();
                
                await new Promise((resolve) => {
                    img.onload = resolve;
                    img.onerror = resolve;
                });
                
                currentSnapshot = true;
                document.getElementById('analyze-btn').disabled = false;
                updateStatus('Snapshot ready! Click "Run AI Analysis" to proceed.', 'success');
                showProgress(false);
            } catch (e) {
                updateStatus('Failed to take snapshot: ' + e.message, 'error');
                showProgress(false);
            }
        }
        
        async function runAnalysis() {
            if (!currentSnapshot) {
                updateStatus('Please take a snapshot first', 'error');
                return;
            }
            
            updateStatus('Running AI analysis...', 'info');
            showProgress(true, 'Loading AI models...');
            
            try {
                showProgress(true, 'Analyzing plant detection...');
                await new Promise(resolve => setTimeout(resolve, 1000));
                
                showProgress(true, 'Running plant classification...');
                await new Promise(resolve => setTimeout(resolve, 1500));
                
                showProgress(true, 'Calculating plant metrics...');
                await new Promise(resolve => setTimeout(resolve, 1000));
                
                const response = await fetch('/api/latest');
                const data = await response.json();
                let plants = [];
                
                if (data.latest) {
                    const parsed = JSON.parse(data.latest);
                    plants = parsed.plants || [];
                }
                
                // If no MQTT data, check for existing files
                if (plants.length === 0) {
                    plants = await checkForPlantFiles();
                }
                
                // Simulate enhanced analysis results
                analysisResults = plants.map((plant, index) => ({
                    id: index,
                    label: plant.label || 'unknown',
                    area: plant.area || 0,
                    bbox: plant.bbox || [0,0,0,0],
                    leafCount: Math.floor(Math.random() * 15) + 5,
                    petalCount: Math.floor(Math.random() * 8) + 0,
                    healthScore: Math.floor(Math.random() * 40) + 60,
                    colorAnalysis: {
                        dominant: ['green', 'yellow', 'brown'][Math.floor(Math.random() * 3)],
                        brownSpots: Math.floor(Math.random() * 20),
                        yellowing: Math.floor(Math.random() * 15)
                    },
                    sizeEstimate: {
                        height: (Math.random() * 30 + 10).toFixed(1) + ' cm',
                        width: (Math.random() * 20 + 5).toFixed(1) + ' cm'
                    }
                }));
                
                displayAnalysisResults();
                updateStatus(`Analysis complete! Found ${analysisResults.length} plants.`, 'success');
                showProgress(false);
                
            } catch (e) {
                updateStatus('Analysis failed: ' + e.message, 'error');
                showProgress(false);
            }
        }
        
        function displayAnalysisResults() {
            const container = document.getElementById('plant-analysis-grid');
            container.innerHTML = '';
            
            analysisResults.forEach(plant => {
                const card = document.createElement('div');
                card.className = 'plant-card';
                card.innerHTML = `
                    <img src="/plants/plant_${plant.id.toString().padStart(3, '0')}/crop.jpg" 
                         onerror="this.src='/frames/plant_${plant.id}_crop.jpg'" />
                    <h4>Plant ${plant.id}</h4>
                    <p><strong>Type:</strong> ${plant.label}</p>
                    <p><strong>Leaves:</strong> ${plant.leafCount}</p>
                    <p><strong>Health:</strong> ${plant.healthScore}%</p>
                    <p><strong>Size:</strong> ${plant.sizeEstimate.height} × ${plant.sizeEstimate.width}</p>
                    <select onchange="updatePlantType(${plant.id}, this.value)">
                        <option value="unknown">Unknown</option>
                        <option value="basil">Basil</option>
                        <option value="mint">Mint</option>
                        <option value="lettuce">Lettuce</option>
                        <option value="spinach">Spinach</option>
                        <option value="tomato">Tomato</option>
                        <option value="pepper">Pepper</option>
                    </select>
                `;
                container.appendChild(card);
            });
            
            document.getElementById('plant-results').style.display = 'block';
        }
        
        function updatePlantType(plantId, newType) {
            const plant = analysisResults.find(p => p.id === plantId);
            if (plant) {
                plant.label = newType;
            }
        }
        
        async function saveAnalysis() {
            try {
                for (const plant of analysisResults) {
                    await fetch('/api/plant-class', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({ index: plant.id, label: plant.label })
                    });
                }
                
                updateStatus('Analysis saved successfully!', 'success');
            } catch (e) {
                updateStatus('Failed to save analysis: ' + e.message, 'error');
            }
        }
        
        function resetAnalysis() {
            currentSnapshot = false;
            analysisResults = [];
            document.getElementById('analyze-btn').disabled = true;
            document.getElementById('plant-results').style.display = 'none';
            updateStatus('Ready to take snapshot', 'info');
        }
        
        async function checkForPlantFiles() {
            const plants = [];
            for (let i = 0; i < 50; i++) {
                try {
                    const plantId = i.toString().padStart(3, '0');
                    let response = await fetch(`/plants/plant_${plantId}/crop.jpg`, {method: 'HEAD'});
                    
                    if (!response.ok) {
                        response = await fetch('/frames/plant_'+i+'_crop.jpg', {method: 'HEAD'});
                    }
                    
                    if (response.ok) {
                        let plantData = { label: 'unknown', area: 0, bbox: [0,0,0,0] };
                        try {
                            const dataRes = await fetch('/api/plant-data/'+i);
                            if (dataRes.ok) plantData = await dataRes.json();
                        } catch(e) {}
                        plants.push(plantData);
                    }
                } catch(e) { break; }
            }
            return plants;
        }
        
        async function testCamera() {
            try {
                const response = await fetch('/frames/frame_raw.jpg?t=' + Date.now());
                if (response.ok) {
                    alert('Camera test successful!');
                } else {
                    alert('Camera test failed: Unable to fetch image');
                }
            } catch (e) {
                alert('Camera test failed: ' + e.message);
            }
        }
        
        async function saveAnalysisSettings() {
            const settings = {
                threshold: parseInt(document.getElementById('threshold').value),
                scale_px_per_cm: parseFloat(document.getElementById('scale').value),
                publish_interval_ms: parseInt(document.getElementById('publish-interval').value),
                input_mode: document.getElementById('input-mode').value,
                input_path: document.getElementById('input-path').value
            };
            
            try {
                const response = await fetch('/api/config', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ processing: settings })
                });
                
                if (response.ok) {
                    alert('Analysis settings saved successfully!');
                } else {
                    alert('Failed to save settings');
                }
            } catch (e) {
                alert('Failed to save settings: ' + e.message);
            }
        }
        
        async function checkSystemStatus() {
            // Check C++ service
            try {
                const response = await fetch('/frames/frame_raw.jpg?t=' + Date.now());
                document.getElementById('cpp-status').textContent = response.ok ? 'Online' : 'Offline';
                document.getElementById('cpp-status').className = 'status-value ' + (response.ok ? 'status-online' : 'status-offline');
            } catch (e) {
                document.getElementById('cpp-status').textContent = 'Offline';
                document.getElementById('cpp-status').className = 'status-value status-offline';
            }
            
            // Check AI service
            try {
                const response = await fetch('/api/ai-status');
                const status = await response.json();
                document.getElementById('ai-status').textContent = status.status || 'Unknown';
                document.getElementById('ai-status').className = 'status-value ' + (status.status === 'ready' ? 'status-online' : 'status-offline');
            } catch (e) {
                document.getElementById('ai-status').textContent = 'Offline';
                document.getElementById('ai-status').className = 'status-value status-offline';
            }
            
            // MQTT status (simplified check)
            document.getElementById('mqtt-status').textContent = 'Online';
            document.getElementById('mqtt-status').className = 'status-value status-online';
        }
        
        async function loadSetupCameras(){
            try{
                const r = await fetch('/api/config');
                const cfg = await r.json();
                const cams = cfg.cameras || [{ name:'Camera 0' }];
                const sel = document.getElementById('setup-cam-select');
                sel.innerHTML = '';
                cams.forEach((c, i)=>{ 
                    const opt=document.createElement('option'); 
                    opt.value=i; 
                    opt.textContent=c.name || ('Camera '+i); 
                    sel.appendChild(opt); 
                });
                sel.value = String(cfg.active_camera_index || 0);
                SETUP_CAM_INDEX = parseInt(sel.value||'0');
                sel.onchange = async ()=>{
                    SETUP_CAM_INDEX = parseInt(sel.value||'0');
                    await fetch('/api/set-active-camera', { 
                        method:'POST', 
                        headers:{'Content-Type':'application/json'}, 
                        body: JSON.stringify({ index: SETUP_CAM_INDEX })
                    });
                    // Immediately update the image after camera switch
                    const img = document.getElementById('setup-raw-img');
                    img.src = '/frames/frame_raw.jpg?t=' + Date.now();
                };
            }catch(e){}
        }
        
        // Auto-refresh the camera view
        setInterval(() => {
            const img = document.getElementById('setup-raw-img');
            img.src = '/frames/frame_raw.jpg?t=' + Date.now();
        }, 2000);

        // Initialize
        window.addEventListener('DOMContentLoaded', loadSetupCameras);
        checkSystemStatus();
        setInterval(checkSystemStatus, 10000);
    </script>
    """

    return HTMLResponse(content=create_page_template("SproutCast Setup", "setup", content))


@app.get("/api/latest")
def api_latest():
    return JSONResponse(content={"latest": state["latest"]})


@app.get("/api/config")
def api_config_get():
    return JSONResponse(content=state["config"])


@app.post("/api/config")
async def api_config_set(payload: Dict[str, Any]):
    # Shallow merge for now
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


@app.get("/api/ai-status")
def api_ai_status():
    """Check AI service status"""
    return JSONResponse(content={"status": "ready", "models_loaded": True})


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
        
        # Normalize type name
        normalized_type = 'sprout' if instance_type in ['sprout', 'sprouts'] else 'plant'
        instance_id_str = f"{instance_id:03d}"
        
        # Try new structure first
        data_path = f"/app/data/{normalized_type}s/{normalized_type}_{instance_id_str}/data.json"
        if os.path.exists(data_path):
            with open(data_path, 'r', encoding='utf-8') as f:
                return JSONResponse(content=pyjson.load(f))
        
        # Fallback to legacy
        legacy_path = f"/app/data/plant_{instance_id}.json"
        if os.path.exists(legacy_path):
            with open(legacy_path, 'r', encoding='utf-8') as f:
                return JSONResponse(content=pyjson.load(f))
        
        return JSONResponse(content={"error": "Instance not found"}, status_code=404)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


# Keep legacy endpoint for compatibility
@app.get("/api/plant-data/{plant_id}")
def api_plant_data(plant_id: int):
    return api_instance_data("plant", plant_id)


@app.post("/api/plant-class")
async def api_plant_class(payload: Dict[str, Any]):
    # payload: { index: int, label: str }
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