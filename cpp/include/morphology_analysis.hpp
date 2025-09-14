#ifndef MORPHOLOGY_ANALYSIS_HPP
#define MORPHOLOGY_ANALYSIS_HPP

#include <opencv2/opencv.hpp>
#include <vector>

namespace PlantVision {
namespace Morphology {

struct MorphologyMetrics {
    // Size measurements
    double area;
    double perimeter;
    double solidity;
    double extent;
    double aspect_ratio;
    
    // Shape descriptors
    double convex_hull_area;
    int convex_hull_vertices;
    double eccentricity;
    double circularity;
    double roundness;
    
    // Skeleton analysis
    double total_path_length;
    double longest_path;
    int branch_points;
    int tip_points;
    std::vector<double> segment_lengths;
    std::vector<double> segment_angles;
    
    // Bounding measurements
    cv::Rect bounding_box;
    cv::RotatedRect min_area_rect;
    cv::Point2f centroid;
    cv::Point2f center_of_mass;
    
    // Advanced shape metrics
    double compactness;
    double form_factor;
    double shape_index;
};

class MorphologyAnalyzer {
public:
    MorphologyAnalyzer();
    ~MorphologyAnalyzer();
    
    // Core analysis functions (adapted from PlantCV concepts)
    MorphologyMetrics analyzeMorphology(const cv::Mat& mask, const cv::Mat& original_img);
    
    // Skeleton analysis (inspired by PlantCV morphology module)
    cv::Mat skeletonize(const cv::Mat& binary_mask);
    std::vector<cv::Point> findBranchPoints(const cv::Mat& skeleton);
    std::vector<cv::Point> findTipPoints(const cv::Mat& skeleton);
    std::vector<std::vector<cv::Point>> segmentSkeleton(const cv::Mat& skeleton);
    
    // Advanced shape analysis
    double calculateSolidity(const std::vector<cv::Point>& contour);
    double calculateEccentricity(const cv::RotatedRect& ellipse);
    double calculateCircularity(double area, double perimeter);
    double calculateCompactness(double area, double perimeter);
    
    // Plant-specific measurements
    double estimateLeafLength(const std::vector<cv::Point>& contour);
    double estimateLeafWidth(const std::vector<cv::Point>& contour);
    double calculateLeafAngle(const std::vector<cv::Point>& contour);
    
private:
    void prunesSkeleton(cv::Mat& skeleton, int iterations = 1);
    std::vector<double> calculateSegmentAngles(const std::vector<std::vector<cv::Point>>& segments);
    double calculatePathLength(const std::vector<cv::Point>& path);
};

} // namespace Morphology
} // namespace PlantVision

#endif // MORPHOLOGY_ANALYSIS_HPP
