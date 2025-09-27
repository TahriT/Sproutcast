#include "ai_inference.hpp"
#include <iostream>
#include <fstream>
#include <filesystem>
#include <algorithm>

#ifdef HAVE_ONNXRUNTIME
#include <onnxruntime_cxx_api.h>
#endif

struct AIInferenceEngine::ModelInstance {
#ifdef HAVE_ONNXRUNTIME
    std::unique_ptr<Ort::Session> session;
    std::unique_ptr<Ort::Env> env;
    Ort::MemoryInfo memoryInfo{nullptr};
    ModelConfig config;
    
    ModelInstance() : memoryInfo(Ort::MemoryInfo::CreateCpu(OrtArenaAllocator, OrtMemTypeDefault)) {
        env = std::make_unique<Ort::Env>(ORT_LOGGING_LEVEL_WARNING, "PlantVisionAI");
    }
#endif
    bool loaded = false;
    ModelType type = ModelType::NONE;
};

AIInferenceEngine::AIInferenceEngine() : impl_(std::make_unique<ModelInstance>()) {}

AIInferenceEngine::~AIInferenceEngine() = default;

bool AIInferenceEngine::isOnnxRuntimeAvailable() const {
#ifdef HAVE_ONNXRUNTIME
    return true;
#else
    return false;
#endif
}

bool AIInferenceEngine::loadModel(ModelType type, const ModelConfig& config) {
#ifdef HAVE_ONNXRUNTIME
    try {
        if (!std::filesystem::exists(config.modelPath)) {
            lastError_ = "Model file not found: " + config.modelPath;
            return false;
        }

        // Create session options
        Ort::SessionOptions sessionOptions;
        sessionOptions.SetIntraOpNumThreads(1);
        sessionOptions.SetGraphOptimizationLevel(GraphOptimizationLevel::ORT_ENABLE_EXTENDED);

        // Load model
        impl_->session = std::make_unique<Ort::Session>(*impl_->env, config.modelPath.c_str(), sessionOptions);
        impl_->config = config;
        impl_->type = type;
        impl_->loaded = true;

        std::cout << "Loaded ONNX model: " << config.modelPath << std::endl;
        return true;
    }
    catch (const std::exception& e) {
        lastError_ = "Failed to load ONNX model: " + std::string(e.what());
        impl_->loaded = false;
        return false;
    }
#else
    lastError_ = "ONNX Runtime not available - using Python fallback";
    return false;
#endif
}

bool AIInferenceEngine::isModelLoaded(ModelType type) const {
    return impl_->loaded && impl_->type == type;
}

void AIInferenceEngine::unloadModel(ModelType type) {
#ifdef HAVE_ONNXRUNTIME
    if (impl_->type == type) {
        impl_->session.reset();
        impl_->loaded = false;
        impl_->type = ModelType::NONE;
    }
#endif
}

AIInferenceEngine::DepthResult AIInferenceEngine::runDepthInference(const cv::Mat& image) {
    DepthResult result;
    
#ifdef HAVE_ONNXRUNTIME
    if (!impl_->loaded || impl_->type != ModelType::DEPTH_ESTIMATION) {
        lastError_ = "Depth estimation model not loaded";
        return result;
    }

    try {
        // Preprocess image
        cv::Mat processedImage = preprocessImage(image, impl_->config);
        
        // Convert to float vector
        std::vector<float> inputData = matToVector(processedImage);
        
        // Create input tensor
        std::vector<int64_t> inputShape = impl_->config.inputShape;
        Ort::Value inputTensor = Ort::Value::CreateTensor<float>(
            impl_->memoryInfo, 
            inputData.data(), 
            inputData.size(), 
            inputShape.data(), 
            inputShape.size()
        );
        
        // Run inference
        auto outputTensors = impl_->session->Run(
            Ort::RunOptions{nullptr},
            impl_->config.inputNames.data(),
            &inputTensor,
            1,
            impl_->config.outputNames.data(),
            impl_->config.outputNames.size()
        );
        
        // Extract output
        if (!outputTensors.empty() && outputTensors[0].IsTensor()) {
            auto& outputTensor = outputTensors[0];
            auto tensorInfo = outputTensor.GetTensorTypeAndShapeInfo();
            auto shape = tensorInfo.GetShape();
            
            float* rawOutput = outputTensor.GetTensorMutableData<float>();
            size_t outputSize = outputTensor.GetTensorTypeAndShapeInfo().GetElementCount();
            
            // Convert back to cv::Mat
            int height = shape.size() >= 2 ? static_cast<int>(shape[shape.size()-2]) : image.rows;
            int width = shape.size() >= 1 ? static_cast<int>(shape[shape.size()-1]) : image.cols;
            
            std::vector<float> depthVec(rawOutput, rawOutput + outputSize);
            result.depthMap = vectorToMat(depthVec, height, width);
            
            // Resize to original image size if needed
            if (result.depthMap.size() != image.size()) {
                cv::resize(result.depthMap, result.depthMap, image.size(), 0, 0, cv::INTER_CUBIC);
            }
            
            // Calculate min/max depth
            cv::minMaxLoc(result.depthMap, (double*)&result.minDepth, (double*)&result.maxDepth);
            result.success = true;
        }
        
    } catch (const std::exception& e) {
        lastError_ = "Depth inference failed: " + std::string(e.what());
        result.success = false;
    }
#else
    // Fallback to Python AI if ONNX not available
    if (pythonCallback_ && usePythonFallback()) {
        std::string tempImagePath = "/tmp/depth_input.jpg";
        cv::imwrite(tempImagePath, image);
        pythonCallback_("depth_estimation", tempImagePath);
        // Note: In a real implementation, you'd wait for the Python result
        lastError_ = "Using Python fallback for depth estimation";
    } else {
        lastError_ = "ONNX Runtime not available and no Python fallback configured";
    }
#endif

    return result;
}

std::vector<cv::Rect> AIInferenceEngine::runPlantDetection(const cv::Mat& image) {
    std::vector<cv::Rect> detections;
    
    // TODO: Implement plant detection model inference
    // For now, fall back to traditional OpenCV methods in the main processing pipeline
    
    return detections;
}

cv::Mat AIInferenceEngine::preprocessImage(const cv::Mat& input, const ModelConfig& config) {
    cv::Mat processed;
    
    // Resize to model input size
    if (config.inputShape.size() >= 3) {
        int height = static_cast<int>(config.inputShape[config.inputShape.size()-2]);
        int width = static_cast<int>(config.inputShape[config.inputShape.size()-1]);
        cv::resize(input, processed, cv::Size(width, height));
    } else {
        processed = input.clone();
    }
    
    // Convert to RGB if needed (ONNX models typically expect RGB)
    if (processed.channels() == 3) {
        cv::cvtColor(processed, processed, cv::COLOR_BGR2RGB);
    }
    
    // Normalize
    if (config.preprocessNormalization) {
        processed.convertTo(processed, CV_32F);
        processed = (processed - config.meanValue) * config.scaleValue;
    }
    
    return processed;
}

std::vector<float> AIInferenceEngine::matToVector(const cv::Mat& mat) {
    cv::Mat flatMat = mat.reshape(1, 1);
    std::vector<float> vec;
    flatMat.copyTo(vec);
    return vec;
}

cv::Mat AIInferenceEngine::vectorToMat(const std::vector<float>& vec, int height, int width) {
    cv::Mat mat(height, width, CV_32F);
    std::memcpy(mat.data, vec.data(), vec.size() * sizeof(float));
    return mat;
}

void AIInferenceEngine::setPythonFallback(std::function<void(const std::string&, const std::string&)> callback) {
    pythonCallback_ = callback;
}

bool AIInferenceEngine::usePythonFallback() const {
    return !isOnnxRuntimeAvailable() || !impl_->loaded;
}

std::string AIInferenceEngine::getLastError() const {
    return lastError_;
}

// AIModelManager implementation
AIModelManager::AIModelManager(const std::string& modelsDir) : modelsDir_(modelsDir) {
    std::filesystem::create_directories(modelsDir_);
}

AIModelManager::ModelInfo AIModelManager::getMiDaSSmallModel() {
    return {
        "midas_small",
        "https://github.com/isl-org/MiDaS/releases/download/v3_1_small/model-small.onnx",
        "midas_small.onnx",
        11030935,  // ~11MB
        ""  // Checksum would be calculated on first download
    };
}

AIModelManager::ModelInfo AIModelManager::getPlantDetectionModel() {
    return {
        "plant_detection",
        "https://github.com/ultralytics/yolov5/releases/download/v7.0/yolov5s.onnx",
        "plant_detection.onnx", 
        28000000,  // ~28MB
        ""
    };
}

bool AIModelManager::downloadModel(const ModelInfo& modelInfo) {
    std::string localPath = getModelPath(modelInfo.name);
    
    if (progressCallback_) {
        progressCallback_(modelInfo.name, 0, "Starting download...");
    }
    
    bool success = downloadFile(modelInfo.url, localPath);
    
    if (success && progressCallback_) {
        progressCallback_(modelInfo.name, 100, "Download complete");
    } else if (progressCallback_) {
        progressCallback_(modelInfo.name, -1, "Download failed");
    }
    
    return success;
}

bool AIModelManager::verifyModel(const ModelInfo& modelInfo) {
    std::string localPath = getModelPath(modelInfo.name);
    
    if (!std::filesystem::exists(localPath)) {
        return false;
    }
    
    // Check file size
    auto fileSize = std::filesystem::file_size(localPath);
    if (modelInfo.expectedSize > 0 && fileSize != modelInfo.expectedSize) {
        // Allow some tolerance for size differences
        if (std::abs(static_cast<long>(fileSize) - static_cast<long>(modelInfo.expectedSize)) > modelInfo.expectedSize * 0.1) {
            return false;
        }
    }
    
    return true;
}

std::string AIModelManager::getModelPath(const std::string& modelName) {
    return modelsDir_ + "/" + modelName + ".onnx";
}

void AIModelManager::setProgressCallback(ProgressCallback callback) {
    progressCallback_ = callback;
}

bool AIModelManager::downloadFile(const std::string& url, const std::string& filepath) {
    // Simple file download implementation
    // In a production system, you'd use a proper HTTP client like curl or libcurl
    std::string command = "wget -O \"" + filepath + "\" \"" + url + "\"";
    return system(command.c_str()) == 0;
}

std::string AIModelManager::calculateChecksum(const std::string& filepath) {
    // Placeholder - would implement SHA256 or similar
    return "";
}
