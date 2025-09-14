#pragma once

#include <opencv2/opencv.hpp>
#include <vector>
#include <string>
#include <chrono>

enum class PlantType {
    SPROUT,
    PLANT
};

enum class GrowthStage {
    COTYLEDON,
    FIRST_LEAVES, 
    EARLY_VEGETATIVE,
    VEGETATIVE,
    FLOWERING,
    FRUITING,
    DORMANT
};

struct PlantInstance {
    PlantType type;
    GrowthStage stage;
    cv::Rect boundingBox;
    double areaPixels;
    double areaCm2;
    double heightCm;
    double widthCm;
    int leafCount;
    int petalCount;
    int budCount;
    int fruitCount;
    cv::Scalar meanColor;
    cv::Scalar stdColor;
    double healthScore;
    std::string classification;
    std::vector<cv::Point> contour;
    cv::Mat cropImage;
    cv::Mat annotatedImage;

    // Enhanced morphological analysis fields
    int branchCount = 0;
    int tipCount = 0;
    double stemLengthCm = 0.0;
    double solidity = 0.0;
    double eccentricity = 0.0;
    double circularity = 0.0;
    double compactness = 0.0;
    double perimeterCm = 0.0;
    double aspectRatio = 0.0;
    double extent = 0.0;
    double orientation = 0.0;
    double convexity = 0.0;
    cv::Point2f centroid = cv::Point2f(0, 0);
    std::vector<cv::Point> branchPoints;
    std::vector<cv::Point> tipPoints;

    // Enhanced color analysis
    double ndvi = 0.0;
    double exg = 0.0;

    // Disease detection fields
    int brownSpotCount = 0;
    int yellowAreaCount = 0;
    std::vector<cv::Point> brownSpotLocations;
    std::vector<cv::Point> yellowAreaLocations;
};

struct PlantAnalysisResult {
    double scalePxPerCm;
    int totalInstanceCount;
    int sproutCount;
    int plantCount;
    double totalAreaPixels;
    double totalAreaCm2;
    std::vector<PlantInstance> instances;
    cv::Mat annotatedFrame;
    std::string analysisTimestamp;
    double averageHealth = 0.0;
    double processingTimeMs = 0.0;
};

// Main analysis function that classifies and processes both sprouts and plants
PlantAnalysisResult analyzePlants(const cv::Mat &frameBgr, int thresholdValue, double scalePxPerCm);

// Classification functions
PlantType classifyPlantType(const cv::Mat &roi, const cv::Rect &bbox, double areaPixels, double scalePxPerCm);
GrowthStage determineGrowthStage(PlantType type, const cv::Mat &roi, double areaPixels, int leafCount);

// Specialized processing pipelines
PlantInstance processSprout(const cv::Mat &frame, const cv::Rect &bbox, const std::vector<cv::Point> &contour, double scalePxPerCm);
PlantInstance processPlant(const cv::Mat &frame, const cv::Rect &bbox, const std::vector<cv::Point> &contour, double scalePxPerCm);

// Legacy compatibility function
struct LeafAreaResult {
    double areaPixels;
    double areaCm2;
    double scalePxPerCm;
    int contourCount;
    std::vector<double> perContourAreaPx;
    std::vector<cv::Rect> perContourBBox;
    std::vector<std::vector<cv::Point>> contours;
    int totalLeafCount;
    std::vector<int> perContourLeafCount;
};

LeafAreaResult estimateLeafArea(const cv::Mat &frameBgr, int thresholdValue, double scalePxPerCm);

