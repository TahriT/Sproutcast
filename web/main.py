from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import os
import threading
import time
import json as pyjson
import paho.mqtt.client as mqtt
from typing import Any, Dict

app = FastAPI(title="PlantVision Web UI")

app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/frames", StaticFiles(directory="/app/data"), name="frames")

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
    topic = f"plantvision/{uns['room']}/{uns['area']}/{uns['camera_id']}/{uns['plant_id']}/telemetry"

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
            <title>PlantVision Dashboard</title>
            <style>
                :root { --bg:#0b1220; --fg:#e8eefb; --card:#111a2e; --accent:#4f8cff; }
                body { font-family: Arial, sans-serif; margin: 0; background: var(--bg); color: var(--fg); }
                header.nav { display:flex; align-items:center; gap:1rem; padding:.75rem 1rem; border-bottom:1px solid #223; position:sticky; top:0; background:rgba(11,18,32,.95); backdrop-filter: blur(6px); }
                header.nav h2 { margin:0; font-size:1.1rem; }
                header.nav a { color: var(--fg); text-decoration:none; opacity:.9; }
                header.nav .spacer { flex:1; }
                header.nav .icons a { padding:.25rem .5rem; border-radius:6px; }
                header.nav select { background:#0f172a; color:var(--fg); border:1px solid #223; border-radius:8px; padding:.35rem .5rem; }
                main { padding: 1rem; max-width: 1200px; margin: 0 auto; }
                .row { display:grid; grid-template-columns: 460px 1fr; gap:1rem; align-items:start; margin-bottom: 1rem; }
                .card { background: var(--card); border:1px solid #223; border-radius:10px; padding:1rem; }
                .img-wrap { width:100%; height:320px; display:flex; align-items:center; justify-content:center; }
                .img-wrap img { max-width:100%; max-height:100%; border-radius:8px; border:1px solid #2a385a; display:block; object-fit: contain; }
                pre.telemetry { background:#0f172a; border:1px solid #223; padding:1rem; border-radius:8px; max-height:240px; overflow:auto; white-space:pre-wrap; word-break:break-word; }
                .muted { opacity:.8; }
                .grid2 { display:grid; grid-template-columns: 1fr 1fr; gap:1rem; }
                .two { display:grid; grid-template-columns: 1fr 1fr; gap:1rem; }
                details { background:#0f172a; border:1px solid #223; border-radius:8px; padding:.5rem .75rem; }
            </style>
        </head>
        <body>
            <header class="nav">
                <div>🌿</div>
                <h2>PlantVision</h2>
                <div class="spacer"></div>
                <label class="muted">Camera</label>
                <select id="cam-select"></select>
                <nav class="icons">
                    <a href="/">🏠 Dashboard</a>
                    <a href="/settings">⚙️ Settings</a>
                </nav>
            </header>
            <main>
                <div class="grid2">
                    <div class="card">
                        <h3 class="muted">Raw Frame</h3>
                        <div class="img-wrap"><img id="img-raw" src="/frames/frame_raw.jpg" /></div>
                    </div>
                    <div class="card">
                        <h3 class="muted">Annotated Frame</h3>
                        <div class="img-wrap"><img id="img-ann" src="/frames/frame_annotated.jpg" /></div>
                    </div>
                </div>
                <div class="card" style="margin-top:1rem;">
                    <h3 class="muted">AI Metrics</h3>
                    <pre class="telemetry" id="ai-box">{}</pre>
                </div>
                <div id="plants"></div>
            </main>
            <script>
                let CAM_INDEX = 0;
                const plantRows = new Map();
                function el(tag, cls, txt){ const e=document.createElement(tag); if(cls) e.className=cls; if(txt) e.textContent=txt; return e; }
                function ensurePlantRow(i){
                    if(plantRows.has(i)) return plantRows.get(i);
                    const row = el('div','row');
                    const imgBox = el('div','card');
                    imgBox.appendChild(el('h3','muted','Plant '+i));
                    const wrap = el('div','img-wrap');
                    const img = new Image(); img.id = 'plant-img-'+i; img.src = '/frames/plant_'+i+'_highlight.jpg';
                    wrap.appendChild(img); imgBox.appendChild(wrap);
                    const dataBox = el('div','card');
                    dataBox.appendChild(el('h3','muted','Telemetry'));
                    const detailsEl = document.createElement('details');
                    const summary = document.createElement('summary'); summary.textContent = 'Topic & Data';
                    const topic = el('div','muted'); topic.id = 'topic-'+i;
                    const pre = el('pre','telemetry'); pre.id = 'plant-pre-'+i; pre.textContent = '{}';
                    detailsEl.appendChild(summary); detailsEl.appendChild(topic); detailsEl.appendChild(pre);
                    dataBox.appendChild(detailsEl);
                    row.appendChild(imgBox); row.appendChild(dataBox);
                    document.getElementById('plants').appendChild(row);
                    plantRows.set(i, {row, img, pre, topic});
                    return plantRows.get(i);
                }
                async function loadCameras(){
                    try{
                        const r = await fetch('/api/config');
                        const cfg = await r.json();
                        const cams = cfg.cameras || [{ id: cfg.uns?.camera_id || '0', plant_id: cfg.uns?.plant_id || 'plant-1', room: cfg.uns?.room || 'room-1', area: cfg.uns?.area || 'area-1' }];
                        const sel = document.getElementById('cam-select');
                        sel.innerHTML='';
                        cams.forEach((c,idx)=>{ const opt=document.createElement('option'); opt.value=idx; opt.textContent = c.name || (`Camera ${idx}`); sel.appendChild(opt); });
                        sel.onchange = async ()=>{ CAM_INDEX = parseInt(sel.value||'0'); await fetch('/api/set-active-camera', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ index: CAM_INDEX })}); };
                    }catch(e){}
                }
                async function refreshAI(){
                    try{ const r = await fetch('/api/ai'); const a = await r.json(); document.getElementById('ai-box').textContent = JSON.stringify(a, null, 2);}catch(e){}
                }
                async function refreshTelemetry(){
                    try{
                        const cfgRes = await fetch('/api/config'); const cfg = await cfgRes.json();
                        const cams = cfg.cameras || [{ room: cfg.uns?.room||'room-1', area: cfg.uns?.area||'area-1', camera_id: cfg.uns?.camera_id||'0', plant_id: cfg.uns?.plant_id||'plant-1' }];
                        const cam = cams[Math.min(CAM_INDEX, cams.length-1)];
                        const r = await fetch('/api/latest');
                        const d = await r.json();
                        const txt = (d && d.latest) ? d.latest : '{}';
                        let plants = [];
                        try{ const o = JSON.parse(txt); plants = o.plants || []; }catch(e){}
                        for(let i=0;i<plants.length;i++){
                            const pr = ensurePlantRow(i);
                            pr.pre.textContent = JSON.stringify(plants[i], null, 2);
                            pr.img.src = '/frames/plant_'+i+'_highlight.jpg?t=' + Date.now();
                            pr.topic.textContent = `plantvision/${cam.room}/${cam.area}/${cam.camera_id}/${cam.plant_id}/telemetry/plants/${i}/telemetry`;
                        }
                    }catch(e){}
                }
                function refreshImages(){
                    const t = Date.now();
                    document.getElementById('img-raw').src = '/frames/frame_raw.jpg?t='+t;
                    document.getElementById('img-ann').src = '/frames/frame_annotated.jpg?t='+t;
                }
                loadCameras();
                setInterval(loadCameras, 5000);
                setInterval(refreshAI, 3000);
                setInterval(refreshTelemetry, 1200);
                setInterval(refreshImages, 2000);
                refreshAI(); refreshTelemetry(); refreshImages();
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
            <title>Settings</title>
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
                <h2>PlantVision</h2>
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

