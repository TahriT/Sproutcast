#include "leaf_area.hpp"
#include "morphology_analysis.hpp"
#include <opencv2/opencv.hpp>
#include <map>
#include <chrono>
#include <iomanip>
#include <sstream>
#include <cmath>
#include <algorithm>

using namespace PlantVision::Morphology;

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

// Base64 encoding function
static std::string base64_encode(unsigned char const* bytes_to_encode, unsigned int in_len) {
    std::string ret;
    int i = 0;
    int j = 0;
    unsigned char char_array_3[3];
    unsigned char char_array_4[4];

    const std::string chars_to_encode = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";

    while (in_len--) {
        char_array_3[i++] = *(bytes_to_encode++);
        if (i == 3) {
            char_array_4[0] = (char_array_3[0] & 0xfc) >> 2;
            char_array_4[1] = ((char_array_3[0] & 0x03) << 4) + ((char_array_3[1] & 0xf0) >> 4);
            char_array_4[2] = ((char_array_3[1] & 0x0f) << 2) + ((char_array_3[2] & 0xc0) >> 6);
            char_array_4[3] = char_array_3[2] & 0x3f;

            for(i = 0; (i <4) ; i++)
                ret += chars_to_encode[char_array_4[i]];
            i = 0;
        }
    }

    if (i) {
        for(j = i; j < 3; j++)
            char_array_3[j] = '\0';

        char_array_4[0] = (char_array_3[0] & 0xfc) >> 2;
        char_array_4[1] = ((char_array_3[0] & 0x03) << 4) + ((char_array_3[1] & 0xf0) >> 4);
        char_array_4[2] = ((char_array_3[1] & 0x0f) << 2) + ((char_array_3[2] & 0xc0) >> 6);
        char_array_4[3] = char_array_3[2] & 0x3f;

        for (j = 0; (j < i + 1); j++)
            ret += chars_to_encode[char_array_4[j]];

        while((i++ < 3))
            ret += '=';
    }

    return ret;
}

// Configuration constants
static const double SPROUT_SIZE_THRESHOLD = 5000.0; // pixels
static const double SPROUT_HEIGHT_THRESHOLD = 8.0;  // cm

static std::string getCurrentTimestamp() {
    auto now = std::chrono::system_clock::now();
    auto time_t = std::chrono::system_clock::to_time_t(now);
    std::stringstream ss;
    ss << std::put_time(std::localtime(&time_t), "%Y-%m-%dT%H:%M:%S");
    return ss.str();
}

static void watershedInstances(const cv::Mat &mask, std::vector<std::vector<cv::Point>> &instances) {
    if (mask.empty()) return;
    cv::Mat dist;
    cv::distanceTransform(mask, dist, cv::DIST_L2, 3);
    cv::normalize(dist, dist, 0, 1.0, cv::NORM_MINMAX);
    cv::threshold(dist, dist, 0.4, 1.0, cv::THRESH_BINARY);
    cv::Mat dist8u;
    dist.convertTo(dist8u, CV_8U, 255);
    std::vector<std::vector<cv::Point>> contours;
    cv::findContours(dist8u, contours, cv::RETR_EXTERNAL, cv::CHAIN_APPROX_SIMPLE);
    cv::Mat markers = cv::Mat::zeros(mask.size(), CV_32S);
    for (int i = 0; i < static_cast<int>(contours.size()); ++i) {
        cv::drawContours(markers, contours, i, cv::Scalar(i + 1), -1);
    }
    cv::circle(markers, cv::Point(5,5), 3, cv::Scalar(255), -1);
    cv::Mat mask3c; cv::cvtColor(mask, mask3c, cv::COLOR_GRAY2BGR);
    cv::watershed(mask3c, markers);
    std::map<int, std::vector<cv::Point>> idToPts;
    for (int y = 0; y < markers.rows; ++y) {
        const int* row = markers.ptr<int>(y);
        for (int x = 0; x < markers.cols; ++x) {
            int id = row[x];
            if (id > 1) idToPts[id].push_back(cv::Point(x,y));
        }
    }
    for (auto &kv : idToPts) {
        std::vector<cv::Point> hull;
        if (!kv.second.empty()) {
            cv::convexHull(kv.second, hull);
            if (!hull.empty()) instances.push_back(hull);
        }
    }
}

static int countLeavesInContour(const cv::Mat &frame, const std::vector<cv::Point> &contour, bool isSprout) {
    if (contour.empty()) return 0;
    
    cv::Mat mask = cv::Mat::zeros(frame.size(), CV_8UC1);
    cv::fillPoly(mask, std::vector<std::vector<cv::Point>>{contour}, cv::Scalar(255));
    
    cv::Rect bbox = cv::boundingRect(contour);
    cv::Mat roi = frame(bbox);
    cv::Mat maskRoi = mask(bbox);
    
    cv::Mat maskedRoi;
    roi.copyTo(maskedRoi, maskRoi);
    
    cv::Mat hsv;
    cv::cvtColor(maskedRoi, hsv, cv::COLOR_BGR2HSV);
    
    cv::Mat leafMask;
    if (isSprout) {
        // More sensitive detection for sprouts - broader green range
        cv::inRange(hsv, cv::Scalar(20, 30, 30), cv::Scalar(90, 255, 255), leafMask);
    } else {
        // Standard detection for mature plants
        cv::inRange(hsv, cv::Scalar(25, 40, 40), cv::Scalar(85, 255, 255), leafMask);
    }
    
    cv::Mat kernel = cv::getStructuringElement(cv::MORPH_ELLIPSE, cv::Size(3, 3));
    cv::morphologyEx(leafMask, leafMask, cv::MORPH_OPEN, kernel);
    cv::morphologyEx(leafMask, leafMask, cv::MORPH_CLOSE, kernel);
    
    std::vector<std::vector<cv::Point>> leafContours;
    cv::findContours(leafMask, leafContours, cv::RETR_EXTERNAL, cv::CHAIN_APPROX_SIMPLE);
    
    int leafCount = 0;
    for (const auto &leafContour : leafContours) {
        double area = cv::contourArea(leafContour);
        double minArea = isSprout ? 10.0 : 20.0;  // Lower threshold for sprouts
        double maxArea = isSprout ? 1000.0 : 5000.0;
        
        if (area > minArea && area < maxArea) {
            cv::Rect rect = cv::boundingRect(leafContour);
            double aspectRatio = static_cast<double>(rect.width) / rect.height;
            if (aspectRatio > 0.2 && aspectRatio < 5.0) {
                leafCount++;
            }
        }
    }
    
    return leafCount;
}

// ========== ENHANCED MORPHOLOGICAL ANALYSIS ==========
// Branch and tip analysis inspired by PlantCV morphology module

static cv::Mat skeletonize(const cv::Mat& binaryMask) {
    cv::Mat skeleton = cv::Mat::zeros(binaryMask.size(), CV_8UC1);
    cv::Mat temp, eroded;
    cv::Mat element = cv::getStructuringElement(cv::MORPH_CROSS, cv::Size(3, 3));
    
    binaryMask.copyTo(temp);
    
    do {
        cv::erode(temp, eroded, element);
        cv::Mat opening;
        cv::morphologyEx(eroded, opening, cv::MORPH_OPEN, element);
        cv::Mat subset = eroded - opening;
        cv::bitwise_or(skeleton, subset, skeleton);
        eroded.copyTo(temp);
    } while (cv::countNonZero(temp) > 0);
    
    return skeleton;
}

static std::vector<cv::Point> findBranchPoints(const cv::Mat& skeleton) {
    std::vector<cv::Point> branchPoints;
    
    // 3x3 kernel for neighbor counting
    for (int y = 1; y < skeleton.rows - 1; y++) {
        for (int x = 1; x < skeleton.cols - 1; x++) {
            if (skeleton.at<uchar>(y, x) == 0) continue;
            
            // Count 8-connected neighbors
            int neighbors = 0;
            for (int dy = -1; dy <= 1; dy++) {
                for (int dx = -1; dx <= 1; dx++) {
                    if (dy == 0 && dx == 0) continue;
                    if (skeleton.at<uchar>(y + dy, x + dx) > 0) {
                        neighbors++;
                    }
                }
            }
            
            // Branch points have 3 or more neighbors
            if (neighbors >= 3) {
                branchPoints.push_back(cv::Point(x, y));
            }
        }
    }
    
    return branchPoints;
}

static std::vector<cv::Point> findTipPoints(const cv::Mat& skeleton) {
    std::vector<cv::Point> tipPoints;
    
    // 3x3 kernel for neighbor counting
    for (int y = 1; y < skeleton.rows - 1; y++) {
        for (int x = 1; x < skeleton.cols - 1; x++) {
            if (skeleton.at<uchar>(y, x) == 0) continue;
            
            // Count 8-connected neighbors
            int neighbors = 0;
            for (int dy = -1; dy <= 1; dy++) {
                for (int dx = -1; dx <= 1; dx++) {
                    if (dy == 0 && dx == 0) continue;
                    if (skeleton.at<uchar>(y + dy, x + dx) > 0) {
                        neighbors++;
                    }
                }
            }
            
            // Tip points have exactly 1 neighbor
            if (neighbors == 1) {
                tipPoints.push_back(cv::Point(x, y));
            }
        }
    }
    
    return tipPoints;
}

static double calculateSolidity(const std::vector<cv::Point>& contour) {
    if (contour.empty()) return 0.0;
    
    double area = cv::contourArea(contour);
    std::vector<cv::Point> hull;
    cv::convexHull(contour, hull);
    double hullArea = cv::contourArea(hull);
    
    return (hullArea > 0) ? (area / hullArea) : 0.0;
}

static double calculateEccentricity(const cv::RotatedRect& ellipse) {
    double a = std::max(ellipse.size.width, ellipse.size.height) / 2.0;  // semi-major axis
    double b = std::min(ellipse.size.width, ellipse.size.height) / 2.0;  // semi-minor axis
    
    if (a == 0) return 0.0;
    
    double eccentricity = std::sqrt(1.0 - (b * b) / (a * a));
    return eccentricity;
}

static double calculateCircularity(double area, double perimeter) {
    if (perimeter == 0) return 0.0;
    return (4.0 * M_PI * area) / (perimeter * perimeter);
}

static double calculateCompactness(double area, double perimeter) {
    if (perimeter == 0) return 0.0;
    return std::sqrt((4.0 * area) / M_PI) / (perimeter / M_PI);
}

static double calculateLongestPath(const cv::Mat& skeleton) {
    std::vector<std::vector<cv::Point>> contours;
    cv::findContours(skeleton, contours, cv::RETR_EXTERNAL, cv::CHAIN_APPROX_NONE);
    
    double maxLength = 0.0;
    for (const auto& contour : contours) {
        if (contour.size() < 2) continue;
        
        double length = cv::arcLength(contour, false);
        maxLength = std::max(maxLength, length);
    }
    
    return maxLength;
}

static double calculateAspectRatio(const cv::Rect& boundingBox) {
    if (boundingBox.height == 0) return 0.0;
    return static_cast<double>(boundingBox.width) / static_cast<double>(boundingBox.height);
}

static double calculateExtent(double contourArea, const cv::Rect& boundingBox) {
    double rectArea = boundingBox.width * boundingBox.height;
    if (rectArea == 0) return 0.0;
    return contourArea / rectArea;
}

static double calculateOrientation(const std::vector<cv::Point>& contour) {
    if (contour.size() < 5) return 0.0;
    
    cv::RotatedRect ellipse = cv::fitEllipse(contour);
    return ellipse.angle;
}

static double calculateConvexity(const std::vector<cv::Point>& contour) {
    if (contour.empty()) return 0.0;
    
    double contourPerimeter = cv::arcLength(contour, true);
    std::vector<cv::Point> hull;
    cv::convexHull(contour, hull);
    double hullPerimeter = cv::arcLength(hull, true);
    
    return (hullPerimeter > 0) ? (contourPerimeter / hullPerimeter) : 0.0;
}

static cv::Point2f calculateCentroid(const std::vector<cv::Point>& contour) {
    cv::Moments moments = cv::moments(contour);
    if (moments.m00 == 0) return cv::Point2f(0, 0);
    
    return cv::Point2f(moments.m10 / moments.m00, moments.m01 / moments.m00);
}

// Enhanced color analysis with vegetation indices
static double calculateNDVI(const cv::Mat& image, const cv::Mat& mask) {
    cv::Mat imageFloat, maskFloat;
    image.convertTo(imageFloat, CV_32F, 1.0/255.0);
    mask.convertTo(maskFloat, CV_32F, 1.0/255.0);
    
    std::vector<cv::Mat> bgr;
    cv::split(imageFloat, bgr);
    
    cv::Mat nir = bgr[1];  // Use green as proxy for NIR
    cv::Mat red = bgr[2];
    
    cv::Mat ndvi = (nir - red) / (nir + red + 1e-10);
    cv::Scalar meanNDVI = cv::mean(ndvi, mask);
    
    return meanNDVI[0];
}

static double calculateEXG(const cv::Mat& image, const cv::Mat& mask) {
    cv::Mat imageFloat;
    image.convertTo(imageFloat, CV_32F, 1.0/255.0);
    
    std::vector<cv::Mat> bgr;
    cv::split(imageFloat, bgr);
    
    cv::Mat exg = 2.0 * bgr[1] - bgr[2] - bgr[0];  // 2*G - R - B
    cv::Scalar meanEXG = cv::mean(exg, mask);
    
    return meanEXG[0];
}

// Disease detection functions
static std::vector<cv::Point> detectBrownSpots(const cv::Mat& image, const cv::Mat& mask) {
    std::vector<cv::Point> brownSpots;
    
    cv::Mat hsv;
    cv::cvtColor(image, hsv, cv::COLOR_BGR2HSV);
    
    // Brown color range in HSV
    cv::Mat brownMask;
    cv::inRange(hsv, cv::Scalar(5, 50, 20), cv::Scalar(15, 255, 200), brownMask);
    
    // Apply plant mask
    cv::Mat maskedBrown;
    cv::bitwise_and(brownMask, mask, maskedBrown);
    
    std::vector<std::vector<cv::Point>> contours;
    cv::findContours(maskedBrown, contours, cv::RETR_EXTERNAL, cv::CHAIN_APPROX_SIMPLE);
    
    for (const auto& contour : contours) {
        double area = cv::contourArea(contour);
        if (area > 10.0) {  // Minimum spot size
            cv::Moments moments = cv::moments(contour);
            if (moments.m00 > 0) {
                cv::Point center(moments.m10 / moments.m00, moments.m01 / moments.m00);
                brownSpots.push_back(center);
            }
        }
    }
    
    return brownSpots;
}

static std::vector<cv::Point> detectYellowAreas(const cv::Mat& image, const cv::Mat& mask) {
    std::vector<cv::Point> yellowAreas;
    
    cv::Mat hsv;
    cv::cvtColor(image, hsv, cv::COLOR_BGR2HSV);
    
    // Yellow color range in HSV
    cv::Mat yellowMask;
    cv::inRange(hsv, cv::Scalar(15, 50, 50), cv::Scalar(35, 255, 255), yellowMask);
    
    // Apply plant mask
    cv::Mat maskedYellow;
    cv::bitwise_and(yellowMask, mask, maskedYellow);
    
    std::vector<std::vector<cv::Point>> contours;
    cv::findContours(maskedYellow, contours, cv::RETR_EXTERNAL, cv::CHAIN_APPROX_SIMPLE);
    
    for (const auto& contour : contours) {
        double area = cv::contourArea(contour);
        if (area > 50.0) {  // Minimum area for yellow regions
            cv::Moments moments = cv::moments(contour);
            if (moments.m00 > 0) {
                cv::Point center(moments.m10 / moments.m00, moments.m01 / moments.m00);
                yellowAreas.push_back(center);
            }
        }
    }
    
    return yellowAreas;
}

// ========== END ENHANCED ANALYSIS ==========

PlantType classifyPlantType(const cv::Mat &roi, const cv::Rect &bbox, double areaPixels, double scalePxPerCm) {
    // Primary classification based on size - smaller threshold for better accuracy
    if (areaPixels < 2500.0) {  // Reduced from 5000 to reduce false positives
        return PlantType::SPROUT;
    }
    
    // Secondary classification based on physical height if scale is known
    if (scalePxPerCm > 0.0) {
        double heightCm = bbox.height / scalePxPerCm;
        if (heightCm < 5.0) {  // Reduced from 8.0 cm for better sprout detection
            return PlantType::SPROUT;
        }
    }
    
    // Advanced morphological analysis for sprout characteristics
    cv::Mat gray, binary;
    cv::cvtColor(roi, gray, cv::COLOR_BGR2GRAY);
    cv::threshold(gray, binary, 0, 255, cv::THRESH_BINARY_INV + cv::THRESH_OTSU);
    
    // Find contours in the ROI
    std::vector<std::vector<cv::Point>> contours;
    cv::findContours(binary, contours, cv::RETR_EXTERNAL, cv::CHAIN_APPROX_SIMPLE);
    
    if (!contours.empty()) {
        // Find the largest contour (main plant structure)
        auto largestContour = *std::max_element(contours.begin(), contours.end(),
            [](const std::vector<cv::Point>& a, const std::vector<cv::Point>& b) {
                return cv::contourArea(a) < cv::contourArea(b);
            });
        
        // Analyze structure for sprout characteristics
        double solidity = calculateSolidity(largestContour);
        cv::RotatedRect ellipse = cv::fitEllipse(largestContour);
        double aspectRatio = std::max(ellipse.size.width, ellipse.size.height) / 
                           std::min(ellipse.size.width, ellipse.size.height);
        
        // Sprout characteristics:
        // - High solidity (compact, simple shape)
        // - Lower aspect ratio (not too elongated)
        // - Smaller overall area
        if (solidity > 0.75 && aspectRatio < 3.0 && areaPixels < 4000.0) {
            return PlantType::SPROUT;
        }
        
        // Check for single origin point characteristic of sprouts
        cv::Point2f bottomCenter(bbox.x + bbox.width/2.0f, bbox.y + bbox.height);
        
        // Create skeleton to analyze branching structure
        cv::Mat skeleton = skeletonize(binary);
        
        // Count connection points near the bottom (root area)
        int originConnections = 0;
        int searchRadius = std::min(bbox.height, bbox.width) / 4;
        cv::Point localBottom(binary.cols/2, binary.rows - 5); // Bottom center in ROI coords
        
        for (int y = std::max(0, localBottom.y - searchRadius); 
             y < std::min(binary.rows, localBottom.y + searchRadius); y++) {
            for (int x = std::max(0, localBottom.x - searchRadius); 
                 x < std::min(binary.cols, localBottom.x + searchRadius); x++) {
                if (skeleton.at<uchar>(y, x) > 0) {
                    // Count neighbors to identify connection points
                    int neighbors = 0;
                    for (int dy = -1; dy <= 1; dy++) {
                        for (int dx = -1; dx <= 1; dx++) {
                            if (dy == 0 && dx == 0) continue;
                            int ny = y + dy, nx = x + dx;
                            if (ny >= 0 && ny < skeleton.rows && nx >= 0 && nx < skeleton.cols) {
                                if (skeleton.at<uchar>(ny, nx) > 0) neighbors++;
                            }
                        }
                    }
                    if (neighbors >= 2) originConnections++;
                }
            }
        }
        
        // Sprouts typically have fewer origin connection points (simpler structure)
        if (originConnections <= 3 && areaPixels < 3500.0) {
            return PlantType::SPROUT;
        }
    }
    
    return PlantType::PLANT;
}

GrowthStage determineGrowthStage(PlantType type, const cv::Mat &roi, double areaPixels, int leafCount) {
    if (type == PlantType::SPROUT) {
        if (leafCount <= 2) return GrowthStage::COTYLEDON;
        if (leafCount <= 4) return GrowthStage::FIRST_LEAVES;
        return GrowthStage::EARLY_VEGETATIVE;
    } else {
        if (areaPixels < 10000) return GrowthStage::VEGETATIVE;
        // TODO: Add more sophisticated analysis for flowering/fruiting detection
        return GrowthStage::VEGETATIVE;
    }
}

static double calculateHealthScore(const cv::Scalar &meanColor, PlantType type) {
    // Extract BGR values
    double b = meanColor[0], g = meanColor[1], r = meanColor[2];
    
    // Calculate green bias (healthy plants are more green)
    double greenBias = g - (r + b) / 2.0;
    
    // Base health score calculation
    double healthScore = 60.0 + (greenBias / 2.0);
    
    // Adjust for plant type
    if (type == PlantType::SPROUT) {
        // Sprouts are more sensitive to color variations
        healthScore = healthScore * 0.9 + 10.0; // Slightly lower base
    }
    
    return std::max(0.0, std::min(100.0, healthScore));
}

PlantInstance processSprout(const cv::Mat &frame, const cv::Rect &bbox, const std::vector<cv::Point> &contour, double scalePxPerCm) {
    PlantInstance instance;
    instance.type = PlantType::SPROUT;
    instance.boundingBox = bbox;
    instance.areaPixels = cv::contourArea(contour);
    instance.areaCm2 = (scalePxPerCm > 0.0) ? (instance.areaPixels / (scalePxPerCm * scalePxPerCm)) : 0.0;
    instance.heightCm = (scalePxPerCm > 0.0) ? (bbox.height / scalePxPerCm) : 0.0;
    instance.widthCm = (scalePxPerCm > 0.0) ? (bbox.width / scalePxPerCm) : 0.0;
    
    // Sprout-specific analysis with enhanced morphology
    cv::Rect roi = bbox & cv::Rect(0, 0, frame.cols, frame.rows);
    if (roi.width > 0 && roi.height > 0) {
        cv::Mat roiFrame = frame(roi);
        instance.meanColor = cv::mean(roiFrame);
        instance.cropImage = roiFrame.clone();

        // Calculate standard deviation of colors
        cv::Mat mean, stddev;
        cv::meanStdDev(roiFrame, mean, stddev);
        instance.stdColor = cv::Scalar(stddev.at<double>(0), stddev.at<double>(1), stddev.at<double>(2));

        // Create binary mask for morphological analysis
        cv::Mat binaryMask;
        cv::cvtColor(roiFrame, binaryMask, cv::COLOR_BGR2GRAY);
        cv::threshold(binaryMask, binaryMask, 0, 255, cv::THRESH_BINARY + cv::THRESH_OTSU);
        
        // ========== ENHANCED MORPHOLOGICAL ANALYSIS (PlantCV-INSPIRED) ==========
        MorphologyAnalyzer analyzer;
        MorphologyMetrics morphology = analyzer.analyzeMorphology(binaryMask, roiFrame);
        
        // Transfer morphological metrics to instance
        instance.solidity = morphology.solidity;
        instance.eccentricity = morphology.eccentricity;
        instance.circularity = morphology.circularity;
        instance.compactness = morphology.compactness;
        instance.aspectRatio = morphology.aspect_ratio;
        instance.extent = morphology.extent;
        instance.perimeterCm = (scalePxPerCm > 0.0) ? (morphology.perimeter / scalePxPerCm) : 0.0;
        
        // Skeleton analysis results
        instance.branchCount = morphology.branch_points;
        instance.tipCount = morphology.tip_points;
        instance.pathLengthCm = (scalePxPerCm > 0.0) ? (morphology.total_path_length / scalePxPerCm) : 0.0;
        instance.longestPathCm = (scalePxPerCm > 0.0) ? (morphology.longest_path / scalePxPerCm) : 0.0;
        
        // Calculate centroid
        if (morphology.centroid.x > 0 && morphology.centroid.y > 0) {
            instance.centroid = cv::Point2f(morphology.centroid.x + roi.x, morphology.centroid.y + roi.y);
        } else {
            instance.centroid = calculateCentroid(contour);
        }
        
        // Calculate orientation from morphology
        if (morphology.min_area_rect.size.width > 0) {
            instance.orientation = morphology.min_area_rect.angle;
        } else {
            instance.orientation = calculateOrientation(contour);
        }
        
        // Calculate convexity
        instance.convexity = calculateConvexity(contour);
        
        // Enhanced color analysis
        instance.ndvi = calculateNDVI(roiFrame, binaryMask);
        instance.exg = calculateEXG(roiFrame, binaryMask);
        
        // Basic disease detection for sprouts
        instance.brownSpotLocations = detectBrownSpots(roiFrame, binaryMask);
        instance.yellowAreaLocations = detectYellowAreas(roiFrame, binaryMask);
        instance.brownSpotCount = static_cast<int>(instance.brownSpotLocations.size());
        instance.yellowAreaCount = static_cast<int>(instance.yellowAreaLocations.size());
    }
    
    instance.leafCount = countLeavesInContour(frame, contour, true);
    instance.petalCount = 0; // Sprouts don't have petals
    instance.budCount = 0;   // Sprouts don't have buds
    instance.fruitCount = 0; // Sprouts don't have fruits
    
    instance.healthScore = calculateHealthScore(instance.meanColor, PlantType::SPROUT);
    // Adjust health score based on disease indicators
    double diseaseReduction = (instance.brownSpotCount * 5.0) + (instance.yellowAreaCount * 3.0);
    instance.healthScore = std::max(0.0, instance.healthScore - diseaseReduction);
    
    instance.stage = determineGrowthStage(PlantType::SPROUT, frame(roi), instance.areaPixels, instance.leafCount);
    instance.classification = "sprout";
    instance.contour = contour;
    
    return instance;
}

PlantInstance processPlant(const cv::Mat &frame, const cv::Rect &bbox, const std::vector<cv::Point> &contour, double scalePxPerCm) {
    PlantInstance instance;
    instance.type = PlantType::PLANT;
    instance.boundingBox = bbox;
    instance.areaPixels = cv::contourArea(contour);
    instance.areaCm2 = (scalePxPerCm > 0.0) ? (instance.areaPixels / (scalePxPerCm * scalePxPerCm)) : 0.0;
    instance.heightCm = (scalePxPerCm > 0.0) ? (bbox.height / scalePxPerCm) : 0.0;
    instance.widthCm = (scalePxPerCm > 0.0) ? (bbox.width / scalePxPerCm) : 0.0;
    
    // Plant-specific analysis with comprehensive PlantCV-inspired morphology
    cv::Rect roi = bbox & cv::Rect(0, 0, frame.cols, frame.rows);
    if (roi.width > 0 && roi.height > 0) {
        cv::Mat roiFrame = frame(roi);
        instance.meanColor = cv::mean(roiFrame);
        instance.cropImage = roiFrame.clone();

        // Calculate standard deviation of colors
        cv::Mat mean, stddev;
        cv::meanStdDev(roiFrame, mean, stddev);
        instance.stdColor = cv::Scalar(stddev.at<double>(0), stddev.at<double>(1), stddev.at<double>(2));

        // Create binary mask for morphological analysis
        cv::Mat binaryMask;
        cv::cvtColor(roiFrame, binaryMask, cv::COLOR_BGR2GRAY);
        cv::threshold(binaryMask, binaryMask, 0, 255, cv::THRESH_BINARY + cv::THRESH_OTSU);
        
        // ========== COMPREHENSIVE MORPHOLOGICAL ANALYSIS (PlantCV-INSPIRED) ==========
        MorphologyAnalyzer analyzer;
        MorphologyMetrics morphology = analyzer.analyzeMorphology(binaryMask, roiFrame);
        
        // Transfer morphological metrics to instance
        instance.solidity = morphology.solidity;
        instance.eccentricity = morphology.eccentricity;
        instance.circularity = morphology.circularity;
        instance.compactness = morphology.compactness;
        instance.aspectRatio = morphology.aspect_ratio;
        instance.extent = morphology.extent;
        instance.perimeterCm = (scalePxPerCm > 0.0) ? (morphology.perimeter / scalePxPerCm) : 0.0;
        
        // Skeleton analysis results for plant architecture
        instance.branchCount = morphology.branch_points;
        instance.tipCount = morphology.tip_points;
        instance.pathLengthCm = (scalePxPerCm > 0.0) ? (morphology.total_path_length / scalePxPerCm) : 0.0;
        instance.longestPathCm = (scalePxPerCm > 0.0) ? (morphology.longest_path / scalePxPerCm) : 0.0;
        
        // Use skeleton analysis for stem length estimation
        instance.stemLengthCm = instance.longestPathCm;
        
        // Calculate centroid from morphology
        if (morphology.centroid.x > 0 && morphology.centroid.y > 0) {
            instance.centroid = cv::Point2f(morphology.centroid.x + roi.x, morphology.centroid.y + roi.y);
        } else {
            instance.centroid = calculateCentroid(contour);
        }
        
        // Calculate orientation from morphology
        if (morphology.min_area_rect.size.width > 0) {
            instance.orientation = morphology.min_area_rect.angle;
        } else {
            instance.orientation = calculateOrientation(contour);
        }
        
        // Calculate convexity
        instance.convexity = calculateConvexity(contour);
        
        // Enhanced color analysis with vegetation indices
        instance.ndvi = calculateNDVI(roiFrame, binaryMask);
        instance.exg = calculateEXG(roiFrame, binaryMask);
        
        // Disease detection
        instance.brownSpotLocations = detectBrownSpots(roiFrame, binaryMask);
        instance.yellowAreaLocations = detectYellowAreas(roiFrame, binaryMask);
        instance.brownSpotCount = static_cast<int>(instance.brownSpotLocations.size());
        instance.yellowAreaCount = static_cast<int>(instance.yellowAreaLocations.size());
    }
    
    instance.leafCount = countLeavesInContour(frame, contour, false);
    // TODO: Implement petal, bud, and fruit detection for mature plants
    instance.petalCount = 0;
    instance.budCount = 0;
    instance.fruitCount = 0;
    
    instance.healthScore = calculateHealthScore(instance.meanColor, PlantType::PLANT);
    // Adjust health score based on disease indicators
    double diseaseReduction = (instance.brownSpotCount * 5.0) + (instance.yellowAreaCount * 3.0);
    instance.healthScore = std::max(0.0, instance.healthScore - diseaseReduction);
    
    instance.stage = determineGrowthStage(PlantType::PLANT, frame(roi), instance.areaPixels, instance.leafCount);
    instance.classification = "plant";
    instance.contour = contour;
    
    return instance;
}

PlantAnalysisResult analyzePlants(const cv::Mat &frameBgr, int thresholdValue, double scalePxPerCm) {
    auto start_time = std::chrono::high_resolution_clock::now();
    
    PlantAnalysisResult result;
    result.scalePxPerCm = scalePxPerCm;
    result.analysisTimestamp = getCurrentTimestamp();
    
    if (frameBgr.empty()) return result;

    // Create annotated frame
    result.annotatedFrame = frameBgr.clone();
    
    // HSV-based green segmentation
    cv::Mat hsv, mask, morph;
    cv::cvtColor(frameBgr, hsv, cv::COLOR_BGR2HSV);
    cv::inRange(hsv, cv::Scalar(25, 40, 40), cv::Scalar(85, 255, 255), mask);
    cv::morphologyEx(mask, morph, cv::MORPH_OPEN, cv::getStructuringElement(cv::MORPH_ELLIPSE, {3,3}));
    cv::morphologyEx(morph, morph, cv::MORPH_CLOSE, cv::getStructuringElement(cv::MORPH_ELLIPSE, {5,5}));

    std::vector<std::vector<cv::Point>> contours;
    watershedInstances(morph, contours);

    // Fallback to grayscale if no contours found
    if (contours.empty()) {
        cv::Mat gray, blurred, thresh;
        cv::cvtColor(frameBgr, gray, cv::COLOR_BGR2GRAY);
        cv::GaussianBlur(gray, blurred, cv::Size(5,5), 0);
        cv::threshold(blurred, thresh, thresholdValue, 255, cv::THRESH_BINARY | cv::THRESH_OTSU);
        cv::findContours(thresh, contours, cv::RETR_EXTERNAL, cv::CHAIN_APPROX_SIMPLE);
    }

    for (const auto &contour : contours) {
        double area = cv::contourArea(contour);
        if (area > 50.0) {
            cv::Rect bbox = cv::boundingRect(contour);
            
            // Classify and process based on type
            PlantType type = classifyPlantType(frameBgr(bbox & cv::Rect(0, 0, frameBgr.cols, frameBgr.rows)), bbox, area, scalePxPerCm);
            
            PlantInstance instance;
            if (type == PlantType::SPROUT) {
                instance = processSprout(frameBgr, bbox, contour, scalePxPerCm);
                result.sproutCount++;
                
                // Draw sprout annotation in light green
                cv::drawContours(result.annotatedFrame, std::vector<std::vector<cv::Point>>{contour}, -1, cv::Scalar(0, 255, 100), 2);
                cv::rectangle(result.annotatedFrame, bbox, cv::Scalar(0, 255, 100), 2);
                cv::putText(result.annotatedFrame, "SPROUT", cv::Point(bbox.x, bbox.y - 10), 
                          cv::FONT_HERSHEY_SIMPLEX, 0.5, cv::Scalar(0, 255, 100), 1);
            } else {
                instance = processPlant(frameBgr, bbox, contour, scalePxPerCm);
                result.plantCount++;
                
                // Draw plant annotation in dark green
                cv::drawContours(result.annotatedFrame, std::vector<std::vector<cv::Point>>{contour}, -1, cv::Scalar(0, 200, 0), 2);
                cv::rectangle(result.annotatedFrame, bbox, cv::Scalar(0, 200, 0), 2);
                cv::putText(result.annotatedFrame, "PLANT", cv::Point(bbox.x, bbox.y - 10), 
                          cv::FONT_HERSHEY_SIMPLEX, 0.5, cv::Scalar(0, 200, 0), 1);
            }
            
            result.instances.push_back(instance);
            result.totalAreaPixels += instance.areaPixels;
            result.totalAreaCm2 += instance.areaCm2;
        }
    }
    
    result.totalInstanceCount = static_cast<int>(result.instances.size());
    
    // Count sprouts and plants
    result.sproutCount = 0;
    result.plantCount = 0;
    double totalHealth = 0.0;
    for (const auto& instance : result.instances) {
        if (instance.type == PlantType::SPROUT) {
            result.sproutCount++;
        } else {
            result.plantCount++;
        }
        totalHealth += instance.healthScore;
    }
    
    // Calculate average health
    if (!result.instances.empty()) {
        result.averageHealth = totalHealth / result.instances.size();
    }
    
    // Calculate processing time
    auto end_time = std::chrono::high_resolution_clock::now();
    auto duration = std::chrono::duration_cast<std::chrono::milliseconds>(end_time - start_time);
    result.processingTimeMs = duration.count();
    
    return result;
}

// Legacy compatibility function
LeafAreaResult estimateLeafArea(const cv::Mat &frameBgr, int thresholdValue, double scalePxPerCm) {
    PlantAnalysisResult newResult = analyzePlants(frameBgr, thresholdValue, scalePxPerCm);
    
    // Convert to legacy format
    LeafAreaResult result;
    result.scalePxPerCm = scalePxPerCm;
    result.areaPixels = newResult.totalAreaPixels;
    result.areaCm2 = newResult.totalAreaCm2;
    result.contourCount = newResult.totalInstanceCount;
    result.totalLeafCount = 0;
    
    for (const auto &instance : newResult.instances) {
        result.perContourAreaPx.push_back(instance.areaPixels);
        result.perContourBBox.push_back(instance.boundingBox);
        result.contours.push_back(instance.contour);
        result.perContourLeafCount.push_back(instance.leafCount);
        result.totalLeafCount += instance.leafCount;
    }
    
    return result;
}

