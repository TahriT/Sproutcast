import os
import time
import json
import orjson
import numpy as np
import paho.mqtt.client as mqtt
import cv2

DATA_DIR = "/app/data"
RAW_PATH = os.path.join(DATA_DIR, "frame_raw.jpg")
METRICS_PATH = os.path.join(DATA_DIR, "ai_metrics.json")

def compute_metrics(img_bgr: np.ndarray) -> dict:
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
    for c in contours:
        area = float(cv2.contourArea(c))
        if area < 50:
            continue
        perim = float(cv2.arcLength(c, True))
        x,y,w,h = cv2.boundingRect(c)
        aspect = float(w) / float(h) if h > 0 else 0.0
        roundness = float(4.0 * np.pi * area / (perim * perim)) if perim > 0 else 0.0
        hu = cv2.HuMoments(cv2.moments(c)).flatten().tolist()
        per_plant.append({
            "area_px": area,
            "perimeter_px": perim,
            "aspect": aspect,
            "roundness": roundness,
            "bbox": [int(x), int(y), int(w), int(h)],
            "hu": [float(v) for v in hu]
        })

    return {
        "mean_hsv": mean_hsv,
        "mean_lab": mean_lab,
        "green_ratio": green_ratio,
        "plants": per_plant,
        "timestamp": int(time.time() * 1000)
    }


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
            metrics = compute_metrics(img)
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

