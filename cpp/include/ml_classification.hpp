#ifndef ML_CLASSIFICATION_HPP
#define ML_CLASSIFICATION_HPP

#include <opencv2/opencv.hpp>
#include <opencv2/ml.hpp>
#include <map>
#include <string>
#include <vector>

namespace PlantVision {
namespace MachineLearning {

struct ClassificationResult {
    std::string predicted_class;
    double confidence;
    std::map<std::string, double> class_probabilities;
    cv::Mat classification_mask;
};

struct TrainingData {
    cv::Mat features;
    cv::Mat labels;
    std::vector<std::string> class_names;
    std::vector<std::string> feature_names;
};

// Naive Bayes Classifier (C++ implementation inspired by PlantCV)
class NaiveBayesClassifier {
public:
    NaiveBayesClassifier();
    ~NaiveBayesClassifier();
    
    // Training (similar to PlantCV naive_bayes_multiclass)
    bool trainFromImages(const std::vector<cv::Mat>& training_images, 
                        const std::vector<cv::Mat>& training_masks,
                        const std::vector<std::string>& class_labels);
    
    bool trainFromSamples(const std::string& samples_file);
    bool saveModel(const std::string& model_path);
    bool loadModel(const std::string& model_path);
    
    // Classification
    ClassificationResult classify(const cv::Mat& image);
    cv::Mat createClassificationMask(const cv::Mat& image);
    
private:
    cv::Ptr<cv::ml::NormalBayesClassifier> classifier;
    std::vector<std::string> class_names;
    
    // HSV-based feature extraction (like PlantCV)
    cv::Mat extractHSVFeatures(const cv::Mat& image);
    void calculateClassPDFs(const cv::Mat& features, const cv::Mat& labels);
};

// K-Means Classifier (C++ implementation inspired by PlantCV kmeans)
class KMeansClassifier {
public:
    KMeansClassifier();
    ~KMeansClassifier();
    
    // Training
    bool trainFromImages(const std::vector<cv::Mat>& training_images, 
                        int k_clusters, int patch_size = 10);
    bool saveModel(const std::string& model_path);
    bool loadModel(const std::string& model_path);
    
    // Classification
    ClassificationResult classify(const cv::Mat& image, int patch_size = 10);
    cv::Mat createLabeledImage(const cv::Mat& image);
    std::map<std::string, cv::Mat> createClassMasks(const cv::Mat& labeled_image, 
                                                   const std::vector<int>& category_list);
    
private:
    cv::Ptr<cv::ml::KMeans> kmeans_model;
    int num_clusters;
    cv::Mat cluster_centers;
    
    // Patch extraction (similar to PlantCV patch_extract)
    cv::Mat extractPatches(const cv::Mat& image, int patch_size, double sampling_rate = 1.0);
    cv::Mat patchesToFeatures(const cv::Mat& patches);
};

// Spatial Clustering (C++ implementation inspired by PlantCV spatial_clustering)
class SpatialClusterer {
public:
    enum Algorithm { DBSCAN, OPTICS };
    
    SpatialClusterer(Algorithm algo = DBSCAN);
    ~SpatialClusterer();
    
    // Spatial clustering
    struct ClusterResult {
        cv::Mat clustered_image;
        std::vector<cv::Mat> individual_masks;
        std::vector<cv::Rect> cluster_bounds;
        int num_clusters;
    };
    
    ClusterResult clusterSpatially(const cv::Mat& binary_mask, 
                                  int min_cluster_size = 5,
                                  double max_distance = -1.0);
    
private:
    Algorithm algorithm;
    
    // DBSCAN implementation for plant separation
    std::vector<std::vector<cv::Point>> dbscanClustering(const std::vector<cv::Point>& points,
                                                        double eps, int min_pts);
    
    // Convert clusters to masks
    std::vector<cv::Mat> clustersToMasks(const std::vector<std::vector<cv::Point>>& clusters,
                                        const cv::Size& image_size);
};

// Feature Extraction for ML (inspired by PlantCV analysis modules)
class FeatureExtractor {
public:
    FeatureExtractor();
    ~FeatureExtractor();
    
    // Comprehensive feature extraction
    struct PlantFeatures {
        // Morphological features
        std::vector<double> shape_features;
        // Color features  
        std::vector<double> color_features;
        // Texture features
        std::vector<double> texture_features;
        // Combined feature vector
        std::vector<double> all_features;
        std::vector<std::string> feature_names;
    };
    
    PlantFeatures extractAllFeatures(const cv::Mat& image, const cv::Mat& mask);
    
    // Individual feature types
    std::vector<double> extractShapeFeatures(const cv::Mat& mask);
    std::vector<double> extractColorFeatures(const cv::Mat& image, const cv::Mat& mask);
    std::vector<double> extractTextureFeatures(const cv::Mat& image, const cv::Mat& mask);
    
    // Create training dataset
    TrainingData createTrainingDataset(const std::vector<cv::Mat>& images,
                                      const std::vector<cv::Mat>& masks,
                                      const std::vector<std::string>& labels);
    
private:
    // Texture analysis using LBP, GLCM, etc.
    std::vector<double> calculateLBP(const cv::Mat& image, const cv::Mat& mask);
    std::vector<double> calculateGLCM(const cv::Mat& image, const cv::Mat& mask);
    std::vector<double> calculateHaralickFeatures(const cv::Mat& image, const cv::Mat& mask);
};

} // namespace MachineLearning
} // namespace PlantVision

#endif // ML_CLASSIFICATION_HPP
