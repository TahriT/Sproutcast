import os
import time
import json
import orjson
import numpy as np
import paho.mqtt.client as mqtt
import cv2
import pathlib
try:
    import onnxruntime as ort
except Exception:
    ort = None
import requests

DATA_DIR = "/app/data"
RAW_PATH = os.path.join(DATA_DIR, "frame_raw.jpg")
METRICS_PATH = os.path.join(DATA_DIR, "ai_metrics.json")
OVERRIDE_PATH = os.path.join(DATA_DIR, "classes_overrides.json")
MODELS_DIR = "/app/models"
MIDAS_ONNX = os.path.join(MODELS_DIR, "midas_small.onnx")
MIDAS_URL = "https://github.com/isl-org/MiDaS/releases/download/v3_1_small/model-small.onnx"

def ensure_dir(p):
    try:
        os.makedirs(p, exist_ok=True)
    except Exception:
        pass

def download_file(url: str, dest: str):
    try:
        r = requests.get(url, timeout=60)
        r.raise_for_status()
        with open(dest, 'wb') as f:
            f.write(r.content)
        return True
    except Exception:
        return False

def load_overrides() -> dict:
    try:
        with open(OVERRIDE_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}

def load_midas():
    ensure_dir(MODELS_DIR)
    if ort and not os.path.exists(MIDAS_ONNX):
        download_file(MIDAS_URL, MIDAS_ONNX)
    if ort and os.path.exists(MIDAS_ONNX):
        try:
            sess = ort.InferenceSession(MIDAS_ONNX, providers=["CPUExecutionProvider"])
            return ("onnx", sess)
        except Exception:
            return (None, None)
    return (None, None)

def run_midas(model, img_bgr: np.ndarray) -> np.ndarray:
    kind, obj = model
    if kind == "onnx":
        # Simple letterbox to 256x256 for small models; adjust if needed
        h, w = img_bgr.shape[:2]
        inp = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        inp = cv2.resize(inp, (256, 256), interpolation=cv2.INTER_AREA)
        inp = inp.astype(np.float32) / 255.0
        inp = inp.transpose(2,0,1)[None, ...]
        out = obj.run(None, {obj.get_inputs()[0].name: inp})[0][0,0]
        out = cv2.resize(out, (w, h), interpolation=cv2.INTER_CUBIC)
        # Normalize to 0..1
        mn, mx = float(out.min()), float(out.max())
        if mx > mn:
            out = (out - mn) / (mx - mn)
        else:
            out = np.zeros_like(out, dtype=np.float32)
        return out.astype(np.float32)
    return None


def compute_metrics(img_bgr: np.ndarray, overrides: dict, depth_model=None) -> dict:
    if img_bgr is None or img_bgr.size == 0:
        return {}
    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2LAB)

    # Simple green mask similar to publisher
    mask = cv2.inRange(hsv, (25, 40, 40), (85, 255, 255))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3,3)))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5,5)))

    # Color stats inside mask
    m = mask > 0
    if np.count_nonzero(m) == 0:
        return {"note": "no mask"}

    mean_hsv = [float(np.mean(hsv[:,:,i][m])) for i in range(3)]
    mean_lab = [float(np.mean(lab[:,:,i][m])) for i in range(3)]
    green_ratio = float(np.count_nonzero(m) / (img_bgr.shape[0] * img_bgr.shape[1]))

    # Contours for shape metrics
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    per_plant = []
    idx = -1
    for c in contours:
        idx += 1
        area = float(cv2.contourArea(c))
        if area < 50:
            continue
        perim = float(cv2.arcLength(c, True))
        x,y,w,h = cv2.boundingRect(c)
        aspect = float(w) / float(h) if h > 0 else 0.0
        roundness = float(4.0 * np.pi * area / (perim * perim)) if perim > 0 else 0.0
        hu = cv2.HuMoments(cv2.moments(c)).flatten().tolist()
        label = overrides.get(str(idx), {}).get("label", "unknown")
        entry = {
            "area_px": area,
            "perimeter_px": perim,
            "aspect": aspect,
            "roundness": roundness,
            "bbox": [int(x), int(y), int(w), int(h)],
            "hu": [float(v) for v in hu],
            "label": label,
            "confidence": 0.0
        }
        per_plant.append(entry)

    out = {
        "mean_hsv": mean_hsv,
        "mean_lab": mean_lab,
        "green_ratio": green_ratio,
        "plants": per_plant,
        "timestamp": int(time.time() * 1000)
    }
    # Optional depth estimation
    if depth_model is not None:
        try:
            depth = run_midas(depth_model, img_bgr)
            if depth is not None:
                out["depth_summary"] = {"min": float(depth.min()), "max": float(depth.max()), "mean": float(depth.mean())}
                for p in out["plants"]:
                    x,y,w,h = p["bbox"]
                    roi = depth[max(y,0):y+h, max(x,0):x+w]
                    if roi.size > 0:
                        p["median_depth"] = float(np.median(roi))
                        p["height_norm"] = float(h / max(img_bgr.shape[0],1))
        except Exception:
            pass
    return out


def main():
    host = os.getenv("MQTT_HOST", "localhost")
    port = int(os.getenv("MQTT_PORT", "1883"))
    room = os.getenv("UNS_ROOM", "room-1")
    area = os.getenv("UNS_AREA", "area-1")
    camera_id = os.getenv("CAMERA_ID", "0")
    plant_id = os.getenv("PLANT_ID", "plant-1")
    topic = f"plantvision/{room}/{area}/{camera_id}/{plant_id}/ai"

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.connect(host, port, 60)

    baseline = None
    last_mtime = 0
    depth_model = load_midas()

    while True:
        try:
            if not os.path.exists(RAW_PATH):
                time.sleep(1)
                continue
            mtime = os.path.getmtime(RAW_PATH)
            if mtime == last_mtime:
                time.sleep(0.5)
                continue
            last_mtime = mtime

            img = cv2.imread(RAW_PATH)
            overrides = load_overrides()
            metrics = compute_metrics(img, overrides, depth_model)
            if not metrics:
                time.sleep(0.5)
                continue

            # Establish baseline once
            if baseline is None:
                baseline = metrics

            # Deviation check (simple thresholds; tune later)
            dev = False
            if baseline and metrics:
                try:
                    dh = abs(metrics["mean_hsv"][0] - baseline["mean_hsv"][0])
                    ds = abs(metrics["mean_hsv"][1] - baseline["mean_hsv"][1])
                    green_diff = abs(metrics["green_ratio"] - baseline.get("green_ratio", 0.0))
                    if dh > 8 or ds > 12 or green_diff > 0.05:
                        dev = True
                except Exception:
                    pass

            payload = {
                "baseline": baseline,
                "metrics": metrics,
                "deviation": dev,
            }
            with open(METRICS_PATH, "wb") as f:
                f.write(orjson.dumps(payload))
            client.publish(topic, orjson.dumps(payload).decode())
        except Exception:
            time.sleep(0.5)
        time.sleep(0.5)


if __name__ == "__main__":
    main()

