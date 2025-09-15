"""
PlantVision AI Module - Streamlined for AI Inference Only
===========================================================

This module has been refactored to focus exclusively on AI inference tasks:
- Depth estimation model loading and inference (MiDaS, DPT)
- ONNX runtime operations
- Neural network model management

All basic OpenCV operations (masking, morphology, color analysis, change detection) 
have been moved to the C++ VisionProcessor for better performance.

The C++ component now handles:
- HSV color conversion and green masking
- Morphological operations (opening/closing) 
- Contour detection and basic shape analysis
- Change detection and motion analysis
- Color space analysis (BGR, HSV, LAB)
- NDVI and EXG vegetation indices

This module only processes AI inference requests from the C++ component.
"""

import os
import time
import json
import numpy as np
import cv2
import pathlib
try:
    import onnxruntime as ort
except Exception:
    ort = None
import requests
import torch
import torchvision.transforms as T
from typing import Dict, Any, Optional, Tuple
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Directory paths - aligned with C++ VisionProcessor
DATA_DIR = "/app/data"
MODELS_DIR = "/app/models"
AI_REQUESTS_DIR = "/app/data/ai_requests"
AI_RESULTS_DIR = "/app/data/ai_results"
MODELS_STATUS_PATH = "/app/data/model_status.json"

# Model URLs and paths
MIDAS_ONNX = os.path.join(MODELS_DIR, "midas_small.onnx")
MIDAS_URL = "https://github.com/isl-org/MiDaS/releases/download/v3_1_small/model-small.onnx"
DPT_SWIN2_PT = os.path.join(MODELS_DIR, "dpt_swin2_tin_256.pt")
DPT_SWIN2_URL = "https://github.com/isl-org/MiDaS/releases/download/v3_1/dpt_swin2_tiny_256.pt"

"""
PlantVision AI Module - Streamlined for AI Inference Only
===========================================================

This module has been refactored to focus exclusively on AI inference tasks:
- Depth estimation model loading and inference (MiDaS, DPT)
- ONNX runtime operations
- Neural network model management

All basic OpenCV operations (masking, morphology, color analysis, change detection) 
have been moved to the C++ VisionProcessor for better performance.

The C++ component now handles:
- HSV color conversion and green masking
- Morphological operations (opening/closing) 
- Contour detection and basic shape analysis
- Change detection and motion analysis
- Color space analysis (BGR, HSV, LAB)
- NDVI and EXG vegetation indices

This module only processes AI inference requests from the C++ component.
"""

import os
import time
import json
import numpy as np
import cv2
import pathlib
try:
    import onnxruntime as ort
except Exception:
    ort = None
import requests
import torch
import torchvision.transforms as T
from typing import Dict, Any, Optional, Tuple
import logging
import glob

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Directory paths - aligned with C++ VisionProcessor
DATA_DIR = "/app/data"
MODELS_DIR = "/app/models"
AI_REQUESTS_DIR = "/app/data/ai_requests"
AI_RESULTS_DIR = "/app/data/ai_results"
MODELS_STATUS_PATH = "/app/data/model_status.json"

# Model URLs and paths
MIDAS_ONNX = os.path.join(MODELS_DIR, "midas_small.onnx")
MIDAS_URL = "https://github.com/isl-org/MiDaS/releases/download/v3_1_small/model-small.onnx"
DPT_SWIN2_PT = os.path.join(MODELS_DIR, "dpt_swin2_tin_256.pt")
DPT_SWIN2_URL = "https://github.com/isl-org/MiDaS/releases/download/v3_1/dpt_swin2_tiny_256.pt"

class AIModelManager:
    """Manages AI model loading and inference - separated from OpenCV processing"""
    
    def __init__(self):
        self.depth_model = None
        self.model_type = None
        self.ensure_directories()
        
    def ensure_directories(self):
        """Create necessary directories"""
        for dir_path in [MODELS_DIR, AI_REQUESTS_DIR, AI_RESULTS_DIR]:
            os.makedirs(dir_path, exist_ok=True)
            
    def update_model_status(self, status: str, model_name: str = "", progress: int = 0, message: str = ""):
        """Update model download/loading status"""
        try:
            status_data = {
                "status": status,  # downloading, loading, ready, error
                "model_name": model_name,
                "progress": progress,  # 0-100
                "message": message,
                "timestamp": time.time()
            }
            with open(MODELS_STATUS_PATH, 'w') as f:
                json.dump(status_data, f)
                
        except Exception as e:
            logger.error(f"Failed to update model status: {e}")

    def download_file(self, url: str, dest: str) -> bool:
        """Download file from URL"""
        try:
            logger.info(f"Downloading {url} to {dest}")
            r = requests.get(url, timeout=60)
            r.raise_for_status()
            with open(dest, 'wb') as f:
                f.write(r.content)
            return True
        except Exception as e:
            logger.error(f"Download failed: {e}")
            return False

    def load_depth_model(self):
        """Load depth estimation model - prioritize DPT Swin2"""
        
        # Priority 1: DPT Swin2 Tiny 256 model
        if not os.path.exists(DPT_SWIN2_PT):
            self.update_model_status("downloading", "DPT Swin2 Tiny 256", 0, "Starting download...")
            if self.download_file(DPT_SWIN2_URL, DPT_SWIN2_PT):
                self.update_model_status("downloading", "DPT Swin2 Tiny 256", 100, "Download complete")
            else:
                self.update_model_status("error", "DPT Swin2 Tiny 256", 0, "Download failed")
        
        if os.path.exists(DPT_SWIN2_PT):
            try:
                self.update_model_status("loading", "DPT Swin2 Tiny 256", 0, "Loading model...")
                logger.info("Loading DPT Swin2 Tiny 256 model...")
                model = torch.jit.load(DPT_SWIN2_PT, map_location='cpu')
                model.eval()
                
                # DPT Swin2 transform
                transform = T.Compose([
                    T.ToTensor(),
                    T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
                ])
                
                self.depth_model = (model, transform)
                self.model_type = "dpt_swin2"
                self.update_model_status("ready", "DPT Swin2 Tiny 256", 100, "Model ready")
                logger.info("DPT Swin2 model loaded successfully")
                return True
                
            except Exception as e:
                self.update_model_status("error", "DPT Swin2 Tiny 256", 0, f"Loading failed: {str(e)}")
                logger.error(f"Failed to load DPT Swin2 model: {e}")
        
        # Fallback: ONNX model
        if ort and not os.path.exists(MIDAS_ONNX):
            self.download_file(MIDAS_URL, MIDAS_ONNX)
            
        if ort and os.path.exists(MIDAS_ONNX):
            try:
                self.update_model_status("loading", "MiDaS ONNX", 0, "Loading ONNX model...")
                sess = ort.InferenceSession(MIDAS_ONNX, providers=["CPUExecutionProvider"])
                self.depth_model = sess
                self.model_type = "onnx"
                self.update_model_status("ready", "MiDaS ONNX", 100, "ONNX model ready")
                logger.info("MiDaS ONNX model loaded successfully")
                return True
                
            except Exception as e:
                logger.error(f"Failed to load ONNX model: {e}")
        
        self.update_model_status("error", "No Model", 0, "No depth model available")
        return False

    def run_depth_inference(self, image_bgr: np.ndarray) -> Optional[np.ndarray]:
        """Run depth inference on image - pure AI processing, no OpenCV masking"""
        if self.depth_model is None:
            logger.error("No depth model loaded")
            return None
            
        try:
            h, w = image_bgr.shape[:2]
            
            if self.model_type == "dpt_swin2":
                model, transform = self.depth_model
                
                with torch.no_grad():
                    # Convert BGR to RGB
                    rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
                    # Resize to model input size
                    rgb_resized = cv2.resize(rgb, (256, 256), interpolation=cv2.INTER_AREA)
                    
                    # Apply transform and add batch dimension
                    tensor = transform(rgb_resized).unsqueeze(0).float()
                    
                    # Run inference
                    pred = model(tensor)
                    if isinstance(pred, (list, tuple)):
                        pred = pred[0]
                    
                    depth = pred.squeeze().cpu().numpy()
                
                # Resize back to original size
                depth = cv2.resize(depth, (w, h), interpolation=cv2.INTER_CUBIC)
                
            elif self.model_type == "onnx":
                # Preprocess for ONNX model
                inp = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
                inp = cv2.resize(inp, (256, 256), interpolation=cv2.INTER_AREA)
                inp = inp.astype(np.float32) / 255.0
                inp = inp.transpose(2, 0, 1)[None, ...]
                
                # Run ONNX inference
                depth = self.depth_model.run(None, {self.depth_model.get_inputs()[0].name: inp})[0][0, 0]
                depth = cv2.resize(depth, (w, h), interpolation=cv2.INTER_CUBIC)
            
            else:
                return None
            
            # Normalize depth to 0-1 range
            mn, mx = float(depth.min()), float(depth.max())
            if mx > mn:
                depth = (depth - mn) / (mx - mn)
            else:
                depth = np.zeros_like(depth, dtype=np.float32)
                
            return depth.astype(np.float32)
            
        except Exception as e:
            logger.error(f"Depth inference error: {e}")
            return None

class AIRequestProcessor:
    """Process AI inference requests from C++ VisionProcessor"""
    
    def __init__(self):
        self.model_manager = AIModelManager()
        self.model_loaded = False
        
    def initialize(self):
        """Initialize AI models"""
        logger.info("Initializing AI models (OpenCV processing now handled by C++)")
        self.model_loaded = self.model_manager.load_depth_model()
        return self.model_loaded
        
    def process_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single AI inference request"""
        request_id = request_data.get('request_id', 'unknown')
        image_path = request_data.get('image_path', '')
        
        logger.info(f"Processing AI request {request_id}")
        
        if not os.path.exists(image_path):
            return {
                "success": False,
                "error": f"Image not found: {image_path}",
                "request_id": request_id
            }
        
        # Load image
        image = cv2.imread(image_path)
        if image is None:
            return {
                "success": False,
                "error": f"Failed to load image: {image_path}",
                "request_id": request_id
            }
        
        result = {
            "success": True,
            "request_id": request_id,
            "timestamp": time.time(),
            "model_type": self.model_manager.model_type
        }
        
        # Depth analysis if requested
        if request_data.get('depth_analysis_required', False):
            depth_map = self.model_manager.run_depth_inference(image)
            
            if depth_map is not None:
                # Convert depth to physical distances (simplified calibration)
                max_distance = 100.0  # cm
                min_distance = 10.0   # cm
                depth_cm = min_distance + (max_distance - min_distance) * (1.0 - depth_map)
                
                result['depth_analysis'] = {
                    "success": True,
                    "min_depth_cm": float(depth_cm.min()),
                    "max_depth_cm": float(depth_cm.max()),
                    "mean_depth_cm": float(depth_cm.mean()),
                    "median_depth_cm": float(np.median(depth_cm))
                }
                
                # Save depth map for C++ access if needed
                depth_file = f"{AI_RESULTS_DIR}/depth_{request_id}.npy"
                np.save(depth_file, depth_cm)
                result['depth_analysis']['depth_file'] = depth_file
                
            else:
                result['depth_analysis'] = {
                    "success": False,
                    "error": "Depth inference failed"
                }
        
        return result
        
    def save_result(self, result_data: Dict[str, Any], request_id: str):
        """Save AI inference result for C++ component"""
        try:
            result_file = f"{AI_RESULTS_DIR}/{request_id}.json"
            with open(result_file, 'w') as f:
                json.dump(result_data, f, indent=2)
            logger.info(f"AI result saved: {result_file}")
            
        except Exception as e:
            logger.error(f"Failed to save result: {e}")

def main():
    """Main AI processing loop - only handles AI inference requests"""
    logger.info("=== PlantVision AI Module Started ===")
    logger.info("Scope: AI inference only (OpenCV moved to C++ VisionProcessor)")
    
    processor = AIRequestProcessor()
    
    if not processor.initialize():
        logger.error("Failed to initialize AI models")
        return
    
    logger.info("AI models loaded - waiting for requests from C++ VisionProcessor...")
    
    # Main processing loop - watch for AI requests from C++
    while True:
        try:
            # Look for signal files from C++ VisionProcessor
            signal_files = glob.glob(f"{DATA_DIR}/ai_analysis_*.signal")
            
            for signal_file in signal_files:
                try:
                    # Read request ID from signal file
                    with open(signal_file, 'r') as f:
                        request_id = f.read().strip()
                    
                    # Load request data
                    request_file = f"{AI_REQUESTS_DIR}/{request_id}.json"
                    if os.path.exists(request_file):
                        with open(request_file, 'r') as f:
                            request_data = json.load(f)
                        
                        # Process the AI inference request
                        result = processor.process_request(request_data)
                        
                        # Save result for C++ component
                        processor.save_result(result, request_id)
                        
                        logger.info(f"Completed AI processing for request {request_id}")
                    
                    # Clean up signal file
                    os.remove(signal_file)
                    
                except Exception as e:
                    logger.error(f"Error processing request {signal_file}: {e}")
                    try:
                        os.remove(signal_file)
                    except:
                        pass
            
            # Brief sleep to avoid excessive CPU usage
            time.sleep(0.1)
            
        except KeyboardInterrupt:
            logger.info("AI module shutting down...")
            break
        except Exception as e:
            logger.error(f"Main loop error: {e}")
            time.sleep(1)

if __name__ == "__main__":
    main()

