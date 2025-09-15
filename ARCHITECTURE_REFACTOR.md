# PlantVision Architecture Refactor - OpenCV Consolidation

## Overview

This refactor addresses the significant architectural inefficiency where OpenCV image processing operations were duplicated between the C++ and Python components. The solution consolidates all basic image processing into C++, while keeping AI inference tasks in Python.

## Problems Addressed

### Before Refactor (Issues Identified):

1. **Duplicate OpenCV Processing**: 
   - Python `main.py` performed HSV conversion, green masking, morphological operations
   - C++ `leaf_area.cpp` performed identical operations
   - Both computed color statistics, contour analysis, and shape metrics

2. **Performance Issues**:
   - Python OpenCV calls in the main processing loop created bottlenecks
   - Unnecessary data marshaling between NumPy and C++ Mat objects
   - Redundant memory allocations for identical operations

3. **Maintenance Complexity**:
   - Changes to image processing algorithms required updates in both codebases
   - Inconsistent parameter configurations between C++ and Python
   - Difficult to debug performance issues

## Solution Architecture

### After Refactor (New Design):

```
┌─────────────────────────────────────────────────────────────┐
│                    C++ VisionProcessor                     │
│                   (All OpenCV Operations)                   │
├─────────────────────────────────────────────────────────────┤
│ • HSV color conversion and green masking                    │
│ • Morphological operations (opening/closing)               │
│ • Contour detection and shape analysis                     │
│ • Change detection and motion analysis                     │
│ • Color space analysis (BGR, HSV, LAB)                     │
│ • NDVI and EXG vegetation indices                          │
│ • Intelligent AI request generation                        │
└─────────────────────────────────────────────────────────────┘
                              │
                         File-based IPC
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   Python AI Module                         │
│                 (AI Inference Only)                        │
├─────────────────────────────────────────────────────────────┤
│ • Depth estimation (MiDaS, DPT Swin2)                      │
│ • ONNX runtime operations                                  │
│ • Neural network model management                          │
│ • PyTorch inference                                        │
└─────────────────────────────────────────────────────────────┘
```

## Key Components

### 1. VisionProcessor Class (C++)

**Location**: `cpp/src/vision_processor.cpp`, `cpp/include/vision_processor.hpp`

**Responsibilities**:
- All OpenCV image processing operations
- Change detection with configurable thresholds
- Color analysis in multiple color spaces
- Smart AI request generation
- Performance monitoring and debugging

**Key Methods**:
```cpp
BasicMetrics processBasicMetrics(const cv::Mat& frame)
ChangeDetectionResult detectChanges(const cv::Mat& current, const cv::Mat& previous)
cv::Mat createPlantMask(const cv::Mat& frame, bool enhanced_sensitivity)
ColorAnalysis analyzeColors(const cv::Mat& frame, const cv::Mat& mask)
AIRequestData generateAIRequest(const cv::Mat& frame, const BasicMetrics& metrics)
```

### 2. Streamlined AI Module (Python)

**Location**: `ai/main.py`

**Responsibilities**:
- AI model loading and management
- Depth estimation inference
- ONNX runtime operations
- Request/response processing

**Key Classes**:
```python
class AIModelManager:
    # Handles model loading and inference
    
class AIRequestProcessor:
    # Processes AI requests from C++ component
```

## Performance Improvements

### Benchmarks (Expected):

1. **Processing Speed**: 
   - ~40% faster frame processing (OpenCV operations in native C++)
   - Reduced Python GIL contention
   - Eliminated duplicate computations

2. **Memory Usage**:
   - ~30% reduction in peak memory usage
   - No duplicate Mat/NumPy conversions
   - Efficient memory management in C++

3. **System Responsiveness**:
   - AI inference only triggered when needed
   - Intelligent change detection reduces unnecessary processing
   - Better resource utilization

## Interface Design

### C++ to Python Communication

**Request Structure** (`/app/data/ai_requests/{request_id}.json`):
```json
{
  "image_path": "/app/data/ai_requests/frame_123.jpg",
  "model_preference": "dpt_swin2",
  "depth_analysis_required": true,
  "classification_required": true,
  "roi": {"x": 10, "y": 20, "width": 200, "height": 150},
  "confidence_threshold": 0.7,
  "timestamp": 1672531200.0,
  "request_id": "req_123"
}
```

**Response Structure** (`/app/data/ai_results/{request_id}.json`):
```json
{
  "success": true,
  "request_id": "req_123",
  "timestamp": 1672531201.5,
  "model_type": "dpt_swin2",
  "depth_analysis": {
    "success": true,
    "min_depth_cm": 15.2,
    "max_depth_cm": 85.7,
    "mean_depth_cm": 42.3,
    "median_depth_cm": 40.1,
    "depth_file": "/app/data/ai_results/depth_req_123.npy"
  }
}
```

## Configuration Changes

### Environment Variables

**C++ Component**:
```bash
VISION_DEBUG_MODE=true          # Enable debug output and image saving
CONFIG_PATH=/app/data/config.json
```

**Python AI Component**:
```bash
DATA_DIR=/app/data
MODELS_DIR=/app/models
AI_REQUESTS_DIR=/app/data/ai_requests
AI_RESULTS_DIR=/app/data/ai_results
```

### Directory Structure

```
/app/data/
├── ai_requests/          # C++ -> Python requests
├── ai_results/           # Python -> C++ responses  
├── debug/               # Debug images and logs (if enabled)
├── sprouts/             # Organized sprout data
├── plants/              # Organized plant data
├── frame_raw.jpg        # Current raw frame
├── frame_annotated.jpg  # Annotated frame
└── config.json          # Configuration
```

## Migration Guide

### 1. Update Dependencies

Ensure C++17 support for `std::filesystem`:
```cmake
set(CMAKE_CXX_STANDARD 17)
target_link_libraries(plantvision_cpp PRIVATE ${OpenCV_LIBS})
```

### 2. Build and Deploy

```bash
# Build updated C++ component
docker compose build cpp-app

# Build updated AI component  
docker compose build ai

# Deploy with new architecture
docker compose up -d
```

### 3. Monitor Performance

Enable debug mode to monitor the consolidation:
```bash
docker compose exec cpp-app ls -la /app/data/debug/
```

### 4. Verify AI Integration

Check AI request processing:
```bash
docker logs sc-ai  # Should show "AI models loaded - waiting for requests"
docker logs sc-cpp # Should show "AI analysis requested" messages
```

## Debugging and Monitoring

### Debug Mode

Enable comprehensive debugging in `docker-compose.yml`:
```yaml
environment:
  - VISION_DEBUG_MODE=true
```

This provides:
- Frame-by-frame processing images
- Performance metrics logging
- Change detection visualizations
- AI request/response tracking

### Log Analysis

**C++ Component Logs**:
```bash
docker logs sc-cpp | grep "VisionProcessor"
# Expected: Processing times, change detection results, AI requests
```

**Python AI Logs**:
```bash
docker logs sc-ai | grep "AI"
# Expected: Model loading, inference processing, request completion
```

## Performance Monitoring

### Key Metrics to Monitor

1. **Frame Processing Time**: Should be <100ms per frame
2. **AI Request Frequency**: Should reduce by ~70% with smart triggering
3. **Memory Usage**: Should be more stable without duplicate processing
4. **Change Detection Accuracy**: Should maintain detection quality

### Expected Behavior

- **Startup**: C++ processes frames immediately, AI loads models async
- **Steady State**: C++ handles all frames, AI processes ~1-2 requests/minute
- **Change Events**: AI requests spike during plant movement/growth
- **Resource Usage**: More predictable CPU/memory patterns

## Troubleshooting

### Common Issues

1. **AI Not Processing Requests**:
   ```bash
   # Check signal files
   ls -la /app/data/ai_analysis_*.signal
   
   # Check request directory
   ls -la /app/data/ai_requests/
   ```

2. **Performance Regression**:
   ```bash
   # Check debug mode isn't enabled in production
   docker compose exec cpp-app env | grep VISION_DEBUG_MODE
   ```

3. **Build Failures**:
   ```bash
   # Ensure C++17 support
   docker compose exec cpp-app g++ --version
   ```

## Future Enhancements

1. **GPU Acceleration**: Move remaining AI preprocessing to CUDA
2. **Model Optimization**: Quantize depth models for faster inference
3. **Streaming Integration**: Add support for video stream processing
4. **Edge Deployment**: Optimize for resource-constrained environments

## Conclusion

This refactor eliminates architectural inefficiencies by:
- Consolidating OpenCV operations in C++ for performance
- Streamlining Python to focus on AI inference
- Implementing efficient inter-process communication
- Providing comprehensive debugging and monitoring

The result is a more maintainable, performant, and scalable plant vision system.
