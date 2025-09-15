#include "morphology_analysis.hpp"
#include <opencv2/opencv.hpp>
#include <cmath>
#include <algorithm>
#include <iostream>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

using namespace PlantVision::Morphology;

MorphologyAnalyzer::MorphologyAnalyzer() {
    // Initialize analyzer
}

MorphologyAnalyzer::~MorphologyAnalyzer() {
    // Cleanup
}

MorphologyMetrics MorphologyAnalyzer::analyzeMorphology(const cv::Mat& mask, const cv::Mat& original_img) {
    MorphologyMetrics metrics = {};
    
    if (mask.empty() || original_img.empty()) {
        std::cerr << "MorphologyAnalyzer: Empty input images" << std::endl;
        return metrics;
    }
    
    try {
        // Find main contour
        std::vector<std::vector<cv::Point>> contours;
        cv::findContours(mask, contours, cv::RETR_EXTERNAL, cv::CHAIN_APPROX_SIMPLE);
        
        if (contours.empty()) {
            return metrics;
        }
        
        // Find largest contour (main plant object)
        auto max_contour = std::max_element(contours.begin(), contours.end(),
            [](const std::vector<cv::Point>& a, const std::vector<cv::Point>& b) {
                return cv::contourArea(a) < cv::contourArea(b);
            });
        
        std::vector<cv::Point> main_contour = *max_contour;
        
        // === BASIC SIZE MEASUREMENTS ===
        metrics.area = cv::contourArea(main_contour);
        metrics.perimeter = cv::arcLength(main_contour, true);
        metrics.bounding_box = cv::boundingRect(main_contour);
        metrics.min_area_rect = cv::minAreaRect(main_contour);
        
        // Calculate centroid
        cv::Moments moments = cv::moments(main_contour);
        if (moments.m00 > 0) {
            metrics.centroid = cv::Point2f(moments.m10 / moments.m00, moments.m01 / moments.m00);
            metrics.center_of_mass = metrics.centroid;
        }
        
        // === SHAPE DESCRIPTORS ===
        // Convex hull analysis
        std::vector<cv::Point> convex_hull;
        cv::convexHull(main_contour, convex_hull);
        metrics.convex_hull_area = cv::contourArea(convex_hull);
        metrics.convex_hull_vertices = static_cast<int>(convex_hull.size());
        metrics.solidity = calculateSolidity(main_contour);
        
        // Aspect ratio and extent
        metrics.aspect_ratio = static_cast<double>(metrics.bounding_box.width) / 
                              static_cast<double>(metrics.bounding_box.height);
        metrics.extent = metrics.area / (metrics.bounding_box.width * metrics.bounding_box.height);
        
        // Eccentricity from fitted ellipse
        if (main_contour.size() >= 5) {
            cv::RotatedRect ellipse = cv::fitEllipse(main_contour);
            metrics.eccentricity = calculateEccentricity(ellipse);
        }
        
        // Circularity and roundness
        metrics.circularity = calculateCircularity(metrics.area, metrics.perimeter);
        metrics.roundness = (4.0 * M_PI * metrics.area) / (metrics.perimeter * metrics.perimeter);
        
        // Compactness and form factor
        metrics.compactness = calculateCompactness(metrics.area, metrics.perimeter);
        metrics.form_factor = (4.0 * M_PI * metrics.area) / (metrics.perimeter * metrics.perimeter);
        metrics.shape_index = metrics.perimeter / std::sqrt(metrics.area);
        
        // === SKELETON ANALYSIS (PlantCV-inspired) ===
        cv::Mat skeleton = skeletonize(mask);
        std::vector<cv::Point> branch_points = findBranchPoints(skeleton);
        std::vector<cv::Point> tip_points = findTipPoints(skeleton);
        std::vector<std::vector<cv::Point>> segments = segmentSkeleton(skeleton);
        
        metrics.branch_points = static_cast<int>(branch_points.size());
        metrics.tip_points = static_cast<int>(tip_points.size());
        
        // Calculate segment lengths and angles
        metrics.segment_lengths.clear();
        for (const auto& segment : segments) {
            double length = calculatePathLength(segment);
            metrics.segment_lengths.push_back(length);
            metrics.total_path_length += length;
        }
        
        if (!metrics.segment_lengths.empty()) {
            metrics.longest_path = *std::max_element(metrics.segment_lengths.begin(), 
                                                   metrics.segment_lengths.end());
        }
        
        metrics.segment_angles = calculateSegmentAngles(segments);
        
    } catch (const cv::Exception& e) {
        std::cerr << "MorphologyAnalyzer OpenCV error: " << e.what() << std::endl;
    } catch (const std::exception& e) {
        std::cerr << "MorphologyAnalyzer error: " << e.what() << std::endl;
    }
    
    return metrics;
}

cv::Mat MorphologyAnalyzer::skeletonize(const cv::Mat& binary_mask) {
    if (binary_mask.empty()) return cv::Mat();
    
    cv::Mat skeleton = cv::Mat::zeros(binary_mask.size(), CV_8UC1);
    cv::Mat temp, eroded;
    cv::Mat element = cv::getStructuringElement(cv::MORPH_CROSS, cv::Size(3, 3));
    
    binary_mask.copyTo(temp);
    
    int iterations = 0;
    int max_iterations = 100; // Prevent infinite loops
    
    do {
        cv::erode(temp, eroded, element);
        cv::Mat opening;
        cv::morphologyEx(eroded, opening, cv::MORPH_OPEN, element);
        cv::Mat subset = eroded - opening;
        cv::bitwise_or(skeleton, subset, skeleton);
        eroded.copyTo(temp);
        
        iterations++;
        if (iterations > max_iterations) {
            std::cerr << "Skeletonization exceeded maximum iterations" << std::endl;
            break;
        }
        
    } while (cv::countNonZero(temp) > 0);
    
    // Optional: Prune short spurious branches
    prunesSkeleton(skeleton, 2);
    
    return skeleton;
}

std::vector<cv::Point> MorphologyAnalyzer::findBranchPoints(const cv::Mat& skeleton) {
    std::vector<cv::Point> branch_points;
    
    if (skeleton.empty()) return branch_points;
    
    // Create kernel for neighbor counting (8-connectivity)
    cv::Mat kernel = (cv::Mat_<int>(3, 3) << 
        1, 1, 1,
        1, 0, 1,
        1, 1, 1);
    
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
                branch_points.push_back(cv::Point(x, y));
            }
        }
    }
    
    return branch_points;
}

std::vector<cv::Point> MorphologyAnalyzer::findTipPoints(const cv::Mat& skeleton) {
    std::vector<cv::Point> tip_points;
    
    if (skeleton.empty()) return tip_points;
    
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
                tip_points.push_back(cv::Point(x, y));
            }
        }
    }
    
    return tip_points;
}

std::vector<std::vector<cv::Point>> MorphologyAnalyzer::segmentSkeleton(const cv::Mat& skeleton) {
    std::vector<std::vector<cv::Point>> segments;
    
    if (skeleton.empty()) return segments;
    
    // Find contours in the skeleton
    std::vector<std::vector<cv::Point>> contours;
    cv::findContours(skeleton, contours, cv::RETR_EXTERNAL, cv::CHAIN_APPROX_NONE);
    
    // Each contour represents a skeleton segment
    for (const auto& contour : contours) {
        if (contour.size() > 5) { // Minimum segment size
            segments.push_back(contour);
        }
    }
    
    return segments;
}

double MorphologyAnalyzer::calculateSolidity(const std::vector<cv::Point>& contour) {
    if (contour.empty()) return 0.0;
    
    double area = cv::contourArea(contour);
    std::vector<cv::Point> hull;
    cv::convexHull(contour, hull);
    double hull_area = cv::contourArea(hull);
    
    return (hull_area > 0) ? (area / hull_area) : 0.0;
}

double MorphologyAnalyzer::calculateEccentricity(const cv::RotatedRect& ellipse) {
    double a = std::max(ellipse.size.width, ellipse.size.height) / 2.0;  // semi-major axis
    double b = std::min(ellipse.size.width, ellipse.size.height) / 2.0;  // semi-minor axis
    
    if (a == 0) return 0.0;
    
    double eccentricity = std::sqrt(1.0 - (b * b) / (a * a));
    return eccentricity;
}

double MorphologyAnalyzer::calculateCircularity(double area, double perimeter) {
    if (perimeter == 0) return 0.0;
    return (4.0 * M_PI * area) / (perimeter * perimeter);
}

double MorphologyAnalyzer::calculateCompactness(double area, double perimeter) {
    if (perimeter == 0) return 0.0;
    return std::sqrt((4.0 * area) / M_PI) / (perimeter / M_PI);
}

double MorphologyAnalyzer::estimateLeafLength(const std::vector<cv::Point>& contour) {
    if (contour.size() < 5) return 0.0;
    
    cv::RotatedRect rect = cv::minAreaRect(contour);
    return std::max(rect.size.width, rect.size.height);
}

double MorphologyAnalyzer::estimateLeafWidth(const std::vector<cv::Point>& contour) {
    if (contour.size() < 5) return 0.0;
    
    cv::RotatedRect rect = cv::minAreaRect(contour);
    return std::min(rect.size.width, rect.size.height);
}

double MorphologyAnalyzer::calculateLeafAngle(const std::vector<cv::Point>& contour) {
    if (contour.size() < 5) return 0.0;
    
    cv::RotatedRect rect = cv::minAreaRect(contour);
    return rect.angle;
}

// Private helper methods

void MorphologyAnalyzer::prunesSkeleton(cv::Mat& skeleton, int iterations) {
    if (skeleton.empty() || iterations <= 0) return;
    
    for (int iter = 0; iter < iterations; iter++) {
        std::vector<cv::Point> to_remove;
        
        for (int y = 1; y < skeleton.rows - 1; y++) {
            for (int x = 1; x < skeleton.cols - 1; x++) {
                if (skeleton.at<uchar>(y, x) == 0) continue;
                
                // Count neighbors
                int neighbors = 0;
                for (int dy = -1; dy <= 1; dy++) {
                    for (int dx = -1; dx <= 1; dx++) {
                        if (dy == 0 && dx == 0) continue;
                        if (skeleton.at<uchar>(y + dy, x + dx) > 0) {
                            neighbors++;
                        }
                    }
                }
                
                // Remove isolated pixels and short branches
                if (neighbors <= 1) {
                    to_remove.push_back(cv::Point(x, y));
                }
            }
        }
        
        // Remove marked pixels
        for (const auto& pt : to_remove) {
            skeleton.at<uchar>(pt.y, pt.x) = 0;
        }
    }
}

std::vector<double> MorphologyAnalyzer::calculateSegmentAngles(const std::vector<std::vector<cv::Point>>& segments) {
    std::vector<double> angles;
    
    for (const auto& segment : segments) {
        if (segment.size() < 2) {
            angles.push_back(0.0);
            continue;
        }
        
        // Calculate angle from first to last point
        cv::Point start = segment.front();
        cv::Point end = segment.back();
        
        double angle = std::atan2(end.y - start.y, end.x - start.x) * 180.0 / M_PI;
        angles.push_back(angle);
    }
    
    return angles;
}

double MorphologyAnalyzer::calculatePathLength(const std::vector<cv::Point>& path) {
    if (path.size() < 2) return 0.0;
    
    double length = 0.0;
    for (size_t i = 1; i < path.size(); i++) {
        cv::Point p1 = path[i-1];
        cv::Point p2 = path[i];
        double dist = std::sqrt(std::pow(p2.x - p1.x, 2) + std::pow(p2.y - p1.y, 2));
        length += dist;
    }
    
    return length;
}
