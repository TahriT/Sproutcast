#include "leaf_area.hpp"
#include <opencv2/imgproc.hpp>

LeafAreaResult estimateLeafArea(const cv::Mat &frameBgr, int thresholdValue, double scalePxPerCm) {
    LeafAreaResult result{};
    if (frameBgr.empty()) return result;

    // 1) Try HSV green segmentation first
    cv::Mat hsv, mask, morph;
    cv::cvtColor(frameBgr, hsv, cv::COLOR_BGR2HSV);
    // Basic green range: adjust in future via config if needed
    // H in [25, 85], S>40, V>40
    cv::inRange(hsv, cv::Scalar(25, 40, 40), cv::Scalar(85, 255, 255), mask);
    cv::morphologyEx(mask, morph, cv::MORPH_OPEN, cv::getStructuringElement(cv::MORPH_ELLIPSE, {3,3}));
    cv::morphologyEx(morph, morph, cv::MORPH_CLOSE, cv::getStructuringElement(cv::MORPH_ELLIPSE, {5,5}));

    std::vector<std::vector<cv::Point>> contours;
    cv::findContours(morph, contours, cv::RETR_EXTERNAL, cv::CHAIN_APPROX_SIMPLE);

    // If nothing detected, fallback to grayscale Otsu
    if (contours.empty()) {
        cv::Mat gray, blurred, thresh;
        cv::cvtColor(frameBgr, gray, cv::COLOR_BGR2GRAY);
        cv::GaussianBlur(gray, blurred, cv::Size(5,5), 0);
        cv::threshold(blurred, thresh, thresholdValue, 255, cv::THRESH_BINARY | cv::THRESH_OTSU);
        cv::findContours(thresh, contours, cv::RETR_EXTERNAL, cv::CHAIN_APPROX_SIMPLE);
    }

    double totalArea = 0.0;
    std::vector<double> perArea;
    std::vector<cv::Rect> bboxes;
    std::vector<std::vector<cv::Point>> kept;
    for (const auto &c : contours) {
        double area = cv::contourArea(c);
        if (area > 50.0) {
            totalArea += area;
            perArea.push_back(area);
            bboxes.push_back(cv::boundingRect(c));
            kept.push_back(c);
        }
    }

    result.areaPixels = totalArea;
    result.scalePxPerCm = scalePxPerCm;
    result.areaCm2 = (scalePxPerCm > 0.0) ? (totalArea / (scalePxPerCm * scalePxPerCm)) : 0.0;
    result.contourCount = static_cast<int>(kept.size());
    result.perContourAreaPx = std::move(perArea);
    result.perContourBBox = std::move(bboxes);
    result.contours = std::move(kept);
    return result;
}

