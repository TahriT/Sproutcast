#include "leaf_area.hpp"
#include <opencv2/imgproc.hpp>

LeafAreaResult estimateLeafArea(const cv::Mat &frameBgr, int thresholdValue, double scalePxPerCm) {
    LeafAreaResult result{};
    if (frameBgr.empty()) return result;

    cv::Mat gray, blurred, thresh;
    cv::cvtColor(frameBgr, gray, cv::COLOR_BGR2GRAY);
    cv::GaussianBlur(gray, blurred, cv::Size(5,5), 0);
    cv::threshold(blurred, thresh, thresholdValue, 255, cv::THRESH_BINARY | cv::THRESH_OTSU);

    std::vector<std::vector<cv::Point>> contours;
    cv::findContours(thresh, contours, cv::RETR_EXTERNAL, cv::CHAIN_APPROX_SIMPLE);

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

