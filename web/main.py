from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import os
import threading
import time
import paho.mqtt.client as mqtt
from typing import Any, Dict

app = FastAPI(title="PlantVision Web UI")

app.mount("/static", StaticFiles(directory="static"), name="static")

state: Dict[str, Any] = {
    "latest": None,
    "config": {
        "camera_id": int(os.getenv("CAMERA_ID", "0")),
        "threshold": int(os.getenv("THRESHOLD", "100")),
        "publish_interval_ms": int(os.getenv("PUBLISH_INTERVAL_MS", "1000")),
        "scale_px_per_cm": float(os.getenv("SCALE_PX_PER_CM", "0")),
        "mqtt_topic": os.getenv("MQTT_TOPIC", "plant/area"),
    },
}


def mqtt_thread():
    host = os.getenv("MQTT_HOST", "localhost")
    port = int(os.getenv("MQTT_PORT", "1883"))
    topic = state["config"]["mqtt_topic"]

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
    latest = state["latest"] or "{}"
    html = f"""
    <html>
        <head>
            <title>PlantVision Dashboard</title>
            <meta http-equiv=\"refresh\" content=\"2\">
            <style>
                body {{ font-family: Arial, sans-serif; margin: 2rem; }}
                .card {{ border: 1px solid #eee; padding: 1rem; border-radius: 8px; max-width: 600px; }}
                pre {{ background: #f8f8f8; padding: 1rem; border-radius: 6px; }}
            </style>
        </head>
        <body>
            <h1>PlantVision</h1>
            <div class="card">
                <h2>Latest Measurement</h2>
                <pre>{latest}</pre>
            </div>
            <div class="card" style="margin-top:1rem;">
                <h2>Config</h2>
                <pre>{state["config"]}</pre>
            </div>
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
    state["config"].update(payload)
    return JSONResponse(content={"ok": True, "config": state["config"]})

