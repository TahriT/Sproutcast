#pragma once

#include <opencv2/opencv.hpp>
#include <nlohmann/json.hpp>
#include <string>
#include <chrono>

/**
 * @brief Consolidated OpenCV vision processing for PlantVision
 * 
 * This class handles all OpenCV-based image processing operations that were
 * previously split between C++ and Python components. It provides a unified
 * interface for plant analysis while maintaining compatibility with the AI module.
 */
class VisionProcessor {
public:
    struct ColorAnalysis {
        cv::Scalar mean_hsv;
        cv::Scalar mean_lab;
        cv::Scalar mean_bgr;
        cv::Scalar std_hsv;
        cv::Scalar std_lab;
        cv::Scalar std_bgr;
        double green_ratio;
        double ndvi;
        double exg;
        double health_indicator;
        int total_green_pixels;
    };

    struct ChangeDetectionResult {
        bool significant_change;
        double hue_change;
        double saturation_change;
        double green_ratio_change;
        double total_area_change;
        int plant_count_change;
        double motion_magnitude;
        std::string change_reason;
    };

    struct BasicMetrics {
        ColorAnalysis color_analysis;
        ChangeDetectionResult change_detection;
        double timestamp;
        int frame_number;
        bool ai_analysis_required;
        std::string processing_notes;
    };

    struct AIRequestData {
        std::string image_path;
        std::string model_preference;
        bool depth_analysis_required;
        bool classification_required;
        cv::Rect roi; // Region of interest for AI processing
        double confidence_threshold;
    };

    VisionProcessor();
    ~VisionProcessor();

    /**
     * @brief Process frame for basic metrics and change detection (C++ only)
     * This replaces the duplicate OpenCV processing currently in Python AI module
     */
    BasicMetrics processBasicMetrics(const cv::Mat& frame);

    /**
     * @brief Detect significant changes between frames for intelligent AI triggering
     * Replaces the change detection logic currently in Python
     */
    ChangeDetectionResult detectChanges(const cv::Mat& current_frame, const cv::Mat& previous_frame);

    /**
     * @brief Create mask for plant regions using optimized OpenCV operations
     * Consolidates green masking logic from both Python and C++
     */
    cv::Mat createPlantMask(const cv::Mat& frame, bool enhanced_sensitivity = false);

    /**
     * @brief Perform comprehensive color analysis using multiple color spaces
     * Replaces redundant color analysis in Python AI module
     */
    ColorAnalysis analyzeColors(const cv::Mat& frame, const cv::Mat& mask);

    /**
     * @brief Generate AI analysis request when needed
     * Creates structured request for Python AI module with minimal data
     */
    AIRequestData generateAIRequest(const cv::Mat& frame, const BasicMetrics& metrics);

    /**
     * @brief Save processed data for AI module consumption
     * Efficient data transfer interface between C++ and Python
     */
    bool saveAIRequestData(const AIRequestData& request, const std::string& request_id);

    /**
     * @brief Load AI analysis results back from Python module
     * Clean interface for receiving AI inference results
     */
    nlohmann::json loadAIResults(const std::string& request_id);

    /**
     * @brief Configure change detection sensitivity and thresholds
     */
    void configureChangeDetection(double hue_threshold = 10.0, 
                                 double saturation_threshold = 15.0,
                                 double green_ratio_threshold = 0.08,
                                 double area_change_threshold = 0.15);

    /**
     * @brief Enable/disable debug visualization and logging
     */
    void setDebugMode(bool enabled, const std::string& debug_output_path = "/app/data/debug/");

private:
    // Configuration
    struct Config {
        // Change detection thresholds
        double hue_threshold = 10.0;
        double saturation_threshold = 15.0;
        double green_ratio_threshold = 0.08;
        double area_change_threshold = 0.15;
        double motion_threshold = 500.0;
        
        // Processing parameters
        cv::Scalar hsv_lower_bound = cv::Scalar(25, 40, 40);
        cv::Scalar hsv_upper_bound = cv::Scalar(85, 255, 255);
        cv::Size morph_kernel_size = cv::Size(5, 5);
        double min_contour_area = 50.0;
        
        // Performance settings
        bool enable_motion_detection = true;
        bool enable_morphological_processing = true;
        int max_processing_time_ms = 100; // Fail-safe for real-time processing
    } config_;

    // State management
    cv::Mat previous_frame_;
    cv::Mat baseline_frame_;
    BasicMetrics baseline_metrics_;
    int frame_counter_;
    bool baseline_established_;
    std::chrono::steady_clock::time_point last_ai_request_;
    
    // Debug support
    bool debug_mode_;
    std::string debug_path_;

    // Internal processing methods
    cv::Mat preprocessFrame(const cv::Mat& frame);
    std::vector<std::vector<cv::Point>> findPlantContours(const cv::Mat& mask);
    double calculateMotionMagnitude(const cv::Mat& current, const cv::Mat& previous);
    cv::Scalar calculateColorMean(const cv::Mat& frame, const cv::Mat& mask, int color_space);
    cv::Scalar calculateColorStd(const cv::Mat& frame, const cv::Mat& mask, int color_space);
    double calculateNDVI(const cv::Mat& frame, const cv::Mat& mask);
    double calculateEXG(const cv::Mat& frame, const cv::Mat& mask);
    bool establishBaseline(const cv::Mat& frame);
    void saveDebugImages(const cv::Mat& frame, const cv::Mat& mask, const std::string& suffix);
    void logMetrics(const BasicMetrics& metrics);

    // Data directory paths
    std::string data_dir_ = "/app/data";
    std::string ai_requests_dir_ = "/app/data/ai_requests";
    std::string ai_results_dir_ = "/app/data/ai_results";
};
