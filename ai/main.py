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
import json as pyjson_std
import torch
import torchvision.transforms as T

DATA_DIR = "/app/data"
RAW_PATH = os.path.join(DATA_DIR, "frame_raw.jpg")
METRICS_PATH = os.path.join(DATA_DIR, "ai_metrics.json")
OVERRIDE_PATH = os.path.join(DATA_DIR, "classes_overrides.json")
CHANGE_SIGNAL_PATH = os.path.join(DATA_DIR, "change_signal.json")
MODELS_DIR = "/app/models"
MIDAS_ONNX = os.path.join(MODELS_DIR, "midas_small.onnx")
MIDAS_URL = "https://github.com/isl-org/MiDaS/releases/download/v3_1_small/model-small.onnx"
MIDAS_TINY_PT = os.path.join(MODELS_DIR, "dpt_tiny_v3_1.pt")
GITHUB_API_MIDAS_V31 = "https://api.github.com/repos/isl-org/MiDaS/releases/tags/v3_1"

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

def load_change_signal() -> dict:
    """Load change detection signal from C++ component"""
    try:
        with open(CHANGE_SIGNAL_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}

def load_midas():
    ensure_dir(MODELS_DIR)
    # Prefer Tiny DPT (v3.1, torch)
    if not os.path.exists(MIDAS_TINY_PT):
        try:
            resp = requests.get(GITHUB_API_MIDAS_V31, timeout=20)
            if resp.ok:
                data = resp.json()
                assets = data.get('assets', [])
                tiny = None
                for a in assets:
                    n = a.get('name','').lower()
                    if 'tiny' in n and (n.endswith('.pt') or n.endswith('.pth')):
                        tiny = a.get('browser_download_url')
                        break
                if tiny:
                    download_file(tiny, MIDAS_TINY_PT)
        except Exception:
            pass
    if os.path.exists(MIDAS_TINY_PT):
        try:
            model = torch.jit.load(MIDAS_TINY_PT, map_location='cpu') if MIDAS_TINY_PT.endswith('.pt') else torch.load(MIDAS_TINY_PT, map_location='cpu')
            model.eval()
            tfm = T.Compose([T.ToTensor()])
            return ("torch_tiny", (model, tfm))
        except Exception:
            pass
    # Fallback to ONNX small (v2.1) if available or downloadable
    if ort and not os.path.exists(MIDAS_ONNX):
        download_file(MIDAS_URL, MIDAS_ONNX)
    if ort and os.path.exists(MIDAS_ONNX):
        try:
            sess = ort.InferenceSession(MIDAS_ONNX, providers=["CPUExecutionProvider"])
            return ("onnx", sess)
        except Exception:
            pass
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
    if kind == "torch_tiny":
        model, tfm = obj
        h, w = img_bgr.shape[:2]
        with torch.no_grad():
            rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
            tensor = tfm(rgb).unsqueeze(0).float()
            pred = model(tensor)
            if isinstance(pred, (list, tuple)):
                pred = pred[0]
            depth = pred.squeeze().cpu().numpy()
        depth = cv2.resize(depth, (w, h), interpolation=cv2.INTER_CUBIC)
        mn, mx = float(depth.min()), float(depth.max())
        if mx > mn:
            depth = (depth - mn) / (mx - mn)
        else:
            depth = np.zeros_like(depth, dtype=np.float32)
        return depth.astype(np.float32)
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
    topic = f"sproutcast/{room}/{area}/{camera_id}/{plant_id}/ai"

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.connect(host, port, 60)

    baseline = None
    last_mtime = 0
    depth_model = None
    
    # Change detection parameters
    frames_without_change = 0
    max_frames_without_ai = 50  # Only run AI every 50 frames if no significant changes
    force_ai_interval = 300  # Force AI analysis every 5 minutes regardless
    last_forced_ai = time.time()
    
    # Enhanced change detection thresholds
    significant_change_thresholds = {
        'hue_change': 10.0,
        'saturation_change': 15.0,
        'green_ratio_change': 0.08,
        'plant_count_change': 1,
        'total_area_change': 0.15  # 15% change in total plant area
    }
    
    # Load depth model only when needed (lazy loading)
    def get_depth_model():
        nonlocal depth_model
        if depth_model is None:
            print("Loading depth model for AI analysis...")
            depth_model = load_midas()
        return depth_model

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
            
            # Check for change signals from C++ component
            cpp_change_signal = load_change_signal()
            cpp_detected_change = cpp_change_signal.get('significant_change', False)
            
            # Quick metrics without depth model for change detection
            metrics = compute_metrics(img, overrides, None)
            if not metrics:
                time.sleep(0.5)
                continue

            # Establish baseline once
            if baseline is None:
                print("Establishing baseline for change detection...")
                baseline = metrics
                # Run full AI analysis on first frame
                metrics = compute_metrics(img, overrides, get_depth_model())

            # Enhanced deviation check
            significant_change = False
            current_time = time.time()
            
            if baseline and metrics:
                try:
                    # Color change detection
                    dh = abs(metrics["mean_hsv"][0] - baseline["mean_hsv"][0])
                    ds = abs(metrics["mean_hsv"][1] - baseline["mean_hsv"][1])
                    green_diff = abs(metrics["green_ratio"] - baseline.get("green_ratio", 0.0))
                    
                    # Plant count and area changes
                    current_plant_count = len(metrics.get("plants", []))
                    baseline_plant_count = len(baseline.get("plants", []))
                    plant_count_change = abs(current_plant_count - baseline_plant_count)
                    
                    current_total_area = sum(p.get("area_px", 0) for p in metrics.get("plants", []))
                    baseline_total_area = sum(p.get("area_px", 0) for p in baseline.get("plants", []))
                    area_change_ratio = abs(current_total_area - baseline_total_area) / max(baseline_total_area, 1)
                    
                    # Check against thresholds
                    if (dh > significant_change_thresholds['hue_change'] or 
                        ds > significant_change_thresholds['saturation_change'] or 
                        green_diff > significant_change_thresholds['green_ratio_change'] or
                        plant_count_change >= significant_change_thresholds['plant_count_change'] or
                        area_change_ratio > significant_change_thresholds['total_area_change']):
                        significant_change = True
                        print(f"Significant change detected: H={dh:.1f}, S={ds:.1f}, Green={green_diff:.3f}, Plants={plant_count_change}, Area={area_change_ratio:.3f}")
                        
                except Exception as e:
                    print(f"Error in change detection: {e}")
                    significant_change = True  # Err on the side of caution

            # Decide whether to run full AI analysis
            run_full_ai = False
            
            if significant_change or cpp_detected_change:
                run_full_ai = True
                frames_without_change = 0
                # Update baseline with significant changes
                baseline = metrics.copy()
                if cpp_detected_change:
                    print("C++ component signaled significant change")
            elif frames_without_change >= max_frames_without_ai:
                run_full_ai = True
                frames_without_change = 0
            elif (current_time - last_forced_ai) > force_ai_interval:
                run_full_ai = True
                last_forced_ai = current_time
                print("Forcing AI analysis due to time interval")
            else:
                frames_without_change += 1

            # Run full AI analysis with depth model if needed
            if run_full_ai:
                change_reason = 'cpp_signal' if cpp_detected_change else ('significant_change' if significant_change else 'periodic_check')
                print(f"Running full AI analysis (reason: {change_reason})")
                metrics = compute_metrics(img, overrides, get_depth_model())
                
            payload = {
                "baseline": baseline,
                "metrics": metrics,
                "deviation": significant_change or cpp_detected_change,
                "ai_analysis": run_full_ai,
                "frames_without_ai": frames_without_change,
                "change_detection": {
                    "color_change": dh if 'dh' in locals() else 0,
                    "saturation_change": ds if 'ds' in locals() else 0,
                    "green_ratio_change": green_diff if 'green_diff' in locals() else 0,
                    "plant_count_change": plant_count_change if 'plant_count_change' in locals() else 0,
                    "area_change_ratio": area_change_ratio if 'area_change_ratio' in locals() else 0,
                    "cpp_signal": cpp_change_signal if cpp_detected_change else None
                }
            }
            
            with open(METRICS_PATH, "wb") as f:
                f.write(orjson.dumps(payload))
            client.publish(topic, orjson.dumps(payload).decode())
            
        except Exception as e:
            print(f"Error in main loop: {e}")
            time.sleep(0.5)
        time.sleep(0.5)


if __name__ == "__main__":
    main()

