#include "vision_processor.hpp"
#include <opencv2/opencv.hpp>
#include <nlohmann/json.hpp>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <iomanip>
#include <cmath>

using json = nlohmann::json;

VisionProcessor::VisionProcessor() 
    : frame_counter_(0), baseline_established_(false), debug_mode_(false) {
    
    // Create necessary directories
    std::filesystem::create_directories(data_dir_);
    std::filesystem::create_directories(ai_requests_dir_);
    std::filesystem::create_directories(ai_results_dir_);
    
    std::cout << "VisionProcessor initialized - consolidating OpenCV operations from Python to C++" << std::endl;
}

VisionProcessor::~VisionProcessor() {
    if (debug_mode_) {
        std::cout << "VisionProcessor processed " << frame_counter_ << " frames" << std::endl;
    }
}

VisionProcessor::BasicMetrics VisionProcessor::processBasicMetrics(const cv::Mat& frame) {
    auto start_time = std::chrono::high_resolution_clock::now();
    
    BasicMetrics metrics;
    metrics.frame_number = ++frame_counter_;
    metrics.timestamp = std::chrono::duration<double>(
        std::chrono::system_clock::now().time_since_epoch()).count();
    metrics.ai_analysis_required = false;
    
    if (frame.empty()) {
        metrics.processing_notes = "Empty frame received";
        return metrics;
    }
    
    try {
        // Step 1: Create optimized plant mask (consolidates Python duplicate)
        cv::Mat plant_mask = createPlantMask(frame, false);
        
        // Step 2: Comprehensive color analysis (replaces Python cv2 operations)
        metrics.color_analysis = analyzeColors(frame, plant_mask);
        
        // Step 3: Change detection (moved from Python to C++)
        if (!previous_frame_.empty()) {
            metrics.change_detection = detectChanges(frame, previous_frame_);
        } else {
            metrics.change_detection.significant_change = true; // First frame
            metrics.change_detection.change_reason = "first_frame";
        }
        
        // Step 4: Establish baseline if needed
        if (!baseline_established_) {
            if (establishBaseline(frame)) {
                baseline_metrics_ = metrics;
                metrics.processing_notes = "Baseline established";
            }
        }
        
        // Step 5: Determine if AI analysis is required
        bool force_ai = (frame_counter_ % 100 == 0); // Periodic AI analysis
        metrics.ai_analysis_required = metrics.change_detection.significant_change || force_ai;
        
        // Step 6: Debug output if enabled
        if (debug_mode_) {
            saveDebugImages(frame, plant_mask, std::to_string(frame_counter_));
            logMetrics(metrics);
        }
        
        // Update state for next frame
        frame.copyTo(previous_frame_);
        
        auto end_time = std::chrono::high_resolution_clock::now();
        auto duration_ms = std::chrono::duration_cast<std::chrono::milliseconds>(
            end_time - start_time).count();
        
        if (duration_ms > config_.max_processing_time_ms) {
            metrics.processing_notes += " WARNING: Processing time exceeded " + 
                                       std::to_string(config_.max_processing_time_ms) + "ms";
        }
        
    } catch (const cv::Exception& e) {
        metrics.processing_notes = "OpenCV error: " + std::string(e.what());
        std::cerr << "VisionProcessor OpenCV error: " << e.what() << std::endl;
    } catch (const std::exception& e) {
        metrics.processing_notes = "Processing error: " + std::string(e.what());
        std::cerr << "VisionProcessor error: " << e.what() << std::endl;
    }
    
    return metrics;
}

cv::Mat VisionProcessor::createPlantMask(const cv::Mat& frame, bool enhanced_sensitivity) {
    cv::Mat hsv, mask;
    
    // Convert to HSV color space (consolidating duplicate from Python)
    cv::cvtColor(frame, hsv, cv::COLOR_BGR2HSV);
    
    // Apply green range detection (unified from both C++ and Python implementations)
    cv::Scalar lower_bound = config_.hsv_lower_bound;
    cv::Scalar upper_bound = config_.hsv_upper_bound;
    
    if (enhanced_sensitivity) {
        // Broader range for sprout detection or challenging lighting
        lower_bound = cv::Scalar(20, 30, 30);
        upper_bound = cv::Scalar(90, 255, 255);
    }
    
    cv::inRange(hsv, lower_bound, upper_bound, mask);
    
    // Morphological operations (consolidating both implementations)
    if (config_.enable_morphological_processing) {
        cv::Mat kernel_open = cv::getStructuringElement(cv::MORPH_ELLIPSE, cv::Size(3, 3));
        cv::Mat kernel_close = cv::getStructuringElement(cv::MORPH_ELLIPSE, config_.morph_kernel_size);
        
        cv::morphologyEx(mask, mask, cv::MORPH_OPEN, kernel_open);
        cv::morphologyEx(mask, mask, cv::MORPH_CLOSE, kernel_close);
    }
    
    return mask;
}

VisionProcessor::ColorAnalysis VisionProcessor::analyzeColors(const cv::Mat& frame, const cv::Mat& mask) {
    ColorAnalysis analysis;
    
    // Count green pixels
    analysis.total_green_pixels = cv::countNonZero(mask);
    analysis.green_ratio = static_cast<double>(analysis.total_green_pixels) / 
                          (frame.rows * frame.cols);
    
    if (analysis.total_green_pixels == 0) {
        // No vegetation detected - return default values
        analysis.health_indicator = 0.0;
        return analysis;
    }
    
    // Multi-colorspace analysis (consolidating Python duplicate processing)
    cv::Mat hsv, lab;
    cv::cvtColor(frame, hsv, cv::COLOR_BGR2HSV);
    cv::cvtColor(frame, lab, cv::COLOR_BGR2Lab);
    
    // Calculate mean values for each color space
    analysis.mean_bgr = cv::mean(frame, mask);
    analysis.mean_hsv = cv::mean(hsv, mask);
    analysis.mean_lab = cv::mean(lab, mask);
    
    // Calculate standard deviations
    analysis.std_bgr = calculateColorStd(frame, mask, 0); // BGR
    analysis.std_hsv = calculateColorStd(hsv, mask, 1);   // HSV  
    analysis.std_lab = calculateColorStd(lab, mask, 2);   // LAB
    
    // Vegetation indices (moving from Python to C++ for performance)
    analysis.ndvi = calculateNDVI(frame, mask);
    analysis.exg = calculateEXG(frame, mask);
    
    // Health indicator calculation (unified from both implementations)
    double green_bias = analysis.mean_bgr[1] - (analysis.mean_bgr[0] + analysis.mean_bgr[2]) / 2.0;
    analysis.health_indicator = std::max(0.0, std::min(100.0, 60.0 + green_bias / 2.0));
    
    // Enhance health calculation with vegetation indices
    if (analysis.ndvi > 0.3) analysis.health_indicator += 10.0;
    if (analysis.exg > 0.2) analysis.health_indicator += 5.0;
    analysis.health_indicator = std::min(100.0, analysis.health_indicator);
    
    return analysis;
}

VisionProcessor::ChangeDetectionResult VisionProcessor::detectChanges(const cv::Mat& current_frame, const cv::Mat& previous_frame) {
    ChangeDetectionResult result;
    result.significant_change = false;
    
    if (current_frame.empty() || previous_frame.empty() || !baseline_established_) {
        result.significant_change = true;
        result.change_reason = "insufficient_data";
        return result;
    }
    
    try {
        // Create masks for both frames
        cv::Mat current_mask = createPlantMask(current_frame, false);
        cv::Mat previous_mask = createPlantMask(previous_frame, false);
        
        // Color analysis for both frames
        ColorAnalysis current_colors = analyzeColors(current_frame, current_mask);
        ColorAnalysis previous_colors = analyzeColors(previous_frame, previous_mask);
        
        // Calculate changes (replacing Python duplicate logic)
        result.hue_change = std::abs(current_colors.mean_hsv[0] - previous_colors.mean_hsv[0]);
        result.saturation_change = std::abs(current_colors.mean_hsv[1] - previous_colors.mean_hsv[1]);
        result.green_ratio_change = std::abs(current_colors.green_ratio - previous_colors.green_ratio);
        result.total_area_change = std::abs(current_colors.total_green_pixels - previous_colors.total_green_pixels) / 
                                  std::max(1.0, static_cast<double>(previous_colors.total_green_pixels));
        
        // Motion detection using OpenCV (new addition, was missing in Python)
        if (config_.enable_motion_detection) {
            result.motion_magnitude = calculateMotionMagnitude(current_frame, previous_frame);
        }
        
        // Check thresholds (moved from Python configuration)
        bool hue_significant = result.hue_change > config_.hue_threshold;
        bool sat_significant = result.saturation_change > config_.saturation_threshold;
        bool ratio_significant = result.green_ratio_change > config_.green_ratio_threshold;
        bool area_significant = result.total_area_change > config_.area_change_threshold;
        bool motion_significant = result.motion_magnitude > config_.motion_threshold;
        
        result.significant_change = hue_significant || sat_significant || ratio_significant || 
                                   area_significant || motion_significant;
        
        // Determine change reason for debugging
        if (result.significant_change) {
            if (hue_significant) result.change_reason += "hue_change ";
            if (sat_significant) result.change_reason += "saturation_change ";
            if (ratio_significant) result.change_reason += "green_ratio_change ";
            if (area_significant) result.change_reason += "area_change ";
            if (motion_significant) result.change_reason += "motion_detected ";
        } else {
            result.change_reason = "no_significant_change";
        }
        
    } catch (const cv::Exception& e) {
        std::cerr << "Change detection error: " << e.what() << std::endl;
        result.significant_change = true; // Fail safe - trigger AI analysis
        result.change_reason = "detection_error";
    }
    
    return result;
}

VisionProcessor::AIRequestData VisionProcessor::generateAIRequest(const cv::Mat& frame, const BasicMetrics& metrics) {
    AIRequestData request;
    
    // Save frame for AI processing
    std::string request_id = "frame_" + std::to_string(metrics.frame_number) + "_" + 
                            std::to_string(static_cast<int>(metrics.timestamp));
    std::string frame_path = ai_requests_dir_ + "/" + request_id + ".jpg";
    
    cv::imwrite(frame_path, frame, {cv::IMWRITE_JPEG_QUALITY, 95});
    
    request.image_path = frame_path;
    request.model_preference = "dpt_swin2"; // Default to best performing model
    request.depth_analysis_required = true;
    request.classification_required = true;
    request.confidence_threshold = 0.7;
    
    // Set ROI based on detected plant regions (optimization for AI processing)
    cv::Mat mask = createPlantMask(frame, false);
    std::vector<std::vector<cv::Point>> contours;
    cv::findContours(mask, contours, cv::RETR_EXTERNAL, cv::CHAIN_APPROX_SIMPLE);
    
    if (!contours.empty()) {
        // Find bounding box of all plant regions
        cv::Rect overall_bbox;
        for (const auto& contour : contours) {
            cv::Rect bbox = cv::boundingRect(contour);
            if (overall_bbox.area() == 0) {
                overall_bbox = bbox;
            } else {
                overall_bbox = overall_bbox | bbox; // Union of bounding boxes
            }
        }
        request.roi = overall_bbox;
    } else {
        request.roi = cv::Rect(0, 0, frame.cols, frame.rows); // Full frame
    }
    
    return request;
}

bool VisionProcessor::saveAIRequestData(const AIRequestData& request, const std::string& request_id) {
    try {
        json request_json = {
            {"image_path", request.image_path},
            {"model_preference", request.model_preference},
            {"depth_analysis_required", request.depth_analysis_required},
            {"classification_required", request.classification_required},
            {"confidence_threshold", request.confidence_threshold},
            {"roi", {
                {"x", request.roi.x},
                {"y", request.roi.y},
                {"width", request.roi.width},
                {"height", request.roi.height}
            }},
            {"timestamp", std::chrono::duration<double>(
                std::chrono::system_clock::now().time_since_epoch()).count()},
            {"request_id", request_id}
        };
        
        std::string request_file = ai_requests_dir_ + "/" + request_id + ".json";
        std::ofstream file(request_file);
        file << request_json.dump(2);
        file.close();
        
        // Create signal file for Python AI module
        std::string signal_file = data_dir_ + "/ai_analysis_" + request_id + ".signal";
        std::ofstream signal(signal_file);
        signal << request_id << std::endl;
        signal.close();
        
        return true;
        
    } catch (const std::exception& e) {
        std::cerr << "Error saving AI request: " << e.what() << std::endl;
        return false;
    }
}

json VisionProcessor::loadAIResults(const std::string& request_id) {
    try {
        std::string result_file = ai_results_dir_ + "/" + request_id + ".json";
        
        if (!std::filesystem::exists(result_file)) {
            return json(); // Empty result - AI processing not complete
        }
        
        std::ifstream file(result_file);
        json result;
        file >> result;
        file.close();
        
        // Clean up processed files
        std::filesystem::remove(result_file);
        std::string request_file = ai_requests_dir_ + "/" + request_id + ".json";
        std::filesystem::remove(request_file);
        
        return result;
        
    } catch (const std::exception& e) {
        std::cerr << "Error loading AI results: " << e.what() << std::endl;
        return json();
    }
}

void VisionProcessor::configureChangeDetection(double hue_threshold, double saturation_threshold, 
                                              double green_ratio_threshold, double area_change_threshold) {
    config_.hue_threshold = hue_threshold;
    config_.saturation_threshold = saturation_threshold;
    config_.green_ratio_threshold = green_ratio_threshold;
    config_.area_change_threshold = area_change_threshold;
    
    std::cout << "Change detection thresholds updated: H=" << hue_threshold 
              << ", S=" << saturation_threshold << ", GR=" << green_ratio_threshold
              << ", Area=" << area_change_threshold << std::endl;
}

void VisionProcessor::setDebugMode(bool enabled, const std::string& debug_output_path) {
    debug_mode_ = enabled;
    debug_path_ = debug_output_path;
    
    if (debug_mode_) {
        std::filesystem::create_directories(debug_path_);
        std::cout << "VisionProcessor debug mode enabled, output: " << debug_path_ << std::endl;
    }
}

// Private helper methods implementation

cv::Mat VisionProcessor::preprocessFrame(const cv::Mat& frame) {
    cv::Mat processed;
    
    // Optional preprocessing (blur, noise reduction)
    cv::GaussianBlur(frame, processed, cv::Size(3, 3), 0);
    
    return processed;
}

double VisionProcessor::calculateMotionMagnitude(const cv::Mat& current, const cv::Mat& previous) {
    cv::Mat diff, gray_current, gray_previous;
    
    cv::cvtColor(current, gray_current, cv::COLOR_BGR2GRAY);
    cv::cvtColor(previous, gray_previous, cv::COLOR_BGR2GRAY);
    
    cv::absdiff(gray_current, gray_previous, diff);
    
    cv::Scalar motion_sum = cv::sum(diff);
    return motion_sum[0];
}

cv::Scalar VisionProcessor::calculateColorStd(const cv::Mat& frame, const cv::Mat& mask, int color_space) {
    cv::Mat mean, stddev;
    cv::meanStdDev(frame, mean, stddev, mask);
    return cv::Scalar(stddev.at<double>(0), stddev.at<double>(1), stddev.at<double>(2));
}

double VisionProcessor::calculateNDVI(const cv::Mat& frame, const cv::Mat& mask) {
    std::vector<cv::Mat> bgr;
    cv::split(frame, bgr);
    
    cv::Mat nir = bgr[1]; // Use green channel as proxy for NIR
    cv::Mat red = bgr[2];
    
    cv::Mat nir_f, red_f;
    nir.convertTo(nir_f, CV_32F);
    red.convertTo(red_f, CV_32F);
    
    cv::Mat ndvi = (nir_f - red_f) / (nir_f + red_f + 1e-10);
    cv::Scalar mean_ndvi = cv::mean(ndvi, mask);
    
    return mean_ndvi[0];
}

double VisionProcessor::calculateEXG(const cv::Mat& frame, const cv::Mat& mask) {
    std::vector<cv::Mat> bgr;
    cv::split(frame, bgr);
    
    cv::Mat b_f, g_f, r_f;
    bgr[0].convertTo(b_f, CV_32F, 1.0/255.0);
    bgr[1].convertTo(g_f, CV_32F, 1.0/255.0);
    bgr[2].convertTo(r_f, CV_32F, 1.0/255.0);
    
    cv::Mat exg = 2.0 * g_f - r_f - b_f;
    cv::Scalar mean_exg = cv::mean(exg, mask);
    
    return mean_exg[0];
}

bool VisionProcessor::establishBaseline(const cv::Mat& frame) {
    if (frame.empty()) return false;
    
    frame.copyTo(baseline_frame_);
    baseline_established_ = true;
    
    std::cout << "VisionProcessor: Baseline established for change detection" << std::endl;
    return true;
}

void VisionProcessor::saveDebugImages(const cv::Mat& frame, const cv::Mat& mask, const std::string& suffix) {
    if (!debug_mode_) return;
    
    try {
        std::string frame_file = debug_path_ + "/frame_" + suffix + ".jpg";
        std::string mask_file = debug_path_ + "/mask_" + suffix + ".jpg";
        
        cv::imwrite(frame_file, frame);
        cv::imwrite(mask_file, mask);
        
        // Create overlay visualization
        cv::Mat overlay;
        cv::cvtColor(mask, overlay, cv::COLOR_GRAY2BGR);
        cv::addWeighted(frame, 0.7, overlay, 0.3, 0, overlay);
        
        std::string overlay_file = debug_path_ + "/overlay_" + suffix + ".jpg";
        cv::imwrite(overlay_file, overlay);
        
    } catch (const cv::Exception& e) {
        std::cerr << "Debug image save error: " << e.what() << std::endl;
    }
}

void VisionProcessor::logMetrics(const BasicMetrics& metrics) {
    if (!debug_mode_) return;
    
    try {
        std::string log_file = debug_path_ + "/metrics.log";
        std::ofstream log(log_file, std::ios::app);
        
        log << std::fixed << std::setprecision(3)
            << "Frame: " << metrics.frame_number
            << ", Time: " << metrics.timestamp
            << ", Green Ratio: " << metrics.color_analysis.green_ratio
            << ", Health: " << metrics.color_analysis.health_indicator
            << ", Change: " << (metrics.change_detection.significant_change ? "YES" : "NO")
            << ", Reason: " << metrics.change_detection.change_reason
            << ", AI Required: " << (metrics.ai_analysis_required ? "YES" : "NO")
            << std::endl;
        
        log.close();
        
    } catch (const std::exception& e) {
        std::cerr << "Metrics logging error: " << e.what() << std::endl;
    }
}
