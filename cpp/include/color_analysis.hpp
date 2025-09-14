#ifndef COLOR_ANALYSIS_HPP
#define COLOR_ANALYSIS_HPP

#include <opencv2/opencv.hpp>
#include <map>
#include <vector>

namespace PlantVision {
namespace ColorAnalysis {

struct ColorMetrics {
    // RGB statistics
    cv::Scalar mean_rgb;
    cv::Scalar std_rgb;
    cv::Scalar min_rgb;
    cv::Scalar max_rgb;
    
    // HSV statistics  
    cv::Scalar mean_hsv;
    cv::Scalar std_hsv;
    cv::Scalar min_hsv;
    cv::Scalar max_hsv;
    
    // LAB statistics (better for color differences)
    cv::Scalar mean_lab;
    cv::Scalar std_lab;
    
    // Advanced color features
    double color_diversity_index;
    double greenness_index;
    double yellowness_index;
    double chlorophyll_estimation;
    
    // Color histograms
    std::vector<cv::Mat> rgb_histograms;
    std::vector<cv::Mat> hsv_histograms;
    
    // Health indicators from color
    double health_score_color;
    bool stress_indicators;
};

struct ColorCard {
    cv::Rect location;
    std::vector<cv::Scalar> reference_colors;
    cv::Mat transformation_matrix;
    bool is_detected;
};

class ColorAnalyzer {
public:
    ColorAnalyzer();
    ~ColorAnalyzer();
    
    // Core color analysis (inspired by PlantCV analyze.color)
    ColorMetrics analyzeColor(const cv::Mat& image, const cv::Mat& mask, 
                             const std::string& colorspace = "all");
    
    // Color correction and normalization
    ColorCard detectColorCard(const cv::Mat& image);
    cv::Mat correctColors(const cv::Mat& image, const ColorCard& color_card);
    cv::Mat whiteBalance(const cv::Mat& image);
    cv::Mat normalizeIllumination(const cv::Mat& image);
    
    // Plant-specific color analysis
    double calculateGreenness(const cv::Mat& image, const cv::Mat& mask);
    double calculateChlorophyllIndex(const cv::Mat& image, const cv::Mat& mask);
    double detectStress(const cv::Mat& image, const cv::Mat& mask);
    
    // Disease detection through color
    std::vector<cv::Point> detectBrownSpots(const cv::Mat& image, const cv::Mat& mask);
    std::vector<cv::Point> detectYellowing(const cv::Mat& image, const cv::Mat& mask);
    double calculateDiseaseScore(const cv::Mat& image, const cv::Mat& mask);
    
    // Color-based classification
    cv::Mat createColorMask(const cv::Mat& image, const cv::Scalar& lower_bound, 
                           const cv::Scalar& upper_bound, const std::string& colorspace = "HSV");
    
    // Advanced color features for ML
    std::vector<double> extractColorFeatures(const cv::Mat& image, const cv::Mat& mask);
    
private:
    // Color space conversions
    cv::Mat convertToLAB(const cv::Mat& image);
    cv::Mat convertToHSV(const cv::Mat& image);
    
    // Statistical calculations
    cv::Scalar calculateMean(const cv::Mat& image, const cv::Mat& mask);
    cv::Scalar calculateStd(const cv::Mat& image, const cv::Mat& mask);
    
    // Color indices calculation
    double calculateNDVI(const cv::Mat& image, const cv::Mat& mask);
    double calculateEXG(const cv::Mat& image, const cv::Mat& mask);
    double calculateVARI(const cv::Mat& image, const cv::Mat& mask);
    
    // Reference color standards
    std::vector<cv::Scalar> standard_color_card_colors;
    void initializeColorStandards();
};

} // namespace ColorAnalysis
} // namespace PlantVision

#endif // COLOR_ANALYSIS_HPP
