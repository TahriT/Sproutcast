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
                main { padding: 1rem; }
                .grid { display:grid; grid-template-columns: 1fr 1fr; gap:1rem; }
                .card { background: var(--card); border:1px solid #223; border-radius:10px; padding:1rem; }
                img { max-width: 100%; border-radius: 8px; border:1px solid #2a385a; display:block; }
                pre.telemetry { background:#0f172a; border:1px solid #223; padding:1rem; border-radius:8px; max-height:260px; overflow:auto; white-space:pre-wrap; word-break:break-word; }
                .muted { opacity:.8; }
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
                <div class="grid">
                    <div class="card">
                        <h3 class="muted">Raw Frame</h3>
                        <img id="img-raw" src="/frames/frame_raw.jpg" />
                    </div>
                    <div class="card">
                        <h3 class="muted">Annotated Frame</h3>
                        <img id="img-ann" src="/frames/frame_annotated.jpg" />
                    </div>
                </div>
                <div class="card" style="margin-top:1rem;">
                    <h3 class="muted">Latest Telemetry</h3>
                    <pre class="telemetry" id="telemetry">{}</pre>
                </div>
            </main>
            <script>
                async function refreshTelemetry() {
                    try {
                        const r = await fetch('/api/latest');
                        const d = await r.json();
                        document.getElementById('telemetry').textContent = d.latest || '{}';
                    } catch (e) { /* ignore */ }
                }
                function refreshImages() {
                    const t = Date.now();
                    const raw = document.getElementById('img-raw');
                    const ann = document.getElementById('img-ann');
                    raw.src = '/frames/frame_raw.jpg?t=' + t;
                    ann.src = '/frames/frame_annotated.jpg?t=' + t;
                }
                setInterval(refreshTelemetry, 1000);
                setInterval(refreshImages, 1500);
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
                body { font-family: Arial, sans-serif; margin: 1.5rem; }
                header { display: flex; gap: 1rem; margin-bottom: 1rem; align-items: center; }
                a { text-decoration: none; color: #0366d6; }
                .card { border: 1px solid #eee; padding: 1rem; border-radius: 8px; max-width: 700px; }
                label { display:block; margin-top: .5rem; }
                input { width: 100%; padding: .5rem; }
                button { margin-top: 1rem; padding: .5rem 1rem; }
            </style>
        </head>
        <body>
            <header>
                <h2 style="margin:0;">PlantVision</h2>
                <nav>
                    <a href="/">Dashboard</a> |
                    <a href="/settings">Settings</a>
                </nav>
            </header>
            <div class="card">
                <h3>Configuration</h3>
                <form id="cfg">
                    <label>MQTT Host <input name="mqtt.host"/></label>
                    <label>MQTT Port <input name="mqtt.port"/></label>
                    <label>Room <input name="uns.room"/></label>
                    <label>Area <input name="uns.area"/></label>
                    <label>Camera ID <input name="uns.camera_id"/></label>
                    <label>Plant ID <input name="uns.plant_id"/></label>
                    <label>Threshold <input name="processing.threshold"/></label>
                    <label>Publish Interval (ms) <input name="processing.publish_interval_ms"/></label>
                    <label>Scale px/cm <input name="processing.scale_px_per_cm"/></label>
                    <label>Input Mode <input name="processing.input_mode"/></label>
                    <label>Input Path <input name="processing.input_path"/></label>
                    <button type="button" onclick="save()">Save</button>
                </form>
            </div>
            <script>
                function toNested(obj) {
                    const out = {};
                    for (const [k, v] of Object.entries(obj)) {
                        const parts = k.split('.');
                        let cur = out;
                        for (let i = 0; i < parts.length; i++) {
                            const p = parts[i];
                            if (i === parts.length - 1) { cur[p] = v; }
                            else { if (!cur[p]) cur[p] = {}; cur = cur[p]; }
                        }
                    }
                    return out;
                }
                async function load() {
                    const res = await fetch('/api/config');
                    const cfg = await res.json();
                    const form = document.getElementById('cfg');
                    for (const el of form.elements) {
                        if (!el.name) continue;
                        const parts = el.name.split('.');
                        let cur = cfg;
                        for (let i = 0; i < parts.length; i++) {
                            const p = parts[i];
                            if (i === parts.length - 1) { if (cur && p in cur) el.value = cur[p]; }
                            else { if (cur && p in cur) cur = cur[p]; }
                        }
                    }
                }
                async function save() {
                    const fd = new FormData(document.getElementById('cfg'));
                    const flat = {};
                    for (const [k, v] of fd.entries()) flat[k] = v;
                    const nested = toNested(flat);
                    await fetch('/api/config', {
                        method: 'POST', headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(nested)
                    });
                    alert('Saved. The publisher will pick this up.');
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


@app.get("/api/ai")
def api_ai():
    try:
        with open(AI_METRICS_PATH, 'r', encoding='utf-8') as f:
            return JSONResponse(content=pyjson.load(f))
    except Exception:
        return JSONResponse(content={})

