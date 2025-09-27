#pragma once

#include <opencv2/opencv.hpp>
#include <string>
#include <vector>
#include <memory>
#include <functional>

#ifdef HAVE_ONNXRUNTIME
#include <onnxruntime_cxx_api.h>
#endif

/**
 * AI Inference Engine for PlantVision
 * Provides C++ ONNX runtime integration for plant analysis models
 */
class AIInferenceEngine {
public:
    enum class ModelType {
        DEPTH_ESTIMATION,  // MiDaS depth estimation
        PLANT_DETECTION,   // Plant/vegetation detection
        DISEASE_DETECTION, // Plant disease classification
        NONE
    };

    struct ModelConfig {
        std::string modelPath;
        std::vector<int64_t> inputShape;
        std::vector<std::string> inputNames;
        std::vector<std::string> outputNames;
        bool preprocessNormalization = true;
        float meanValue = 127.5f;
        float scaleValue = 1.0f / 127.5f;
    };

    struct DepthResult {
        cv::Mat depthMap;
        float minDepth;
        float maxDepth;
        bool success = false;
    };

    AIInferenceEngine();
    ~AIInferenceEngine();

    // Model management
    bool loadModel(ModelType type, const ModelConfig& config);
    bool isModelLoaded(ModelType type) const;
    void unloadModel(ModelType type);

    // Inference methods
    DepthResult runDepthInference(const cv::Mat& image);
    std::vector<cv::Rect> runPlantDetection(const cv::Mat& image);
    
    // Utility methods
    bool isOnnxRuntimeAvailable() const;
    std::string getLastError() const;
    
    // Fallback to Python AI if ONNX not available
    void setPythonFallback(std::function<void(const std::string&, const std::string&)> callback);
    bool usePythonFallback() const;

private:
    struct ModelInstance;
    std::unique_ptr<ModelInstance> impl_;
    
    std::string lastError_;
    std::function<void(const std::string&, const std::string&)> pythonCallback_;
    
    // Helper methods
    cv::Mat preprocessImage(const cv::Mat& input, const ModelConfig& config);
    std::vector<float> matToVector(const cv::Mat& mat);
    cv::Mat vectorToMat(const std::vector<float>& vec, int height, int width);
};

/**
 * Model Manager - handles downloading and caching of ONNX models
 */
class AIModelManager {
public:
    struct ModelInfo {
        std::string name;
        std::string url;
        std::string localPath;
        size_t expectedSize;
        std::string checksum;
    };

    AIModelManager(const std::string& modelsDir = "/app/models");

    // Download and verify models
    bool downloadModel(const ModelInfo& modelInfo);
    bool verifyModel(const ModelInfo& modelInfo);
    std::string getModelPath(const std::string& modelName);
    
    // Progress callback for downloads
    using ProgressCallback = std::function<void(const std::string&, int, const std::string&)>;
    void setProgressCallback(ProgressCallback callback);

    // Pre-configured model definitions
    static ModelInfo getMiDaSSmallModel();
    static ModelInfo getPlantDetectionModel();

private:
    std::string modelsDir_;
    ProgressCallback progressCallback_;
    
    bool downloadFile(const std::string& url, const std::string& filepath);
    std::string calculateChecksum(const std::string& filepath);
};
