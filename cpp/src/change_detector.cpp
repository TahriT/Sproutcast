#include "change_detector.hpp"
#include "leaf_area.hpp"
#include <nlohmann/json.hpp>
#include <fstream>
#include <cmath>
#include <algorithm>

using json = nlohmann::json;

ChangeDetectionMetrics ChangeDetector::analyzeFrame(const std::vector<PlantInstance>& instances) {
    ChangeDetectionMetrics metrics;
    metrics.timestamp = std::chrono::steady_clock::now();
    
    // Compute current frame baseline
    BaselineData current = computeBaseline(instances);
    
    // If no baseline exists, establish one
    if (!baseline_.isValid) {
        baseline_ = current;
        baseline_.isValid = true;
        return metrics; // No change on first frame
    }
    
    // Calculate changes
    if (baseline_.totalArea > 0) {
        metrics.totalAreaChange = std::abs(current.totalArea - baseline_.totalArea) / baseline_.totalArea;
    }
    
    metrics.plantCountChange = std::abs(current.plantCount - baseline_.plantCount);
    
    // Color changes in HSV space
    metrics.avgColorChangeH = std::abs(current.avgColor[0] - baseline_.avgColor[0]);
    metrics.avgColorChangeS = std::abs(current.avgColor[1] - baseline_.avgColor[1]);
    metrics.avgColorChangeV = std::abs(current.avgColor[2] - baseline_.avgColor[2]);
    
    // Morphology change (based on shape descriptors)
    metrics.morphologyChange = std::abs(calculateMorphologyScore(instances) - 
                                       calculateMorphologyScore(std::vector<PlantInstance>()));
    
    // Determine if change is significant
    metrics.significantChange = (
        metrics.totalAreaChange > AREA_CHANGE_THRESHOLD ||
        metrics.plantCountChange >= COUNT_CHANGE_THRESHOLD ||
        metrics.avgColorChangeH > COLOR_CHANGE_THRESHOLD_H ||
        metrics.avgColorChangeS > COLOR_CHANGE_THRESHOLD_S ||
        metrics.avgColorChangeV > COLOR_CHANGE_THRESHOLD_V ||
        metrics.morphologyChange > MORPHOLOGY_CHANGE_THRESHOLD
    );
    
    return metrics;
}

void ChangeDetector::updateBaseline(const std::vector<PlantInstance>& instances) {
    baseline_ = computeBaseline(instances);
    baseline_.isValid = true;
    lastUpdate_ = std::chrono::steady_clock::now();
}

void ChangeDetector::reset() {
    baseline_ = BaselineData();
    lastUpdate_ = std::chrono::steady_clock::now();
}

bool ChangeDetector::writeChangeSignal(const ChangeDetectionMetrics& metrics, const std::string& filePath) const {
    try {
        json changeData;
        changeData["timestamp"] = std::chrono::duration_cast<std::chrono::milliseconds>(
            metrics.timestamp.time_since_epoch()).count();
        changeData["significant_change"] = metrics.significantChange;
        changeData["changes"] = {
            {"total_area_change", metrics.totalAreaChange},
            {"plant_count_change", metrics.plantCountChange},
            {"avg_color_change_h", metrics.avgColorChangeH},
            {"avg_color_change_s", metrics.avgColorChangeS},
            {"avg_color_change_v", metrics.avgColorChangeV},
            {"morphology_change", metrics.morphologyChange}
        };
        changeData["thresholds"] = {
            {"area_threshold", AREA_CHANGE_THRESHOLD},
            {"count_threshold", COUNT_CHANGE_THRESHOLD},
            {"color_h_threshold", COLOR_CHANGE_THRESHOLD_H},
            {"color_s_threshold", COLOR_CHANGE_THRESHOLD_S},
            {"color_v_threshold", COLOR_CHANGE_THRESHOLD_V},
            {"morphology_threshold", MORPHOLOGY_CHANGE_THRESHOLD}
        };
        
        std::ofstream file(filePath);
        if (!file.is_open()) return false;
        
        file << changeData.dump(4);
        return true;
    } catch (const std::exception& e) {
        return false;
    }
}

ChangeDetector::BaselineData ChangeDetector::computeBaseline(const std::vector<PlantInstance>& instances) const {
    BaselineData baseline;
    if (instances.empty()) return baseline;
    
    baseline.plantCount = static_cast<int>(instances.size());
    baseline.totalArea = 0.0;
    
    // Accumulate values for averaging
    cv::Scalar colorSum(0, 0, 0);
    double soliditySum = 0.0;
    double circularitySum = 0.0;
    double eccentricitySum = 0.0;
    int validInstances = 0;
    
    for (const auto& instance : instances) {
        baseline.totalArea += instance.areaPixels;
        
        // Convert BGR mean color to HSV for better change detection
        cv::Mat colorMat(1, 1, CV_8UC3, cv::Scalar(instance.meanColor[0], instance.meanColor[1], instance.meanColor[2]));
        cv::Mat hsvMat;
        cv::cvtColor(colorMat, hsvMat, cv::COLOR_BGR2HSV);
        cv::Scalar hsvColor = cv::mean(hsvMat);
        
        colorSum[0] += hsvColor[0];
        colorSum[1] += hsvColor[1];
        colorSum[2] += hsvColor[2];
        
        soliditySum += instance.solidity;
        circularitySum += instance.circularity;
        eccentricitySum += instance.eccentricity;
        validInstances++;
    }
    
    if (validInstances > 0) {
        baseline.avgColor = cv::Scalar(
            colorSum[0] / validInstances,
            colorSum[1] / validInstances,
            colorSum[2] / validInstances
        );
        baseline.avgSolidity = soliditySum / validInstances;
        baseline.avgCircularity = circularitySum / validInstances;
        baseline.avgEccentricity = eccentricitySum / validInstances;
        baseline.isValid = true;
    }
    
    return baseline;
}

double ChangeDetector::calculateMorphologyScore(const std::vector<PlantInstance>& instances) const {
    if (instances.empty()) return 0.0;
    
    double score = 0.0;
    for (const auto& instance : instances) {
        // Combine multiple morphological features into a single score
        score += instance.solidity * 0.3 + 
                 instance.circularity * 0.3 + 
                 (1.0 - instance.eccentricity) * 0.2 +  // Lower eccentricity = more circular
                 (instance.compactness * 0.2);
    }
    
    return score / instances.size();
}
