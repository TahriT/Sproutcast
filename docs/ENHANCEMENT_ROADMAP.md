# PlantVision Enhancement Roadmap

This document outlines planned enhancements and features that have not yet been implemented. For current system architecture and capabilities, see [ARCHITECTURE.md](ARCHITECTURE.md).

## Currently Implemented ✅

The following features from the original PlantCV enhancement plan are **already implemented**:

- ✅ Advanced morphological analysis (skeleton, shape descriptors)
- ✅ Multi-colorspace analysis (BGR, HSV, LAB)
- ✅ Plant/Sprout classification system
- ✅ Change detection optimization
- ✅ NDVI and EXG vegetation indices
- ✅ Disease detection (brown spots, yellowing)
- ✅ Health scoring system
- ✅ Hierarchical MQTT topic structure (UNS)
- ✅ VisionProcessor architecture (consolidated OpenCV in C++)
- ✅ AI integration with file-based IPC
- ✅ Per-instance data organization (plants/sprouts directories)

## Planned Enhancements 🚀

### Phase 1: Advanced ML Classification (Q1 2026)

#### 1.1 Native C++ Machine Learning
**Status**: Not Started  
**Priority**: High  
**Complexity**: Medium

Implement machine learning models using OpenCV's ML module (no Python dependency):

```cpp
class PlantClassifier {
    cv::Ptr<cv::ml::NormalBayesClassifier> naive_bayes;
    cv::Ptr<cv::ml::KMeans> kmeans_clusterer;
    
public:
    // Train from HSV sample images
    bool trainFromHSVSamples(const std::string& samples_file);
    
    // Classify pixels into plant/background/disease
    cv::Mat classifyPixels(const cv::Mat& image);
    
    // Species classification from features
    std::string classifySpecies(const cv::Mat& image, const cv::Mat& mask);
};
```

**Benefits**:
- Automated plant/background segmentation (reduce manual threshold tuning)
- Species-specific analysis parameters
- Improved disease classification accuracy

**Estimated Effort**: 3-4 weeks

#### 1.2 Public Dataset Integration
**Status**: Not Started  
**Priority**: Medium  
**Complexity**: Low

Integrate publicly available plant phenotyping datasets for training and validation:

- **Setaria Dataset**: 79,200 images (CC BY 4.0)
- **Sorghum Dataset**: 96,867 images (CC BY 4.0)
- **Color Calibration**: 24,000 images (CC0 Public Domain)

```cpp
class DatasetManager {
public:
    bool loadSetariaDataset(const std::string& dataset_path);
    bool loadSorghumDataset(const std::string& dataset_path);
    
    std::vector<TrainingSample> extractTrainingSamples(
        const std::string& dataset_path, 
        const std::vector<std::string>& target_classes
    );
    
    ValidationResults validateAgainstDataset(const std::string& dataset_path);
};
```

**Benefits**:
- Validate algorithms against scientific benchmarks
- Train species-specific classifiers
- Improve generalization across plant types

**Estimated Effort**: 2-3 weeks

### Phase 2: Enhanced Morphological Features (Q2 2026)

#### 2.1 Advanced Skeleton Analysis
**Status**: Partially Implemented  
**Priority**: Medium  
**Complexity**: High

Extend current skeleton analysis with detailed branch/tip measurements:

```cpp
struct EnhancedSkeletonMetrics {
    // Currently implemented
    double total_path_length;
    int branch_points;
    int tip_points;
    
    // To be implemented
    std::vector<double> branch_angles;       // Angle at each branch point
    std::vector<double> segment_curvatures;  // Curvature along segments
    std::vector<cv::Point> leaf_attachment_points;
    double branching_pattern_score;          // Symmetry/regularity metric
    double apical_dominance_index;           // Main stem vs. branch growth
};
```

**Benefits**:
- Better growth stage identification
- Improved plant stress detection (abnormal branching)
- Species-specific morphological signatures

**Estimated Effort**: 3-4 weeks

#### 2.2 Leaf-Level Analysis
**Status**: Not Started  
**Priority**: Low  
**Complexity**: High

Implement individual leaf detection and analysis:

```cpp
struct LeafMetrics {
    int leaf_id;
    cv::Rect bbox;
    double area_cm2;
    double length_cm;
    double width_cm;
    double serration_index;      // Edge complexity
    double symmetry_score;        // Left/right symmetry
    std::vector<cv::Point> venation_pattern;
    cv::Scalar mean_color;
    bool disease_detected;
    std::vector<DiseaseSpot> spots;
};

std::vector<LeafMetrics> analyzeIndividualLeaves(const cv::Mat& plant_mask);
```

**Benefits**:
- Precise disease localization
- Per-leaf health tracking
- Better leaf count accuracy

**Estimated Effort**: 4-5 weeks

### Phase 3: Performance Optimizations (Q2 2026)

#### 3.1 GPU Acceleration
**Status**: Not Started  
**Priority**: High  
**Complexity**: Medium

Add CUDA support for compute-intensive operations:

```cpp
class GPUVisionProcessor {
    cv::cuda::GpuMat gpu_frame;
    cv::Ptr<cv::cuda::Filter> gpu_morph_filter;
    
public:
    void processOnGPU(const cv::Mat& cpu_frame);
    cv::Mat retrieveResult();
};
```

**Target Operations**:
- Color space conversions (BGR→HSV, LAB)
- Morphological operations (erosion, dilation)
- Contour detection acceleration
- Skeleton extraction

**Expected Performance Gain**: 3-5x faster processing

**Estimated Effort**: 2-3 weeks

#### 3.2 Multi-Camera Support
**Status**: Not Started  
**Priority**: High  
**Complexity**: Medium

Support simultaneous processing of multiple camera feeds:

```cpp
class MultiCameraManager {
    std::vector<std::unique_ptr<VisionProcessor>> processors;
    std::vector<std::thread> processing_threads;
    
public:
    void addCamera(const CameraConfig& config);
    void startAllCameras();
    void stopAllCameras();
    
    // Aggregate data from all cameras
    CombinedTelemetry getAggregateData();
};
```

**Benefits**:
- Monitor multiple grow areas simultaneously
- Compare growth across different environments
- Scalable deployment for commercial operations

**Estimated Effort**: 3-4 weeks

### Phase 4: Advanced AI Integration (Q3 2026)

#### 4.1 On-Device AI Inference
**Status**: Not Started  
**Priority**: Medium  
**Complexity**: High

Replace file-based IPC with in-process AI inference:

```cpp
class EmbeddedAIProcessor {
    std::shared_ptr<onnxruntime::Env> ort_env;
    std::unique_ptr<onnxruntime::Session> depth_session;
    
public:
    DepthMap estimateDepth(const cv::Mat& frame);
    SegmentationMask segmentPlant(const cv::Mat& frame);
};
```

**Benefits**:
- Eliminate IPC overhead
- Real-time AI inference (<50ms)
- Reduced disk I/O

**Estimated Effort**: 4-5 weeks

#### 4.2 Lightweight Disease Classification
**Status**: Not Started  
**Priority**: Medium  
**Complexity**: High

Train and deploy lightweight CNN for disease classification:

- **Model**: MobileNetV3 or EfficientNet-Lite
- **Target**: <10MB model size, <100ms inference
- **Classes**: Healthy, nutrient deficiency, fungal infection, pest damage

**Benefits**:
- Real-time disease alerts
- Automated treatment recommendations
- Reduce false positives vs. color-based detection

**Estimated Effort**: 5-6 weeks (including training)

### Phase 5: Data Analytics & Visualization (Q3-Q4 2026)

#### 5.1 Time-Series Database Integration
**Status**: Not Started  
**Priority**: Medium  
**Complexity**: Medium

Integrate TimescaleDB for historical data analysis:

```sql
CREATE TABLE plant_telemetry (
    time TIMESTAMPTZ NOT NULL,
    plant_id INTEGER,
    area_cm2 DOUBLE PRECISION,
    height_cm DOUBLE PRECISION,
    health_score DOUBLE PRECISION,
    -- ... additional metrics
);

SELECT create_hypertable('plant_telemetry', 'time');
```

**Benefits**:
- Growth rate analysis over weeks/months
- Trend detection and forecasting
- Anomaly detection via SQL queries
- Efficient historical data queries

**Estimated Effort**: 2-3 weeks

#### 5.2 Enhanced Web Dashboard
**Status**: Partially Implemented  
**Priority**: Medium  
**Complexity**: Medium

Add advanced visualization features:

- Interactive growth charts (Chart.js or Plotly)
- Heatmaps for multi-plant monitoring
- Timelapse video generation from frame sequences
- Comparative analysis (plant A vs. plant B)
- Export reports (PDF, CSV)

**Estimated Effort**: 4-5 weeks

#### 5.3 Mobile Application
**Status**: Not Started  
**Priority**: Low  
**Complexity**: High

Develop mobile app for remote monitoring:

- **Platform**: React Native or Flutter
- **Features**: Push notifications, dashboard viewing, configuration
- **Integration**: REST API and MQTT subscriptions

**Estimated Effort**: 8-10 weeks

### Phase 6: Edge Deployment & Scalability (Q4 2026)

#### 6.1 Raspberry Pi / Jetson Optimization
**Status**: Not Started  
**Priority**: Medium  
**Complexity**: Medium

Optimize builds for edge devices:

```dockerfile
# ARM64 optimized build
FROM arm64v8/ubuntu:22.04
RUN apt-get install -y \
    libopencv-dev \
    libtbb-dev \
    # Optimized BLAS for ARM
    libopenblas-dev
```

**Target Devices**:
- Raspberry Pi 4 (4GB RAM minimum)
- NVIDIA Jetson Nano / Xavier NX
- Other ARM64 single-board computers

**Expected Performance**: 5-10 FPS processing on Raspberry Pi 4

**Estimated Effort**: 2-3 weeks

#### 6.2 Kubernetes Deployment
**Status**: Not Started  
**Priority**: Low  
**Complexity**: Medium

Create Kubernetes manifests for scalable deployment:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: plantvision-cpp
spec:
  replicas: 3
  selector:
    matchLabels:
      app: plantvision-cpp
  template:
    # ... pod specification
```

**Benefits**:
- Auto-scaling based on load
- High availability
- Rolling updates with zero downtime
- Multi-node deployment

**Estimated Effort**: 2-3 weeks

### Phase 7: Research & Experimental Features (2027)

#### 7.1 3D Plant Reconstruction
**Status**: Research Phase  
**Priority**: Low  
**Complexity**: Very High

Use depth maps to reconstruct 3D plant models:

- Multi-view geometry from single camera
- Point cloud generation
- Volume estimation from depth
- 3D growth visualization

**Potential Benefits**:
- Accurate biomass estimation
- 3D canopy analysis
- Virtual plant inspection

**Estimated Effort**: 12-16 weeks (research + implementation)

#### 7.2 Hyperspectral Imaging
**Status**: Research Phase  
**Priority**: Low  
**Complexity**: Very High

Integrate hyperspectral camera for advanced analysis:

- Multi-band spectral analysis (>3 channels)
- Precise chlorophyll measurement
- Water stress detection
- Nutrient deficiency identification

**Hardware Requirements**: Specialized hyperspectral camera ($1000+)

**Estimated Effort**: 16-20 weeks

#### 7.3 Automated Growth Optimization
**Status**: Concept Phase  
**Priority**: Low  
**Complexity**: Very High

Closed-loop system with environmental control:

- Reinforcement learning for optimal growth parameters
- Automated light/water/nutrient adjustment
- Integration with smart greenhouse controllers
- Predictive yield modeling

**Estimated Effort**: 20+ weeks

## Resource Requirements Summary

### Development Priorities (Next 12 Months)

| Quarter | Focus Area | Estimated Effort | Key Deliverables |
|---------|------------|------------------|------------------|
| Q1 2026 | ML Classification | 5-7 weeks | Native C++ ML, Dataset integration |
| Q2 2026 | Morphology & Performance | 9-13 weeks | Advanced skeleton analysis, GPU support, Multi-camera |
| Q3 2026 | AI Integration | 9-11 weeks | On-device inference, Disease classification, TimescaleDB |
| Q4 2026 | Scalability | 6-9 weeks | Edge optimization, Kubernetes, Enhanced dashboard |

### Hardware/Infrastructure Needs

- **GPU Development**: NVIDIA GPU (GTX 1060 or better) for CUDA development
- **Edge Testing**: Raspberry Pi 4, Jetson Nano for optimization
- **Multi-Camera**: 2-3 USB cameras for testing
- **Storage**: Additional 1TB SSD for dataset storage
- **Cloud**: Optional K8s cluster for scalability testing

## Contributing

We welcome contributions! Priority areas for community involvement:

1. **Dataset Integration**: Help process and label public datasets
2. **Model Training**: Train species-specific classifiers
3. **Testing**: Test on different hardware platforms
4. **Documentation**: Improve guides and tutorials
5. **Feature Requests**: Suggest new capabilities

See [CONTRIBUTING.md](../CONTRIBUTING.md) for guidelines.

## Licensing Considerations

All enhancements maintain compatibility with:

- **PlantCV** (Mozilla Public License 2.0) - Algorithm inspiration
- **OpenCV** (Apache 2.0) - Core library
- **Public Datasets** (CC BY 4.0, CC0) - Training data

New ML models and algorithms developed for this project will be released under MIT License to encourage adoption.

## Performance Targets

### Current Baseline (October 2025)

- Frame Processing: ~80-100ms per frame
- Memory Usage: ~500MB
- AI Request Rate: ~2-3 per minute
- Throughput: 10-15 plants per frame

### Post-Enhancement Targets (End of 2026)

- Frame Processing: <30ms per frame (GPU)
- Memory Usage: <300MB (optimized)
- AI Request Rate: Real-time (all frames)
- Throughput: 50+ plants per frame (multi-camera)

## Feedback & Roadmap Updates

This roadmap is reviewed quarterly. Submit feature requests via:

- GitHub Issues with `enhancement` label
- GitHub Discussions for larger proposals
- Direct email to maintainers

---

**Last Updated**: October 2, 2025  
**Next Review**: January 2, 2026
