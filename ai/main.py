"""
PlantVision AI Module - ONNX Runtime Only
==========================================
Lightweight AI inference using only ONNX Runtime.
No PyTorch dependency required.
"""

import os, time, json, numpy as np, cv2, requests, logging, glob
try:
    import onnxruntime as ort
except: ort = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATA_DIR, MODELS_DIR = "/app/data", "/app/models"
AI_REQUESTS_DIR, AI_RESULTS_DIR = f"{DATA_DIR}/ai_requests", f"{DATA_DIR}/ai_results"
MIDAS_ONNX = f"{MODELS_DIR}/midas_small.onnx"
MIDAS_URL = "https://github.com/isl-org/MiDaS/releases/download/v3_1/model-small.onnx"

class AIModelManager:
    def __init__(self):
        self.depth_model, self.model_type = None, None
        for d in [MODELS_DIR, AI_REQUESTS_DIR, AI_RESULTS_DIR]: os.makedirs(d, exist_ok=True)
    
    def load_depth_model(self):
        if not ort: return False
        if not os.path.exists(MIDAS_ONNX):
            try:
                r = requests.get(MIDAS_URL, timeout=60)
                r.raise_for_status()
                with open(MIDAS_ONNX, 'wb') as f: f.write(r.content)
            except: return False
        try:
            self.depth_model = ort.InferenceSession(MIDAS_ONNX, providers=["CPUExecutionProvider"])
            self.model_type = "onnx"
            return True
        except: return False
    
    def run_depth_inference(self, img):
        if not self.depth_model: return None
        try:
            h, w = img.shape[:2]
            inp = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            inp = cv2.resize(inp, (256, 256))
            inp = (inp.astype(np.float32) / 255.0).transpose(2, 0, 1)[None, ...]
            depth = self.depth_model.run(None, {self.depth_model.get_inputs()[0].name: inp})[0][0, 0]
            depth = cv2.resize(depth, (w, h))
            mn, mx = depth.min(), depth.max()
            return (depth - mn) / (mx - mn) if mx > mn else np.zeros_like(depth)
        except: return None

def main():
    logger.info("AI Module Started (ONNX Only)")
    mgr = AIModelManager()
    mgr.load_depth_model()
    while True:
        try:
            for sig in glob.glob(f"{DATA_DIR}/ai_analysis_*.signal"):
                try:
                    with open(sig) as f: req_id = f.read().strip()
                    req_file = f"{AI_REQUESTS_DIR}/{req_id}.json"
                    if os.path.exists(req_file):
                        with open(req_file) as f: req = json.load(f)
                        img = cv2.imread(req.get('image_path', ''))
                        result = {"success": bool(img is not None), "request_id": req_id}
                        if img is not None and req.get('depth_analysis_required'):
                            depth = mgr.run_depth_inference(img)
                            if depth is not None:
                                depth_cm = 10 + 90 * (1 - depth)
                                result['depth_analysis'] = {"success": True, "mean_depth_cm": float(depth_cm.mean())}
                        with open(f"{AI_RESULTS_DIR}/{req_id}.json", 'w') as f: json.dump(result, f)
                    os.remove(sig)
                except: pass
            time.sleep(0.1)
        except KeyboardInterrupt: break

if __name__ == "__main__": main()
