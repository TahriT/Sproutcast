#pragma once

#include <opencv2/core.hpp>
#include <vector>

struct LeafAreaResult {
    double areaPixels;
    double areaCm2;
    double scalePxPerCm; // if known; 0 if unknown
    int contourCount;
    std::vector<double> perContourAreaPx;
    std::vector<cv::Rect> perContourBBox;
    std::vector<std::vector<cv::Point>> contours;
};

// Estimate leaf area using simple thresholding and contour detection.
// If scalePxPerCm is 0, areaCm2 will be 0 and only pixel area is provided.
LeafAreaResult estimateLeafArea(const cv::Mat &frameBgr, int thresholdValue, double scalePxPerCm);

