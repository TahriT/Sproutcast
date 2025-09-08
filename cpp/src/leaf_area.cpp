#include "leaf_area.hpp"
#include <opencv2/imgproc.hpp>
#include <opencv2/imgcodecs.hpp>
#include <map>

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
    // Instance separation via watershed to avoid merging adjacent plants
    watershedInstances(morph, contours);

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

