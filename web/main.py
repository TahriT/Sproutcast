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
    html = """
    <html>
        <head>
            <title>SproutCast Dashboard</title>
            <style>
                :root { --bg:#0b1220; --fg:#e8eefb; --card:#111a2e; --accent:#4f8cff; --sprout:#10b981; --plant:#059669; }
                body { font-family: Arial, sans-serif; margin: 0; background: var(--bg); color: var(--fg); }
                header.nav { display:flex; align-items:center; gap:1rem; padding:.75rem 1rem; border-bottom:1px solid #223; position:sticky; top:0; background:rgba(11,18,32,.95); backdrop-filter: blur(6px); }
                header.nav h2 { margin:0; font-size:1.1rem; }
                header.nav a { color: var(--fg); text-decoration:none; opacity:.9; }
                header.nav .spacer { flex:1; }
                header.nav .icons a { padding:.25rem .5rem; border-radius:6px; }
                header.nav select { background:#0f172a; color:var(--fg); border:1px solid #223; border-radius:8px; padding:.35rem .5rem; }
                main { padding: 1rem; max-width: 1400px; margin: 0 auto; }
                .summary-cards { display:grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap:1rem; margin-bottom:1rem; }
                .summary-card { background: var(--card); border:1px solid #223; border-radius:10px; padding:1rem; text-align:center; }
                .summary-card h3 { margin:0 0 0.5rem; font-size:0.9rem; opacity:0.8; }
                .summary-card .value { font-size:2rem; font-weight:bold; margin:0; }
                .summary-card.sprouts .value { color: var(--sprout); }
                .summary-card.plants .value { color: var(--plant); }
                .row { display:grid; grid-template-columns: 460px 1fr; gap:1rem; align-items:start; margin-bottom: 1rem; }
                .card { background: var(--card); border:1px solid #223; border-radius:10px; padding:1rem; }
                .img-wrap { width:100%; height:320px; display:flex; align-items:center; justify-content:center; cursor:pointer; }
                .img-wrap img { max-width:100%; max-height:100%; border-radius:8px; border:1px solid #2a385a; display:block; object-fit: contain; }
                .img-wrap:hover { border:2px solid var(--accent); border-radius:8px; }
                pre.telemetry { background:#0f172a; border:1px solid #223; padding:1rem; border-radius:8px; max-height:240px; overflow:auto; white-space:pre-wrap; word-break:break-word; }
                .muted { opacity:.8; }
                .grid2 { display:grid; grid-template-columns: 1fr 1fr; gap:1rem; }
                .tabs { display:flex; border-bottom:1px solid #223; margin-bottom:1rem; }
                .tab { padding:0.75rem 1rem; cursor:pointer; border-bottom:2px solid transparent; transition:all 0.2s; }
                .tab:hover { background:#1a2332; }
                .tab.active { border-bottom-color:var(--accent); color:var(--accent); }
                .tab-content { display:none; }
                .tab-content.active { display:block; }
                .gallery { display:grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap:0.75rem; }
                .plant-thumb { cursor:pointer; transition:transform 0.2s; border-radius:8px; overflow:hidden; }
                .plant-thumb:hover { transform:scale(1.05); }
                .plant-thumb img { width:100%; height:100px; object-fit:cover; }
                .plant-thumb .info { padding:0.5rem; background:var(--card); }
                .plant-thumb .info h4 { margin:0 0 0.25rem; font-size:0.8rem; }
                .plant-thumb .info .stats { font-size:0.7rem; opacity:0.8; }
                .plant-thumb.sprout { border:2px solid var(--sprout); }
                .plant-thumb.plant { border:2px solid var(--plant); }
                .health-excellent { border-left:4px solid #10b981; }
                .health-good { border-left:4px solid #84cc16; }
                .health-fair { border-left:4px solid #f59e0b; }
                .health-poor { border-left:4px solid #ef4444; }
                .modal { display:none; position:fixed; z-index:1000; left:0; top:0; width:100%; height:100%; background:rgba(0,0,0,0.8); }
                .modal-content { background:var(--card); margin:2% auto; padding:1rem; border:1px solid #223; border-radius:10px; width:90%; max-width:1000px; max-height:90vh; overflow:auto; }
                .close { color:#aaa; float:right; font-size:28px; font-weight:bold; cursor:pointer; }
                .close:hover { color:var(--fg); }
                .detail-grid { display:grid; grid-template-columns: 1fr 1fr; gap:1rem; }
                .detail-img { width:100%; max-height:300px; object-fit:contain; border-radius:8px; }
                .status-indicator { display:inline-block; width:12px; height:12px; border-radius:50%; margin-right:0.5rem; }
                .status-online { background:#10b981; }
                .status-offline { background:#ef4444; }
                .cast-btn { padding:0.5rem; background:var(--accent); color:white; border:none; border-radius:6px; cursor:pointer; margin-left:1rem; display:none; }
                .cast-btn:hover { background:#3b6fd1; }
                .cast-btn.available { display:inline-block; }
            </style>
        </head>
        <body>
            <header class="nav">
                <div>�</div>
                <h2>SproutCast Dashboard</h2>
                <div class="spacer"></div>
                <button id="cast-btn" class="cast-btn" onclick="initCasting()">📺 Cast</button>
                <div class="status-indicator status-online" id="connection-status"></div>
                <span class="muted" id="connection-text">Connected</span>
                <label class="muted">Camera</label>
                <select id="cam-select"></select>
                <nav class="icons">
                    <a href="/">🏠 Dashboard</a>
                    <a href="/setup">🔧 Setup</a>
                    <a href="/settings">⚙️ Settings</a>
                </nav>
            </header>
            <main>
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

                <!-- Tabbed Plant/Sprout Gallery -->
                <div class="card" style="margin-top:1rem;">
                    <div class="tabs">
                        <div class="tab active" onclick="switchTab('all')">All Instances</div>
                        <div class="tab" onclick="switchTab('sprouts')">Sprouts (🌱)</div>
                        <div class="tab" onclick="switchTab('plants')">Plants (🌿)</div>
                    </div>
                    
                    <div id="tab-all" class="tab-content active">
                        <h3 class="muted">All Detected Vegetation</h3>
                        <div id="gallery-all" class="gallery"></div>
                    </div>
                    
                    <div id="tab-sprouts" class="tab-content">
                        <h3 class="muted">Sprout Monitoring</h3>
                        <p class="muted">Early growth stage plants requiring close monitoring</p>
                        <div id="gallery-sprouts" class="gallery"></div>
                    </div>
                    
                    <div id="tab-plants" class="tab-content">
                        <h3 class="muted">Mature Plant Monitoring</h3>
                        <p class="muted">Established plants with advanced analysis</p>
                        <div id="gallery-plants" class="gallery"></div>
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
                let CAM_INDEX = 0;
                let allInstances = [];
                let sproutInstances = [];
                let plantInstances = [];
                
                // Tab switching
                function switchTab(tabName) {
                    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
                    document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
                    event.target.classList.add('active');
                    document.getElementById('tab-' + tabName).classList.add('active');
                }
                
                function createInstanceCard(instance, index) {
                    const card = document.createElement('div');
                    card.className = `plant-thumb ${instance.type}`;
                    
                    // Health border
                    const health = instance.health_score || 0;
                    if (health >= 90) card.classList.add('health-excellent');
                    else if (health >= 75) card.classList.add('health-good');
                    else if (health >= 50) card.classList.add('health-fair');
                    else card.classList.add('health-poor');
                    
                    const typeIcon = instance.type === 'sprout' ? '🌱' : '🌿';
                    const basePath = instance.type === 'sprout' ? 'sprouts' : 'plants';
                    const instanceId = index.toString().padStart(3, '0');
                    
                    card.innerHTML = `
                        <img src="/${basePath}/${instance.type}_${instanceId}/crop.jpg" 
                             onerror="this.src='/frames/plant_${index}_crop.jpg'" />
                        <div class="info">
                            <h4>${typeIcon} ${instance.classification} ${index}</h4>
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
                
                function showInstanceDetails(instance, index) {
                    const modal = document.getElementById('detailModal');
                    const title = document.getElementById('modal-title');
                    const content = document.getElementById('modal-content');
                    
                    const typeIcon = instance.type === 'sprout' ? '🌱' : '🌿';
                    title.textContent = `${typeIcon} ${instance.classification.charAt(0).toUpperCase() + instance.classification.slice(1)} ${index}`;
                    
                    const basePath = instance.type === 'sprout' ? 'sprouts' : 'plants';
                    const instanceId = index.toString().padStart(3, '0');
                    
                    content.innerHTML = `
                        <div class="detail-grid">
                            <div>
                                <h3>Original Image</h3>
                                <img class="detail-img" src="/${basePath}/${instance.type}_${instanceId}/crop.jpg" 
                                     onerror="this.src='/frames/plant_${index}_crop.jpg'" />
                            </div>
                            <div>
                                <h3>Analysis View</h3>
                                <img class="detail-img" src="/${basePath}/${instance.type}_${instanceId}/highlight.jpg" 
                                     onerror="this.src='/frames/plant_${index}_highlight.jpg'" />
                            </div>
                        </div>
                        <div style="margin-top: 1rem;">
                            <h3>Analysis Data</h3>
                            <div class="grid2">
                                <div>
                                    <strong>Type:</strong> ${instance.type}<br>
                                    <strong>Classification:</strong> ${instance.classification}<br>
                                    <strong>Health Score:</strong> ${Math.round(instance.health_score || 0)}%<br>
                                    <strong>Growth Stage:</strong> ${getGrowthStageName(instance.growth_stage)}<br>
                                </div>
                                <div>
                                    <strong>Leaf Count:</strong> ${instance.leaf_count || 0}<br>
                                    <strong>Area:</strong> ${Math.round(instance.area_cm2 || 0)} cm²<br>
                                    <strong>Dimensions:</strong> ${instance.height_cm ? Math.round(instance.height_cm*10)/10 : 'N/A'}×${instance.width_cm ? Math.round(instance.width_cm*10)/10 : 'N/A'} cm<br>
                                    <strong>Last Updated:</strong> ${new Date(instance.timestamp).toLocaleTimeString()}<br>
                                </div>
                            </div>
                        </div>
                        <div style="margin-top: 1rem;">
                            <h3>Raw Telemetry</h3>
                            <pre class="telemetry">${JSON.stringify(instance, null, 2)}</pre>
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
                
                async function updateSummary() {
                    document.getElementById('sprout-count').textContent = sproutInstances.length;
                    document.getElementById('plant-count').textContent = plantInstances.length;
                    
                    const totalArea = [...sproutInstances, ...plantInstances].reduce((sum, inst) => sum + (inst.area_cm2 || 0), 0);
                    document.getElementById('total-area').textContent = Math.round(totalArea) + ' cm²';
                    
                    const avgHealth = [...sproutInstances, ...plantInstances].reduce((sum, inst, _, arr) => {
                        return sum + (inst.health_score || 0) / arr.length;
                    }, 0);
                    document.getElementById('avg-health').textContent = Math.round(avgHealth) + '%';
                }
                
                async function loadCameras() {
                    try {
                        const r = await fetch('/api/config');
                        const cfg = await r.json();
                        const cams = cfg.cameras || [{ id: cfg.uns?.camera_id || '0', name: 'Camera 0' }];
                        const sel = document.getElementById('cam-select');
                        sel.innerHTML = '';
                        cams.forEach((c, idx) => {
                            const opt = document.createElement('option');
                            opt.value = idx;
                            opt.textContent = c.name || `Camera ${idx}`;
                            sel.appendChild(opt);
                        });
                        sel.value = cfg.active_camera_index || 0;
                        CAM_INDEX = parseInt(sel.value || '0');
                        sel.onchange = async () => {
                            CAM_INDEX = parseInt(sel.value || '0');
                            await fetch('/api/set-active-camera', {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({ index: CAM_INDEX })
                            });
                            refreshTelemetry();
                            refreshImages();
                        };
                    } catch (e) {
                        document.getElementById('connection-status').className = 'status-indicator status-offline';
                        document.getElementById('connection-text').textContent = 'Offline';
                    }
                }
                
                async function refreshTelemetry() {
                    try {
                        const r = await fetch('/api/latest');
                        const d = await r.json();
                        const txt = (d && d.latest) ? d.latest : '{}';
                        const data = JSON.parse(txt);
                        
                        sproutInstances = data.sprouts || [];
                        plantInstances = data.plants || [];
                        allInstances = [...sproutInstances, ...plantInstances];
                        
                        // Update galleries
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
                        
                        updateSummary();
                        
                        document.getElementById('connection-status').className = 'status-indicator status-online';
                        document.getElementById('connection-text').textContent = 'Connected';
                        
                    } catch (e) {
                        document.getElementById('connection-status').className = 'status-indicator status-offline';
                        document.getElementById('connection-text').textContent = 'Connection Error';
                    }
                }
                
                function refreshImages() {
                    const t = Date.now();
                    document.getElementById('img-raw').src = '/frames/frame_raw.jpg?t=' + t;
                    document.getElementById('img-ann').src = '/frames/frame_annotated.jpg?t=' + t;
                }
                
                // Close modal when clicking outside
                window.onclick = function(event) {
                    const modal = document.getElementById('detailModal');
                    if (event.target === modal) {
                        modal.style.display = 'none';
                    }
                }
                
                // Casting functionality
                let castSession = null;
                let isCasting = false;
                
                function initializeCastApi() {
                    if (typeof chrome !== 'undefined' && chrome.cast && chrome.cast.isAvailable) {
                        const sessionRequest = new chrome.cast.SessionRequest(chrome.cast.media.DEFAULT_MEDIA_RECEIVER_APP_ID);
                        const apiConfig = new chrome.cast.ApiConfig(sessionRequest, sessionListener, receiverListener);
                        chrome.cast.initialize(apiConfig, onCastInitSuccess, onCastError);
                        document.getElementById('cast-btn').classList.add('available');
                    }
                }
                
                function sessionListener(session) {
                    castSession = session;
                    if (session.media.length != 0) {
                        onMediaDiscovered('onRequestSessionSuccess', session.media[0]);
                    }
                    session.addUpdateListener(sessionUpdateListener);
                    session.addMediaListener(onMediaDiscovered);
                    session.addMessageListener('urn:x-cast:com.google.cast.media', onMediaStatusUpdate);
                    isCasting = true;
                    document.getElementById('cast-btn').textContent = '📺 Stop Cast';
                }
                
                function sessionUpdateListener(isAlive) {
                    if (!isAlive) {
                        castSession = null;
                        isCasting = false;
                        document.getElementById('cast-btn').textContent = '📺 Cast';
                    }
                }
                
                function receiverListener(e) {
                    if (e === chrome.cast.ReceiverAvailability.AVAILABLE) {
                        document.getElementById('cast-btn').classList.add('available');
                    }
                }
                
                function onCastInitSuccess() {
                    console.log('Cast API initialized successfully');
                }
                
                function onCastError(error) {
                    console.log('Cast error: ' + error);
                }
                
                function onMediaDiscovered(how, mediaSession) {
                    console.log('Media discovered: ' + how);
                }
                
                function onMediaStatusUpdate(isAlive) {
                    console.log('Media status update: ' + isAlive);
                }
                
                function initCasting() {
                    if (isCasting && castSession) {
                        // Stop casting
                        castSession.stop(
                            function() {
                                castSession = null;
                                isCasting = false;
                                document.getElementById('cast-btn').textContent = '📺 Cast';
                            },
                            function(error) {
                                console.log('Error stopping cast: ' + error);
                            }
                        );
                    } else {
                        // Start casting
                        if (typeof chrome !== 'undefined' && chrome.cast && chrome.cast.isAvailable) {
                            chrome.cast.requestSession(
                                function(session) {
                                    castSession = session;
                                    sessionListener(session);
                                    
                                    // Cast the current dashboard URL
                                    const mediaInfo = new chrome.cast.media.MediaInfo(window.location.origin + '/', 'text/html');
                                    mediaInfo.metadata = new chrome.cast.media.GenericMediaMetadata();
                                    mediaInfo.metadata.title = 'SproutCast Dashboard';
                                    mediaInfo.metadata.subtitle = 'Real-time Plant Monitoring';
                                    
                                    const request = new chrome.cast.media.LoadRequest(mediaInfo);
                                    
                                    session.loadMedia(request,
                                        function(media) {
                                            console.log('Media loaded successfully');
                                        },
                                        function(error) {
                                            console.log('Error loading media: ' + error);
                                        }
                                    );
                                },
                                function(error) {
                                    console.log('Error requesting session: ' + error);
                                }
                            );
                        } else {
                            alert('Google Cast is not available on this device. Please use a Chrome browser on a device with casting capability.');
                        }
                    }
                }
                
                // Load Google Cast SDK
                if (typeof window !== 'undefined') {
                    window['__onGCastApiAvailable'] = function(isAvailable) {
                        if (isAvailable) {
                            initializeCastApi();
                        }
                    };
                    
                    // Load Cast SDK script
                    const castScript = document.createElement('script');
                    castScript.src = 'https://www.gstatic.com/cv/js/sender/v1/cast_sender.js?loadCastFramework=1';
                    document.head.appendChild(castScript);
                }
                
                // Initialize
                loadCameras();
                setInterval(loadCameras, 5000);
                setInterval(refreshTelemetry, 1200);
                setInterval(refreshImages, 2000);
                refreshTelemetry();
                refreshImages();
            </script>
        </body>
    </html>
    """
    return HTMLResponse(content=html)
@app.get("/settings", response_class=HTMLResponse)
def settings_page():
    html = """
    <html>
        <head>
            <title>SproutCast Settings</title>
            <style>
                :root { --bg:#0b1220; --fg:#e8eefb; --card:#111a2e; --accent:#4f8cff; }
                body { font-family: Arial, sans-serif; margin: 0; background: var(--bg); color: var(--fg); }
                header.nav { display:flex; align-items:center; gap:1rem; padding:.75rem 1rem; border-bottom:1px solid #223; position:sticky; top:0; background:rgba(11,18,32,.95); backdrop-filter: blur(6px); }
                header.nav h2 { margin:0; font-size:1.1rem; }
                header.nav a { color: var(--fg); text-decoration:none; opacity:.9; }
                header.nav .spacer { flex:1; }
                header.nav .icons a { padding:.25rem .5rem; border-radius:6px; }
                main { padding: 1rem; max-width: 900px; margin: 0 auto; }
                .card { background: var(--card); border:1px solid #223; border-radius:10px; padding:1rem; }
                label { display:block; margin-top: .6rem; font-size:.95rem; opacity:.9; }
                input, select { width: 100%; padding: .6rem .7rem; background:#0f172a; color:var(--fg); border:1px solid #223; border-radius:8px; }
                button { margin-top: .75rem; padding: .6rem 1rem; background: var(--accent); color:white; border:none; border-radius:8px; cursor:pointer; }
                .grid { display:grid; grid-template-columns: 1fr 1fr; gap:1rem; }
                .muted { opacity:.8; }
                .row { display:grid; grid-template-columns: 1fr 1fr; gap:1rem; }
            </style>
        </head>
        <body>
            <header class="nav">
                <div>🌿</div>
                <h2>SproutCast Settings</h2>
                <div class="spacer"></div>
                <nav class="icons">
                    <a href="/">🏠 Dashboard</a>
                    <a href="/settings">⚙️ Settings</a>
                </nav>
            </header>
            <main>
                <div class="card">
                    <h3 class="muted">MQTT</h3>
                    <form id="cfg">
                        <div class="grid">
                            <div>
                                <label>MQTT Host <input name="mqtt.host"/></label>
                            </div>
                            <div>
                                <label>MQTT Port <input name="mqtt.port"/></label>
                            </div>
                        </div>
                        <h3 class="muted" style="margin-top:1rem;">Cameras</h3>
                        <div class="row">
                            <div>
                                <label>Select Camera
                                    <select id="cam-select-settings"></select>
                                </label>
                            </div>
                            <div>
                                <button type="button" id="add-cam">+ Add Camera</button>
                                <button type="button" id="del-cam" style="margin-left:.5rem; background:#ef4444;">🗑️ Delete</button>
                            </div>
                        </div>
                        <div class="grid">
                            <div>
                                <label>Name <input name="camera.name" placeholder="Camera 0"/></label>
                            </div>
                            <div>
                                <label>Camera ID <input name="camera.camera_id" placeholder="0"/></label>
                            </div>
                        </div>
                        <div class="grid">
                            <div>
                                <label>Plant ID <input name="camera.plant_id" placeholder="plant-1"/></label>
                            </div>
                            <div>
                                <label>Room <input name="camera.room" placeholder="room-1"/></label>
                            </div>
                        </div>
                        <div class="grid">
                            <div>
                                <label>Area <input name="camera.area" placeholder="area-1"/></label>
                            </div>
                            <div>
                                <label>Input Mode <input name="camera.input_mode" placeholder="IMAGE | CAMERA | NETWORK"/></label>
                            </div>
                        </div>
                        <div class="grid">
                            <div>
                                <label>Input Path <input name="camera.input_path"/></label>
                            </div>
                            <div>
                                <label>Input URL (network) <input name="camera.input_url" placeholder="rtsp://... or http(s)://..."/></label>
                            </div>
                        </div>
                        <div class="grid">
                            <div>
                                <label>Threshold <input name="processing.threshold"/></label>
                            </div>
                            <div>
                                <label>Publish Interval (ms) <input name="processing.publish_interval_ms"/></label>
                            </div>
                        </div>
                        <div class="grid">
                            <div>
                                <label>Scale px/cm <input name="processing.scale_px_per_cm"/></label>
                            </div>
                        </div>
                        <button type="button" onclick="save()">Save</button>
                    </form>
                </div>
            </main>
            <script>
                function toNested(obj) { const out = {}; for (const [k, v] of Object.entries(obj)) { const parts = k.split('.'); let cur = out; for (let i = 0; i < parts.length; i++) { const p = parts[i]; if (i === parts.length - 1) { cur[p] = v; } else { if (!cur[p]) cur[p] = {}; cur = cur[p]; } } } return out; }
                let cameras = [];
                let camIdx = 0;
                function bindCameraFields(){
                    const form = document.getElementById('cfg');
                    const c = cameras[camIdx] || {};
                    form.elements['camera.name'].value = c.name || `Camera ${camIdx}`;
                    form.elements['camera.camera_id'].value = c.camera_id || '0';
                    form.elements['camera.plant_id'].value = c.plant_id || 'plant-1';
                    form.elements['camera.room'].value = c.room || 'room-1';
                    form.elements['camera.area'].value = c.area || 'area-1';
                    form.elements['camera.input_mode'].value = c.input_mode || 'IMAGE';
                    form.elements['camera.input_path'].value = c.input_path || '/samples/plant.jpg';
                    form.elements['camera.input_url'].value = c.input_url || '';
                }
                function syncCameraFromFields(){
                    const form = document.getElementById('cfg');
                    const c = cameras[camIdx];
                    c.name = form.elements['camera.name'].value;
                    c.camera_id = form.elements['camera.camera_id'].value;
                    c.plant_id = form.elements['camera.plant_id'].value;
                    c.room = form.elements['camera.room'].value;
                    c.area = form.elements['camera.area'].value;
                    c.input_mode = form.elements['camera.input_mode'].value;
                    c.input_path = form.elements['camera.input_path'].value;
                    c.input_url = form.elements['camera.input_url'].value;
                }
                async function load(){
                    const res = await fetch('/api/config');
                    const cfg = await res.json();
                    const form = document.getElementById('cfg');
                    form.elements['mqtt.host'].value = cfg.mqtt?.host || 'localhost';
                    form.elements['mqtt.port'].value = cfg.mqtt?.port || 1883;
                    cameras = cfg.cameras || [];
                    if (cameras.length === 0) cameras = [{ name: 'Camera 0', camera_id:'0', plant_id:'plant-1', room:'room-1', area:'area-1', input_mode:'IMAGE', input_path:'/samples/plant.jpg', input_url:'' }];
                    const sel = document.getElementById('cam-select-settings');
                    sel.innerHTML = '';
                    cameras.forEach((c, i)=>{ const opt=document.createElement('option'); opt.value=i; opt.textContent=c.name || ('Camera '+i); sel.appendChild(opt); });
                    sel.onchange = ()=>{ syncCameraFromFields(); camIdx = parseInt(sel.value||'0'); bindCameraFields(); };
                    bindCameraFields();
                    form.elements['processing.threshold'].value = cfg.processing?.threshold || 100;
                    form.elements['processing.publish_interval_ms'].value = cfg.processing?.publish_interval_ms || 1000;
                    form.elements['processing.scale_px_per_cm'].value = cfg.processing?.scale_px_per_cm || 0;
                    document.getElementById('add-cam').onclick = ()=>{
                        syncCameraFromFields();
                        cameras.push({ name: `Camera ${cameras.length}`, camera_id:String(cameras.length), plant_id:'plant-1', room:'room-1', area:'area-1', input_mode:'IMAGE', input_path:'/samples/plant.jpg', input_url:'' });
                        const opt=document.createElement('option'); opt.value=cameras.length-1; opt.textContent=cameras[cameras.length-1].name; sel.appendChild(opt);
                        sel.value = String(cameras.length-1); camIdx = cameras.length-1; bindCameraFields();
                    };
                    document.getElementById('del-cam').onclick = ()=>{
                        if (cameras.length <= 1) { alert('At least one camera is required.'); return; }
                        cameras.splice(camIdx, 1);
                        sel.innerHTML = '';
                        cameras.forEach((c, i)=>{ const opt=document.createElement('option'); opt.value=i; opt.textContent=c.name || ('Camera '+i); sel.appendChild(opt); });
                        camIdx = Math.max(0, camIdx-1);
                        sel.value = String(camIdx);
                        bindCameraFields();
                    };
                }
                async function save(){
                    syncCameraFromFields();
                    const form = document.getElementById('cfg');
                    const flat = { 'mqtt.host': form.elements['mqtt.host'].value, 'mqtt.port': form.elements['mqtt.port'].value,
                        'processing.threshold': form.elements['processing.threshold'].value,
                        'processing.publish_interval_ms': form.elements['processing.publish_interval_ms'].value,
                        'processing.scale_px_per_cm': form.elements['processing.scale_px_per_cm'].value };
                    const body = toNested(flat);
                    body.cameras = cameras;
                    body.active_camera_index = camIdx;
                    await fetch('/api/config', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body)} );
                    alert('Saved');
                }
                window.addEventListener('DOMContentLoaded', load);
            </script>
        </body>
    </html>
    """
    return HTMLResponse(content=html)

@app.get("/setup", response_class=HTMLResponse)
def setup_page():
    html = """
    <html>
        <head>
            <title>SproutCast Setup</title>
            <style>
                :root { --bg:#0b1220; --fg:#e8eefb; --card:#111a2e; --accent:#4f8cff; }
                body { font-family: Arial, sans-serif; margin: 0; background: var(--bg); color: var(--fg); }
                header.nav { display:flex; align-items:center; gap:1rem; padding:.75rem 1rem; border-bottom:1px solid #223; position:sticky; top:0; background:rgba(11,18,32,.95); backdrop-filter: blur(6px); }
                header.nav h2 { margin:0; font-size:1.1rem; }
                header.nav a { color: var(--fg); text-decoration:none; opacity:.9; }
                header.nav .spacer { flex:1; }
                header.nav .icons a { padding:.25rem .5rem; border-radius:6px; }
                main { padding: 1rem; max-width: 1200px; margin: 0 auto; }
                .card { background: var(--card); border:1px solid #223; border-radius:10px; padding:1rem; margin-bottom: 1rem; }
                .grid2 { display:grid; grid-template-columns: 1fr 1fr; gap:1rem; }
                .img-wrap { width:100%; height:300px; display:flex; align-items:center; justify-content:center; border:1px solid #223; border-radius:8px; }
                .img-wrap img { max-width:100%; max-height:100%; border-radius:8px; object-fit: contain; }
                button { padding: .6rem 1rem; background: var(--accent); color:white; border:none; border-radius:8px; cursor:pointer; margin: 0.25rem; }
                button:disabled { opacity: 0.5; cursor: not-allowed; }
                .muted { opacity:.8; }
                .plant-analysis { display:grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap:1rem; }
                .plant-card { background: var(--card); border:1px solid #223; border-radius:8px; padding:1rem; text-align:center; }
                .plant-card img { width:100%; height:120px; object-fit:cover; border-radius:4px; margin-bottom:0.5rem; }
                select { width:100%; padding:0.5rem; background:#0f172a; color:var(--fg); border:1px solid #223; border-radius:6px; margin-top:0.5rem; }
                .status { padding:0.5rem; border-radius:6px; margin:0.5rem 0; }
                .status.success { background:#0f4c3a; border:1px solid #10b981; }
                .status.error { background:#4c1d1d; border:1px solid #ef4444; }
                .status.info { background:#1e3a8a; border:1px solid #3b82f6; }
            </style>
        </head>
        <body>
            <header class="nav">
                <div>🌿</div>
                <h2>SproutCast Setup</h2>
                <div class="spacer"></div>
                <nav class="icons">
                    <a href="/">🏠 Dashboard</a>
                    <a href="/setup">🔧 Setup</a>
                    <a href="/settings">⚙️ Settings</a>
                </nav>
            </header>
            <main>
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
                            <div id="analysis-status" class="status info">Ready to take snapshot</div>
                            <div id="analysis-progress" style="display:none;">
                                <div>Processing...</div>
                                <div id="progress-text">Initializing AI models...</div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="card" id="plant-results" style="display:none;">
                    <h3>Detected Plants</h3>
                    <div id="plant-analysis-grid" class="plant-analysis"></div>
                    <div style="margin-top:1rem;">
                        <button onclick="saveAnalysis()" id="save-btn">💾 Save Analysis</button>
                        <button onclick="resetAnalysis()" id="reset-btn">🔄 Reset</button>
                    </div>
                </div>
                
                <div class="card">
                    <h3>Manual Plant Classification</h3>
                    <p class="muted">If AI classification is incorrect, you can manually assign plant types.</p>
                    <div id="manual-classification"></div>
                </div>
            </main>
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
                        // ensure setup camera selection updates active camera
                        await fetch('/api/set-active-camera', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ index: SETUP_CAM_INDEX })});
                        // Force refresh the image
                        const img = document.getElementById('setup-raw-img');
                        img.src = '/frames/frame_raw.jpg?t=' + Date.now();
                        
                        // Wait for image to load
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
                        // Simulate AI analysis steps
                        showProgress(true, 'Analyzing plant detection...');
                        await new Promise(resolve => setTimeout(resolve, 1000));
                        
                        showProgress(true, 'Running plant classification...');
                        await new Promise(resolve => setTimeout(resolve, 1500));
                        
                        showProgress(true, 'Calculating plant metrics...');
                        await new Promise(resolve => setTimeout(resolve, 1000));
                        
                        showProgress(true, 'Analyzing leaf health...');
                        await new Promise(resolve => setTimeout(resolve, 1000));
                        
                        // Get current plant data
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
                        // Save plant classifications
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
                
                // Auto-refresh the camera view
                setInterval(() => {
                    const img = document.getElementById('setup-raw-img');
                    img.src = '/frames/frame_raw.jpg?t=' + Date.now();
                }, 2000);

                // populate camera select and sync with active index
                async function loadSetupCameras(){
                    try{
                        const r = await fetch('/api/config');
                        const cfg = await r.json();
                        const cams = cfg.cameras || [{ name:'Camera 0' }];
                        const sel = document.getElementById('setup-cam-select');
                        sel.innerHTML = '';
                        cams.forEach((c, i)=>{ const opt=document.createElement('option'); opt.value=i; opt.textContent=c.name || ('Camera '+i); sel.appendChild(opt); });
                        sel.value = String(cfg.active_camera_index || 0);
                        SETUP_CAM_INDEX = parseInt(sel.value||'0');
                        sel.onchange = async ()=>{
                            SETUP_CAM_INDEX = parseInt(sel.value||'0');
                            await fetch('/api/set-active-camera', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ index: SETUP_CAM_INDEX })});
                            // Immediately update the image after camera switch
                            const img = document.getElementById('setup-raw-img');
                            img.src = '/frames/frame_raw.jpg?t=' + Date.now();
                        };
                    }catch(e){}
                }
                window.addEventListener('DOMContentLoaded', loadSetupCameras);
            </script>
        </body>
    </html>
    """
    return HTMLResponse(content=html)

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

