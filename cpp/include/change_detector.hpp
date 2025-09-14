#pragma once

#include <opencv2/core.hpp>
#include <vector>
#include <string>
#include <chrono>

// Forward declaration
struct PlantInstance;

#include <opencv2/core.hpp>
#include <vector>
#include <string>
#include <chrono>

struct ChangeDetectionMetrics {
    double totalAreaChange = 0.0;
    int plantCountChange = 0;
    double avgColorChangeH = 0.0;
    double avgColorChangeS = 0.0;
    double avgColorChangeV = 0.0;
    double morphologyChange = 0.0;  // Based on shape descriptor changes
    bool significantChange = false;
    std::chrono::steady_clock::time_point timestamp;
};

class ChangeDetector {
private:
    struct BaselineData {
        int plantCount = 0;
        double totalArea = 0.0;
        cv::Scalar avgColor = cv::Scalar(0, 0, 0);
        double avgSolidity = 0.0;
        double avgCircularity = 0.0;
        double avgEccentricity = 0.0;
        bool isValid = false;
    };
    
    BaselineData baseline_;
    std::chrono::steady_clock::time_point lastUpdate_;
    
    // Change detection thresholds
    static constexpr double AREA_CHANGE_THRESHOLD = 0.10;  // 10% area change
    static constexpr int COUNT_CHANGE_THRESHOLD = 1;       // 1 plant difference
    static constexpr double COLOR_CHANGE_THRESHOLD_H = 8.0;
    static constexpr double COLOR_CHANGE_THRESHOLD_S = 12.0;
    static constexpr double COLOR_CHANGE_THRESHOLD_V = 15.0;
    static constexpr double MORPHOLOGY_CHANGE_THRESHOLD = 0.08;

public:
    ChangeDetector() : lastUpdate_(std::chrono::steady_clock::now()) {}
    
    // Analyze current frame and detect significant changes
    ChangeDetectionMetrics analyzeFrame(const std::vector<PlantInstance>& instances);
    
    // Force update baseline (e.g., after significant changes)
    void updateBaseline(const std::vector<PlantInstance>& instances);
    
    // Reset detector (e.g., when system restarts)
    void reset();
    
    // Check if baseline is established
    bool hasBaseline() const { return baseline_.isValid; }
    
    // Write change detection results to file for AI component
    bool writeChangeSignal(const ChangeDetectionMetrics& metrics, const std::string& filePath = "/app/data/change_signal.json") const;

private:
    BaselineData computeBaseline(const std::vector<PlantInstance>& instances) const;
    double calculateMorphologyScore(const std::vector<PlantInstance>& instances) const;
};
